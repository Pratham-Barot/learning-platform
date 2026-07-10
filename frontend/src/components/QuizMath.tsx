import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { formatQuizMath } from "../utils/mathText";

const inlineComponents = {
  p: ({ children }: { children?: ReactNode }) => <span className="quiz-math-inline">{children}</span>,
};

export default function QuizMath({ text }: { text: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={inlineComponents}
    >
      {formatQuizMath(text)}
    </ReactMarkdown>
  );
}
