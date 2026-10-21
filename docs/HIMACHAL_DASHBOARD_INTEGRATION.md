# Connected INDRA dashboard

The supplied DP Mesh Dashboard is integrated in `apps/indra-himachal-ui`.
Its original source, reports and integration contract are retained unchanged in
`docs/reference/dp_mesh_dashboard_handoff/`, with SHA-256 identities in
`original_manifest.json` and `docs/plans/PROTECTED_PATHS.json`.
The original Downloads folder is unchanged.

The working application retains the teammate's React/Leaflet layout and IndexedDB
cache. Its API adapter now uses `server/dashboard.py`, independently of the
existing operational application. API version is **0.4.0**: the active six-channel
forecast is now the saved expanded Mandi LightGBM/neural/retained-hybrid ensemble, with explicit
history and fallback status. API-versioned caches discard older predictions.
This does not modify the team's firmware
contract automatically; the communications owner must adopt the versioned adapter.

See [current v2 and online-learning guide](MANDI_V2_PIPELINE.md) for the active model, mixed comparisons, shadow state and rollback.

## Run locally

Install once with Python 3.11–3.13 and Node 22:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dashboard.txt
cd apps/indra-himachal-ui
npm ci
cd ../..
```

Then start the complete local demonstration:

```sh
.venv/bin/python scripts/run_himachal_demo.py --offline
```

Open **http://127.0.0.1:8080**. The script builds and serves the PWA and API
from the same address. No weather API, NASA/CDS credentials, map downloads,
SMS/email, RF transmission or physical sensor connection is required. Dependencies
must already be installed; `--offline` does not install packages. The four demo
nodes are synthetic rain/snow/cloudburst-pattern/incomplete-history fixtures,
marked in the header and telemetry. They stop at a fixed observation time and
become stale; polling never manufactures new sensor readings.

The tested temporary environment on this computer is
`/private/tmp/indra-himachal-venv/bin/python`; its location is not a permanent
deployment dependency.

For frontend development, start `python -m server.dashboard --demo` from the
root, then `npm run dev` in the app directory. Vite proxies `/api` to port 8080.
For an independently hosted backend, set `VITE_MASTER_BASE_URL` at build time;
that deployment must configure its own authenticated gateway and CORS. No token
belongs in frontend environment variables. Optional OSM background tiles require
`VITE_OSM_TILES=true` and internet access; default node markers work offline.

## What is connected

| Dashboard content | Actual implementation/evidence |
| --- | --- |
| Six measurements with units and short histories | Native snapshots validated by `ml/himachal/contracts.py`; no seventh physical input |
| Six numerical +6h estimates | Active `india_mandi_tabular_v2`: validation-selected LightGBM + residual MLP + retained hybrid + persistence; checksum-verified components and bounds |
| Rain, snowstorm and cloudburst risk cards | Versioned `ml/himachal/features.py` and `rules.py`, including evidence and abstention |
| Storm sequence | Separate experimental six-hour pressure fall followed by native 15-minute rebound rule; not a fitted storm model |
| Node positions | Supplied WGS84 coordinates, with source class and observation age |
| Battery | Unavailable until measured; no invented voltage |
| Spatial surface | Explicitly unavailable; no invented kriging or smoothing of risk scores |
| Device commands | Disabled; HTTP 501, never a fake physical acknowledgement |

The numerical model was trained on **Mandi-location IFS/CAMS modeled grids**,
not verified six-channel Mandi station observations. This interface performs
inference, not a new accuracy evaluation. Forecasts are one endpoint at +6h,
not six hourly predictions. Risk assessments concern the input time and do not
inherit that six-hour forecast horizon.

The hybrid uses 66 causal features from **25 complete hourly snapshots spanning
24 hours**, selected at the latest observation's exact hourly phase. No missing
hour is interpolated. The UI shows the model identity, history count and each
target's three blend coefficients. Incomplete history uses explicitly named
`WARMING_UP_PERSISTENCE` (current values copied to +6h); a missing current channel
produces `MISSING_CURRENT_SENSOR` with unavailable outputs. Neither is presented
as hybrid inference. Startup recomputes legacy SQLite forecasts from retained
history; a legacy seven-hour cache warms up rather than retaining an old XGBoost
prediction under a new label.

Selection uses only the August validation partition; its report uses 954
previously examined September/October modeled rows, not a new untouched field
test. See [hybrid results](../reports/india_mandi_hybrid_6h_v1/REPORT.md).
The existing compact ESP32 export is separate; this promotion runs on the
Python gateway and does not export the hybrid to firmware.

Risk scores remain **uncalibrated rule matches**, with `probability: null` and
no measured warning lead time. Missing channels/history or incompatible pressure
references cause explicit abstention. A high cloudburst score does not measure
rainfall intensity, and a high snowstorm score does not confirm snowfall.
Flood and landslide prediction remain unavailable. Public notifications are off.

## Import measured observations

The backend is a read-only local adapter, not a network telemetry collector.
An operator imports a JSON list of full native snapshot records following
`docs/HIMACHAL_FEATURE_CONTRACT.md`. Preserve actual units, station pressure,
measurement/availability times, site/registration, cadence, source class and
per-channel calibration identities. Source identity is operator-supplied and
does not establish cryptographic verification or voting privileges.

```sh
.venv/bin/python scripts/run_himachal_demo.py --offline --observations /absolute/path/snapshots.json
```

To refresh a running dashboard without restarting it:

```sh
.venv/bin/python scripts/import_dashboard_observations.py --input /absolute/path/snapshots.json
```

Validation and model inference finish before the SQLite snapshot is replaced
atomically. Polling updates the UI within eight seconds. Invalid imports preserve
the previous state. Use the same `--db` path for server and importer. Raw data
and the local SQLite store stay under ignored `data/himachal/`.
No source automatically falls back to synthetic values.

The firmware's positional serial JSON is **not** this full snapshot contract.
The remaining live bridge must add reviewed site/calibration/units metadata,
preserve serial quality flags and actual receipt times, and reject duplicates,
clock errors and invalid frames. Bench-test that bridge against the connected
ESP32 before declaring a live product. This change does not claim physical
execution, a LoRa link or a calibrated hazard probability.

## Contract and verification

Five teammate-compatible endpoint paths are implemented: `/api/nodes`,
`/api/nodes/{id}/telemetry`, `/api/status`, `/api/kriging/heatmap` and
`POST /api/rpc/{id}`. Telemetry now uses the canonical six channel names.
Additional fields identify source, history availability, forecast model,
rule evidence, stale state and unsupported capabilities. SQLite survives restart.
There is no public listening interface or write API; the server binds loopback.

Backend tests exercise the real saved model, partial-history abstention, missing
channels, invalid/future/relocated/duplicate observations, tampered model weights,
atomic import preservation, restart/staleness and original-source hashes.
Browser tests exercise desktop/mobile layouts, all three risk cards, node
selection, disabled RPC and cached/offline states. Cache keys include API version
and backend address. Cached or stale values are never shown as current warnings.

```sh
.venv/bin/python -m pytest tests/test_dashboard_integration.py -q
cd apps/indra-himachal-ui
npm test
npm run test:e2e
```

On macOS the browser tests use installed Google Chrome. CI uses Playwright
Chromium. `INDRA_PYTHON` selects the Python environment for the browser-test
backend. Local validation results and screenshots are recorded under
`reports/himachal/dashboard/`.
