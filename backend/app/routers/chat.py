import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import ensure_project_root_on_path
from app.database import SessionLocal, get_db
from app.dependencies import get_current_user
from app.models import ChatMessage, User

ensure_project_root_on_path()

from app.schemas import ChatMessageOut, ChatRequest
from app.services.session_service import (
    add_chat_message,
    delete_chat_messages_from,
    get_session,
    list_chat_messages,
)
from app.services.vector_store import get_source_for_session
from chatbot import build_memory_context, stream_context_answer, stream_direct_answer

router = APIRouter(prefix="/api/sessions/{session_id}/chat", tags=["chat"])

SOURCE_LABELS = {
    "notes": "Answered from Notes",
    "general": "Answered by Gemini",
}


@router.get("", response_model=list[ChatMessageOut])
def get_chat_history(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not get_session(db, session_id, current_user.id):
        raise HTTPException(status_code=404, detail="Session not found.")
    messages = list_chat_messages(db, session_id)
    return [
        ChatMessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            source_label=m.source_label,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.post("/stream")
def chat_stream(
    session_id: int,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if payload.edit_message_id is not None:
        target = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.id == payload.edit_message_id,
                ChatMessage.session_id == session_id,
                ChatMessage.role == "user",
            )
            .first()
        )
        if not target:
            raise HTTPException(status_code=404, detail="Message not found.")
        delete_chat_messages_from(db, session_id, payload.edit_message_id)

    add_chat_message(db, session_id, "user", payload.message)

    history_rows = list_chat_messages(db, session_id)
    chat_history = [{"role": m.role, "content": m.content} for m in history_rows]
    summary_cache: dict = {}

    source, context, _ = get_source_for_session(
        session_id,
        session.notes,
        payload.message,
    )

    memory_context = build_memory_context(chat_history, summary_cache)
    output_language = getattr(session, "output_language", None) or "en"

    def event_generator():
        full_response = ""
        try:
            stream = (
                stream_context_answer(
                    context,
                    payload.message,
                    memory_context,
                    output_language=output_language,
                )
                if source == "notes"
                else stream_direct_answer(
                    payload.message,
                    memory_context,
                    output_language=output_language,
                )
            )

            for chunk in stream:
                full_response += chunk
                yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"

            label = SOURCE_LABELS.get(source, "")
            final_text = f"{full_response}\n\n*{label}*" if label else full_response

            save_db = SessionLocal()
            try:
                add_chat_message(
                    save_db,
                    session_id,
                    "assistant",
                    final_text,
                    source_label=label or None,
                )
            finally:
                save_db.close()

            yield f"data: {json.dumps({'type': 'done', 'source': source, 'content': final_text})}\n\n"
        except Exception as exc:
            message = str(exc)
            if "429" in message or "RESOURCE_EXHAUSTED" in message:
                message = (
                    "Gemini API rate limit reached. Please wait a minute and try again."
                )
            elif "API key" in message.lower():
                message = "Invalid or missing Gemini API key. Check your .env file."
            yield f"data: {json.dumps({'type': 'error', 'message': message})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
