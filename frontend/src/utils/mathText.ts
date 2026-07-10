function hasLatexDelimiters(text: string): boolean {
  return /\$(?:\\.|[^$])+\$/.test(text) || /\$\$(?:\\.|[^$])+\$\$/.test(text);
}

function plainExponentsToLatex(text: string): string {
  let out = text;
  out = out.replace(/([a-zA-Z0-9]+)\^\(([^)]+)\)/g, (_, base, exp) => `${base}^{${exp}}`);
  out = out.replace(/([a-zA-Z0-9]+)\^([a-zA-Z0-9+-]+)/g, (_, base, exp) => `${base}^{${exp}}`);
  out = out.replace(/\s*\*\s*/g, " \\cdot ");
  return out.trim();
}

/** Convert plain quiz math (x^a, x^(a+b)) into inline LaTeX for KaTeX. */
export function formatQuizMath(text: string): string {
  if (!text || hasLatexDelimiters(text)) return text;

  const trimmed = text.trim();

  if (/^[\da-zA-Z^()+\-*/.\s,]+$/.test(trimmed) && /\^/.test(trimmed)) {
    return `$${plainExponentsToLatex(trimmed)}$`;
  }

  let result = text;
  result = result.replace(/([a-zA-Z0-9]+)\^\(([^)]+)\)/g, (_, base, exp) => `$${base}^{${exp}}$`);
  result = result.replace(/([a-zA-Z0-9]+)\^([a-zA-Z0-9+-]+)/g, (_, base, exp) => `$${base}^{${exp}}$`);
  result = result.replace(/\s\*\s/g, " $\\cdot$ ");
  return result;
}
