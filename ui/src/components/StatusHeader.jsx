import React from "react";
export default function StatusHeader({
  isLive,
  cachedAt,
  versionMismatch,
  view,
  onViewChange,
}) {
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
        <div
          className={`sync-pill ${isLive ? "sync-live" : "sync-stale"}`}
          role="status"
        >
          <span className="sync-dot" />
          {isLive
            ? "Connected"
            : cachedAt
              ? "Offline · saved data"
              : "Connecting…"}
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
