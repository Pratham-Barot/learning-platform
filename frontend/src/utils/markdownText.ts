/** Unwrap backticks Gemini sometimes places around LaTeX, e.g. `$x^2$`. */
export function unwrapMathBackticks(text: string): string {
  return text
    .replace(/`(\$\$[\s\S]*?\$\$)`/g, "$1")
    .replace(/`(\$[^$\n]+?\$)`/g, "$1");
}

/** Prevent GFM from treating | inside math (e.g. P(Y|X)) as table syntax. */
export function normalizeMathPipes(text: string): string {
  let result = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, content) => {
    return `$$${content.replace(/\|/g, "\\vert ")}$$`;
  });

  result = result.replace(/(?<!\$)\$([^$\n]+?)\$(?!\$)/g, (_, content) => {
    return `$${content.replace(/\|/g, "\\vert ")}$`;
  });

  return result;
}

/** Fix markdown tables where row breaks were collapsed onto one line. */
export function normalizeMarkdownTables(text: string): string {
  if (!text.includes("|")) return text;

  return text.replace(/\|\s+\|/g, "|\n|");
}

export function prepareMarkdown(text: string): string {
  return normalizeMarkdownTables(normalizeMathPipes(unwrapMathBackticks(text)));
}
