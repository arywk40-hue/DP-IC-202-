/**
 * Lab stand-in for Master firmware (api.cpp).
 * Usage: node mock-master.mjs
 * Then set MASTER_BASE_URL = 'http://127.0.0.1:8080' in src/api/client.js
 */
import http from 'node:http';

const PORT = 8080;
const ANOMALY_LABELS = ['Normal', 'Rain', 'Thunderstorm', 'High PM2.5', 'Radiation Spike'];

function nodes() {
  const now = Date.now();
  return [
    { id: '01', lat: 31.7076, lng: 76.9366, name: 'Node 01 — Ridge', lastSeen: now - 45_000, battery: 3.31 },
    { id: '02', lat: 31.7112, lng: 76.9420, name: 'Node 02 — Valley', lastSeen: now - 120_000, battery: 3.18 },
    { id: '03', lat: 31.7050, lng: 76.9300, name: 'Node 03 — Slope', lastSeen: now - 3_600_000, battery: 3.02 },
    { id: '04', lat: 31.7140, lng: 76.9280, name: 'Node 04 — Field', lastSeen: now - 30_000, battery: 3.29 }
  ];
}

function telemetry(id) {
  const node = nodes().find((n) => n.id === id) ?? nodes()[0];
  const anomaly = id === '02' ? 1 : 0;
  return {
    id,
    timestamp: node.lastSeen,
    anomalyIndex: anomaly,
    anomalyLabel: ANOMALY_LABELS[anomaly],
    battery: node.battery,
    sensors: {
      temperature_c: 22.4,
      humidity_pct: 58,
      pressure_hpa: 913.2,
      voc_iaq: 74,
      wind_speed_ms: 2.1,
      wind_dir_deg: 214,
      rain_mm: anomaly === 1 ? 4.2 : 0,
      pm25_ugm3: 12,
      pm10_ugm3: 19,
      uv_index: 3,
      radiation_cpm: 18
    }
  };
}

function heatmap() {
  return {
    type: 'FeatureCollection',
    features: nodes().map((n) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [n.lng, n.lat] },
      properties: { intensity: n.id === '02' ? 0.9 : 0.35 }
    }))
  };
}

function json(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(payload),
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  });
  res.end(payload);
}

const server = http.createServer(async (req, res) => {
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    });
    res.end();
    return;
  }

  const url = new URL(req.url, `http://127.0.0.1:${PORT}`);
  const { pathname } = url;

  if (req.method === 'GET' && pathname === '/api/nodes') {
    json(res, 200, nodes());
    return;
  }
  if (req.method === 'GET' && pathname === '/api/status') {
    json(res, 200, {
      uptimeSeconds: Math.floor(process.uptime()),
      batteryVoltage: 3.34,
      meshNodeCount: nodes().length,
      appVersion: '0.1.0'
    });
    return;
  }
  if (req.method === 'GET' && pathname === '/api/kriging/heatmap') {
    json(res, 200, heatmap());
    return;
  }
  const tel = pathname.match(/^\/api\/nodes\/([^/]+)\/telemetry$/);
  if (req.method === 'GET' && tel) {
    json(res, 200, telemetry(tel[1]));
    return;
  }
  const rpc = pathname.match(/^\/api\/rpc\/([^/]+)$/);
  if (req.method === 'POST' && rpc) {
    let raw = '';
    for await (const chunk of req) raw += chunk;
    let body = {};
    try {
      body = raw ? JSON.parse(raw) : {};
    } catch {
      json(res, 400, { error: 'invalid json' });
      return;
    }
    json(res, 200, { ok: true, nodeId: rpc[1], command: body.command ?? null });
    return;
  }

  json(res, 404, { error: 'not found', path: pathname });
});

server.listen(PORT, () => {
  console.log(`Mock Master API at http://127.0.0.1:${PORT}`);
  console.log('Point mesh-dashboard MASTER_BASE_URL at this origin.');
});
