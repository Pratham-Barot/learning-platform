import threading
from typing import Callable, Optional, TypedDict

from langgraph.graph import END, StateGraph

from content_summarizer import prepare_source_for_notes
from difficulty_detection import detect_content_difficulty
from notes_generation import generate_notes
from output_languages import normalize_output_language
from quiz_generation import generate_quiz

_status_ctx = threading.local()


def _report_status(message: str) -> None:
    callback = getattr(_status_ctx, "callback", None)
    if callback:
        callback(message)


class StudyState(TypedDict):
    source_text: str
    source_segments: Optional[list]
    prepared_source_text: Optional[str]
    language: str
    language_code: str
    output_language: str
    notes: Optional[str]
    content_difficulty: str
    difficulty_reason: str
    quiz: Optional[list]
    status: str


def _content_for_notes(state: StudyState) -> str:
    return state.get("prepared_source_text") or state["source_text"]


def _ensure_prepared_content(state: StudyState) -> tuple[StudyState, str]:
    if state.get("prepared_source_text"):
        return state, state["prepared_source_text"]

    prepared = prepare_source_for_notes(
        state["source_text"],
        segments=state.get("source_segments"),
        language=state["language"],
        language_code=state["language_code"],
        output_language=state.get("output_language") or "en",
        on_status=_report_status,
    )
    updated_state = {**state, "prepared_source_text": prepared}
    return updated_state, prepared


def notes_generator_node(state: StudyState) -> StudyState:
    state, content = _ensure_prepared_content(state)
    output_lang = normalize_output_language(state.get("output_language"))
    notes = generate_notes(
        source_text=content,
        language=state["language"],
        language_code=state["language_code"],
        output_language=output_lang,
    )

    return {
        **state,
        "notes": notes,
        "status": "Generating study notes...",
    }


def difficulty_detector_node(state: StudyState) -> StudyState:
    state, content = _ensure_prepared_content(state)
    detection = detect_content_difficulty(content, state.get("notes"))

    return {
        **state,
        "content_difficulty": detection["level"],
        "difficulty_reason": detection["reason"],
        "status": f"Content classified as {detection['level']} level",
    }


def quiz_generator_node(state: StudyState) -> StudyState:
    difficulty = state.get("content_difficulty") or "intermediate"
    quiz = generate_quiz(
        state["notes"],
        content_difficulty=difficulty,
        output_language=state.get("output_language") or "en",
    )

    return {
        **state,
        "quiz": quiz,
        "status": "Quiz generated successfully!",
    }


def build_pipeline():
    graph = StateGraph(StudyState)

    graph.add_node("notes_generator", notes_generator_node)
    graph.add_node("difficulty_detector", difficulty_detector_node)
    graph.add_node("quiz_generator", quiz_generator_node)

    graph.set_entry_point("notes_generator")
    graph.add_edge("notes_generator", "difficulty_detector")
    graph.add_edge("difficulty_detector", "quiz_generator")

    graph.add_edge("quiz_generator", END)

    return graph.compile()


study_pipeline = build_pipeline()


def run_pipeline(
    source_text: str,
    language: str,
    language_code: str,
    source_segments: list[dict] | None = None,
    output_language: str = "en",
    on_status: Callable[[str], None] | None = None,
) -> dict:
    initial_state: StudyState = {
        "source_text": source_text,
        "source_segments": source_segments,
        "prepared_source_text": None,
        "language": language,
        "language_code": language_code,
        "output_language": normalize_output_language(output_language),
        "notes": None,
        "content_difficulty": "intermediate",
        "difficulty_reason": "",
        "quiz": None,
        "status": "Starting pipeline...",
    }

    _status_ctx.callback = on_status
    try:
        return study_pipeline.invoke(initial_state)
    finally:
        _status_ctx.callback = None
