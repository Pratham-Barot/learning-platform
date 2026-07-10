import { downloadPdf } from "../api/client";
import type { SessionDetail } from "../types";
import { DownloadIcon } from "./icons";
import MarkdownContent from "./MarkdownContent";

export default function NotesTab({ session }: { session: SessionDetail }) {
  return (
    <div className="tab-panel">
      <div className="notes-toolbar">
        <button
          className="btn-secondary"
          type="button"
          onClick={() => downloadPdf(session.id).catch(console.error)}
        >
          <DownloadIcon />
          Download PDF
        </button>
      </div>

      <hr className="notes-divider" />

      <article className="markdown-body">
        <MarkdownContent text={session.notes} />
      </article>
    </div>
  );
}
