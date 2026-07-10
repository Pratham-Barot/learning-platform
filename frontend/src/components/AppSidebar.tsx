import { useState } from "react";
import type { SessionSummary, SourceType } from "../types";
import { deleteSession, renameSession } from "../api/client";
import {
  BookIcon,
  ChevronLeftIcon,
  ClockIcon,
  FileIcon,
  GlobeIcon,
  HistoryIcon,
  HomeIcon,
  NotesIcon,
  PencilIcon,
  SparklesIcon,
  TrashIcon,
  UserIcon,
  YoutubeIcon,
  sourceIcon,
} from "./icons";

const SOURCE_LABELS: Record<string, string> = {
  youtube: "YouTube",
  document: "Document",
  web: "Blog",
};

function plainTitle(title: string): string {
  return title.replace(/^#+\s*/, "").replace(/\*\*|__|\*/g, "").trim();
}

const CREATE_SOURCES: {
  value: SourceType;
  label: string;
  description: string;
  icon: typeof YoutubeIcon;
}[] = [
  { value: "youtube", label: "YouTube", description: "Paste a video link", icon: YoutubeIcon },
  { value: "document", label: "Document", description: "Upload PDF or TXT", icon: FileIcon },
  { value: "web", label: "Blog", description: "Paste an article URL", icon: GlobeIcon },
];

export type MainView = "home" | "account" | "create" | "session";

interface Props {
  sessions: SessionSummary[];
  activeSessionId: number | null;
  selectedSource: SourceType;
  mainView: MainView;
  open: boolean;
  onToggle: () => void;
  onSelectHome: () => void;
  onSelectAccount: () => void;
  onSelectSource: (source: SourceType) => void;
  onSelectSession: (id: number) => void;
  onRefresh: () => void;
  onDeleted?: (id: number) => void;
}

export default function AppSidebar({
  sessions,
  activeSessionId,
  selectedSource,
  mainView,
  open,
  onToggle,
  onSelectHome,
  onSelectAccount,
  onSelectSource,
  onSelectSession,
  onRefresh,
  onDeleted,
}: Props) {
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const handleRename = async (id: number) => {
    if (!renameValue.trim()) return;
    await renameSession(id, renameValue.trim());
    setRenamingId(null);
    onRefresh();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this study session?")) return;
    await deleteSession(id);
    onDeleted?.(id);
    onRefresh();
  };

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 86400000) {
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }
    if (diff < 604800000) {
      return d.toLocaleDateString([], { weekday: "short", hour: "2-digit", minute: "2-digit" });
    }
    return d.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
  };

  return (
    <>
      {open && (
        <button
          type="button"
          className="sidebar-backdrop"
          onClick={onToggle}
          aria-label="Close menu"
        />
      )}

      <aside className={`sidebar ${open ? "open" : "closed"}`} aria-hidden={!open}>
        <div className="sidebar-inner">
          <div className="sidebar-brand">
            <button type="button" className="sidebar-brand-main" onClick={onSelectHome}>
              <BookIcon className="brand-icon" />
              <div className="brand-text">
                <h2>StudyForge</h2>
                <span>AI Study Assistant</span>
              </div>
            </button>
            <button
              type="button"
              className="sidebar-toggle"
              onClick={onToggle}
              title="Close menu"
              aria-label="Close menu"
            >
              <ChevronLeftIcon />
            </button>
          </div>

          <div className="sidebar-section sidebar-section-home">
            <nav className="sidebar-nav">
              <button
                type="button"
                className={`sidebar-nav-item ${mainView === "home" ? "active" : ""}`}
                onClick={onSelectHome}
              >
                <HomeIcon className="sidebar-nav-icon" />
                <span className="sidebar-nav-text">
                  <strong>Home</strong>
                  <small>Dashboard & quick start</small>
                </span>
              </button>
              <button
                type="button"
                className={`sidebar-nav-item ${mainView === "account" ? "active" : ""}`}
                onClick={onSelectAccount}
              >
                <UserIcon className="sidebar-nav-icon" />
                <span className="sidebar-nav-text">
                  <strong>Account</strong>
                  <small>Profile & settings</small>
                </span>
              </button>
            </nav>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-header">
              <h3>
                <SparklesIcon />
                Create New
              </h3>
            </div>
            <nav className="sidebar-nav">
              {CREATE_SOURCES.map(({ value, label, description, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  className={`sidebar-nav-item ${
                    mainView === "create" && selectedSource === value ? "active" : ""
                  }`}
                  onClick={() => onSelectSource(value)}
                >
                  <Icon className="sidebar-nav-icon" />
                  <span className="sidebar-nav-text">
                    <strong>{label}</strong>
                    <small>{description}</small>
                  </span>
                </button>
              ))}
            </nav>
          </div>

          <div className="sidebar-section sidebar-section-grow">
            <div className="sidebar-header">
              <h3>
                <HistoryIcon />
                Study History
              </h3>
              <span className="session-count">{sessions.length}</span>
            </div>

            <div className="session-list">
              {sessions.length === 0 && (
                <div className="empty-history">
                  <NotesIcon />
                  <p>No history yet</p>
                  <span>Create from YouTube, Document, or Blog above.</span>
                </div>
              )}

              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`history-item ${
                    mainView === "session" && activeSessionId === session.id ? "active" : ""
                  } ${renamingId === session.id ? "renaming" : ""}`}
                >
                  {renamingId === session.id ? (
                    <div className="rename-row">
                      <input
                        type="text"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleRename(session.id);
                          if (e.key === "Escape") setRenamingId(null);
                        }}
                        autoFocus
                        aria-label="Rename session"
                      />
                      <button
                        className="btn-primary"
                        style={{ padding: "0.5rem 0.875rem" }}
                        onClick={() => handleRename(session.id)}
                      >
                        Save
                      </button>
                      <button
                        className="btn-secondary"
                        style={{ padding: "0.5rem 0.875rem" }}
                        onClick={() => setRenamingId(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <>
                      <button
                        className="history-load"
                        type="button"
                        onClick={() => onSelectSession(session.id)}
                        aria-current={
                          mainView === "session" && activeSessionId === session.id
                            ? "true"
                            : undefined
                        }
                      >
                        <span className="history-source">
                          {sourceIcon(session.source_type, "history-source-icon")}
                          {SOURCE_LABELS[session.source_type] || session.source_type}
                        </span>
                        <span className="history-title">{session.title}</span>
                        <span className="history-meta">
                          <span className="history-date">
                            <ClockIcon className="history-clock" />
                            {formatDate(session.created_at)}
                          </span>
                        </span>
                      </button>
                      <div className="history-actions">
                        <button
                          className="icon-btn"
                          type="button"
                          title="Rename"
                          onClick={() => {
                            setRenamingId(session.id);
                            setRenameValue(plainTitle(session.title));
                          }}
                        >
                          <PencilIcon />
                        </button>
                        <button
                          className="icon-btn danger"
                          type="button"
                          title="Delete"
                          onClick={() => handleDelete(session.id)}
                        >
                          <TrashIcon />
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
