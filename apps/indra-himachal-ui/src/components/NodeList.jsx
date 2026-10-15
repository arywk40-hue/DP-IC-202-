import React from 'react';



function nodeHealth(lastSeen, interval = 300) {
  const age = Date.now() - lastSeen;
  if (age < Math.max(120, interval) * 1000) return 'ok';
  if (age < Math.max(120, interval * 2) * 1000) return 'late';
  return 'offline';
}

function timeAgo(ts) {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

export default function NodeList({ nodes, selectedId, onSelect, onOpenRpc }) {
  const live = nodes.filter((n) => nodeHealth(n.lastSeen, n.reportingIntervalSeconds) === 'ok').length;

  return (
    <div className="node-list">
      <div className="panel-title">
        Mesh nodes
        <span className="panel-count">
          {live}/{nodes.length} recent
        </span>
      </div>
      <ul>
        {nodes.map((node) => {
          const health = nodeHealth(node.lastSeen, node.reportingIntervalSeconds);
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
                  {timeAgo(node.lastSeen)} ago · {node.sourceClass} · {Number.isFinite(node.battery) ? `${node.battery.toFixed(2)} V` : 'Battery unknown'}
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
