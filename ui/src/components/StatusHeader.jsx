import React from "react";
import { useAuth } from "../context/AuthContext";

export default function StatusHeader({
  isLive,
  mandiConnected,
  cachedAt,
  versionMismatch,
  view,
  onViewChange,
  onOpenAuth,
}) {
  const { user } = useAuth();

  return (
    <>
      <header className="status-header">
        <a
          className="brand"
          href="#observations"
          onClick={(e) => {
            e.preventDefault();
            onViewChange("observations");
          }}
          aria-label="INDRA home"
        >
          <svg
            className="brand-mark"
            viewBox="0 0 32 32"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M4 22 12 8l6 10 4-6 6 10M4 27h24"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx="24" cy="6" r="2" fill="currentColor" />
          </svg>
          <span>
            <strong>INDRA</strong>
            <small>Local weather</small>
          </span>
        </a>
        <nav className="primary-nav" aria-label="Main navigation">
          {[
            ["observations", "Observations"],
            ["parameters", "Parameters"],
            ["system", "System"],
            ["apis", "APIs"],
          ].map(([id, label]) => (
            <button
              key={id}
              type="button"
              aria-current={view === id ? "page" : undefined}
              className={view === id ? "nav-active" : ""}
              onClick={() => onViewChange(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="header-right-group">
          <button
            type="button"
            className={`auth-header-btn ${user ? "logged-in" : ""}`}
            onClick={onOpenAuth}
            aria-label={user ? `Profile: ${user.name}` : "Sign in with Google"}
          >
            {user ? (
              <>
                {user.picture ? (
                  <img
                    src={user.picture}
                    alt=""
                    className="auth-header-avatar"
                  />
                ) : (
                  <span className="auth-header-avatar-initial">
                    {user.name ? user.name[0].toUpperCase() : "U"}
                  </span>
                )}
                <span className="auth-header-name">{user.name}</span>
                <span className="auth-header-tag">{user.provider === "google" ? "Google" : "Demo"}</span>
              </>
            ) : (
              <>
                <svg className="google-icon-sm" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>Sign in with Google</span>
              </>
            )}
          </button>
          <div
            className={`sync-pill ${isLive ? "sync-live" : "sync-stale"}`}
            role="status"
          >
            <span className="sync-dot" />
            {isLive && mandiConnected
              ? "Connected"
              : cachedAt
                ? "Offline · Mandi data saved"
                : isLive
                  ? "Mandi API offline"
                  : "Connecting…"}
          </div>
        </div>
      </header>
      {versionMismatch && (
        <div className="version-banner" role="alert">
          An update is available. Refresh this page to reconnect.
        </div>
      )}
    </>
  );
}
