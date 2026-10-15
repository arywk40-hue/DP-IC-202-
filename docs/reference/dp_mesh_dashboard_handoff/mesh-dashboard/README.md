# Mesh Dashboard — High Level Systems

Team docs (submit these with the PWA):

- `../High_Level_Systems_Report.md` — original design worksheet (already submitted)
- `../High_Level_Systems_Complete.md` — architecture, hosting research, risks, merge plan
- `../integration/` — JSON contract and handoff notes for other sub-teams


Admin dashboard for the Hybrid Mesh Micro-Climate WSN. Built with React 18 +
Leaflet.js, packaged as an installable, offline-first PWA — matching the
stack decided in the High Level Systems architecture report.

Runs entirely on **mock data** out of the box, so you can develop/demo the
frontend before the Master Node firmware (Phase 3 of the pipeline) exists.

## Quick start

```bash
npm install
npm run dev
```

Open the printed local URL (default `http://localhost:5173`). You'll see 4
mock nodes on the map, a live-updating node list, telemetry on click, and a
working RPC command menu (simulated — occasionally shows the "not
confirmed" state on purpose, so that UI path gets exercised).

## Lab Master (firmware not ready yet)

```bash
npm run mock-master
```

In another terminal, set `MASTER_BASE_URL` in `src/api/client.js` to `http://127.0.0.1:8080` and run `npm run dev`. The mock serves GeoJSON heatmap matching `integration/example_payloads.json`.

## Integrating with the real Master Node

This is the **only file you need to edit**: `src/api/client.js`.

1. Open `src/api/client.js`.
2. Find this line near the top:
   ```js
   const MASTER_BASE_URL = null; // e.g. 'http://192.168.4.1'
   ```
3. Set it to the Master Node's WiFi AP address, e.g.:
   ```js
   const MASTER_BASE_URL = 'http://192.168.4.1';
   ```
4. That's it — every component (`NodeList`, `MapView`, `TelemetryPanel`,
   `RpcMenu`) already calls the shared functions in this file
   (`getNodes`, `getTelemetry`, `getHeatmap`, `getStatus`, `sendRpc`), so
   nothing else needs to change. The mock data path and the real fetch
   path are switched automatically based on whether `MASTER_BASE_URL` is
   set.

### Expected API contract

The client expects the Master's firmware to expose exactly the 5 endpoints
from the project overview (Section 13.1):

| Method | Path | Expected response shape |
|---|---|---|
| GET | `/api/nodes` | `[{ id, lat, lng, name, lastSeen, battery }]` |
| GET | `/api/nodes/{id}/telemetry` | `{ id, timestamp, anomalyIndex, anomalyLabel, battery, sensors: {...11 keys...} }` |
| GET | `/api/kriging/heatmap` | `[{ lat, lng, intensity }]` |
| GET | `/api/status` | `{ uptimeSeconds, batteryVoltage, meshNodeCount, appVersion }` |
| POST | `/api/rpc/{id}` | body `{ command: <opcode>, ...params }`, any 2xx response |

If firmware's actual field names differ, you have two options:
- Change firmware to match this contract, **or**
- Add a small mapping step inside the `apiGet`/`apiPost` calls in
  `client.js` to translate field names — no component code needs to
  change either way, since components only ever see the shapes above.

### RPC opcodes

`RPC_COMMANDS` in `client.js` must stay in sync with `firmware/rpc.h`.
If the firmware enum changes, update the array in `client.js` to match —
this is also called out in the architecture report as an explicit
cross-functional dependency.

### Timeout tuning

`RPC_TIMEOUT_MS` in `client.js` (currently 2000ms) is a placeholder. Per
the report's handoff notes, this should be tuned once real AODV
route-discovery timing and the mesh's synchronized polling window
(~500ms re-discovery, 2s/hour poll window) are confirmed with the
Communications team.

## What's implemented vs. what's still a stretch goal

**Implemented:**
- Node list with live/late/offline status (2x reporting-interval rule)
- Leaflet map with node markers + Kriging heatmap overlay (`leaflet.heat`)
- Telemetry panel for all 11 sensors + anomaly banner
- RPC command menu with explicit "confirmed / not confirmed / error"
  states (never silently assumes success — see report's risk analysis)
- IndexedDB caching (`src/api/cache.js`) with a visible live/cached
  indicator in the header
- Installable offline PWA (via `vite-plugin-pwa`)
- Conservative polling intervals (8s core data, 60s heatmap) to stay
  under the Master's 10 req/s stress-test ceiling

**Not implemented (intentionally out of scope for this stage):**
- Service Worker request-level caching of live API calls beyond the
  simple IndexedDB snapshot approach used here (fine for this data
  volume; revisit only if telemetry history views are added later)
- Historical/time-series charts (current scope is live snapshot only)
- Authentication — the project has no auth layer defined yet at the
  Master Node level

## Build for production

```bash
npm run build
```

Outputs a static bundle to `dist/`. This is the bundle that gets
installed once on the admin's device per the "hosting" design decision
in the report — the Master Node never serves this bundle itself.
