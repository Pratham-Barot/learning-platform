from unittest.mock import MagicMock, patch

import pytest

from transcript import get_transcript, main, print_transcript_from_url
from utils import extract_video_id


def test_extract_video_id_watch_url():
    assert (
        extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        == "dQw4w9WgXcQ"
    )


def test_extract_video_id_short_url():
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_invalid():
    assert extract_video_id("https://example.com/video") is None


def test_get_transcript_joins_segment_text():
    snippet_a = MagicMock(start=0.0, duration=1.0, text="Hello")
    snippet_b = MagicMock(start=1.0, duration=1.0, text=" world ")
    snippet_empty = MagicMock(start=2.0, duration=1.0, text="   ")

    transcript = MagicMock()
    transcript.language = "English"
    transcript.language_code = "en"
    transcript.fetch.return_value = [snippet_a, snippet_b, snippet_empty]

    transcript_list = MagicMock()
    transcript_list.__iter__ = MagicMock(return_value=iter([transcript]))

    api = MagicMock()
    api.list.return_value = transcript_list

    with patch("transcript.YouTubeTranscriptApi", return_value=api):
        result = get_transcript("abc123")

    assert result["text"] == "Hello world"
    assert result["language"] == "English"
    assert result["language_code"] == "en"
    assert len(result["segments"]) == 2
    api.list.assert_called_once_with("abc123")


def test_print_transcript_from_url_prints_text(capsys):
    fake = {
        "text": "Sample transcript",
        "language": "English",
        "language_code": "en",
        "segments": [],
    }
    with patch("transcript.get_transcript", return_value=fake) as mock_get:
        text = print_transcript_from_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

    assert text == "Sample transcript"
    mock_get.assert_called_once_with("dQw4w9WgXcQ")
    assert capsys.readouterr().out.strip() == "Sample transcript"


def test_print_transcript_from_url_rejects_invalid():
    with pytest.raises(ValueError, match="Invalid YouTube URL"):
        print_transcript_from_url("https://example.com/not-youtube")


def test_main_with_argv_prints_transcript(capsys):
    fake = {
        "text": "CLI transcript",
        "language": "English",
        "language_code": "en",
        "segments": [],
    }
    with patch("transcript.get_transcript", return_value=fake):
        code = main(["https://youtu.be/dQw4w9WgXcQ"])

    assert code == 0
    assert capsys.readouterr().out.strip() == "CLI transcript"


def test_main_prompts_for_url(capsys):
    fake = {
        "text": "Prompted transcript",
        "language": "English",
        "language_code": "en",
        "segments": [],
    }
    with (
        patch("transcript.input", return_value="https://youtu.be/dQw4w9WgXcQ"),
        patch("transcript.get_transcript", return_value=fake),
    ):
        code = main([])

    assert code == 0
    assert capsys.readouterr().out.strip() == "Prompted transcript"


def test_main_empty_url_returns_error(capsys):
    with patch("transcript.input", return_value="   "):
        code = main([])

    assert code == 1
    assert "required" in capsys.readouterr().err.lower()


def test_main_invalid_url_returns_error(capsys):
    code = main(["https://example.com/nope"])
    assert code == 1
    assert "invalid" in capsys.readouterr().err.lower()
