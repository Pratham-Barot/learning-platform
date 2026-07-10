import os
import re
from google import genai
from dotenv import load_dotenv

from output_languages import (
    normalize_output_language,
    output_language_instruction,
    output_language_name,
)

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

NOTES_FORMAT_RULES = """
Format rules (follow strictly):
- First line MUST be exactly one markdown H1 with a SHORT topic title only (2-6 words).
  Good: # Quantum Computing
  Bad: # Understanding the Foundations of Quantum Computing and Its Applications
- Use numbered section headings as ## 1. Introduction, ## 2. Key Concepts, etc.
- For ALL mathematical notation use LaTeX:
  - Inline math: $N$, $O(\\sqrt{N})$, $\\alpha$
  - Display math on its own line: $$E = mc^2$$
- Do NOT write formulas as plain text like O(sqrt(N)) or $N$ without proper LaTeX inside the dollars.
"""


def generate_notes(
    source_text,
    language="English",
    language_code="en",
    output_language="en",
):
    """
    Generates study notes from plain text.
    Works the same whether source_text came from a YouTube transcript
    or an uploaded document.
    output_language controls the language of the generated notes (en/hi).
    """
    out_code = normalize_output_language(output_language)
    out_name = output_language_name(out_code)
    out_instruction = output_language_instruction(out_code)

    source_note = ""
    if language_code != "en" and language_code != out_code:
        source_note = (
            f"\nThe following content is written in {language}. "
            f"First understand the content, then write the notes in {out_name}.\n"
        )
    elif language_code != "en" and language_code == out_code:
        source_note = (
            f"\nThe following content is written in {language}. "
            f"Generate the notes in {out_name}.\n"
        )

    prompt = f"""
You are an expert study assistant.

Generate well-structured study notes from the following content.

{out_instruction}
{source_note}
Your notes should include:
1. Title (short, 2-6 words only)
2. Introduction
3. Key Concepts
4. Detailed Explanation
5. Important Points
6. Summary

{NOTES_FORMAT_RULES}
- Section headings may be written in {out_name}, but keep the same six-part structure.

Content:
{source_text}
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )

    return response.text


def generate_session_title(notes: str) -> str:
    """Return a short ChatGPT-style title (2-6 words) for history sidebar."""
    excerpt = notes[:2000].strip()
    prompt = f"""
Based on these study notes, reply with ONLY a short chat-style title: 2-6 words, main topic keyword.
Examples: Quantum Computing, Photosynthesis Basics, React Hooks, Grover's Algorithm
Prefer English for the title when possible so it stays short and clear in the sidebar.
No quotes, no punctuation at the end, no full sentences, no markdown.

Notes:
{excerpt}
"""
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
        )
        title = (response.text or "").strip().strip('"\'`#')
        title = re.sub(r"^#+\s*", "", title)
        title = re.sub(r"\s+", " ", title)
        if 2 <= len(title) <= 80:
            return title[:80]
    except Exception:
        pass
    return extract_title_from_notes(notes)


def extract_title_from_notes(notes: str) -> str:
    """Fallback: parse the first short H1 or first meaningful line."""
    for line in notes.split("\n"):
        clean = line.strip().lstrip("#").strip()
        if clean and len(clean) > 3:
            words = clean.split()
            if len(words) > 8:
                clean = " ".join(words[:6])
            return clean[:60]
    return "Untitled Notes"
