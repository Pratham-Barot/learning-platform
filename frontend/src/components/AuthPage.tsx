import { useState } from "react";
import { loginUser, registerUser } from "../api/client";
import ThemeToggle from "./ThemeToggle";
import { BookIcon, ChatIcon, NotesIcon, QuizIcon } from "./icons";

interface Props {
  onSuccess: () => void;
}

export default function AuthPage({ onSuccess }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await loginUser(email, password);
      } else {
        await registerUser({ email, password, fullName: fullName || undefined });
      }
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-top-bar">
        <ThemeToggle />
      </div>
      <div className="auth-hero">
        <div className="auth-hero-brand">
          <BookIcon className="brand-icon" />
          <h1>StudyForge</h1>
        </div>
        <h2>Turn any source into study material</h2>
        <p>
          Upload PDFs, paste YouTube links, or share web articles — get AI-generated
          notes, quizzes, and a chat tutor in seconds.
        </p>
        <div className="auth-features">
          <div className="auth-feature">
            <NotesIcon className="auth-feature-icon" />
            Structured notes with key concepts
          </div>
          <div className="auth-feature">
            <QuizIcon className="auth-feature-icon" />
            Interactive quizzes with explanations
          </div>
          <div className="auth-feature">
            <ChatIcon className="auth-feature-icon" />
            RAG-powered chat over your content
          </div>
        </div>
      </div>

      <div className="auth-panel">
        <div className="auth-card">
          <h2>{mode === "login" ? "Welcome back" : "Create account"}</h2>
          <p>
            {mode === "login"
              ? "Sign in to access your study sessions"
              : "Get started with your free account"}
          </p>

          <form onSubmit={handleSubmit} className="auth-form">
            {mode === "register" && (
              <div className="input-field">
                <label htmlFor="fullName">Full name</label>
                <input
                  id="fullName"
                  type="text"
                  placeholder="Optional"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>
            )}
            <div className="input-field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="input-field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                placeholder="Min. 6 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={6}
                required
              />
            </div>
            <button type="submit" className="btn-primary" disabled={loading} style={{ width: "100%" }}>
              {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
            </button>
          </form>

          {error && <p className="error">{error}</p>}

          <button
            type="button"
            className="link-btn"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login"
              ? "Don't have an account? Register"
              : "Already have an account? Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}
