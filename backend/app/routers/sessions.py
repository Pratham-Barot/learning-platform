from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import SessionDetail, SessionRename, SessionSummary
from app.services.session_service import (
    delete_session,
    get_session,
    list_sessions,
    rename_session,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionSummary])
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = list_sessions(db, current_user.id)
    return [
        SessionSummary(
            id=s.id,
            title=s.title,
            source_type=s.source_type,
            source_ref=s.source_ref,
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=SessionDetail)
def get_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return SessionDetail(
        id=session.id,
        title=session.title,
        source_type=session.source_type,
        source_ref=session.source_ref,
        notes=session.notes,
        quiz=session.quiz,
        content_difficulty=session.content_difficulty or "intermediate",
        output_language=session.output_language or "en",
        created_at=session.created_at,
    )


@router.patch("/{session_id}", response_model=SessionSummary)
def patch_session(
    session_id: int,
    payload: SessionRename,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = rename_session(db, session_id, current_user.id, payload.title)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return SessionSummary(
        id=session.id,
        title=session.title,
        source_type=session.source_type,
        source_ref=session.source_ref,
        created_at=session.created_at,
    )


@router.delete("/{session_id}")
def remove_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not delete_session(db, session_id, current_user.id):
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"ok": True}
