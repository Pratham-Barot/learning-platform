from sqlalchemy.orm import Session

from app.models import ChatMessage, QuizAttempt, StudySession, User


def extract_title(notes: str) -> str:
    """Resolve a short session title for sidebar/history."""
    try:
        from notes_generation import generate_session_title

        return generate_session_title(notes)
    except Exception:
        try:
            from notes_generation import extract_title_from_notes

            return extract_title_from_notes(notes)
        except Exception:
            pass

    for line in notes.split("\n"):
        clean = line.strip().lstrip("#").strip()
        if clean and len(clean) > 3:
            return clean[:60]
    return "Untitled Notes"


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower()).first()


def create_user(db: Session, email: str, password_hash: str, full_name: str | None) -> User:
    user = User(
        email=email.lower().strip(),
        password_hash=password_hash,
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_session(
    db: Session,
    *,
    user_id: int,
    notes: str,
    quiz: list,
    source_type: str,
    source_ref: str,
    source_text: str,
    content_difficulty: str = "intermediate",
    output_language: str = "en",
) -> StudySession:
    session = StudySession(
        user_id=user_id,
        title=extract_title(notes),
        source_type=source_type,
        source_ref=source_ref,
        source_text=source_text,
        notes=notes,
        quiz=quiz,
        content_difficulty=content_difficulty,
        output_language=output_language or "en",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(db: Session, user_id: int) -> list[StudySession]:
    return (
        db.query(StudySession)
        .filter(StudySession.user_id == user_id)
        .order_by(StudySession.id.desc())
        .all()
    )


def get_session(db: Session, session_id: int, user_id: int) -> StudySession | None:
    return (
        db.query(StudySession)
        .filter(StudySession.id == session_id, StudySession.user_id == user_id)
        .first()
    )


def rename_session(
    db: Session, session_id: int, user_id: int, title: str
) -> StudySession | None:
    session = get_session(db, session_id, user_id)
    if not session:
        return None
    session.title = title.strip()
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: Session, session_id: int, user_id: int) -> bool:
    session = get_session(db, session_id, user_id)
    if not session:
        return False
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.query(QuizAttempt).filter(QuizAttempt.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return True


def list_chat_messages(db: Session, session_id: int) -> list[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.asc())
        .all()
    )


def delete_chat_messages_from(db: Session, session_id: int, message_id: int) -> None:
    db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.id >= message_id,
    ).delete()
    db.commit()


def add_chat_message(
    db: Session,
    session_id: int,
    role: str,
    content: str,
    source_label: str | None = None,
) -> ChatMessage:
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        source_label=source_label,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def save_quiz_attempt(
    db: Session,
    *,
    session_id: int,
    user_id: int,
    score: int,
    total: int,
    answers: dict,
) -> QuizAttempt:
    attempt = QuizAttempt(
        session_id=session_id,
        user_id=user_id,
        score=score,
        total=total,
        answers=answers,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def list_quiz_attempts(db: Session, session_id: int, user_id: int) -> list[QuizAttempt]:
    return (
        db.query(QuizAttempt)
        .filter(QuizAttempt.session_id == session_id, QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.id.desc())
        .all()
    )


def update_session_quiz(db: Session, session_id: int, user_id: int, quiz: list) -> StudySession | None:
    session = get_session(db, session_id, user_id)
    if not session:
        return None
    session.quiz = quiz
    db.commit()
    db.refresh(session)
    return session
