import type { SessionSummary, User } from "../types";
import ThemeToggle from "./ThemeToggle";
import {
  FileIcon,
  GlobeIcon,
  LogOutIcon,
  NotesIcon,
  UserIcon,
  YoutubeIcon,
} from "./icons";

interface Props {
  user: User | null;
  sessions: SessionSummary[];
  onLogout: () => void;
}

export default function AccountPage({ user, sessions, onLogout }: Props) {
  const userInitial =
    user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || "?";
  const displayName = user?.full_name?.trim() || "Student";

  const sourceCounts = sessions.reduce(
    (acc, s) => {
      acc[s.source_type] = (acc[s.source_type] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <div className="account-page">
      <section className="account-hero card">
        <div className="account-hero-profile">
          <div className="account-avatar">{userInitial}</div>
          <div>
            <h2>{displayName}</h2>
            <p>{user?.email}</p>
          </div>
        </div>
        <div className="account-hero-badge">
          <UserIcon />
          StudyForge member
        </div>
      </section>

      <section className="account-section">
        <div className="account-section-header">
          <h3>Your activity</h3>
          <p>Overview of your study sessions</p>
        </div>
        <div className="account-stats-grid">
          <div className="account-stat-card card">
            <strong>{sessions.length}</strong>
            <span>Total sessions</span>
          </div>
          <div className="account-stat-card card">
            <strong>{sourceCounts.youtube || 0}</strong>
            <span>YouTube sessions</span>
          </div>
          <div className="account-stat-card card">
            <strong>{sourceCounts.document || 0}</strong>
            <span>Document sessions</span>
          </div>
          <div className="account-stat-card card">
            <strong>{sourceCounts.web || 0}</strong>
            <span>Blog sessions</span>
          </div>
          <div className="account-stat-card card">
            <strong>{sessions.length > 0 ? "Active" : "—"}</strong>
            <span>{sessions.length > 0 ? "Learning status" : "No sessions yet"}</span>
          </div>
        </div>
      </section>

      <div className="account-panels">
        <section className="account-section">
          <div className="account-section-header">
            <h3>Profile</h3>
          </div>
          <div className="account-info-card card">
            <div className="account-info-row">
              <span className="account-info-label">Full name</span>
              <span className="account-info-value">{user?.full_name || "Not set"}</span>
            </div>
            <div className="account-info-row">
              <span className="account-info-label">Email</span>
              <span className="account-info-value">{user?.email}</span>
            </div>
            <div className="account-info-row">
              <span className="account-info-label">User ID</span>
              <span className="account-info-value">#{user?.id}</span>
            </div>
          </div>
        </section>

        <section className="account-section">
          <div className="account-section-header">
            <h3>Preferences</h3>
          </div>
          <div className="account-info-card card">
            <div className="account-pref-row">
              <div>
                <strong>Appearance</strong>
                <p>Switch between light and dark mode</p>
              </div>
              <ThemeToggle />
            </div>
          </div>
        </section>
      </div>

      {sessions.length > 0 && (
        <section className="account-section">
          <div className="account-section-header">
            <h3>Source breakdown</h3>
          </div>
          <div className="account-source-grid">
            <div className="account-source-item card">
              <YoutubeIcon />
              <span>YouTube</span>
              <strong>{sourceCounts.youtube || 0}</strong>
            </div>
            <div className="account-source-item card">
              <FileIcon />
              <span>Documents</span>
              <strong>{sourceCounts.document || 0}</strong>
            </div>
            <div className="account-source-item card">
              <GlobeIcon />
              <span>Blogs</span>
              <strong>{sourceCounts.web || 0}</strong>
            </div>
          </div>
        </section>
      )}

      {sessions.length === 0 && (
        <div className="account-empty card">
          <NotesIcon />
          <p>You haven&apos;t created any study sessions yet. Head to Home to get started.</p>
        </div>
      )}

      <section className="account-section">
        <div className="account-danger-card card">
          <div>
            <strong>Sign out</strong>
            <p>Log out of StudyForge on this device</p>
          </div>
          <button type="button" className="account-logout-btn" onClick={onLogout}>
            <LogOutIcon />
            Log out
          </button>
        </div>
      </section>
    </div>
  );
}
