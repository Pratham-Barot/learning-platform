import os

PHASE_DURATION_SECONDS = int(os.getenv("PHASE_DURATION_SECONDS", "3600"))
LONG_VIDEO_PHASE_DURATION_SECONDS = int(
    os.getenv("LONG_VIDEO_PHASE_DURATION_SECONDS", "1800")
)
LONG_VIDEO_PHASE_THRESHOLD_HOURS = float(
    os.getenv("LONG_VIDEO_PHASE_THRESHOLD_HOURS", "15")
)
PHASE_CHAR_SIZE = int(os.getenv("PHASE_CHAR_SIZE", "50000"))
MAP_REDUCE_CHAR_THRESHOLD = int(os.getenv("MAP_REDUCE_CHAR_THRESHOLD", "30000"))

MAX_RUNNING_OUTLINE_CHARS = int(os.getenv("MAX_RUNNING_OUTLINE_CHARS", "2000"))
SKELETON_THRESHOLD_HOURS = float(os.getenv("SKELETON_THRESHOLD_HOURS", "10"))
USE_ROLLING_CONTEXT = os.getenv("USE_ROLLING_CONTEXT", "true").lower() in {
    "1",
    "true",
    "yes",
}


def should_use_map_reduce(text: str) -> bool:
    return len(text.strip()) >= MAP_REDUCE_CHAR_THRESHOLD


def estimate_total_hours(segments: list[dict] | None) -> float | None:
    """Estimate lecture duration from transcript segment timestamps."""
    if not segments:
        return None

    last_start = 0.0
    last_duration = 0.0
    for segment in segments:
        start = float(segment.get("start", 0))
        duration = float(segment.get("duration", 0))
        if start >= last_start:
            last_start = start
            last_duration = duration

    total_seconds = last_start + last_duration
    if total_seconds <= 0:
        return None
    return total_seconds / 3600.0


def estimate_phase_count(
    text: str,
    segments: list[dict] | None,
    *,
    phase_seconds: int | None = None,
) -> int:
    """Rough phase count before splitting (for choosing phase duration)."""
    seconds = phase_seconds or PHASE_DURATION_SECONDS
    if segments:
        total_hours = estimate_total_hours(segments)
        if total_hours is not None and total_hours > 0:
            return max(1, int((total_hours * 3600) // seconds) + 1)

    return max(1, (len(text.strip()) // PHASE_CHAR_SIZE) + 1)


def effective_phase_seconds(
    text: str,
    segments: list[dict] | None,
) -> int:
    """
    Use 1-hour chunks by default; switch to shorter chunks for very long videos.
    """
    total_hours = estimate_total_hours(segments)
    if total_hours is not None and total_hours >= LONG_VIDEO_PHASE_THRESHOLD_HOURS:
        return LONG_VIDEO_PHASE_DURATION_SECONDS

    if total_hours is None:
        estimated_phases = estimate_phase_count(text, segments)
        threshold_phases = int(
            (LONG_VIDEO_PHASE_THRESHOLD_HOURS * 3600) / PHASE_DURATION_SECONDS
        )
        if estimated_phases >= threshold_phases:
            return LONG_VIDEO_PHASE_DURATION_SECONDS

    return PHASE_DURATION_SECONDS


def should_build_skeleton(
    phase_count: int,
    segments: list[dict] | None,
) -> bool:
    total_hours = estimate_total_hours(segments)
    if total_hours is not None:
        return total_hours >= SKELETON_THRESHOLD_HOURS
    threshold_phases = int((SKELETON_THRESHOLD_HOURS * 3600) / PHASE_DURATION_SECONDS)
    return phase_count >= threshold_phases


def split_by_time_segments(
    segments: list[dict],
    phase_seconds: int = PHASE_DURATION_SECONDS,
) -> list[str]:
    """Group transcript snippets into fixed-duration phases (default 1 hour)."""
    if not segments:
        return []

    phases: list[str] = []
    current_parts: list[str] = []
    phase_end = float(phase_seconds)

    for segment in segments:
        start = float(segment.get("start", 0))
        text = str(segment.get("text", "")).strip()
        if not text:
            continue

        while start >= phase_end:
            if current_parts:
                phases.append(" ".join(current_parts))
                current_parts = []
            phase_end += float(phase_seconds)

        current_parts.append(text)

    if current_parts:
        phases.append(" ".join(current_parts))

    return [phase for phase in phases if phase.strip()]


def split_by_char_size(text: str, chunk_size: int = PHASE_CHAR_SIZE) -> list[str]:
    """Split plain text into roughly equal character chunks for documents/web pages."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return [chunk for chunk in splitter.split_text(text) if chunk.strip()]


def split_into_phases(
    text: str,
    segments: list[dict] | None = None,
    *,
    phase_seconds: int | None = None,
) -> list[str]:
    seconds = phase_seconds or effective_phase_seconds(text, segments)
    if segments:
        time_phases = split_by_time_segments(segments, phase_seconds=seconds)
        if time_phases:
            return time_phases
    return split_by_char_size(text)
