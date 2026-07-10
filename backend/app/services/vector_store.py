from pathlib import Path

from app.config import ensure_project_root_on_path

ensure_project_root_on_path()

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import CHROMA_PATH
from chatbot import embed_question, retrieve_chunks

_chroma_client = None


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _chroma_client


def _notes_collection_name(session_id: int) -> str:
    return f"notes_{session_id}"


def _legacy_transcript_collection_name(session_id: int) -> str:
    return f"transcript_{session_id}"


def build_vector_store(session_id: int, notes: str):
    """Embed study notes only. Transcript is stored in Postgres but not embedded for chat."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chroma_client = get_chroma_client()
    notes_name = _notes_collection_name(session_id)
    legacy_transcript_name = _legacy_transcript_collection_name(session_id)

    for name in (notes_name, legacy_transcript_name):
        try:
            chroma_client.delete_collection(name)
        except Exception:
            pass

    from chatbot import client as gemini_client

    notes_collection = chroma_client.create_collection(
        name=notes_name,
        metadata={"hnsw:space": "cosine"},
    )
    for i, chunk in enumerate(splitter.split_text(notes)):
        embedding = gemini_client.models.embed_content(
            model="gemini-embedding-2",
            contents=chunk,
        ).embeddings[0].values
        notes_collection.add(
            ids=[str(i)],
            documents=[chunk],
            embeddings=[embedding],
        )

    return notes_collection


def get_notes_collection(session_id: int):
    chroma_client = get_chroma_client()
    return chroma_client.get_collection(_notes_collection_name(session_id))


def ensure_vector_store(session_id: int, notes: str):
    try:
        return get_notes_collection(session_id)
    except Exception:
        return build_vector_store(session_id, notes)


def get_source_for_session(
    session_id: int,
    notes: str,
    question: str,
    fallback_threshold: float = 0.5,
):
    """
    Notes-first RAG:
    1. Search embedded notes chunks
    2. If no good match, fall back to direct Gemini (no transcript search)
    """
    notes_collection = ensure_vector_store(session_id, notes)
    question_embedding = embed_question(question)

    notes_context, notes_distance = retrieve_chunks(
        notes_collection, question_embedding
    )
    if notes_distance <= fallback_threshold:
        return "notes", notes_context, question_embedding

    return "general", None, question_embedding
