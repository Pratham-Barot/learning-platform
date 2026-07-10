import { useCallback, useEffect, useState } from "react";
import { fetchMe, fetchSession, fetchSessions } from "./api/client";
import { clearAuth, getStoredUser, isLoggedIn } from "./auth/storage";
import AccountPage from "./components/AccountPage";
import AppSidebar, { type MainView } from "./components/AppSidebar";
import AuthPage from "./components/AuthPage";
import ChatTab from "./components/ChatTab";
import HomeDashboard from "./components/HomeDashboard";
import InputForm from "./components/InputForm";
import NotesTab from "./components/NotesTab";
import QuizTab from "./components/QuizTab";
import {
  ChatIcon,
  MenuIcon,
  NotesIcon,
  QuizIcon,
  sourceIcon,
} from "./components/icons";
import type { SessionDetail, SessionSummary, SourceType, User } from "./types";
import "./App.css";

type Tab = "notes" | "quiz" | "chat";

const SIDEBAR_STORAGE_KEY = "studyforge-sidebar-open";

function getInitialSidebarOpen(): boolean {
  return localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true";
}

const TABS: { id: Tab; label: string; icon: typeof NotesIcon }[] = [
  { id: "notes", label: "Notes", icon: NotesIcon },
  { id: "quiz", label: "Quiz", icon: QuizIcon },
  { id: "chat", label: "Chat", icon: ChatIcon },
];

function App() {
  const [authed, setAuthed] = useState(isLoggedIn());
  const [user, setUser] = useState<User | null>(getStoredUser());
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<SessionDetail | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("notes");
  const [sidebarOpen, setSidebarOpen] = useState(getInitialSidebarOpen);
  const [mainView, setMainView] = useState<MainView>("home");
  const [selectedSource, setSelectedSource] = useState<SourceType>("youtube");

  useEffect(() => {
    localStorage.setItem(SIDEBAR_STORAGE_KEY, String(sidebarOpen));
  }, [sidebarOpen]);

  const refreshSessions = useCallback(async () => {
    const data = await fetchSessions();
    setSessions(data);
  }, []);

  const loadSession = useCallback(async (id: number) => {
    const data = await fetchSession(id);
    setActiveSession(data);
    setActiveTab("notes");
    setMainView("session");
  }, []);

  const bootstrap = useCallback(async () => {
    try {
      const me = await fetchMe();
      setUser(me);
      setAuthed(true);
      await refreshSessions();
    } catch {
      clearAuth();
      setAuthed(false);
      setUser(null);
    }
  }, [refreshSessions]);

  useEffect(() => {
    if (isLoggedIn()) bootstrap().catch(console.error);
  }, [bootstrap]);

  const handleLogout = () => {
    clearAuth();
    setAuthed(false);
    setUser(null);
    setSessions([]);
    setActiveSession(null);
    setMainView("home");
  };

  const handleSelectSource = (source: SourceType) => {
    setSelectedSource(source);
    setMainView("create");
    setSidebarOpen(false);
  };

  const handleSelectHome = () => {
    setMainView("home");
    setSidebarOpen(false);
  };

  const handleSelectAccount = () => {
    setMainView("account");
    setSidebarOpen(false);
  };

  const handleSelectSession = (id: number) => {
    loadSession(id).catch(console.error);
    setSidebarOpen(false);
  };

  if (!authed) {
    return <AuthPage onSuccess={bootstrap} />;
  }

  return (
    <div className={`app-shell ${sidebarOpen ? "sidebar-open" : "sidebar-closed"}`}>
      <AppSidebar
        sessions={sessions}
        activeSessionId={activeSession?.id ?? null}
        selectedSource={selectedSource}
        mainView={mainView}
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((o) => !o)}
        onSelectHome={handleSelectHome}
        onSelectAccount={handleSelectAccount}
        onSelectSource={handleSelectSource}
        onSelectSession={handleSelectSession}
        onRefresh={refreshSessions}
        onDeleted={(id) => {
          if (activeSession?.id === id) {
            setActiveSession(null);
            setMainView("home");
          }
        }}
      />

      <main className="main-content">
        <header className="top-bar">
          <div className="top-bar-left">
            <button
              type="button"
              className="menu-btn"
              onClick={() => setSidebarOpen((o) => !o)}
              title={sidebarOpen ? "Close menu" : "Open menu"}
              aria-label={sidebarOpen ? "Close menu" : "Open menu"}
              aria-expanded={sidebarOpen}
            >
              <MenuIcon />
            </button>
            <div className="top-bar-info">
              <h1>
                {mainView === "create"
                  ? "New Study Session"
                  : mainView === "session"
                    ? "Study Session"
                    : mainView === "account"
                      ? "Account"
                      : "Home"}
              </h1>
              <p>
                {mainView === "create"
                  ? "Add your source and generate AI study material"
                  : mainView === "session"
                    ? "Review notes, quiz, and chat for this session"
                    : mainView === "account"
                      ? "Manage your profile and preferences"
                      : "Your AI-powered study workspace"}
              </p>
            </div>
          </div>
        </header>

        {mainView === "create" && (
          <InputForm
            sourceType={selectedSource}
            onGenerated={async (sessionId) => {
              await refreshSessions();
              await loadSession(sessionId);
            }}
          />
        )}

        {mainView === "session" && activeSession && (
          <section className="card session-panel">
            <div className="session-panel-header">
              <h2>{activeSession.title}</h2>
              <span className="session-source-badge">
                {sourceIcon(activeSession.source_type)}
                {activeSession.source_type === "web"
                  ? "blog"
                  : activeSession.source_type}
              </span>
            </div>

            <div className="tabs">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  className={activeTab === id ? "active" : ""}
                  onClick={() => setActiveTab(id)}
                >
                  <Icon />
                  {label}
                </button>
              ))}
            </div>

            {activeTab === "notes" && <NotesTab session={activeSession} />}
            {activeTab === "quiz" && (
              <QuizTab
                session={activeSession}
                onSessionUpdated={(updated) => setActiveSession(updated)}
              />
            )}
            {activeTab === "chat" && <ChatTab sessionId={activeSession.id} />}
          </section>
        )}

        {mainView === "home" && (
          <HomeDashboard
            user={user}
            sessions={sessions}
            onSelectSource={handleSelectSource}
            onSelectSession={handleSelectSession}
          />
        )}

        {mainView === "account" && (
          <AccountPage user={user} sessions={sessions} onLogout={handleLogout} />
        )}
      </main>
    </div>
  );
}

export default App;
