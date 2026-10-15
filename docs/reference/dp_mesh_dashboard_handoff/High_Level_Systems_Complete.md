# High Level Systems — Complete Architecture, Research & Integration
**Assignee:** Mannan (sheet: Manan)  
**Module:** 1.f High Level Systems  
**Project:** Hybrid Mesh Micro-Climate WSN  
**Status:** Ready to merge into the team report  
**Depends on:** submitted `High_Level_Systems_Report.md` (Design 01 — unchanged)

This document is the rest of Mannan’s deliverable: research alternatives, hosting decision, risk analysis, final architecture, and the **integration contract** other sub-teams implement against. The React/Leaflet PWA in `mesh-dashboard/` is the working artefact of Design 01.

---

## 0. Role of High Level Systems in the project

High Level Systems is **Zone 1 — Admin Client Device** in the project overview (Section 2.1). It is not another mesh node. It is the only human interface.

```
Slave mesh (LoRa / AODV / AES-128-CCM / TinyML)
        │  encrypted telemetry + anomaly alerts
        ▼
Master Node  ESP32-S3-N16R8
  · SX1262 LoRa
  · Spatial Kriging + optional Gaussian plume
  · MicroSD registry
  · lwIP JSON REST API  (JSON only — never HTML)
        │  WiFi Access Point  (typical 192.168.4.1)
        ▼
Admin laptop / phone
  React 18 + Leaflet PWA  ← THIS MODULE
  IndexedDB cache + Service Worker
```

If this module is wrong, the rest of the hardware still works, but operators cannot see heatmaps, cannot inject RPC, and cannot tell live data from stale data. That is why the prerequisites in the submitted report are non-compromisable.

---

## 1. Design iterations (research)

Design 01 is the submitted, shortlisted design. Designs 02 and 03 were evaluated and rejected so the hosting choice is justified, not assumed.

### Design No: 01 — React 18 + Leaflet PWA on the admin device  **(CHOSEN)**

**System Architecture:** A React 18 + Leaflet.js Progressive Web App running on the admin’s device, talking to the Master Node over its local WiFi AP via a stateless JSON REST API. The dashboard is installed once as a static bundle (Service Worker). Thereafter only lightweight JSON is exchanged. The Master never serves HTML/CSS/JS.

This is the design in `High_Level_Systems_Report.md`. Cross-functional constraints, stack, hosting table, effort, failure modes, and prerequisites are unchanged. Implementation lives in `mesh-dashboard/`.

### Design No: 02 — Serve the dashboard from Master SPIFFS / LittleFS  **(REJECTED)**

**System Architecture:** Build the React app, gzip the `dist/` files, flash them onto the ESP32-S3, and have `lwIP` serve `index.html` + JS + CSS plus the JSON API.

**Why it fails the prerequisites**

| Check | Result |
|---|---|
| Master MUST NOT serve HTML/CSS/JS | Fail — this is exactly what SPIFFS hosting does |
| Master load ≤ 10 req/s of *small* JSON | Fail — a Leaflet + React bundle is hundreds of KB to several MB. One page load saturates the radio/CPU for seconds |
| ESP32-S3 N16R8 flash | 16 MB flash is shared with firmware, Kriging working set, and logs. A PWA plus OSM-style assets does not fit a maintainable partition map |
| Offline after leaving the AP | Partial — browser cache might help, but first load *requires* the Master to be a web server |

**Verdict:** Architecturally incompatible with Section 13 of the overview (“The Master Node is a stateless JSON REST API only”). Rejected.

### Design No: 03 — Cloud dashboard (MQTT / HTTP to AWS/Firebase)  **(REJECTED)**

**System Architecture:** Master uplinks telemetry to the internet (cellular modem or WAN). Operators view a hosted dashboard from anywhere.

**Why it fails the prerequisites**

| Check | Result |
|---|---|
| Cloud/cellular independence | Fail — recurring SIM cost, dies when towers fail (the exact failure mode Table 1 claims we avoid) |
| License-exempt ISM-only operation | Compromised — WAN path is a new regulatory and cost surface |
| Severe-weather / wildfire use case | Fail — the network is most needed when infrastructure is down |

**Verdict:** Contradicts the project’s core claim. Rejected.

### Shortlisting (updated)

| Design No | Design Name | Meets all prerequisites? | Rank |
|---|---|---|---|
| 01 | React + Leaflet PWA, thin JSON API on Master | Y | 1 — implemented |
| 02 | Dashboard hosted on Master SPIFFS | N | Rejected |
| 03 | Cloud MQTT / hosted dashboard | N | Rejected |

---

## 2. Efficient hosting on the high-level compute side

“High-level compute” in this project is **the admin’s laptop or phone**, not a cloud VM and not the ESP32.

| Layer | Where it runs | Why |
|---|---|---|
| React/Leaflet app shell | Admin device (installed PWA) | Heavy JS/CSS never touches `lwIP` |
| Service Worker | Admin device | App still opens with no AP |
| IndexedDB last-known-good JSON | Admin device | Maps/telemetry remain reviewable offline |
| JSON REST (5 endpoints) | Master firmware (`api.cpp`) | Fits ESP32; 10 req/s stress test |
| Kriging + plume | Master firmware | Spatial math stays next to the node registry |
| Mesh radio | Master + slaves | Invisible to the dashboard |

**Deployment procedure (no cloud account):**

1. Developer machine: `npm run build` → static `mesh-dashboard/dist/`.
2. Admin installs the PWA once (Chrome/Safari) while on any network, or sideloads `dist/`.
3. In the field, admin joins Master WiFi AP.
4. Set `MASTER_BASE_URL` in `src/api/client.js` (default field AP: `http://192.168.4.1`). Rebuild, or use the mock Master at `http://127.0.0.1:8080` for lab demos.
5. Dashboard polls JSON only.

**Polling budget (keeps Master under 10 req/s):**

| Client request | Interval | Notes |
|---|---|---|
| `GET /api/nodes` | 8 s | Staggered — not fired in the same instant as status |
| `GET /api/status` | 8 s | +400 ms after nodes |
| `GET /api/kriging/heatmap` | 60 s | Heavy GeoJSON; on-demand enough for interpolations |
| `GET /api/nodes/{id}/telemetry` | On node select | Not a background poll of every node |
| `POST /api/rpc/{id}` | User-initiated | Timeout 2000 ms until Comms confirms AODV timing |

One admin client ≈ 2/8 + 1/60 ≈ **0.27 req/s**, ~37× under the 10 req/s ceiling.

**Map tiles:** OpenStreetMap tiles need the public internet *or* a pre-cached tile pack. The PWA caches the *app shell* and *last JSON*. If OSM is unreachable, the map canvas still shows node markers and heatmap on a dark basemap (offline-safe). This is documented so Physical Structure / field ops do not assume live satellite imagery in a forest with no WAN.

---

## 3. Component failure modes & mitigation

Submitted table stands. Implementation mapping:

| Component | Mitigation in code |
|---|---|
| WiFi AP drop | `withCache()` in `src/api/cache.js`; header pill **Live** vs **Cached · synced Xm ago** |
| Silent RPC reject (crypto MIC/nonce) | `RpcTimeoutError`; UI **Not confirmed** — never green without a 2xx body |
| API overload | 8 s / 60 s stagger in `App.jsx` |
| Kriging over a dead node | Heatmap still drawn; offline nodes get a red ring + LATE/OFFLINE in the list (2× 5-min cycle) |
| Cached mistaken for live | Persistent pill, not a toast |
| Silent node | `NodeList` health: ok &lt; 5 min, late &lt; 10 min, else OFFLINE |
| SW / API skew | `DASHBOARD_API_VERSION` checked against `/api/status.appVersion`; mismatch banner |

**Additional HLS-owned risks**

| Component | Failure | Mitigation |
|---|---|---|
| LiFePO4 voltage shown as “%” | Wrong chemistry (3.2 V nominal, 3.65 V full, ~3.0 V LDO brownout) | Dashboard shows **volts**, warns &lt; 3.10 V, critical &lt; 3.00 V |
| GeoJSON vs simple points | Firmware emits FeatureCollection; naive client crashes | `normalizeHeatmap()` accepts both |
| Leaflet default icons under Vite | Broken marker URLs | Circle markers (no PNG icon pack required) |
| OSM tiles offline | Blank map, operator thinks nodes vanished | Dark fallback pane; markers still render |

---

## 4. Constraints resolved from other modules (so HLS can ship)

The submitted report waited on four teams. Until they freeze their docs, HLS uses the **verified overview.pdf** as the integration baseline. If a team’s final number differs, only `client.js` / this contract change — not the UI components.

| From | Question | Baseline used now | File to keep in sync |
|---|---|---|---|
| **Ariyan (ML)** | SensorDataStruct + anomaly index | 11-sensor set from overview Table 4. Anomaly: `0` Normal, `1` Rain, `2` Thunderstorm, `3` High PM2.5, `4` Radiation Spike. Tensor is 22 floats (11 absolute + 11 delta) — dashboard shows **engineering units**, not the tensor | `TelemetryPanel.jsx`, `example_payloads.json` |
| **Aditi (Power)** | Battery units / thresholds | ADC reports **volts** on the 3.3 V rail / cell. LiFePO4: nominal 3.2 V, charge terminate 3.65 V. Warn &lt; 3.10 V, critical &lt; 3.00 V (XC6220 brownout region) | `src/api/contract.js` |
| **Abhinav (Comms)** | RPC timeout | AODV re-discover ~500 ms; poll window 2 s/hour. UI timeout **2000 ms** (covers 1 hop + margin). Tune `RPC_TIMEOUT_MS` after bench traces | `client.js` |
| **Anushka (Crypto)** | Reject signalling | Slave **silently** drops bad MIC/nonce (overview §6.3). Master has nothing to forward. Dashboard **must** treat timeout as unconfirmed | `RpcMenu.jsx` |
| **Vishal (Physical)** | Map coordinates | NEO-6M at deploy; thereafter NVRAM. Mock nodes use a Himachal-style lat/lng stand-in; real IDs come from `/api/nodes` | `MapView.jsx` |
| **Jenish (Business)** | Operator UX | Offline-first, zero recurring cost — same story as the market canvas (no SIM, no cloud SaaS) | this hosting section |

---

## 5. API contract (Master firmware ↔ dashboard)

Firmware Phase 3 (`api.cpp`, `registry.cpp`) **must** match these shapes. The dashboard’s **only** firmware touch-point is `mesh-dashboard/src/api/client.js`.

### 5.1 Endpoints (overview Table 14)

| Method | Path | Client function |
|---|---|---|
| GET | `/api/nodes` | `getNodes()` |
| GET | `/api/nodes/{id}/telemetry` | `getTelemetry(id)` |
| GET | `/api/kriging/heatmap` | `getHeatmap()` |
| GET | `/api/status` | `getStatus()` |
| POST | `/api/rpc/{id}` | `sendRpc(id, opcode, params)` |

CORS: Master AP typically has no CORS browser policy issues for same-origin if the PWA is opened against the AP IP. If the PWA is `localhost` talking to `192.168.4.1`, firmware should send `Access-Control-Allow-Origin: *` on JSON responses (lab only).

### 5.2 JSON shapes

**GET `/api/nodes`**

```json
[
  {
    "id": "01",
    "lat": 31.7076,
    "lng": 76.9366,
    "name": "Node 01 — Ridge",
    "lastSeen": 1755715200000,
    "battery": 3.31
  }
]
```

`lastSeen` is Unix **milliseconds** UTC (JS `Date.now()`). If firmware stores seconds, multiply by 1000 in `client.js` — do not change components.

**GET `/api/nodes/{id}/telemetry`**

```json
{
  "id": "01",
  "timestamp": 1755715200000,
  "anomalyIndex": 0,
  "anomalyLabel": "Normal",
  "battery": 3.31,
  "sensors": {
    "temperature_c": 22.4,
    "humidity_pct": 58,
    "pressure_hpa": 913.2,
    "voc_iaq": 74,
    "wind_speed_ms": 2.1,
    "wind_dir_deg": 214,
    "rain_mm": 0,
    "pm25_ugm3": 12,
    "pm10_ugm3": 19,
    "uv_index": 3,
    "radiation_cpm": 18
  }
}
```

Optional extras (soil from SHT20, lightning distance, PM1.0) may be added later as extra keys; the panel ignores unknown keys.

**GET `/api/kriging/heatmap`** — preferred GeoJSON (overview §13):

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [76.9366, 31.7076] },
      "properties": { "intensity": 0.35 }
    }
  ]
}
```

Also accepted: `[{ "lat", "lng", "intensity" }]`. Intensity is 0–1 for Leaflet.heat.

Optional later: GeoJSON contour for Gaussian plume (`/api/plume`). Dashboard can add a layer without changing the five core endpoints.

**GET `/api/status`**

```json
{
  "uptimeSeconds": 186420,
  "batteryVoltage": 3.34,
  "meshNodeCount": 4,
  "appVersion": "0.1.0"
}
```

`appVersion` must match `DASHBOARD_API_VERSION` in `src/api/contract.js` when the JSON schema changes.

**POST `/api/rpc/{id}`** body:

```json
{ "command": 2 }
```

`command` is the `uint8_t` opcode from `firmware/rpc.h`. Extra fields (`seconds`, `threshold`, `periph`) are optional and ignored by the UI until firmware documents them.

Success: any **2xx** with JSON (even `{ "ok": true }`).  
Failure: non-2xx, or **no response within timeout** → UI **Not confirmed**.

### 5.3 RPC opcodes (must equal `firmware/rpc.h`)

| Opcode | Name |
|---|---|
| 0x01 | CMD_FORCE_INFERENCE |
| 0x02 | CMD_SEND_TELEMETRY |
| 0x03 | CMD_UPDATE_THRESH |
| 0x04 | CMD_SET_SLEEP_PERIOD |
| 0x05 | CMD_DISABLE_PERIPH |
| 0x06 | CMD_REBOOT |
| 0x07 | CMD_SYNC_NONCE |
| 0x08 | CMD_GET_BATTERY |

---

## 6. How this folder merges into the main project

| Team artefact | What they do with HLS |
|---|---|
| **This report** | Paste into the combined Design Practicum PDF as section “1.f High Level Systems”. Keep submitted `High_Level_Systems_Report.md` as the iteration worksheet; this file is the architecture + integration annex |
| **`mesh-dashboard/`** | Phase 4 deliverable (pipeline 4.1–4.3). Demo with mock data (`MASTER_BASE_URL = null`) today; point at Master when `api.cpp` exists |
| **`integration/example_payloads.json`** | Golden samples for firmware unit tests |
| **`mesh-dashboard/mock-master.mjs`** | Local stand-in for the Master REST API so Comms/firmware can test without the PWA mock path |

**Integration sequence (Phase 5.1):**

1. Firmware serves the five endpoints on the AP.
2. Set `MASTER_BASE_URL = 'http://192.168.4.1'` in `client.js`.
3. Bench: 4 slaves + 1 master → `/api/nodes` lists all four; heatmap GeoJSON renders; one RPC round-trip shows **Confirmed**.
4. Kill WiFi → pill turns **Cached**; last telemetry still visible.
5. Corrupt MIC on a slave (crypto test) → RPC shows **Not confirmed**.

Nothing in NodeList / MapView / TelemetryPanel / RpcMenu should be rewritten for firmware — only `client.js` mapping if field names differ.

---

## 7. Minimum prerequisites (reconfirmed)

| Requirement | Checks out? |
|---|---|
| Local WiFi only, zero cloud | Y |
| Client well under 10 req/s | Y (~0.27 req/s) |
| Offline cached view | Y (IndexedDB) |
| Master JSON-only | Y |
| RPC never assumed successful | Y |
| Live vs cached always visible | Y |
| RPC menu = 8 firmware opcodes | Y |

---

## 8. Final conclusion

**Chosen design remains Design 01.** Alternatives that host the UI on the ESP32 or in the cloud fail the project’s own constraints.

Mannan’s submission pack:

1. `High_Level_Systems_Report.md` — original iteration worksheet (already submitted).  
2. **This file** — research (01–03), hosting, risks, resolved interfaces, merge plan.  
3. `mesh-dashboard/` — Phase 4 PWA.  
4. `integration/` — payloads and handoff notes for other modules.

Handoff still required in writing from other teams only if they **deviate** from overview.pdf. Until then, the contract in Section 5 is what Master firmware should implement.
