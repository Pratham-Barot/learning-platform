from content_chunking import (
    MAP_REDUCE_CHAR_THRESHOLD,
    LONG_VIDEO_PHASE_DURATION_SECONDS,
    PHASE_DURATION_SECONDS,
    SKELETON_THRESHOLD_HOURS,
    effective_phase_seconds,
    estimate_phase_count,
    estimate_total_hours,
    should_build_skeleton,
    should_use_map_reduce,
    split_by_char_size,
    split_by_time_segments,
    split_into_phases,
)
from content_summarizer import parse_phase_response


def test_should_use_map_reduce():
    assert not should_use_map_reduce("a" * (MAP_REDUCE_CHAR_THRESHOLD - 1))
    assert should_use_map_reduce("a" * MAP_REDUCE_CHAR_THRESHOLD)


def test_split_by_time_segments_groups_ten_minute_blocks():
    segments = [
        {"start": 0, "duration": 2, "text": "Intro"},
        {"start": 599, "duration": 2, "text": "End of part one"},
        {"start": 601, "duration": 2, "text": "Start part two"},
    ]
    phases = split_by_time_segments(segments, phase_seconds=600)
    assert len(phases) == 2
    assert "Intro" in phases[0]
    assert "End of part one" in phases[0]
    assert "Start part two" in phases[1]


def test_split_into_phases_prefers_timestamps():
    text = "full transcript text"
    segments = [
        {"start": 0, "duration": 1, "text": "A"},
        {"start": 700, "duration": 1, "text": "B"},
    ]
    phases = split_into_phases(text, segments, phase_seconds=600)
    assert phases == ["A", "B"]


def test_split_by_char_size_returns_multiple_chunks():
    text = "word " * 5000
    phases = split_by_char_size(text, chunk_size=1000)
    assert len(phases) > 1


def test_estimate_total_hours_from_segments():
    segments = [
        {"start": 0, "duration": 100, "text": "A"},
        {"start": 36000, "duration": 1200, "text": "B"},
    ]
    hours = estimate_total_hours(segments)
    assert hours is not None
    assert 10.0 < hours < 11.0


def test_effective_phase_seconds_uses_shorter_chunks_for_long_videos():
    segments = [
        {"start": 0, "duration": 60, "text": "A"},
        {"start": 16 * 3600, "duration": 60, "text": "B"},
    ]
    seconds = effective_phase_seconds("x" * 100_000, segments)
    assert seconds == LONG_VIDEO_PHASE_DURATION_SECONDS


def test_effective_phase_seconds_default_for_medium_videos():
    segments = [
        {"start": 0, "duration": 60, "text": "A"},
        {"start": 5 * 3600, "duration": 60, "text": "B"},
    ]
    seconds = effective_phase_seconds("x" * 100_000, segments)
    assert seconds == PHASE_DURATION_SECONDS


def test_should_build_skeleton_for_long_videos():
    segments = [
        {"start": 0, "duration": 60, "text": "A"},
        {"start": 11 * 3600, "duration": 60, "text": "B"},
    ]
    assert should_build_skeleton(6, segments) is True


def test_should_not_build_skeleton_for_medium_videos():
    segments = [
        {"start": 0, "duration": 60, "text": "A"},
        {"start": 4 * 3600, "duration": 60, "text": "B"},
    ]
    assert should_build_skeleton(4, segments) is False


def test_estimate_phase_count_without_segments():
    text = "a" * 120_000
    assert estimate_phase_count(text, None) >= 2


def test_parse_phase_response_extracts_summary_and_outline():
    raw = """---SUMMARY---
- Topic A
- Topic B

---OUTLINE---
Topics covered:
- Topic A
- Topic B
"""
    summary, outline = parse_phase_response(raw)
    assert "Topic A" in summary
    assert "Topics covered" in outline


def test_parse_phase_response_fallback_to_full_text():
    raw = "Plain summary without markers"
    summary, outline = parse_phase_response(raw)
    assert summary == raw
    assert outline == ""
