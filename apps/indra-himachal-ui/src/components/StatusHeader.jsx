import React from 'react';

function formatUptime(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function timeAgo(ts) {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

export default function StatusHeader({
  status,
  isLive,
  cachedAt,
  nodeCount,
  versionMismatch,
  showHeatmap,
  onToggleHeatmap
}) {
  return (
    <>
    <header className="status-header">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true" />
        <div>
          <div className="brand-title">INDRA · MESH DASHBOARD</div>
          <div className="brand-subtitle">Six-channel Himalayan research prototype</div>
        </div>
      </div>

      <div className="status-metrics">
        <div className="metric">
          <span className="metric-label">Nodes</span>
          <span className="metric-value">{nodeCount}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Service uptime</span>
          <span className="metric-value">
            {status ? formatUptime(status.uptimeSeconds) : '—'}
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Master battery</span>
          <span className="metric-value">
            {Number.isFinite(status?.batteryVoltage) ? `${status.batteryVoltage.toFixed(2)} V` : 'Not measured'}
          </span>
        </div>
      </div>

      <button
        type="button"
        className={`heat-toggle ${showHeatmap ? 'heat-toggle-on' : ''}`}
        onClick={onToggleHeatmap}
      >
        Spatial overlay {showHeatmap ? 'on' : 'off'}
      </button>
      <div className={`sync-pill ${isLive ? 'sync-live' : 'sync-stale'}`}>
        <span className="sync-dot" />
        {isLive ? 'API connected' : `Cached · synced ${cachedAt ? timeAgo(cachedAt) : 'unknown'}`}
      </div>
    </header>
    {versionMismatch && (
      <div className="version-banner">
        Master API version does not match this dashboard. Force-refresh the PWA
        after a firmware/schema update (report §2, App Bundle).
      </div>
    )}
    </>
  );
}
