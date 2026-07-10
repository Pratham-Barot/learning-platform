import json
import os
import re

from dotenv import load_dotenv
from google import genai

from output_languages import (
    normalize_output_language,
    output_language_instruction,
    output_language_name,
)

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

DIFFICULTY_GUIDANCE = {
    "beginner": (
        "Target a beginner audience. Use clear wording, fundamental concepts, "
        "and avoid trick questions. Most questions should be easy to medium."
    ),
    "intermediate": (
        "Target an intermediate audience. Mix recall and application questions "
        "with moderate complexity."
    ),
    "advanced": (
        "Target an advanced audience. Emphasize deep understanding, edge cases, "
        "and multi-step reasoning. Most questions should be medium to hard."
    ),
}


def _quiz_prompt(
    notes: str,
    content_difficulty: str,
    extra_rules: str = "",
    output_language: str = "en",
) -> str:
    guidance = DIFFICULTY_GUIDANCE.get(content_difficulty, DIFFICULTY_GUIDANCE["intermediate"])
    out_code = normalize_output_language(output_language)
    out_name = output_language_name(out_code)
    out_instruction = output_language_instruction(out_code)
    return f"""
You are an expert quiz generator.

Generate a quiz ONLY from the study notes provided below.

Content difficulty level: {content_difficulty}
Calibration: {guidance}

Requirements:

- Generate exactly 10 multiple-choice questions.
- Each question must have exactly 4 options.
- Only one option should be correct.
- Include the correct answer.
- Include a short explanation for every answer.
- Include a short "topic" label per question (2-5 words, e.g. "Gradient Descent").
- Include per-question "difficulty": "easy", "medium", or "hard" relative to the content level.
- Questions should test conceptual understanding.
- {out_instruction}
- Write questions, options, answers, explanations, and topics in {out_name}.
- Keep technical terms and LaTeX math in their standard form.
- For ALL mathematical notation use LaTeX inline math:
  - Examples: $x^{{a+b}}$, $x^0$, $a \\cdot b$, $\\frac{{a}}{{b}}$
  - Do NOT write formulas as plain text like x^a, x^(a+b), or x^2 without $ delimiters.
- In JSON strings, escape every LaTeX backslash twice (e.g. "$\\\\frac{{a}}{{b}}$", not "$\\frac{{a}}{{b}}$").
{extra_rules}
Return ONLY valid JSON.

Example:

[
  {{
    "question": "What is LangChain?",
    "options": [
      "Database",
      "Framework",
      "Programming Language",
      "Operating System"
    ],
    "answer": "Framework",
    "explanation": "LangChain is a framework for developing applications using LLMs.",
    "topic": "LangChain Basics",
    "difficulty": "easy"
  }}
]

Study Notes:

{notes}
"""


def _strip_markdown_fence(text: str) -> str:
    quiz = text.strip()
    if quiz.startswith("```json"):
        quiz = quiz.replace("```json", "").replace("```", "").strip()
    elif quiz.startswith("```"):
        quiz = quiz.replace("```", "").strip()
    return quiz


def _is_escaped_quote(out: list[str]) -> bool:
    backslashes = 0
    index = len(out) - 1
    while index >= 0 and out[index] == "\\":
        backslashes += 1
        index -= 1
    return backslashes % 2 == 1


def _escape_latex_in_json_strings(text: str) -> str:
    """Repair Gemini JSON where LaTeX backslashes are not JSON-escaped."""
    out: list[str] = []
    i = 0
    in_string = False

    while i < len(text):
        ch = text[i]

        if ch == '"':
            if not _is_escaped_quote(out):
                in_string = not in_string
            out.append(ch)
            i += 1
            continue

        if not in_string:
            out.append(ch)
            i += 1
            continue

        if ch == "\\" and i + 1 < len(text):
            nxt = text[i + 1]

            if nxt == '"':
                out.append('\\"')
                i += 2
                continue
            if nxt == "\\":
                out.append("\\\\")
                i += 2
                continue
            if nxt == "u" and i + 5 < len(text):
                hexpart = text[i + 2 : i + 6]
                if re.fullmatch(r"[0-9a-fA-F]{4}", hexpart):
                    out.append(text[i : i + 6])
                    i += 6
                    continue
            if nxt in "bfnrt/":
                # \theta, \frac, \neq, etc. are LaTeX, not JSON escapes.
                if i + 2 < len(text) and text[i + 2].isalpha():
                    out.append("\\\\")
                    i += 1
                    continue
                out.append("\\")
                out.append(nxt)
                i += 2
                continue
            if nxt.isalpha() or nxt in "{}^_":
                out.append("\\\\")
                i += 1
                continue

            out.append("\\\\")
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def _loads_quiz_json(text: str):
    repaired = _escape_latex_in_json_strings(text)
    return json.loads(repaired)


def _parse_quiz_response(text: str) -> list:
    quiz = _strip_markdown_fence(text)
    parsed = _loads_quiz_json(quiz)
    if isinstance(parsed, str):
        parsed = _loads_quiz_json(parsed)

    return normalize_quiz(parsed)


def generate_quiz(
    notes: str,
    content_difficulty: str = "intermediate",
    output_language: str = "en",
) -> list:
    """Generate a calibrated quiz from study notes."""
    prompt = _quiz_prompt(
        notes,
        content_difficulty,
        output_language=output_language,
    )
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )
    return _parse_quiz_response(response.text)


def generate_adaptive_quiz(
    notes: str,
    *,
    content_difficulty: str = "intermediate",
    weak_topics: list[str],
    missed_questions: list[str] | None = None,
    output_language: str = "en",
) -> list:
    """Generate targeted practice questions for weak topics."""
    topics = ", ".join(weak_topics)
    missed = ""
    if missed_questions:
        missed = (
            "\nThe student missed questions like:\n- "
            + "\n- ".join(missed_questions[:6])
        )

    extra_rules = f"""
- Generate exactly 8 multiple-choice questions focused ONLY on these weak topics: {topics}.
- Do NOT repeat or rephrase these previously missed questions:{missed}
- Go deeper on the weak areas with new angles and scenarios.
- Tag each question with the relevant topic from: {topics}
"""
    prompt = _quiz_prompt(
        notes,
        content_difficulty,
        extra_rules=extra_rules,
        output_language=output_language,
    )
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )
    parsed = _parse_quiz_response(response.text)
    return parsed[:8] if len(parsed) > 8 else parsed


def normalize_quiz(parsed) -> list:
    """Ensure quiz data is always a list of question dicts."""
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]

    if isinstance(parsed, dict):
        for key in ("quiz", "questions", "items"):
            nested = parsed.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]

        if "question" in parsed:
            return [parsed]

    raise ValueError("Quiz generation returned an unexpected format. Please try again.")
