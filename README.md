# INDRA — six-channel Mandi forecasting prototype

INDRA forecasts **temperature, humidity, pressure, PM2.5, PM10 and wind at +6 hours**.
The active Python backend uses a residual neural network + history XGBoost + ridge
ensemble, `india_mandi_hybrid_6h_v1`. It derives 66 causal features from 25 hourly
snapshots spanning 24 hours. Short histories explicitly use persistence warm-up.

**Submission scope:** implemented ML/software prototype with retrospective Mandi
modeled-data evaluation. Physical Mandi accuracy, disaster prediction, live online
learning and ESP32/radio execution are not established.

## Start here

- [Features and what is actually available](docs/FEATURES.md)
- [Submission guide and demonstration steps](docs/SUBMISSION_GUIDE.md)
- [Latest Mandi test report](reports/submission/2026-10-21/REPORT.md)
- [Inputs, architecture and evidence](docs/PROJECT_OVERVIEW.md)
- [Documentation index](docs/README.md)

## Run locally

Python 3.13 and Node 22 are the tested setup. From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dashboard.txt
npm ci --prefix apps/indra-himachal-ui
```

Test the committed models on the locally retained Mandi dataset, then start the
historical Mandi dashboard:

```sh
.venv/bin/python scripts/test_mandi_submission.py
.venv/bin/python scripts/run_himachal_demo.py --offline --db data/himachal/mandi_dashboard.sqlite --observations data/himachal/mandi_replay.json
```

Open **http://127.0.0.1:8080**. For frontend development, run `npm run dev --prefix apps/indra-himachal-ui` in another terminal and open **http://127.0.0.1:5173**.
The development frontend proxies `/api` to the same backend.

A fresh checkout does not contain raw CSVs. Retrieve the configured source first:
`.venv/bin/python scripts/test_india_mandi.py --prepare`. This downloads data and
writes the older baseline report; it does not train. Existing source/model hashes
must match. The latest submission command itself is offline and does not retrain.

For clearly labelled synthetic rain/snow/cloudburst-rule fixtures, use
`.venv/bin/python scripts/run_himachal_demo.py --offline` without `--observations`.
Do not present that demonstration as measured Mandi weather.

## Current Mandi result

24,336 hourly API/model positions, January 2024–10 October 2026; 22,602 training,
738 validation and **954 reused future-test pairs** with six-hour boundary purges.
No Chinese observations or weights enter this run. Source weather/PM use different
ECMWF/CAMS grids; these are not six co-located station sensors.

| +6h target | Hybrid MAE | Unit |
| --- | ---: | --- |
| Temperature | 1.3063 | °C |
| Relative humidity | 6.9332 | percentage points |
| Pressure | 0.9255 | hPa |
| PM2.5 | 6.8923 | µg/m³ |
| PM10 | 8.9972 | µg/m³ |
| Wind | 0.3128 | m/s |

All seven candidate/baseline results, RMSE/R², inputs, later API labels and blend
weights are in the [submission report](reports/submission/2026-10-21/REPORT.md).
Regression errors are not classification accuracy percentages. The test period
was examined previously, so it is not a new untouched or field test.

## Repository map

| Path | Purpose |
| --- | --- |
| `apps/indra-himachal-ui/` | Active React dashboard |
| `server/` | Local SQLite/FastAPI read-only backend |
| `ml/india_mandi/`, `scripts/test_mandi_submission.py` | Active hybrid and Mandi evaluation |
| `ml/models/india_mandi_hybrid_6h_v1/` | Active profile, component hashes and blend coefficients |
| `ml/models/india_mandi_neural_history_v1/` | Saved neural arrays and normalization |
| `ml/models/india_mandi_modeled_6h_v1/` | Saved Mandi tree/ridge components and compact comparison |
| `ml/himachal/` | Features, experimental current-condition rules, anomalies and neighbour modules |
| `ml/hazard_context/`, `storm_risk/` | Separate data-gated hazard/ERA5 research |
| `esp32/`, `ml/generated/` | Separate embedded applications/exports; not the Python hybrid |
| `tests/`, `simulator/` | Software tests and engineering simulations |
| `reports/submission/2026-10-21/` | Current numerical report and verification |
| `docs/archive/`, `docs/reference/`, other report folders | Historical evidence and specialist research |
| `data/`, `outputs/`, `results/` | Source provenance and local working data; raw/runtime files are ignored |

Existing model/export paths and frozen catalog files are preserved because
checksums and reproducibility depend on them. Raw datasets, SQLite stores,
credentials and local node_modules/.venv are not submission source artifacts.
