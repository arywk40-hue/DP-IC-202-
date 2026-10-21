# Submission and local demonstration

INDRA is a six-channel environmental forecasting and Himalayan risk research prototype. The active gateway is `india_mandi_tabular_v2`: LightGBM, a residual MLP, retained hybrid and persistence with validation-selected prediction blends. A persistent delayed-label learner runs in shadow mode. Physical station accuracy, disaster probabilities, promotion of adaptive outputs and ESP32/RF execution remain separate empirical work.

## Files for the examiner

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
.venv/bin/python scripts/run_himachal_demo.py --offline --db data/himachal/mandi_dashboard.sqlite --observations data/himachal/live_hourly.json --online-state data/himachal/mandi_v2_online_live.sqlite
```

Open http://127.0.0.1:8080. For development run `npm run dev --prefix apps/indra-himachal-ui` and open http://127.0.0.1:5173. The backend also serves the built UI. The preparation step initially creates the stable input file only when absent, preserving an existing live stream. Matching frozen source/model hashes are required; changed upstream values require a new version.

Demonstrate the historical-modeled banner, one grid node, six readings, `HYBRID_READY`, 25/25 hourly history, +6h forecasts, blend details and the model workspace's mixed v1/v2 results. Historical inputs correctly show stale state, zero eligible live updates and unavailable hazard probabilities. The separate replay count is simulated timely-arrival research, not a live count.

To watch future reviewed hourly files, start `scripts/online_mandi_worker.py` with the same input/state paths and `--watch-seconds 5`. Published offline outputs remain unchanged by shadow updates. See the pipeline guide for source identities and availability requirements.

Synthetic multi-node/current-rule fixtures are a separate demonstration. Use a separate database when running the demo without `--observations`; do not present those fixtures as measured Mandi weather.

## Software verification

```sh
.venv/bin/python -m pip install -r requirements-physics.txt -r requirements-hazard-context.txt -r requirements-operational.txt -r requirements-online-research.txt -r requirements-storm-risk.txt
.venv/bin/python -m pytest -q
npm test --prefix apps/indra-himachal-ui
# Browser tests require Chrome on macOS, Chromium in CI:
INDRA_PYTHON="$PWD/.venv/bin/python" npm run test:e2e --prefix apps/indra-himachal-ui
# With the actual local Mandi application running:
npm run test:mandi --prefix apps/indra-himachal-ui
```

Synthetic browser fixtures verify wiring only. The actual Mandi browser test separately checks source labels, numerical forecasts and hazard abstention; it saves evidence in `reports/mandi_pipeline_v2/`.

## Questions to answer

- **Labels:** the six modeled values exactly six hours later. Current sensor rules are not independent hazard labels.
- **Accuracy:** report MAE/RMSE/R² in channel units, including regressions. The test is retrospective/reused, not synchronized station truth.
- **Synthetic PM:** simulated missing history can exercise the pipeline; it cannot establish historical pollution or event accuracy.
- **Remaining work:** measured six-channel Mandi evaluation, independent event/non-event records, sensor/ESP32/RF tests, validated hazard fitting/calibration and controlled shadow-model promotion. Both services stay local as requested.
