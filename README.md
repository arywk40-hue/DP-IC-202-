# INDRA — six-channel weather forecasting

INDRA forecasts **temperature, humidity, pressure, PM2.5, PM10 and wind at +6 hours**.
It also provides **six parameter heatmaps** from synchronized locations and
**ten current weather-pattern categories** from a synthetic-trained classifier.
See [the feature guide and complete local demo](docs/EVERYTHING.md#source-4f516879b0b8).
Category scores are not calibrated real-event probabilities.
It also provides [cloudburst, flash-flood and landslide scenarios](docs/EVERYTHING.md#source-76ac9fbe3adb)
using a documented Monte Carlo simulator. Their percentages describe simulated
outcomes under assumed rainfall/soil/drainage, not real-event probabilities.
The active Python backend uses LightGBM, a residual neural network, the retained
hybrid and persistence in `india_mandi_tabular_v2`. It derives 66 causal features from 25 hourly
snapshots spanning 24 hours. Short histories explicitly use persistence warm-up.

**Submission scope:** implemented ML/software prototype with retrospective Mandi
modeled-data evaluation. Physical Mandi accuracy, disaster prediction, promoted live adaptive outputs and ESP32/radio execution are not established.
A durable delayed-label online learner is implemented in shadow mode.

## Documentation and audit trail

[docs/EVERYTHING.md](docs/EVERYTHING.md) is the consolidated operating handbook, including
architecture, model evaluation, online learning, data provenance and blockchain
setup. Original source paths are indexed in
[the consolidation manifest](docs/documentation_consolidation.json).
All Markdown documentation is in the handbook. Original Markdown evidence is
preserved in `docs/archive/original_markdown.zip`; model weights and binary exports
retain their original bytes. Folder moves are recorded in
[the repository migration manifest](docs/repository_reorganization.json).

The backend records hash-linked audit events within its SQLite transactions.
The System page shows local audit status; signed exports and a Solidity contract
support local EVM anchoring. This does not yet provide independently witnessed
public-network verification. See the handbook for commands and trust boundaries.

## Run locally

For newly fetched Mandi model values and automatic delayed shadow testing, see
[the current feed guide](docs/EVERYTHING.md#source-6d85e1c96415).

Complete synthetic maps/category showcase: `.venv/bin/python server/scripts/run_himachal_demo.py --offline --weather-demo --db ml/data/himachal/weather_demo.sqlite --port 8082`, then open http://127.0.0.1:8082. It stays separate from the downloaded Mandi view.

Python 3.13 and Node 22 are the tested setup. From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r server/requirements.txt
npm ci --prefix ui
```

Test the committed models on the locally retained Mandi dataset, then start the
historical Mandi dashboard:

```sh
.venv/bin/python ml/scripts/train_mandi_v2.py --evaluate
.venv/bin/python server/scripts/run_himachal_demo.py --offline --db ml/data/himachal/mandi_dashboard.sqlite --observations ml/data/himachal/live_hourly.json
```

Open **http://127.0.0.1:8080**. For frontend development, run `npm run dev --prefix ui` in another terminal and open **http://127.0.0.1:5173**.
The development frontend proxies `/api` to the same backend.

A fresh checkout does not contain raw CSVs. Retrieve the configured source first:
`.venv/bin/python ml/scripts/train_mandi_v2.py --prepare`. This downloads the configured source without training. Existing source/model hashes
must match. The latest submission command itself is offline and does not retrain.

For clearly labelled synthetic rain/snow/cloudburst-rule fixtures, use
`.venv/bin/python server/scripts/run_himachal_demo.py --offline` without `--observations`.
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
weights are in the [submission report](docs/EVERYTHING.md#source-992f2b21c23a).
Results are mixed versus v1; regression errors are not classification accuracy percentages. The test period
was examined previously, so it is not a new untouched or field test.

## Repository map

```text
ml/                  Models, training code, data, configs, scripts and ML tests
  configs/           Versioned model and dataset settings
  data/              Datasets, source receipts and local stores
  models/            Saved trained models
  generated/         Generated model exports
  scripts/           Training, fetching, evaluation and research commands
  storm_risk/        Separate storm-risk research pipeline
  tests/             Model, data and firmware integration tests
  requirements/      Python dependency sets for ML workflows
  reports/           Evaluation reports and preserved evidence
  outputs/, results/ Local generated experiment outputs
ui/                  React dashboard, browser tests and UI verification reports
server/              FastAPI backend, dashboard scripts and integration tests
contracts/           Solidity contract, audit code, anchor scripts and blockchain tests
esp32/               Embedded applications and firmware
simulator/           Network and radio engineering simulations
docs/                Complete handbook, reports, references and migration records
```

Run Python commands from the repository root. The dashboard dependencies are in
`server/requirements.txt`; optional blockchain dependencies are in
`contracts/requirements.txt`. Historical training environments are under
`ml/requirements/`.

```sh
.venv/bin/python -m pytest -q
npm test --prefix ui
npm run build --prefix ui
```

Original Markdown evidence is preserved in `docs/archive/original_markdown.zip`.
The frozen model catalog retains its original bytes; the export verifier resolves
its historical config references. Raw datasets, SQLite stores, credentials,
`node_modules/` and `.venv/` remain local and ignored.
