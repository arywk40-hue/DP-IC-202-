// INDRA adapter integration. No silent fallback to invented live readings.
import { DASHBOARD_API_VERSION, normalizeHeatmap } from './contract.js';

export const MASTER_BASE_URL = (import.meta.env?.VITE_MASTER_BASE_URL ?? '').replace(/\/$/, '');
export const CACHE_SCOPE = `${DASHBOARD_API_VERSION}:${MASTER_BASE_URL || 'same-origin'}`;
export const RPC_COMMANDS = [
  { code: 0x01, label: 'Force sensor read + inference' },
  { code: 0x02, label: 'Request telemetry' },
  { code: 0x08, label: 'Get battery voltage' }
];
export class RpcTimeoutError extends Error {}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const res = await fetch(`${MASTER_BASE_URL}${path}`, { ...options, signal: controller.signal, cache: 'no-store' });
    if (!res.ok) throw new Error(`INDRA API ${res.status}: ${await res.text()}`);
    return await res.json();
  } catch (error) {
    if (options.method === 'POST' && error.name === 'AbortError') throw new RpcTimeoutError('No hardware ACK');
    throw error;
  } finally { clearTimeout(timer); }
}
export const getNodes = () => request('/api/nodes');
export const getStatus = () => request('/api/status');
export const getModelLab = () => request('/api/model-lab');
export const getStormReport = () => request('/api/storm-risk/report');
export const getStormScores = () => request('/api/storm-risk/scores');
export const getStormHeatmap = (feature) => request(`/api/storm-risk/heatmap?feature=${encodeURIComponent(feature)}`);
export const getTelemetry = (id) => request(`/api/nodes/${encodeURIComponent(id)}/telemetry`);
export const getHeatmap = async () => {
  const payload = await request('/api/kriging/heatmap');
  return { points: normalizeHeatmap(payload), status: payload.status, reason: payload.reason };
};
export async function sendRpc(id, command, params = {}) {
  const ack = await request(`/api/rpc/${encodeURIComponent(id)}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ command, ...params })
  });
  // A queued/accepted HTTP request is not a hardware acknowledgement.
  if (ack?.confirmed !== true || ack.nodeId !== id || ack.command !== command) throw new RpcTimeoutError('No verified hardware ACK');
  return ack;
}
