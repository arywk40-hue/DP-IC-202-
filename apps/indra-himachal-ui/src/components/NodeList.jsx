import React from "react";
import { locationName, ageLabel } from "../api/presentation";
export default function NodeList({ nodes, selectedId, onSelect }) {
  return (
    <aside className="node-list" aria-label="Locations">
      <div className="panel-title">
        Locations <span className="panel-count">{nodes.length}</span>
      </div>
      {!nodes.length && (
        <p className="empty-message">
          Your locations will appear here when readings are available.
        </p>
      )}
      <ul>
        {nodes.map((node) => (
          <li
            key={node.id}
            className={`node-row ${node.id === selectedId ? "node-row-active" : ""}`}
          >
            <button
              type="button"
              className="location-button"
              aria-pressed={node.id === selectedId}
              onClick={() => onSelect(node.id)}
            >
              <span
                className={`health-dot ${node.stale ? "health-late" : "health-ok"}`}
              />
              <span className="node-row-text">
                <span className="node-row-name">{locationName(node)}</span>
                <span className="node-row-meta">
                  {node.lat?.toFixed(3)}° N, {node.lng?.toFixed(3)}° E
                </span>
                <span className="node-row-age">
                  {ageLabel(node.lastSeen)}
                  {node.stale ? " · Older reading" : ""}
                </span>
              </span>
              <span className="location-chevron" aria-hidden="true">
                ›
              </span>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
