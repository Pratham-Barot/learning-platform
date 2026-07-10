import os
from typing import Callable

from google import genai
from dotenv import load_dotenv

from content_chunking import (
    MAP_REDUCE_CHAR_THRESHOLD,
    MAX_RUNNING_OUTLINE_CHARS,
    PHASE_DURATION_SECONDS,
    SKELETON_THRESHOLD_HOURS,
    USE_ROLLING_CONTEXT,
    effective_phase_seconds,
    estimate_total_hours,
    should_build_skeleton,
    should_use_map_reduce,
    split_into_phases,
)
from output_languages import (
    normalize_output_language,
    output_language_instruction,
    output_language_name,
)

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
SUMMARY_MODEL = os.getenv("GEMINI_NOTES_MODEL", "gemini-3.1-flash-lite")
MERGE_BATCH_SIZE = int(os.getenv("MAP_REDUCE_MERGE_BATCH_SIZE", "10"))
SKELETON_EXCERPT_CHARS = int(os.getenv("SKELETON_EXCERPT_CHARS", "2500"))
SKELETON_MAX_INPUT_CHARS = int(os.getenv("SKELETON_MAX_INPUT_CHARS", "120000"))

_SUMMARY_MARKER = "---SUMMARY---"
_OUTLINE_MARKER = "---OUTLINE---"


def _format_phase_label(index: int, total: int, phase_seconds: int) -> str:
    phase_minutes = max(1, phase_seconds // 60)
    start_min = (index - 1) * phase_minutes
    end_min = index * phase_minutes
    return f"Part {index}/{total} ({start_min}-{end_min} min)"


def _language_note(language: str, language_code: str, output_language: str) -> str:
    out_code = normalize_output_language(output_language)
    if language_code != "en" and language_code != out_code:
        out_name = output_language_name(out_code)
        return (
            f"\nThe source content is in {language}. "
            f"Understand it, then write in {out_name}.\n"
        )
    return ""


def parse_phase_response(raw: str) -> tuple[str, str]:
    """Split model output into section summary and running outline."""
    text = (raw or "").strip()
    if not text:
        return "", ""

    if _SUMMARY_MARKER in text and _OUTLINE_MARKER in text:
        _, rest = text.split(_SUMMARY_MARKER, 1)
        summary_part, outline_part = rest.split(_OUTLINE_MARKER, 1)
        return summary_part.strip(), outline_part.strip()

    return text, ""


def compress_outline(
    outline: str,
    *,
    language: str = "English",
    language_code: str = "en",
    output_language: str = "en",
) -> str:
    """Shrink running outline when it grows too large for long videos."""
    outline = outline.strip()
    if not outline or len(outline) <= MAX_RUNNING_OUTLINE_CHARS:
        return outline

    out_instruction = output_language_instruction(output_language)
    language_note = _language_note(language, language_code, output_language)

    prompt = f"""
You are an expert study assistant.

Compress the following course-progress outline for a long lecture series.
Keep only the most important topics, definitions, formulas, and open threads.
Target length: at most {MAX_RUNNING_OUTLINE_CHARS} characters.
Use concise bullet points grouped under:
- Topics covered
- Key definitions
- Important formulas
- Open threads

{out_instruction}
{language_note}
Outline to compress:
{outline}

Compressed outline:
"""
    response = client.models.generate_content(
        model=SUMMARY_MODEL,
        contents=prompt,
    )
    compressed = (response.text or "").strip()
    if not compressed:
        return outline[:MAX_RUNNING_OUTLINE_CHARS]
    if len(compressed) > MAX_RUNNING_OUTLINE_CHARS:
        return compressed[:MAX_RUNNING_OUTLINE_CHARS].rsplit("\n", 1)[0].strip()
    return compressed


def build_global_skeleton(
    phases: list[str],
    *,
    language: str = "English",
    language_code: str = "en",
    output_language: str = "en",
) -> str:
    """Cheap course-wide skeleton for very long videos (10+ hours)."""
    excerpts: list[str] = []
    for index, phase in enumerate(phases, start=1):
        excerpt = phase[:SKELETON_EXCERPT_CHARS].strip()
        if len(phase) > SKELETON_EXCERPT_CHARS:
            excerpt += "\n[...]"
        excerpts.append(f"### Section {index}\n{excerpt}")

    combined = "\n\n".join(excerpts)
    if len(combined) > SKELETON_MAX_INPUT_CHARS:
        combined = combined[:SKELETON_MAX_INPUT_CHARS] + "\n[... truncated ...]"

    out_instruction = output_language_instruction(output_language)
    language_note = _language_note(language, language_code, output_language)

    prompt = f"""
You are an expert study assistant.

Create a compact course skeleton for a long educational video or document split into
{len(phases)} sequential sections.

For each section, list:
- Section number and a short title (5-10 words)
- 3-5 main topic bullets
- Optional: what earlier sections it may depend on

Rules:
- Be concise.
- Capture the overall learning arc across all sections.
- {out_instruction}
{language_note}
Section excerpts:
{combined}

Course skeleton:
"""
    response = client.models.generate_content(
        model=SUMMARY_MODEL,
        contents=prompt,
    )
    return (response.text or "").strip()


def summarize_phase(
    phase_text: str,
    *,
    phase_index: int,
    total_phases: int,
    language: str = "English",
    language_code: str = "en",
    output_language: str = "en",
    phase_seconds: int = PHASE_DURATION_SECONDS,
) -> str:
    """Summarize one section without prior context (legacy / fallback)."""
    label = _format_phase_label(phase_index, total_phases, phase_seconds)
    out_instruction = output_language_instruction(output_language)
    language_note = _language_note(language, language_code, output_language)

    prompt = f"""
You are an expert study assistant.

Summarize the following section of educational content.
This is {label} of a longer lecture or document.

Rules:
- Capture all key concepts, definitions, formulas, and examples from this section.
- Use concise bullet points grouped by topic.
- Keep important technical terms.
- For math, use LaTeX inline like $x^2$ or $O(n)$.
- Do not say "this section" or refer to part numbers in the summary.
- {out_instruction}
{language_note}
Section content:
{phase_text}

Summary:
"""
    response = client.models.generate_content(
        model=SUMMARY_MODEL,
        contents=prompt,
    )
    return (response.text or "").strip()


def summarize_phase_with_context(
    phase_text: str,
    *,
    phase_index: int,
    total_phases: int,
    running_outline: str,
    global_skeleton: str | None = None,
    language: str = "English",
    language_code: str = "en",
    output_language: str = "en",
    phase_seconds: int = PHASE_DURATION_SECONDS,
) -> tuple[str, str]:
    """
    Summarize one section with awareness of prior sections.
    Returns (section_summary, updated_running_outline).
    """
    label = _format_phase_label(phase_index, total_phases, phase_seconds)
    out_instruction = output_language_instruction(output_language)
    language_note = _language_note(language, language_code, output_language)

    prior_context = running_outline.strip() or "None — this is the first section."
    skeleton_block = ""
    if global_skeleton:
        skeleton_block = f"""
Course skeleton (where this section fits in the full lecture):
{global_skeleton}
"""

    prompt = f"""
You are an expert study assistant.

Summarize the following section of educational content.
This is {label} of a longer lecture or document.

Previous topics already covered (from earlier sections — use for continuity):
{prior_context}
{skeleton_block}
Rules for the section summary:
- Capture all key concepts, definitions, formulas, and examples from THIS section.
- Connect new ideas to prior topics when the lecturer builds on them.
- Use concise bullet points grouped by topic.
- Keep important technical terms.
- For math, use LaTeX inline like $x^2$ or $O(n)$.
- Do not say "this section" or refer to part numbers in the summary.
- {out_instruction}
{language_note}
Section content:
{phase_text}

Return your answer in EXACTLY this format (include both markers):

{_SUMMARY_MARKER}
(section summary here)

{_OUTLINE_MARKER}
(updated running outline for the NEXT section: topics covered so far, key definitions,
important formulas, and open threads that may continue later — keep compact)
"""
    response = client.models.generate_content(
        model=SUMMARY_MODEL,
        contents=prompt,
    )
    summary, outline = parse_phase_response(response.text or "")
    if not summary:
        summary = summarize_phase(
            phase_text,
            phase_index=phase_index,
            total_phases=total_phases,
            language=language,
            language_code=language_code,
            output_language=output_language,
            phase_seconds=phase_seconds,
        )
    if not outline:
        outline = running_outline
    if len(outline) > MAX_RUNNING_OUTLINE_CHARS:
        outline = compress_outline(
            outline,
            language=language,
            language_code=language_code,
            output_language=output_language,
        )
    return summary, outline


def _merge_batch(
    summaries: list[str],
    *,
    language: str,
    language_code: str,
    output_language: str = "en",
    batch_label: str = "",
) -> str:
    joined = "\n\n---\n\n".join(
        f"Section {index + 1}:\n{summary}"
        for index, summary in enumerate(summaries)
    )
    out_instruction = output_language_instruction(output_language)
    language_note = _language_note(language, language_code, output_language)

    label_note = f" ({batch_label})" if batch_label else ""
    prompt = f"""
You are an expert study assistant.

Combine the following section summaries into one coherent master summary{label_note}.

Rules:
- Merge overlapping ideas and remove repetition.
- Preserve all important concepts, formulas, and examples.
- Keep cross-section continuity (later sections may build on earlier ones).
- Organize by major topics in logical order.
- Use concise bullet points and short paragraphs.
- For math, use LaTeX inline like $x^2$.
- {out_instruction}
{language_note}
Section summaries:
{joined}

Master summary:
"""
    response = client.models.generate_content(
        model=SUMMARY_MODEL,
        contents=prompt,
    )
    return (response.text or "").strip()


def merge_summaries(
    summaries: list[str],
    *,
    language: str = "English",
    language_code: str = "en",
    output_language: str = "en",
) -> str:
    if not summaries:
        return ""
    if len(summaries) == 1:
        return summaries[0]

    if len(summaries) <= MERGE_BATCH_SIZE:
        return _merge_batch(
            summaries,
            language=language,
            language_code=language_code,
            output_language=output_language,
        )

    merged_batches: list[str] = []
    for start in range(0, len(summaries), MERGE_BATCH_SIZE):
        batch = summaries[start : start + MERGE_BATCH_SIZE]
        batch_label = f"sections {start + 1}-{start + len(batch)}"
        merged_batches.append(
            _merge_batch(
                batch,
                language=language,
                language_code=language_code,
                output_language=output_language,
                batch_label=batch_label,
            )
        )
    return merge_summaries(
        merged_batches,
        language=language,
        language_code=language_code,
        output_language=output_language,
    )


def _summarize_phases_parallel(
    phases: list[str],
    *,
    language: str,
    language_code: str,
    output_language: str,
    phase_seconds: int,
    on_status: Callable[[str], None] | None,
) -> list[str]:
    """Legacy independent summarization (no cross-phase context)."""
    partial_summaries: list[str] = []
    for index, phase in enumerate(phases, start=1):
        if on_status:
            on_status(f"Summarizing part {index}/{len(phases)}...")
        partial_summaries.append(
            summarize_phase(
                phase,
                phase_index=index,
                total_phases=len(phases),
                language=language,
                language_code=language_code,
                output_language=output_language,
                phase_seconds=phase_seconds,
            )
        )
    return partial_summaries


def _summarize_phases_with_rolling_context(
    phases: list[str],
    *,
    language: str,
    language_code: str,
    output_language: str,
    phase_seconds: int,
    segments: list[dict] | None,
    on_status: Callable[[str], None] | None,
) -> list[str]:
    """Sequential summarization where each phase knows prior context."""
    global_skeleton: str | None = None
    if should_build_skeleton(len(phases), segments):
        if on_status:
            on_status(
                f"Long video ({len(phases)} parts, {SKELETON_THRESHOLD_HOURS:g}+ hrs). "
                "Building course skeleton..."
            )
        global_skeleton = build_global_skeleton(
            phases,
            language=language,
            language_code=language_code,
            output_language=output_language,
        )

    running_outline = ""
    partial_summaries: list[str] = []
    for index, phase in enumerate(phases, start=1):
        if on_status:
            on_status(
                f"Summarizing part {index}/{len(phases)} with prior context..."
            )
        summary, running_outline = summarize_phase_with_context(
            phase,
            phase_index=index,
            total_phases=len(phases),
            running_outline=running_outline,
            global_skeleton=global_skeleton,
            language=language,
            language_code=language_code,
            output_language=output_language,
            phase_seconds=phase_seconds,
        )
        partial_summaries.append(summary)

    return partial_summaries


def prepare_source_for_notes(
    source_text: str,
    *,
    segments: list[dict] | None = None,
    language: str = "English",
    language_code: str = "en",
    output_language: str = "en",
    on_status: Callable[[str], None] | None = None,
) -> str:
    """
    Map-reduce long content into one condensed summary suitable for notes generation.
    Short content is returned unchanged.

    Medium/long videos use a rolling outline chain so each phase knows prior topics.
    Very long videos (10+ hrs) also build a global skeleton first.
    """
    text = source_text.strip()
    if not should_use_map_reduce(text):
        return text

    phase_seconds = effective_phase_seconds(text, segments)
    phases = split_into_phases(text, segments, phase_seconds=phase_seconds)
    if len(phases) <= 1:
        return text

    out_code = normalize_output_language(output_language)
    total_hours = estimate_total_hours(segments)
    phase_minutes = max(1, phase_seconds // 60)

    if on_status:
        hours_note = f", ~{total_hours:.1f} hrs" if total_hours else ""
        mode = "rolling context" if USE_ROLLING_CONTEXT else "independent parts"
        on_status(
            f"Long content detected ({len(text):,} chars{hours_note}). "
            f"Summarizing {len(phases)} parts (~{phase_minutes} min each, {mode})..."
        )

    if USE_ROLLING_CONTEXT:
        partial_summaries = _summarize_phases_with_rolling_context(
            phases,
            language=language,
            language_code=language_code,
            output_language=out_code,
            phase_seconds=phase_seconds,
            segments=segments,
            on_status=on_status,
        )
    else:
        partial_summaries = _summarize_phases_parallel(
            phases,
            language=language,
            language_code=language_code,
            output_language=out_code,
            phase_seconds=phase_seconds,
            on_status=on_status,
        )

    if on_status:
        on_status("Combining section summaries into master summary...")

    return merge_summaries(
        partial_summaries,
        language=language,
        language_code=language_code,
        output_language=out_code,
    )


def map_reduce_threshold() -> int:
    return MAP_REDUCE_CHAR_THRESHOLD
