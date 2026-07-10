import type { SessionSummary, SourceType, User } from "../types";
import {
  BookIcon,
  ChatIcon,
  DownloadIcon,
  FileIcon,
  GlobeIcon,
  HistoryIcon,
  NotesIcon,
  QuizIcon,
  SparklesIcon,
  YoutubeIcon,
  sourceIcon,
} from "./icons";

const QUICK_SOURCES: {
  type: SourceType;
  label: string;
  description: string;
  icon: typeof YoutubeIcon;
}[] = [
  {
    type: "youtube",
    label: "YouTube Video",
    description: "Paste a lecture or tutorial link",
    icon: YoutubeIcon,
  },
  {
    type: "document",
    label: "Document",
    description: "Upload a PDF or TXT file",
    icon: FileIcon,
  },
  {
    type: "web",
    label: "Blog / Article",
    description: "Paste any educational web URL",
    icon: GlobeIcon,
  },
];

const FEATURES = [
  {
    icon: NotesIcon,
    title: "Smart Notes",
    description: "Structured summaries with formulas and key concepts.",
  },
  {
    icon: QuizIcon,
    title: "Auto Quiz",
    description: "Multiple-choice questions with instant feedback and explanations.",
  },
  {
    icon: ChatIcon,
    title: "AI Tutor Chat",
    description: "Ask follow-up questions grounded in your source material.",
  },
  {
    icon: DownloadIcon,
    title: "PDF Export",
    description: "Download notes and quiz as a polished PDF for offline review.",
  },
];

const STEPS = [
  { step: "1", title: "Add a source", text: "Choose YouTube, a document, or a blog article." },
  { step: "2", title: "Generate material", text: "AI builds notes, a quiz, and a searchable knowledge base." },
  { step: "3", title: "Study & chat", text: "Review, test yourself, and ask the tutor anything." },
];

interface Props {
  user: User | null;
  sessions: SessionSummary[];
  onSelectSource: (source: SourceType) => void;
  onSelectSession: (id: number) => void;
}

function plainTitle(title: string): string {
  return title.replace(/^#+\s*/, "").replace(/\*\*|__|\*/g, "").trim();
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 86400000) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export default function HomeDashboard({
  user,
  sessions,
  onSelectSource,
  onSelectSession,
}: Props) {
  const firstName = user?.full_name?.split(" ")[0] || "there";
  const recentSessions = sessions.slice(0, 5);

  return (
    <div className="home-dashboard">
      <section className="home-hero card">
        <div className="home-hero-content">
          <div className="home-hero-badge">
            <SparklesIcon />
            AI Study Assistant
          </div>
          <h2 className="home-hero-title">
            Welcome back, {firstName}
          </h2>
          <p className="home-hero-desc">
            Turn lectures, documents, and articles into notes, quizzes, and an interactive
            tutor — all from one place.
          </p>
          <div className="home-stats">
            <div className="home-stat">
              <strong>{sessions.length}</strong>
              <span>{sessions.length === 1 ? "Session" : "Sessions"}</span>
            </div>
            <div className="home-stat">
              <strong>3</strong>
              <span>Source types</span>
            </div>
          </div>
        </div>
        <div className="home-hero-visual" aria-hidden="true">
          <div className="home-hero-orbit">
            <BookIcon className="home-hero-orbit-icon center" />
            <NotesIcon className="home-hero-orbit-icon orbit-1" />
            <QuizIcon className="home-hero-orbit-icon orbit-2" />
            <ChatIcon className="home-hero-orbit-icon orbit-3" />
          </div>
        </div>
      </section>

      <section className="home-section">
        <div className="home-section-header">
          <h3>Quick Start</h3>
          <p>Pick a source type to begin a new study session</p>
        </div>
        <div className="home-quick-grid">
          {QUICK_SOURCES.map(({ type, label, description, icon: Icon }) => (
            <button
              key={type}
              type="button"
              className="home-quick-card"
              onClick={() => onSelectSource(type)}
            >
              <span className="home-quick-icon">
                <Icon />
              </span>
              <span className="home-quick-text">
                <strong>{label}</strong>
                <small>{description}</small>
              </span>
              <SparklesIcon className="home-quick-arrow" />
            </button>
          ))}
        </div>
      </section>

      <section className="home-section">
        <div className="home-section-header">
          <h3>What you get</h3>
          <p>Everything you need to learn faster from any content</p>
        </div>
        <div className="home-features-grid">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <div key={title} className="home-feature-card card">
              <Icon className="home-feature-icon" />
              <h4>{title}</h4>
              <p>{description}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="home-bottom-grid">
        <section className="home-section">
          <div className="home-section-header">
            <h3>How it works</h3>
          </div>
          <ol className="home-steps">
            {STEPS.map(({ step, title, text }) => (
              <li key={step} className="home-step">
                <span className="home-step-num">{step}</span>
                <div>
                  <strong>{title}</strong>
                  <p>{text}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="home-section">
          <div className="home-section-header">
            <h3>
              <HistoryIcon className="home-section-icon" />
              Recent sessions
            </h3>
          </div>
          {recentSessions.length === 0 ? (
            <div className="home-recent-empty card">
              <NotesIcon />
              <p>No sessions yet — start with Quick Start above.</p>
            </div>
          ) : (
            <div className="home-recent-list">
              {recentSessions.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  className="home-recent-item card"
                  onClick={() => onSelectSession(session.id)}
                >
                  <span className="home-recent-source">
                    {sourceIcon(session.source_type, "home-recent-source-icon")}
                  </span>
                  <span className="home-recent-info">
                    <strong>{plainTitle(session.title)}</strong>
                    <small>{formatDate(session.created_at)}</small>
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
