import sys

from youtube_transcript_api import YouTubeTranscriptApi

from utils import extract_video_id


def get_transcript(video_id):
    api = YouTubeTranscriptApi()

    transcript_list = api.list(video_id)
    transcript = next(iter(transcript_list))
    fetched = transcript.fetch()

    segments = [
        {
            "start": float(snippet.start),
            "duration": float(snippet.duration),
            "text": snippet.text.strip(),
        }
        for snippet in fetched
        if snippet.text and snippet.text.strip()
    ]

    transcript_text = " ".join(segment["text"] for segment in segments)

    return {
        "text": transcript_text,
        "language": transcript.language,
        "language_code": transcript.language_code,
        "segments": segments,
    }


def print_transcript_from_url(youtube_url: str) -> str:
    """Fetch and print the transcript for a YouTube URL. Returns the text."""
    video_id = extract_video_id(youtube_url.strip())
    if video_id is None:
        raise ValueError("Invalid YouTube URL.")

    result = get_transcript(video_id)
    print(result["text"])
    return result["text"]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        url = args[0]
    else:
        url = input("Enter YouTube link: ").strip()

    if not url:
        print("Error: YouTube URL is required.", file=sys.stderr)
        return 1

    try:
        print_transcript_from_url(url)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
