"""Supported output languages for notes, quiz, and chat."""

from typing import Literal

OutputLanguageCode = Literal["en", "hi"]

OUTPUT_LANGUAGES: dict[str, dict[str, str]] = {
    "en": {
        "code": "en",
        "name": "English",
        "native_name": "English",
    },
    "hi": {
        "code": "hi",
        "name": "Hindi",
        "native_name": "हिन्दी",
    },
}

DEFAULT_OUTPUT_LANGUAGE = "en"
SUPPORTED_OUTPUT_LANGUAGE_CODES = frozenset(OUTPUT_LANGUAGES.keys())


def normalize_output_language(code: str | None) -> str:
    if not code:
        return DEFAULT_OUTPUT_LANGUAGE
    normalized = code.strip().lower()
    if normalized in SUPPORTED_OUTPUT_LANGUAGE_CODES:
        return normalized
    return DEFAULT_OUTPUT_LANGUAGE


def output_language_name(code: str | None) -> str:
    normalized = normalize_output_language(code)
    return OUTPUT_LANGUAGES[normalized]["name"]


def output_language_instruction(code: str | None) -> str:
    """Prompt fragment telling the model which language to write in."""
    name = output_language_name(code)
    if normalize_output_language(code) == "en":
        return (
            f"Write the entire output in {name}. "
            "Keep technical terms, product names, and LaTeX math unchanged."
        )
    return (
        f"Write the entire output in {name} ({OUTPUT_LANGUAGES['hi']['native_name']}). "
        "Keep technical terms, English brand/library names, and LaTeX math unchanged. "
        "Do not mix languages except for those terms."
    )
