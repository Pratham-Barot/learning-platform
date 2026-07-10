from __future__ import annotations

from fpdf import FPDF
import html
import re
from pathlib import Path

import matplotlib

MATH_BLOCK_RE = re.compile(
    r"^\s*(\$\$(.+?)\$\$|\\\[([\s\S]+?)\\\])\s*$"
)
INLINE_MATH_RE = re.compile(
    r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)|\\\((.+?)\\\)"
)

# DejaVu covers Latin + math symbols; Noto Devanagari covers Hindi and related scripts.
FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
PROJECT_FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
DEVANAGARI_REGULAR = PROJECT_FONT_DIR / "NotoSansDevanagari-Regular.ttf"
DEVANAGARI_BOLD = PROJECT_FONT_DIR / "NotoSansDevanagari-Bold.ttf"
SYSTEM_DEVANAGARI_REGULAR = Path(
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
)
SYSTEM_DEVANAGARI_BOLD = Path(
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
)

BODY_SIZE = 11
HEADING_SIZE = 13
SECTION_SIZE = 16
TITLE_SIZE = 24
PRIMARY_FONT = "DejaVu"
FALLBACK_FONT = "NotoSansDevanagari"

# Strip HTML after markdown conversion for multi_cell rendering.
_TAG_RE = re.compile(r"<[^>]+>")
_SUPERSCRIPT_MAP = str.maketrans("0123456789+-=()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾")
_SUBSCRIPT_MAP = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")


def _resolve_devanagari_fonts() -> tuple[Path | None, Path | None]:
    regular = DEVANAGARI_REGULAR if DEVANAGARI_REGULAR.exists() else None
    bold = DEVANAGARI_BOLD if DEVANAGARI_BOLD.exists() else None
    if regular is None and SYSTEM_DEVANAGARI_REGULAR.exists():
        regular = SYSTEM_DEVANAGARI_REGULAR
    if bold is None and SYSTEM_DEVANAGARI_BOLD.exists():
        bold = SYSTEM_DEVANAGARI_BOLD
    return regular, bold


def setup_fonts(pdf: FPDF) -> None:
    pdf.add_font(PRIMARY_FONT, "", str(FONT_DIR / "DejaVuSans.ttf"))
    pdf.add_font(PRIMARY_FONT, "B", str(FONT_DIR / "DejaVuSans-Bold.ttf"))
    pdf.add_font(PRIMARY_FONT, "I", str(FONT_DIR / "DejaVuSans-Oblique.ttf"))
    pdf.add_font(PRIMARY_FONT, "BI", str(FONT_DIR / "DejaVuSans-BoldOblique.ttf"))

    regular, bold = _resolve_devanagari_fonts()
    if regular is None:
        raise FileNotFoundError(
            "Noto Sans Devanagari font not found. "
            f"Expected at {DEVANAGARI_REGULAR} or {SYSTEM_DEVANAGARI_REGULAR}."
        )

    pdf.add_font(FALLBACK_FONT, "", str(regular))
    # Noto Devanagari may not ship an italic face; reuse regular/bold.
    pdf.add_font(FALLBACK_FONT, "I", str(regular))
    if bold is not None:
        pdf.add_font(FALLBACK_FONT, "B", str(bold))
        pdf.add_font(FALLBACK_FONT, "BI", str(bold))
    else:
        pdf.add_font(FALLBACK_FONT, "B", str(regular))
        pdf.add_font(FALLBACK_FONT, "BI", str(regular))

    # Critical: without this, Hindi glyphs are skipped and leave blank gaps.
    pdf.set_fallback_fonts([FALLBACK_FONT])

    # Shape Devanagari correctly (conjuncts / matras). Requires uharfbuzz.
    try:
        pdf.set_text_shaping(True)
    except Exception:
        pass

    pdf.set_font(PRIMARY_FONT, "", BODY_SIZE)


def _read_braced_group(text: str, start: int) -> tuple[str | None, int]:
    if start >= len(text) or text[start] != "{":
        return None, start
    depth = 0
    for i in range(start, len(text)):
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
    return None, start


def _replace_fracs_with_placeholders(text: str) -> tuple[str, list[str]]:
    """Replace \\frac{a}{b} with placeholders and store plain text for each fraction."""
    fracs: list[str] = []

    while True:
        idx = text.find(r"\frac")
        if idx == -1:
            break
        pos = idx + len(r"\frac")
        numerator, pos = _read_braced_group(text, pos)
        if numerator is None:
            text = text[:idx] + text[idx + len(r"\frac") :]
            continue
        denominator, pos = _read_braced_group(text, pos)
        if denominator is None:
            text = text[:idx] + text[idx + len(r"\frac") :]
            continue
        num_text = latex_to_text(numerator)
        den_text = latex_to_text(denominator)
        fracs.append(f"{num_text}/{den_text}")
        placeholder = f"@@FRAC{len(fracs) - 1}@@"
        text = text[:idx] + placeholder + text[pos:]

    return text, fracs


def latex_to_text(latex: str) -> str:
    """Convert LaTeX math to plain Unicode text for PDF multi_cell rendering."""
    text = latex.strip()

    for _ in range(16):
        updated = re.sub(r"\\text\{([^{}]*)\}", r"\1", text)
        if updated == text:
            break
        text = updated

    text, fracs = _replace_fracs_with_placeholders(text)

    def sqrt_repl(match: re.Match) -> str:
        return f"√({latex_to_text(match.group(1))})"

    text = re.sub(r"\\sqrt\{([^{}]*)\}", sqrt_repl, text)

    replacements = {
        r"\pm": "±",
        r"\mp": "∓",
        r"\neq": "≠",
        r"\leq": "≤",
        r"\geq": "≥",
        r"\times": "×",
        r"\cdot": "·",
        r"\infty": "∞",
        r"\pi": "π",
        r"\alpha": "α",
        r"\beta": "β",
        r"\gamma": "γ",
        r"\delta": "δ",
        r"\theta": "θ",
        r"\lambda": "λ",
        r"\sigma": "σ",
        r"\omega": "ω",
        r"\left": "",
        r"\right": "",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    def _to_sup(value: str) -> str:
        return latex_to_text(value).translate(_SUPERSCRIPT_MAP)

    def _to_sub(value: str) -> str:
        return latex_to_text(value).translate(_SUBSCRIPT_MAP)

    text = re.sub(r"\^\{([^{}]+)\}", lambda m: _to_sup(m.group(1)), text)
    text = re.sub(r"\^([a-zA-Z0-9+-])", lambda m: _to_sup(m.group(1)), text)
    text = re.sub(r"_\{([^{}]+)\}", lambda m: _to_sub(m.group(1)), text)
    text = re.sub(r"_([a-zA-Z0-9+-])", lambda m: _to_sub(m.group(1)), text)
    text = re.sub(r"\\([a-zA-Z]+)", r"\1", text)
    text = re.sub(r"\{([^{}]+)\}", r"\1", text)

    for i, frac_text in enumerate(fracs):
        text = text.replace(f"@@FRAC{i}@@", frac_text)

    return text.strip()


# Backwards-compatible alias used by older call sites / tests.
def latex_to_html(latex: str) -> str:
    return html.escape(latex_to_text(latex), quote=False)


def convert_math_markup(text: str) -> str:
    text = re.sub(
        r"\$\$(.+?)\$\$",
        lambda m: latex_to_text(m.group(1)),
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"\\\[(.+?)\\\]",
        lambda m: latex_to_text(m.group(1)),
        text,
        flags=re.DOTALL,
    )

    def _repl(match: re.Match) -> str:
        latex = match.group(1) or match.group(2) or ""
        return latex_to_text(latex)

    return INLINE_MATH_RE.sub(_repl, text)


def plain_math_to_text(text: str) -> str:
    """Convert plain-text math like x^(a+b) or x^2 to Unicode superscripts."""
    text = re.sub(
        r"([a-zA-Z0-9]+)\^\(([^)]+)\)",
        lambda m: f"{m.group(1)}{m.group(2).translate(_SUPERSCRIPT_MAP)}",
        text,
    )
    text = re.sub(
        r"([a-zA-Z0-9]+)\^([a-zA-Z0-9+-]+)",
        lambda m: f"{m.group(1)}{m.group(2).translate(_SUPERSCRIPT_MAP)}",
        text,
    )
    text = re.sub(
        r"\^\(([^)]+)\)",
        lambda m: m.group(1).translate(_SUPERSCRIPT_MAP),
        text,
    )
    return text


def markdown_to_plain(text: str) -> str:
    """Convert markdown + math into plain Unicode suitable for multi_cell."""
    if not text:
        return ""

    text = convert_math_markup(text)
    text = plain_math_to_text(text)

    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)

    text = re.sub(r"^#+\s*", "", text)
    text = text.replace("`", "")
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


# Keep old name for any importers.
def markdown_to_html(text: str) -> str:
    return html.escape(markdown_to_plain(text), quote=False)


def extract_block_math(line: str) -> str | None:
    match = MATH_BLOCK_RE.match(line.strip())
    if not match:
        return None
    return match.group(2) or match.group(3)


def is_section_heading(original_line: str) -> bool:
    return bool(re.match(r"^#+\s+", original_line.strip()))


def _contains_bold_markdown(content: str) -> bool:
    return bool(re.search(r"\*\*.+?\*\*|__.+?__", content))


def write_paragraph(
    pdf: FPDF,
    content: str,
    *,
    bold: bool = False,
    italic: bool = False,
    align: str = "L",
    font_size: int = BODY_SIZE,
    color: tuple[int, int, int] = (40, 40, 40),
    line_height: float = 6,
):
    """Render text with DejaVu + Devanagari fallback (avoids write_html glyph drops)."""
    plain = markdown_to_plain(content)
    if not plain:
        return

    if not bold and _contains_bold_markdown(content):
        bold = True

    style = ""
    if bold and italic:
        style = "BI"
    elif bold:
        style = "B"
    elif italic:
        style = "I"

    pdf.set_font(PRIMARY_FONT, style, font_size)
    pdf.set_text_color(*color)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, line_height, plain, align=align)


def write_html_paragraph(
    pdf: FPDF,
    content: str,
    *,
    bold: bool = False,
    italic: bool = False,
    align: str = "LEFT",
    font_size: int = BODY_SIZE,
    color: tuple[int, int, int] = (40, 40, 40),
    line_height: float = 6,
):
    """Compatibility wrapper — maps old HTML path onto multi_cell rendering."""
    align_map = {"LEFT": "L", "CENTER": "C", "RIGHT": "R", "JUSTIFY": "J"}
    write_paragraph(
        pdf,
        content,
        bold=bold,
        italic=italic,
        align=align_map.get(align.upper(), "L"),
        font_size=font_size,
        color=color,
        line_height=line_height,
    )


def render_notes_line(pdf: FPDF, original_line: str):
    block_latex = extract_block_math(original_line)
    if block_latex:
        formula = latex_to_text(block_latex)
        pdf.ln(2)
        write_paragraph(
            pdf,
            formula,
            align="C",
            font_size=BODY_SIZE,
            color=(30, 30, 30),
            line_height=6,
        )
        pdf.ln(4)
        return

    stripped = original_line.strip()
    if not stripped:
        pdf.ln(2)
        return

    if re.match(r"^[\-\*=_]{2,}\s*$", stripped):
        pdf.ln(1)
        return

    bullet = re.match(r"^[-*+]\s+(.*)", stripped)
    content = bullet.group(1) if bullet else stripped.lstrip("#").strip()

    if is_section_heading(original_line):
        pdf.ln(4)
        write_paragraph(
            pdf,
            content,
            bold=True,
            font_size=HEADING_SIZE,
            color=(30, 30, 30),
            line_height=7,
        )
        pdf.ln(1)
        pdf.set_draw_color(180, 180, 180)
        pdf.set_line_width(0.2)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(2)
    else:
        prefix = "• " if bullet else ""
        write_paragraph(pdf, prefix + content, line_height=6)


def generate_pdf(notes: str, quiz: list) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    setup_fonts(pdf)

    pdf.add_page()
    pdf.set_font(PRIMARY_FONT, "B", TITLE_SIZE)
    pdf.set_text_color(30, 30, 30)
    pdf.ln(35)
    pdf.cell(0, 12, "StudyForge", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(PRIMARY_FONT, "", 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "Study Notes & Quiz", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.add_page()
    pdf.set_font(PRIMARY_FONT, "B", SECTION_SIZE)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "Study Notes", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(99, 102, 241)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)

    for line in notes.split("\n"):
        render_notes_line(pdf, line)

    pdf.add_page()
    pdf.set_font(PRIMARY_FONT, "B", SECTION_SIZE)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "Quiz", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(99, 102, 241)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)

    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for i, q in enumerate(quiz):
        if not isinstance(q, dict):
            continue

        question = q.get("question", "")
        options = q.get("options", [])
        answer = q.get("answer", "")
        explanation = q.get("explanation", "")

        if not isinstance(options, list):
            options = []

        write_paragraph(
            pdf,
            f"Q{i + 1}. {question}",
            font_size=BODY_SIZE,
            color=(30, 30, 30),
        )
        pdf.ln(1)

        for j, option in enumerate(options):
            label = labels[j] if j < len(labels) else str(j + 1)
            is_correct = option == answer
            suffix = " (correct)" if is_correct else ""
            write_paragraph(
                pdf,
                f"{label}) {option}{suffix}",
                font_size=10,
                color=(34, 139, 34) if is_correct else (60, 60, 60),
                line_height=5,
            )

        if explanation:
            pdf.ln(1)
            write_paragraph(
                pdf,
                f"Explanation: {explanation}",
                italic=True,
                font_size=10,
                color=(90, 90, 90),
                line_height=5,
            )

        pdf.ln(3)
        pdf.set_draw_color(220, 220, 220)
        pdf.set_line_width(0.2)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(3)

    return bytes(pdf.output())
