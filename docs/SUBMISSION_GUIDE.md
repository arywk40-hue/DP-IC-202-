# Submission and local demonstration

INDRA is a six-channel environmental forecasting and Himalayan risk research prototype. The active gateway is `india_mandi_tabular_v2`: LightGBM, a residual MLP, retained hybrid and persistence with validation-selected prediction blends. A persistent delayed-label learner runs in shadow mode. Physical station accuracy, disaster probabilities, promotion of adaptive outputs and ESP32/RF execution remain separate empirical work.

## Files for the examiner

**Current showcase:** follow the [five-minute runbook](SHOWCASE_RUNBOOK.md).
The :8080 view now uses the current API collector, not just the original frozen
archive. Its update count is live and must not be described as permanently zero.
Current values remain model grids, not physical station measurements. The
runbook covers both :8080 and the separate twelve-location :8082 demonstration.

The two newly completed features are documented in
[parameter maps and weather categories](PARAMETER_MAPS_AND_WEATHER_CATEGORIES.md)
and the [feature report](../reports/weather_features_v1/REPORT.md).
Use the separate 12-location synthetic demo on :8082 to show both end to end;
the downloaded Mandi archive remains a one-location view on :8080.

1. [Features](FEATURES.md), [overview](PROJECT_OVERVIEW.md) and [architecture](ARCHITECTURE.md).
2. [Current Mandi report](../reports/mandi_pipeline_v2/REPORT.md), its `results.json` and `verification.json`: data provenance, inputs, exact +6h targets, comparisons, software/browser checks and limits.
3. [Active profile](../ml/models/india_mandi_tabular_v2/profile.json) and [blend coefficients](../ml/models/india_mandi_tabular_v2/ensemble_weights.json). These reference checksummed learned artifacts; weights are not hidden in the frontend.
4. [Pipeline and online-learning guide](MANDI_V2_PIPELINE.md): reproduction, durable shadow state and rollback.
5. [Synthetic PM report](../reports/mandi_synthetic_pm_v1/README.md): explicitly separate simulation data, excluded from reported forecast scores.

Retained v1 results are in `reports/submission/2026-10-21/`; `scripts/test_mandi_submission.py` reproduces that version. Preserve their original model/report paths. The frozen export catalog is historical; `ml/india_mandi/registry.py` selects the active gateway.

Submit source and committed trained artifacts. Raw CSVs, virtual environments, node_modules, SQLite state, credentials and downloaded TabPFN checkpoints stay local.

## Reproduce and show the model

From the repository root with Python 3.13 and Node 22:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dashboard.txt
npm ci --prefix apps/indra-himachal-ui
# Download the configured source if it is absent; does not train:
.venv/bin/python scripts/train_mandi_v2.py --prepare
# Evaluate frozen committed components; does not select new weights:
.venv/bin/python scripts/train_mandi_v2.py --evaluate
# Obtain the current input file on a fresh checkout, before starting its collector:
.venv/bin/python scripts/fetch_mandi_live.py
.venv/bin/python -m server.dashboard --observations data/himachal/mandi_current_api_v1/history.json --db data/himachal/mandi_dashboard.sqlite --online-state data/himachal/mandi_v2_online_live.sqlite --ui apps/indra-himachal-ui/dist --port 8080
```

Open http://127.0.0.1:8080. For development run `npm run dev --prefix apps/indra-himachal-ui` and open http://127.0.0.1:5173. The backend also serves the built UI. The preparation step initially creates the stable input file only when absent, preserving an existing live stream. Matching frozen source/model hashes are required; changed upstream values require a new version.

Demonstrate the weather-model source label, actual input time, one grid location,
six readings, `HYBRID_READY`, 25/25 hourly history, +6h numerical forecasts, blend
details and the model workspace's mixed v1/v2 results. The initial archive-only
replay had zero eligible live updates; the current collector can now show updates.
Read its actual count and issuance timing. The separate retrospective replay count
is simulated timely-arrival research, not the current worker count. Hazard
scenarios remain synthetic conditional fractions, not calibrated probabilities.

For the current API feed, run `scripts/fetch_mandi_live.py` as shown in the
runbook. It both publishes new snapshots and drives the shadow learner; no second
worker is needed. The older `scripts/online_mandi_worker.py` remains available
for separately supplied reviewed hourly files. Published offline outputs remain
unchanged by shadow updates.

Synthetic multi-node/current-rule fixtures are a separate demonstration. Use a separate database when running the demo without `--observations`; do not present those fixtures as measured Mandi weather.

## Software verification

```sh
.venv/bin/python -m pip install -r requirements-physics.txt -r requirements-hazard-context.txt -r requirements-operational.txt -r requirements-online-research.txt -r requirements-storm-risk.txt
.venv/bin/python -m pytest -q
npm test --prefix apps/indra-himachal-ui
# Browser tests require Chrome on macOS, Chromium in CI:
INDRA_PYTHON="$PWD/.venv/bin/python" npm run test:e2e --prefix apps/indra-himachal-ui
# With the actual current Mandi application running:
cd apps/indra-himachal-ui
node tests/verify-current-mandi.mjs
```

Synthetic browser fixtures verify wiring only. The current Mandi browser check
verifies source labels, numerical forecasts and timing diagnostics. The older
`npm run test:mandi` check targets the historical archive node specifically.

## Questions to answer

- **Labels:** the six modeled values exactly six hours later. Current sensor rules are not independent hazard labels.
- **Accuracy:** report MAE/RMSE/R² in channel units, including regressions. The test is retrospective/reused, not synchronized station truth.
- **Synthetic PM:** simulated missing history can exercise the pipeline; it cannot establish historical pollution or event accuracy.
- **Remaining work:** measured six-channel Mandi evaluation, independent event/non-event records, sensor/ESP32/RF tests, validated hazard fitting/calibration and controlled shadow-model promotion. Both services stay local as requested.
