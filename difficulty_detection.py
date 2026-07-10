import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

VALID_LEVELS = {"beginner", "intermediate", "advanced"}


def detect_content_difficulty(
    source_text: str,
    notes: str | None = None,
) -> dict[str, str]:
    """
    Classify study material complexity for quiz calibration.
    Returns {"level": "beginner"|"intermediate"|"advanced", "reason": "..."}.
    """
    notes_excerpt = ""
    if notes:
        notes_excerpt = notes[:4000]

    prompt = f"""
You are an educational content analyst.

Classify the difficulty of the study material below for a student audience.

Choose exactly one level:
- beginner: introductory concepts, minimal prerequisites, simple vocabulary
- intermediate: assumes foundational knowledge, moderate technical depth
- advanced: specialized, dense, or graduate-level material

Return ONLY valid JSON, no markdown:
{{"level": "intermediate", "reason": "One sentence explaining why."}}

Source excerpt:
{source_text[:6000]}

Notes excerpt:
{notes_excerpt}
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )

    raw = response.text.strip()
    if raw.startswith("```json"):
        raw = raw.replace("```json", "").replace("```", "").strip()
    elif raw.startswith("```"):
        raw = raw.replace("```", "").strip()

    result = json.loads(raw)
    level = str(result.get("level", "intermediate")).lower().strip()
    if level not in VALID_LEVELS:
        level = "intermediate"

    reason = str(result.get("reason", "")).strip()
    return {"level": level, "reason": reason}
