# Submission and local demonstration

## Present this scope

**INDRA: six-channel environmental forecasting and Himalayan risk research prototype.**
The completed deliverable is a working local ML/dashboard prototype, with a
validation-selected neural/history-XGBoost/ridge measurement forecaster and a
reproducible retrospective Mandi modeled-data test. Disaster probability, deployed
sensor/radio operation and live online adaptation are separate unfinished claims.

## Files for the examiner

1. [Feature/status list](FEATURES.md): what the project provides and what is experimental.
2. [Project overview](PROJECT_OVERVIEW.md) and [implemented architecture](ARCHITECTURE.md).
3. [Current Mandi report](../reports/submission/2026-10-21/REPORT.md) and its `metrics.json`:
   source, inputs, exact +6h labels, seven model comparisons, MAE/RMSE/R² and examples.
4. [Active model profile](../ml/models/india_mandi_hybrid_6h_v1/profile.json) and
   [blend coefficients](../ml/models/india_mandi_hybrid_6h_v1/ensemble_weights.json).
   The profile links checksummed neural arrays, XGBoost heads and ridge arrays.
5. `reports/submission/2026-10-21/verification.json`: executed software/browser and
   integrity checks. Historical reports elsewhere retain their original scope.

Submit source and committed trained artifacts. Do not add raw CSVs, .venv,
node_modules, local SQLite, API keys or generated working directories. Preserve
model paths: renaming them breaks checked references. The frozen export catalog
is historical; the active gateway profile is selected in `server/dashboard.py`.

## Reproduce the numerical test

From the repository root with Python 3.13 and Node 22:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dashboard.txt
npm ci --prefix apps/indra-himachal-ui
.venv/bin/python scripts/test_mandi_submission.py
```

The test requires the existing ignored `data/india_mandi_modeled/observations.csv`
and its matching committed provenance manifest. On a fresh checkout use
`.venv/bin/python scripts/test_india_mandi.py --prepare` first to fetch the frozen
period. No new source, model or report should silently replace a version whose
hash differs. The submission test does not train, select weights or use Beijing.

## Show the Mandi dashboard

```sh
.venv/bin/python scripts/run_himachal_demo.py --offline --db data/himachal/mandi_dashboard.sqlite --observations data/himachal/mandi_replay.json
```

Open http://127.0.0.1:8080. For development, run
`npm run dev --prefix apps/indra-himachal-ui` in another terminal and open
http://127.0.0.1:5173. Both pages use the same local backend. With both running, verify the actual Mandi replay using `npm run test:mandi --prefix apps/indra-himachal-ui`; it saves desktop/mobile screenshots and a receipt next to the report.

Demonstrate the historical-modeled banner, one `mandi-api-grid` node, six readings,
`HYBRID_READY`, 25/25 hourly history, +6h values, model blend details, stale times,
and unavailable hazard scores. Explain why there is only one node and no native
15-minute sequence or validated risk map. This is the honest API-data demonstration.

For rule and multi-node UI wiring only, stop the backend and run
`.venv/bin/python scripts/run_himachal_demo.py --offline`. It explicitly replaces
the selected local store with synthetic fixtures. Do not label them real Mandi tests.

## Software verification

```sh
.venv/bin/python -m pip install -r requirements-physics.txt -r requirements-hazard-context.txt -r requirements-operational.txt -r requirements-online-research.txt -r requirements-storm-risk.txt
.venv/bin/python -m pytest -q
npm test --prefix apps/indra-himachal-ui
export INDRA_PYTHON="$PWD/.venv/bin/python"
cd apps/indra-himachal-ui
INDRA_SCREENSHOT_DIR=../../reports/submission/2026-10-21 npm run test:e2e
```

Browser tests require installed Chrome on macOS (Chromium in CI). Their synthetic
fixtures verify software only; the Mandi numerical report is a separate run.

## Answer these questions explicitly

- **What are labels?** The six API/model values exactly six hours after an input;
  current hazard rules are not independent event labels.
- **Where are weights?** Referenced original arrays/trees plus per-target convex
  prediction coefficients in the active profile. No trained weights are hidden
  in frontend JavaScript.
- **Can this predict cloudbursts/floods/landslides?** No validated predictor exists
  for those outcomes. Collect matched independent events and monitored negatives.
- **Why not call it Indian station accuracy?** The six-channel Mandi source is a
  retrospective weather/air modeled grid with different resolutions and unverified
  original issue-time availability. It is not synchronized station ground truth.
- **What remains?** Measured Mandi tests, sensor/ESP32/RF integration, independently
  validated hazard training/calibration, live learning and deployment. Keep both
  services local until the backend is ready, as requested.
