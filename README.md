# INDRA — six-channel weather forecasting

INDRA forecasts **temperature, humidity, pressure, PM2.5, PM10 and wind at +6 hours**.
It also provides **six parameter heatmaps** from synchronized locations and
**ten current weather-pattern categories** from a synthetic-trained classifier.
See [the feature guide and complete local demo](EVERYTHING.md#source-4f516879b0b8).
Category scores are not calibrated real-event probabilities.
It also provides [cloudburst, flash-flood and landslide scenarios](EVERYTHING.md#source-76ac9fbe3adb)
using a documented Monte Carlo simulator. Their percentages describe simulated
outcomes under assumed rainfall/soil/drainage, not real-event probabilities.
The active Python backend uses LightGBM, a residual neural network, the retained
hybrid and persistence in `india_mandi_tabular_v2`. It derives 66 causal features from 25 hourly
snapshots spanning 24 hours. Short histories explicitly use persistence warm-up.

**Submission scope:** implemented ML/software prototype with retrospective Mandi
modeled-data evaluation. Physical Mandi accuracy, disaster prediction, promoted live adaptive outputs and ESP32/radio execution are not established.
A durable delayed-label online learner is implemented in shadow mode.

## Documentation and audit trail

[EVERYTHING.md](EVERYTHING.md) is the consolidated operating handbook, including
architecture, model evaluation, online learning, data provenance and blockchain
setup. Original source paths are indexed in
[the consolidation manifest](docs/documentation_consolidation.json).
All Markdown documentation is in the handbook. Original Markdown evidence is
preserved in `docs/archive/original_markdown.zip`; model and binary artifacts
remain at their original paths.

The backend records hash-linked audit events within its SQLite transactions.
The System page shows local audit status; signed exports and a Solidity contract
support local EVM anchoring. This does not yet provide independently witnessed
public-network verification. See the handbook for commands and trust boundaries.

## Run locally

For newly fetched Mandi model values and automatic delayed shadow testing, see
[the current feed guide](EVERYTHING.md#source-6d85e1c96415).

Complete synthetic maps/category showcase: `.venv/bin/python scripts/run_himachal_demo.py --offline --weather-demo --db data/himachal/weather_demo.sqlite --port 8082`, then open http://127.0.0.1:8082. It stays separate from the downloaded Mandi view.

Python 3.13 and Node 22 are the tested setup. From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dashboard.txt
npm ci --prefix apps/indra-himachal-ui
```

Test the committed models on the locally retained Mandi dataset, then start the
historical Mandi dashboard:

```sh
.venv/bin/python scripts/train_mandi_v2.py --evaluate
.venv/bin/python scripts/run_himachal_demo.py --offline --db data/himachal/mandi_dashboard.sqlite --observations data/himachal/live_hourly.json
```

Open **http://127.0.0.1:8080**. For frontend development, run `npm run dev --prefix apps/indra-himachal-ui` in another terminal and open **http://127.0.0.1:5173**.
The development frontend proxies `/api` to the same backend.

A fresh checkout does not contain raw CSVs. Retrieve the configured source first:
`.venv/bin/python scripts/train_mandi_v2.py --prepare`. This downloads the configured source without training. Existing source/model hashes
must match. The latest submission command itself is offline and does not retrain.

For clearly labelled synthetic rain/snow/cloudburst-rule fixtures, use
`.venv/bin/python scripts/run_himachal_demo.py --offline` without `--observations`.
Do not present that demonstration as measured Mandi weather.

## Current Mandi result

35,520 hourly API/model positions, October 2022–19 October 2026; 33,570 training,
738 validation and **1,170 future-test pairs** (including the reused earlier test) with six-hour boundary purges.
No Chinese observations or weights enter this run. Source weather/PM use different
ECMWF/CAMS grids; these are not six co-located station sensors.

| +6h target | Hybrid MAE | Unit |
| --- | ---: | --- |
| Temperature | 1.4264 | °C |
| Relative humidity | 6.8214 | percentage points |
| Pressure | 0.9412 | hPa |
| PM2.5 | 6.5932 | µg/m³ |
| PM10 | 8.6987 | µg/m³ |
| Wind | 0.3019 | m/s |

Candidate/baseline results, TabPFN’s bounded comparison, RMSE/R² and blend
weights are in the [submission report](EVERYTHING.md#source-992f2b21c23a).
Results are mixed versus v1; regression errors are not classification accuracy percentages. The test period
was examined previously, so it is not a new untouched or field test.

## Repository map

| Path | Purpose |
| --- | --- |
| `apps/indra-himachal-ui/` | Active React dashboard |
| `server/` | Local SQLite/FastAPI read-only backend |
| `ml/india_mandi/`, `scripts/train_mandi_v2.py` | Active v2 ensemble, online shadow learner and Mandi evaluation |
| `ml/models/india_mandi_tabular_v2/` | Active LightGBM/MLP profile, component hashes and blend coefficients |
| `ml/models/india_mandi_hybrid_6h_v1/` | Retained baseline/rollback hybrid |
| `ml/models/india_mandi_neural_history_v1/` | Saved neural arrays and normalization |
| `ml/models/india_mandi_modeled_6h_v1/` | Saved Mandi tree/ridge components and compact comparison |
| `ml/himachal/` | Features, experimental current-condition rules, anomalies and neighbour modules |
| `ml/hazard_context/`, `storm_risk/` | Separate data-gated hazard/ERA5 research |
| `esp32/`, `ml/generated/` | Separate embedded applications/exports; not the Python hybrid |
| `tests/`, `simulator/` | Software tests and engineering simulations |
| `reports/mandi_pipeline_v2/` | Current numerical, online/TabPFN and UI evidence |
| `reports/submission/2026-10-21/` | Retained v1 submission evidence |
| `docs/archive/`, `docs/reference/`, other report folders | Historical evidence and specialist research |
| `data/`, `outputs/`, `results/` | Source provenance and local working data; raw/runtime files are ignored |

Existing model/export paths and frozen catalog files are preserved because
checksums and reproducibility depend on them. Raw datasets, SQLite stores,
credentials and local node_modules/.venv are not submission source artifacts.
