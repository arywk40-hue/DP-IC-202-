import React, { useState } from 'react';
import { RPC_COMMANDS, sendRpc, RpcTimeoutError } from '../api/client';

export default function RpcMenu({ nodeId, nodeName, onClose, available = false }) {
  const [pending, setPending] = useState(null); // command code currently in flight
  const [results, setResults] = useState({}); // code -> 'ok' | 'unconfirmed' | 'error'

  async function handleSend(cmd) {
    setPending(cmd.code);
    try {
      await sendRpc(nodeId, cmd.code);
      setResults((r) => ({ ...r, [cmd.code]: 'ok' }));
    } catch (err) {
      // Per report §risk-analysis: no ACK = treat as unconfirmed, never assume success.
      if (err instanceof RpcTimeoutError) {
        setResults((r) => ({ ...r, [cmd.code]: 'unconfirmed' }));
      } else {
        setResults((r) => ({ ...r, [cmd.code]: 'error' }));
      }
    } finally {
      setPending(null);
    }
  }

  if (!nodeId) return null;

  return (
    <div className="rpc-overlay" onClick={onClose}>
      <div className="rpc-menu" onClick={(e) => e.stopPropagation()}>
        <div className="rpc-menu-header">
          <span>Commands — {nodeName}</span>
          <button className="rpc-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <p className="evidence-note">{available ? 'Commands require a verified hardware ACK.' : 'No connected hardware command transport. Commands are disabled.'}</p>
        <ul>
          {RPC_COMMANDS.map((cmd) => {
            const state = results[cmd.code];
            return (
              <li key={cmd.code} className="rpc-row">
                <span className="rpc-label">{cmd.label}</span>
                <div className="rpc-action">
                  {state === 'ok' && <span className="rpc-status rpc-ok">Confirmed</span>}
                  {state === 'unconfirmed' && (
                    <span className="rpc-status rpc-unconfirmed">Not confirmed</span>
                  )}
                  {state === 'error' && <span className="rpc-status rpc-error">Error</span>}
                  <button
                    className="rpc-send-btn"
                    disabled={!available || pending !== null}
                    onClick={() => handleSend(cmd)}
                  >
                    {pending === cmd.code ? 'Sending…' : 'Send'}
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
