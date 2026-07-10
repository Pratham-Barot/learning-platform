import importlib
import threading
import uuid
from typing import Any

from app.config import ensure_project_root_on_path

ensure_project_root_on_path()

from app.database import SessionLocal
from app.services.session_service import create_session
from app.services.source import extract_source
from app.services.vector_store import build_vector_store

_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _load_run_pipeline():
    """Reload root-level pipeline modules so code changes apply without restarting uvicorn."""
    import content_chunking
    import content_summarizer
    import difficulty_detection
    import notes_generation
    import output_languages
    import pipeline
    import quiz_generation

    for module in (
        content_chunking,
        content_summarizer,
        difficulty_detection,
        notes_generation,
        output_languages,
        quiz_generation,
        pipeline,
    ):
        importlib.reload(module)

    return pipeline.run_pipeline


def _update(job_id: str, **fields):
    with _lock:
        _jobs[job_id].update(fields)


def get_job(job_id: str, user_id: int | None = None) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        if user_id is not None and job.get("user_id") != user_id:
            return None
        return dict(job)


def start_generation_job(
    *,
    user_id: int,
    source_type: str,
    youtube_url: str | None = None,
    web_url: str | None = None,
    filename: str | None = None,
    file_content: bytes | None = None,
    output_language: str = "en",
) -> str:
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "user_id": user_id,
            "status": "pending",
            "step": "Queued",
            "error": None,
            "session_id": None,
        }

    thread = threading.Thread(
        target=_run_job,
        args=(
            job_id,
            user_id,
            source_type,
            youtube_url,
            web_url,
            filename,
            file_content,
            output_language,
        ),
        daemon=True,
    )
    thread.start()
    return job_id


def _run_job(
    job_id: str,
    user_id: int,
    source_type: str,
    youtube_url: str | None,
    web_url: str | None,
    filename: str | None,
    file_content: bytes | None,
    output_language: str = "en",
):
    db = SessionLocal()
    try:
        _update(job_id, status="processing", step="Reading source content...")
        source_text, language, language_code, source_segments = extract_source(
            source_type=source_type,
            youtube_url=youtube_url,
            web_url=web_url,
            filename=filename,
            file_content=file_content,
        )

        _update(job_id, step="Running AI pipeline (summarize → notes → quiz)...")
        run_pipeline = _load_run_pipeline()
        result = run_pipeline(
            source_text,
            language,
            language_code,
            source_segments=source_segments,
            output_language=output_language,
            on_status=lambda step: _update(job_id, step=step),
        )

        notes = (result.get("notes") or "").strip()
        quiz = result.get("quiz")
        if not notes:
            raise ValueError("Notes generation returned empty content.")
        if not quiz or not isinstance(quiz, list):
            raise ValueError("Quiz generation failed.")

        source_ref = youtube_url or web_url or filename or ""

        _update(job_id, step="Saving session and building knowledge base...")
        session = create_session(
            db,
            user_id=user_id,
            notes=notes,
            quiz=quiz,
            source_type=source_type,
            source_ref=source_ref,
            source_text=source_text,
            content_difficulty=result.get("content_difficulty") or "intermediate",
            output_language=output_language,
        )

        build_vector_store(session.id, notes)

        _update(
            job_id,
            status="completed",
            step="Done",
            session_id=session.id,
        )
    except Exception as exc:
        _update(job_id, status="failed", step="Failed", error=str(exc))
    finally:
        db.close()
