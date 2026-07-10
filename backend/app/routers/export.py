import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import ensure_project_root_on_path

ensure_project_root_on_path()

import importlib

import pdf_generator
from quiz_generation import generate_adaptive_quiz

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    AdaptiveQuizRequest,
    AdaptiveQuizResponse,
    QuizAttemptOut,
    QuizSubmitRequest,
    QuizSubmitResponse,
    QuizSubmitResult,
)
from app.services.session_service import (
    get_session,
    list_quiz_attempts,
    save_quiz_attempt,
    update_session_quiz,
)

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["export"])


def _topic_fallback(question_text: str, index: int) -> str:
    """Derive a weak-area label when older quizzes lack a topic field."""
    cleaned = re.sub(r"\$[^$]+\$", "", question_text or "")
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > 56:
        cleaned = cleaned[:56].rsplit(" ", 1)[0] + "..."
    return cleaned or f"Question {index + 1}"


def _collect_weak_topics(quiz: list, results: list[QuizSubmitResult]) -> list[str]:
    topics: list[str] = []
    for item in results:
        if item.is_correct:
            continue
        topic = item.topic
        if not topic and 0 <= item.question_index < len(quiz):
            question = quiz[item.question_index]
            if isinstance(question, dict):
                topic = question.get("topic")
        if not topic:
            topic = _topic_fallback(item.question, item.question_index)
        if topic and topic not in topics:
            topics.append(topic)
    return topics


def _missed_questions(results: list[QuizSubmitResult]) -> list[str]:
    return [item.question for item in results if not item.is_correct and item.question]


def _should_auto_practice(score: int, total: int) -> bool:
    return total > 0 and score < total


@router.get("/pdf")
def download_pdf(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Root-level modules are outside uvicorn's watch dir; reload so PDF font
    # fixes apply without a full server restart.
    pdf_mod = importlib.reload(pdf_generator)
    pdf_bytes = pdf_mod.generate_pdf(
        notes=session.notes,
        quiz=session.quiz,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="study_notes_and_quiz.pdf"'
        },
    )


@router.get("/quiz/attempts", response_model=list[QuizAttemptOut])
def get_quiz_attempts(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not get_session(db, session_id, current_user.id):
        raise HTTPException(status_code=404, detail="Session not found.")
    attempts = list_quiz_attempts(db, session_id, current_user.id)
    return [
        QuizAttemptOut(
            id=a.id,
            score=a.score,
            total=a.total,
            created_at=a.created_at,
        )
        for a in attempts
    ]


@router.post("/quiz/submit", response_model=QuizSubmitResponse)
def submit_quiz(
    session_id: int,
    payload: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    quiz = session.quiz or []
    results: list[QuizSubmitResult] = []
    score = 0

    for i, question in enumerate(quiz):
        if not isinstance(question, dict):
            continue
        user_answer = payload.answers.get(str(i))
        correct = question.get("answer", "")
        is_correct = user_answer == correct
        if is_correct:
            score += 1
        results.append(
            QuizSubmitResult(
                question_index=i,
                question=question.get("question", ""),
                user_answer=user_answer,
                correct_answer=correct,
                explanation=question.get("explanation", ""),
                is_correct=is_correct,
                topic=question.get("topic"),
                difficulty=question.get("difficulty"),
            )
        )

    save_quiz_attempt(
        db,
        session_id=session_id,
        user_id=current_user.id,
        score=score,
        total=len(results),
        answers=payload.answers,
    )

    weak_topics = _collect_weak_topics(quiz, results)
    should_practice = len(weak_topics) > 0
    practice_generated = False
    practice_quiz = None
    practice_error = None

    if payload.auto_practice and _should_auto_practice(score, len(results)) and should_practice:
        try:
            practice_quiz = generate_adaptive_quiz(
                session.notes,
                content_difficulty=session.content_difficulty or "intermediate",
                weak_topics=weak_topics,
                missed_questions=_missed_questions(results),
                output_language=session.output_language or "en",
            )
            updated = update_session_quiz(db, session_id, current_user.id, practice_quiz)
            if updated:
                practice_generated = True
        except Exception as exc:
            practice_error = str(exc)

    return QuizSubmitResponse(
        score=score,
        total=len(results),
        results=results,
        weak_topics=weak_topics,
        should_practice=should_practice,
        practice_generated=practice_generated,
        practice_quiz=practice_quiz,
        practice_error=practice_error,
    )


@router.post("/quiz/adaptive", response_model=AdaptiveQuizResponse)
def generate_adaptive_practice_quiz(
    session_id: int,
    payload: AdaptiveQuizRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        new_quiz = generate_adaptive_quiz(
            session.notes,
            content_difficulty=session.content_difficulty or "intermediate",
            weak_topics=payload.weak_topics,
            missed_questions=payload.missed_questions,
            output_language=session.output_language or "en",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Adaptive quiz generation failed: {exc}",
        ) from exc

    updated = update_session_quiz(db, session_id, current_user.id, new_quiz)
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found.")

    return AdaptiveQuizResponse(quiz=new_quiz, question_count=len(new_quiz))
