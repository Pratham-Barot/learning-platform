import pdfplumber
from transcript import get_transcript
from utils import extract_video_id
from web_extractor import extract_text_from_url, is_educational_content


# ─────────────────────────────────────────────
# Document extraction
# ─────────────────────────────────────────────

def extract_text_from_document(uploaded_file):
    """
    Extracts plain text from an uploaded PDF or TXT file.
    """
    if uploaded_file.name.endswith(".pdf"):
        text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    elif uploaded_file.name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8")

    else:
        raise ValueError("Unsupported file type. Please upload a PDF or TXT file.")


# ─────────────────────────────────────────────
# Unified source router
# ─────────────────────────────────────────────

def get_source_text(
    input_type,
    youtube_url=None,
    uploaded_file=None,
    web_url=None
):
    """
    Returns (source_text, language, language_code) for any input type.

    input_type options:
      "youtube"  → extract transcript from YouTube URL
      "document" → extract text from uploaded PDF/TXT
      "web"      → scrape text from an article/blog URL,
                   with educational content check
    """

    if input_type == "youtube":
        if not youtube_url:
            raise ValueError("YouTube URL is required.")

        video_id = extract_video_id(youtube_url)
        if video_id is None:
            raise ValueError("Invalid YouTube URL.")

        transcript = get_transcript(video_id)
        return (
            transcript["text"],
            transcript["language"],
            transcript["language_code"],
            transcript.get("segments"),
        )

    elif input_type == "document":
        if not uploaded_file:
            raise ValueError("Please upload a PDF or TXT file.")

        text = extract_text_from_document(uploaded_file)
        return text, "English", "en", None

    elif input_type == "web":
        if not web_url:
            raise ValueError("Please enter a URL.")

        # Block YouTube URLs from the web path
        if "youtube.com" in web_url or "youtu.be" in web_url:
            raise ValueError(
                "This looks like a YouTube link. "
                "Please use the 'YouTube Link' option instead."
            )

        # Extract text from the URL
        text = extract_text_from_url(web_url)

        # Check if content is educational
        allowed, reason = is_educational_content(text, web_url)

        if not allowed:
            raise ValueError(
                f"This link was rejected: {reason}\n\n"
                "Only educational content is allowed — tutorials, articles, "
                "documentation, research, or any content a student would study."
            )

        return text, "English", "en", None

    else:
        raise ValueError("Invalid input type.")