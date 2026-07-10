import { useState } from "react";
import type { OutputLanguage, SourceType } from "../types";
import { OUTPUT_LANGUAGE_OPTIONS } from "../types";
import { fetchJobStatus, startGenerate } from "../api/client";
import { FileIcon, GlobeIcon, SparklesIcon, YoutubeIcon } from "./icons";

interface Props {
  sourceType: SourceType;
  onGenerated: (sessionId: number) => void;
}

const SOURCE_META: Record<
  SourceType,
  { title: string; subtitle: string; icon: typeof YoutubeIcon }
> = {
  youtube: {
    title: "YouTube Video",
    subtitle: "Paste a link to generate notes, quiz & chat from the video",
    icon: YoutubeIcon,
  },
  document: {
    title: "Document Upload",
    subtitle: "Upload a PDF or TXT file to create study material",
    icon: FileIcon,
  },
  web: {
    title: "Blog / Article",
    subtitle: "Paste a blog or tutorial URL — educational content only",
    icon: GlobeIcon,
  },
};

export default function InputForm({ sourceType, onGenerated }: Props) {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [webUrl, setWebUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [outputLanguage, setOutputLanguage] = useState<OutputLanguage>("en");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  const meta = SOURCE_META[sourceType];
  const Icon = meta.icon;

  const handleGenerate = async () => {
    setError("");
    setLoading(true);
    setStatus("Starting pipeline...");

    try {
      const { job_id } = await startGenerate({
        sourceType,
        youtubeUrl: sourceType === "youtube" ? youtubeUrl : undefined,
        webUrl: sourceType === "web" ? webUrl : undefined,
        file: sourceType === "document" ? file || undefined : undefined,
        outputLanguage,
      });

      const poll = async (): Promise<number> => {
        const job = await fetchJobStatus(job_id);
        setStatus(job.step || job.status);

        if (job.status === "completed" && job.session_id) return job.session_id;
        if (job.status === "failed") throw new Error(job.error || "Generation failed");

        await new Promise((r) => setTimeout(r, 2000));
        return poll();
      };

      const sessionId = await poll();
      onGenerated(sessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
      setStatus("");
    }
  };

  return (
    <div className="card create-panel">
      <div className="card-header">
        <Icon className="card-header-icon" />
        <div>
          <h2>{meta.title}</h2>
          <p>{meta.subtitle}</p>
        </div>
      </div>

      <div className="create-form-body">
        <div className="create-form-fields">
          {sourceType === "youtube" && (
            <div className="input-field">
              <label htmlFor="youtubeUrl">YouTube URL</label>
              <input
                id="youtubeUrl"
                type="url"
                placeholder="https://www.youtube.com/watch?v=..."
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
              />
            </div>
          )}

          {sourceType === "document" && (
            <div className="input-field">
              <label htmlFor="fileUpload">Upload PDF or TXT</label>
              <input
                id="fileUpload"
                type="file"
                accept=".pdf,.txt"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </div>
          )}

          {sourceType === "web" && (
            <div className="input-field">
              <label htmlFor="webUrl">Article URL</label>
              <input
                id="webUrl"
                type="url"
                placeholder="https://example.com/article"
                value={webUrl}
                onChange={(e) => setWebUrl(e.target.value)}
              />
              <p className="hint">Educational blogs, tutorials, and documentation only.</p>
            </div>
          )}

          <div className="input-field">
            <label htmlFor="outputLanguage">Notes & quiz language</label>
            <select
              id="outputLanguage"
              value={outputLanguage}
              onChange={(e) => setOutputLanguage(e.target.value as OutputLanguage)}
              disabled={loading}
            >
              {OUTPUT_LANGUAGE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <p className="hint">
              English is the default. Choose Hindi to get notes, quiz, and chat answers in
              Hindi.
            </p>
          </div>
        </div>

        <div className="create-form-actions">
          <button className="btn-primary btn-generate" onClick={handleGenerate} disabled={loading}>
            <SparklesIcon />
            {loading ? "Generating..." : "Generate Study Material"}
          </button>
        </div>
      </div>

      {loading && status && (
        <div className="progress-bar-wrap">
          <div className="progress-bar-label">
            <SparklesIcon />
            {status}
          </div>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" />
          </div>
        </div>
      )}

      {error && <p className="error">{error}</p>}
    </div>
  );
}
