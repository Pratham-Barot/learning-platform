from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


SourceType = Literal["youtube", "document", "web"]
JobStatus = Literal["pending", "processing", "completed", "failed"]
OutputLanguage = Literal["en", "hi"]


class SessionSummary(BaseModel):
    id: int
    title: str
    source_type: str
    source_ref: str | None
    created_at: datetime


class SessionDetail(BaseModel):
    id: int
    title: str
    source_type: str
    source_ref: str | None
    notes: str
    quiz: list[dict[str, Any]]
    content_difficulty: str | None = "intermediate"
    output_language: str | None = "en"
    created_at: datetime


class SessionRename(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class GenerateResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    step: str | None = None
    error: str | None = None
    session_id: int | None = None


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    source_label: str | None = None
    created_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    edit_message_id: int | None = None


class QuizSubmitRequest(BaseModel):
    answers: dict[str, str]
    auto_practice: bool = False


class QuizSubmitResult(BaseModel):
    question_index: int
    question: str
    user_answer: str | None
    correct_answer: str
    explanation: str
    is_correct: bool
    topic: str | None = None
    difficulty: str | None = None


class QuizSubmitResponse(BaseModel):
    score: int
    total: int
    results: list[QuizSubmitResult]
    weak_topics: list[str] = []
    should_practice: bool = False
    practice_generated: bool = False
    practice_quiz: list[dict[str, Any]] | None = None
    practice_error: str | None = None


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class QuizAttemptOut(BaseModel):
    id: int
    score: int
    total: int
    created_at: datetime


class AdaptiveQuizRequest(BaseModel):
    weak_topics: list[str] = Field(min_length=1)
    missed_questions: list[str] = Field(default_factory=list)


class AdaptiveQuizResponse(BaseModel):
    quiz: list[dict[str, Any]]
    question_count: int
