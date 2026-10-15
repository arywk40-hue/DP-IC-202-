import React from 'react';

const STALE_AFTER_MS = 2 * 5 * 60 * 1000;

function nodeHealth(lastSeen) {
  const age = Date.now() - lastSeen;
  if (age < 5 * 60 * 1000) return 'ok';
  if (age < STALE_AFTER_MS) return 'late';
  return 'offline';
}

function timeAgo(ts) {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

export default function NodeList({ nodes, selectedId, onSelect, onOpenRpc }) {
  const live = nodes.filter((n) => nodeHealth(n.lastSeen) === 'ok').length;

  return (
    <div className="node-list">
      <div className="panel-title">
        Mesh nodes
        <span className="panel-count">
          {live}/{nodes.length} live
        </span>
      </div>
      <ul>
        {nodes.map((node) => {
          const health = nodeHealth(node.lastSeen);
          return (
            <li
              key={node.id}
              className={`node-row ${node.id === selectedId ? 'node-row-active' : ''}`}
              onClick={() => onSelect(node.id)}
            >
              <span className={`health-dot health-${health}`} />
              <div className="node-row-text">
                <div className="node-row-name">{node.name}</div>
                <div className="node-row-meta">
                  {timeAgo(node.lastSeen)} ago · {node.battery.toFixed(2)} V
                </div>
              </div>
              <div className="node-row-flags">
                {node.anomalyIndex > 0 && <span className="badge badge-danger">ALERT</span>}
                {health === 'offline' && <span className="badge badge-danger">OFFLINE</span>}
                {health === 'late' && <span className="badge badge-warning">LATE</span>}
                <button
                  type="button"
                  className="node-rpc-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenRpc(node.id);
                  }}
                >
                  RPC
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
