// ─────────────────────────────────────────────────────────────────────────
// API CLIENT — talks to the Master Node's REST API.
//
// INTEGRATION POINT: This is the ONLY file you need to touch to connect
// this dashboard to the real Master Node firmware. Everything else
// (components, state, map) consumes the functions exported here and
// does not care whether the data came from the real ESP32-S3 or from
// the mock fixtures below.
//
// Endpoints implemented against (per project spec, Section 13.1):
//   GET  /api/nodes
//   GET  /api/nodes/{id}/telemetry
//   GET  /api/kriging/heatmap
//   POST /api/rpc/{id}
//   GET  /api/status
// ─────────────────────────────────────────────────────────────────────────

import { ANOMALY_LABELS, normalizeHeatmap } from './contract';

// Set this to the Master Node's AP address once you're testing against
// real firmware, e.g. 'http://192.168.4.1', or 'http://127.0.0.1:8080' for
// `node mock-master.mjs`. Leave as null to run entirely on in-browser mocks.
const MASTER_BASE_URL = null; // e.g. 'http://192.168.4.1'

const USE_MOCK = MASTER_BASE_URL === null;

// RPC opcodes — MUST stay in sync with firmware/rpc.h (Section 9 of overview).
export const RPC_COMMANDS = [
  { code: 0x01, name: 'CMD_FORCE_INFERENCE', label: 'Force sensor read + inference' },
  { code: 0x02, name: 'CMD_SEND_TELEMETRY', label: 'Request telemetry now' },
  { code: 0x03, name: 'CMD_UPDATE_THRESH', label: 'Update anomaly threshold' },
  { code: 0x04, name: 'CMD_SET_SLEEP_PERIOD', label: 'Set sleep interval (s)' },
  { code: 0x05, name: 'CMD_DISABLE_PERIPH', label: 'Disable a peripheral' },
  { code: 0x06, name: 'CMD_REBOOT', label: 'Reboot node' },
  { code: 0x07, name: 'CMD_SYNC_NONCE', label: 'Resync nonce' },
  { code: 0x08, name: 'CMD_GET_BATTERY', label: 'Get battery voltage' }
];

const MOCK_BOOT_MS = Date.now() - 186_420 * 1000;

const MOCK_PROFILES = {
  '01': {
    name: 'Node 01 — Ridge',
    lat: 31.7076,
    lng: 76.9366,
    lastSeenAgo: 45_000,
    battery: 3.31,
    anomaly: 0,
    sensors: {
      temperature_c: 18.6,
      humidity_pct: 41,
      pressure_hpa: 901.4,
      voc_iaq: 52,
      wind_speed_ms: 4.8,
      wind_dir_deg: 278,
      rain_mm: 0,
      pm25_ugm3: 9,
      pm10_ugm3: 14,
      uv_index: 7,
      radiation_cpm: 16,
      lightning_km: 0,
      soil_temp_c: 16.1,
      soil_rh_pct: 38
    }
  },
  '02': {
    name: 'Node 02 — Valley',
    lat: 31.7112,
    lng: 76.9420,
    lastSeenAgo: 120_000,
    battery: 3.18,
    anomaly: 1,
    sensors: {
      temperature_c: 21.2,
      humidity_pct: 86,
      pressure_hpa: 912.8,
      voc_iaq: 61,
      wind_speed_ms: 1.4,
      wind_dir_deg: 192,
      rain_mm: 4.2,
      pm25_ugm3: 18,
      pm10_ugm3: 27,
      uv_index: 1,
      radiation_cpm: 19,
      lightning_km: 12,
      soil_temp_c: 19.4,
      soil_rh_pct: 79
    }
  },
  '03': {
    name: 'Node 03 — Slope',
    lat: 31.7050,
    lng: 76.9300,
    lastSeenAgo: 3_600_000,
    battery: 3.02,
    anomaly: 0,
    sensors: {
      temperature_c: 19.1,
      humidity_pct: 54,
      pressure_hpa: 907.0,
      voc_iaq: 70,
      wind_speed_ms: 2.6,
      wind_dir_deg: 221,
      rain_mm: 0,
      pm25_ugm3: 11,
      pm10_ugm3: 17,
      uv_index: 4,
      radiation_cpm: 15,
      lightning_km: 0,
      soil_temp_c: 17.8,
      soil_rh_pct: 44
    }
  },
  '04': {
    name: 'Node 04 — Field',
    lat: 31.7140,
    lng: 76.9280,
    lastSeenAgo: 30_000,
    battery: 3.29,
    anomaly: 0,
    sensors: {
      temperature_c: 23.8,
      humidity_pct: 48,
      pressure_hpa: 913.6,
      voc_iaq: 58,
      wind_speed_ms: 3.1,
      wind_dir_deg: 245,
      rain_mm: 0,
      pm25_ugm3: 13,
      pm10_ugm3: 21,
      uv_index: 6,
      radiation_cpm: 17,
      lightning_km: 0,
      soil_temp_c: 22.0,
      soil_rh_pct: 51
    }
  }
};

function mockNodeList() {
  const now = Date.now();
  return Object.entries(MOCK_PROFILES).map(([id, p]) => ({
    id,
    lat: p.lat,
    lng: p.lng,
    name: p.name,
    lastSeen: now - p.lastSeenAgo,
    battery: p.battery,
    anomalyIndex: p.anomaly
  }));
}

function mockTelemetry(nodeId) {
  const node = mockNodeList().find((n) => n.id === nodeId) ?? mockNodeList()[0];
  const profile = MOCK_PROFILES[node.id];
  return {
    id: nodeId,
    timestamp: node.lastSeen,
    anomalyIndex: profile.anomaly,
    anomalyLabel: ANOMALY_LABELS[profile.anomaly] ?? 'Unknown',
    battery: node.battery,
    sensors: { ...profile.sensors }
  };
}

/** Inverse-distance stand-in for Master Spatial Kriging (demo only). */
function mockKrigingGrid() {
  const list = mockNodeList();
  const lats = list.map((n) => n.lat);
  const lngs = list.map((n) => n.lng);
  const latMin = Math.min(...lats) - 0.004;
  const latMax = Math.max(...lats) + 0.004;
  const lngMin = Math.min(...lngs) - 0.004;
  const lngMax = Math.max(...lngs) + 0.004;
  const features = [];
  for (let lat = latMin; lat <= latMax; lat += 0.0012) {
    for (let lng = lngMin; lng <= lngMax; lng += 0.0012) {
      let num = 0;
      let den = 0;
      for (const n of list) {
        const d2 = (lat - n.lat) ** 2 + (lng - n.lng) ** 2 + 1e-10;
        const w = 1 / d2;
        const z = MOCK_PROFILES[n.id].anomaly > 0 ? 0.95 : 0.28;
        num += w * z;
        den += w;
      }
      features.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [lng, lat] },
        properties: { intensity: Math.min(1, num / den) }
      });
    }
  }
  return { type: 'FeatureCollection', features };
}

// ── Public API surface ─────────────────────────────────────────────────

export async function getNodes() {
  if (USE_MOCK) {
    await delay(150);
    return mockNodeList();
  }
  return apiGet('/api/nodes');
}

export async function getTelemetry(nodeId) {
  if (USE_MOCK) {
    await delay(150);
    return mockTelemetry(nodeId);
  }
  return apiGet(`/api/nodes/${nodeId}/telemetry`);
}

export async function getHeatmap() {
  if (USE_MOCK) {
    await delay(200);
    return normalizeHeatmap(mockKrigingGrid());
  }
  return normalizeHeatmap(await apiGet('/api/kriging/heatmap'));
}

export async function getStatus() {
  if (USE_MOCK) {
    await delay(100);
    return {
      uptimeSeconds: Math.floor((Date.now() - MOCK_BOOT_MS) / 1000),
      batteryVoltage: 3.34,
      meshNodeCount: mockNodeList().length,
      appVersion: '0.1.0'
    };
  }
  return apiGet('/api/status');
}

export async function sendRpc(nodeId, commandCode, params = {}) {
  if (USE_MOCK) {
    await delay(400);
    // Simulate the crypto module's silent-rejection behavior ~10% of the time,
    // so the UI's "unconfirmed" state is exercised during frontend dev.
    if (Math.random() < 0.1) {
      throw new RpcTimeoutError(nodeId, commandCode);
    }
    return { ok: true, nodeId, commandCode, params };
  }
  return apiPost(`/api/rpc/${nodeId}`, { command: commandCode, ...params });
}

// ── Error type for unconfirmed / silently-rejected RPC commands ───────────
// The overview (Section 6.3) states a bad MIC or nonce causes SILENT
// rejection on the Slave side — no error is sent back. So the dashboard
// must treat "no response within timeout" as failure, never as success.
export class RpcTimeoutError extends Error {
  constructor(nodeId, commandCode) {
    super(`No ACK received from node ${nodeId} for command 0x${commandCode.toString(16)}`);
    this.name = 'RpcTimeoutError';
    this.nodeId = nodeId;
    this.commandCode = commandCode;
  }
}

// ── Low-level fetch helpers (used once MASTER_BASE_URL is set) ────────────
const RPC_TIMEOUT_MS = 2000; // Master/mesh round trip budget — tune once
                              // real AODV route-discovery timing is known
                              // (per report handoff note to Abhinav/Comms).

async function apiGet(path) {
  const res = await fetchWithTimeout(`${MASTER_BASE_URL}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetchWithTimeout(`${MASTER_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), RPC_TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(t);
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
