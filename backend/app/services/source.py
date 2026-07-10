from io import BytesIO

from app.config import ensure_project_root_on_path

ensure_project_root_on_path()

import pdfplumber

from source_router import get_source_text


def extract_text_from_bytes(filename: str, content: bytes) -> tuple[str, str, str, list[dict] | None]:
    """Extract text from uploaded file bytes (PDF or TXT)."""
    lower = filename.lower()

    if lower.endswith(".pdf"):
        text = ""
        with pdfplumber.open(BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text, "English", "en", None

    if lower.endswith(".txt"):
        return content.decode("utf-8"), "English", "en", None

    raise ValueError("Unsupported file type. Please upload a PDF or TXT file.")


def extract_source(
    source_type: str,
    youtube_url: str | None = None,
    web_url: str | None = None,
    filename: str | None = None,
    file_content: bytes | None = None,
) -> tuple[str, str, str, list[dict] | None]:
    if source_type == "youtube":
        return get_source_text("youtube", youtube_url=youtube_url)

    if source_type == "web":
        return get_source_text("web", web_url=web_url)

    if source_type == "document":
        if not filename or file_content is None:
            raise ValueError("Please upload a PDF or TXT file.")

        return extract_text_from_bytes(filename, file_content)

    raise ValueError("Invalid source type.")
