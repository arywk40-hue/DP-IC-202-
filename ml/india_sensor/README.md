# India sensor-only research pipeline

**Confidential: do not publish before IP review.** [Audit/capabilities](../../docs/INDIA_SENSOR_RISK_PLAN.md), [phase evidence](../../reports/india_sensor_phase/REPORT.md), [main guide](../../docs/PROJECT_OVERVIEW.md).

This adds India-only **same-node six-hour forecasts of measured thresholds**. It does not replace the working current-weather two-node spatial ensemble, predict disasters, or interpolate risk between nodes. All cloudburst/flood/landslide/fire/storm heads remain unavailable. Their eventual probabilities require independent labeled data and validation.

## Current offline phase

The latest executed evidence is [6 October offline report](../../reports/offline_phase/REPORT.md), superseding October 5 model-selection/calibration statements below. Four protocols now include temporal-only and Himalayan-only, validation-only class-weight/cutoff selection, 61 identical repeated fits, optional PM admission/training, replay and a host-verified C export. National wind remains uncalibrated and misses both test positives. Disaster alerts remain disabled.

```sh
# Raw-free checkout demo with the committed national-B bundle (synthetic inputs).
python3 -m ml.india_sensor.predict --config configs/india_sensor_offline.json --model-dir ml/models/india_sensor_v1 --input esp32/india_sensor/example_hourly.csv
python3 -m ml.india_sensor.replay --config configs/india_sensor_offline.json --model-dir ml/models/india_sensor_v1 --input esp32/india_sensor/example_hourly.csv --synthetic --output /tmp/indra-replay.json
# Full acquired-archive reproduction; choose fresh output directories for a rerun.
python3 -m ml.india_sensor.prepare --config configs/india_sensor_offline.json
python3 -m ml.india_sensor.train --config configs/india_sensor_offline.json
python3 -m ml.india_sensor.evaluate --config configs/india_sensor_offline.json
python3 -m ml.india_sensor.verify --config configs/india_sensor_offline.json
python3 -m ml.india_sensor.pm --output /tmp/indra-pm-admission.json
python3 -m ml.india_sensor.export --config configs/india_sensor_offline.json
python3 -m pytest -q
pio run -d esp32/india_sensor
```

Bundle supports national B; C/D can only fall back to B, and regional/A artifacts require local training. `--model-dir` changes artifact lookup only; the exact training configuration hash and model hashes are still required. Metadata paths to source files describe original provenance, not a requirement to download data for the bundled demo. Changed source/configuration needs a fresh prepared run; do not reuse matrices from another config.

## October 5 configuration reference and acquisition commands

Run from the repository root. The completed run used Python 3.13.11 and the versions pinned below; the legacy/physics environments stay separate.

```sh
python3 -m venv /tmp/indra-india-sensor-venv
/tmp/indra-india-sensor-venv/bin/python -m pip install -r requirements-india-sensor.txt
```

Public NOAA acquisition already exists. These are optional **network/download** commands for a fresh checkout, not new downloads performed in this phase. They reuse unsigned public access; no authentication is bypassed. A valid enriched station registry and prior physics `station_qc.csv` must also be present. The original registry, SRTM and climate receipts are kept in `data/registry/`; these instructions do not claim every future NOAA station is surveyed or terrain-valid.

```sh
python3 -m ml.datasets.noaa --output data/noaa_ghcnh --year 2024
python3 -m ml.datasets.hourly_noaa --acquire-year 2023
python3 -m ml.datasets.hourly_noaa --years 2023 2024
```

`hourly_noaa` rebuilds the existing archive outputs; do not run it merely to execute this new model. For the already acquired archive, prepare/features and train/calibrate/evaluate are:

```sh
python3 -m ml.india_sensor.prepare --config configs/india_sensor_risk.json
python3 -m ml.india_sensor.train --config configs/india_sensor_risk.json
python3 -m ml.india_sensor.evaluate --config configs/india_sensor_risk.json
python3 -m pytest tests/test_india_sensor.py -q
python3 -m pytest -q
```

Replace `python3` with the isolated interpreter if needed. Preparation writes per-site normalized rows/labels to `data/india_sensor/processed/` and causal features to `features/`; raw source files remain untouched. It refuses an already populated feature directory. For another dataset version, copy the configuration to a new file, change `processed`, `features`, `models`, `reports` to fresh directories, then pass that file to every command. This avoids deleting or mixing previous artifacts. Paths resolve from the repository root, not the caller's current directory.

Training includes both scopes, all A–D variants and calibration; there is no separate command that secretly fits the Himalayan test data. C uses eligible Himalayan **calibration** stations; a whole-Himalaya holdout leaves none and intentionally falls back. D's routing derives from GPS/height proxies; unavailable/uncalibrated experts use B. All fitted models are bounded depth-3, 40-tree XGBoost, reusing the node-forecast approach. PM never blocks this fit; all PM features are currently inactive because NOAA has no PM truth here.

## Sensor view and features

The sensor feature builder requires exactly these columns. Units are encoded in the column names and the original canonical long-form source schema; arbitrary wrong-unit numbers cannot always be detected from range checks.

| Category | Fields / semantics |
|---|---|
| Identity | `location_id`, `physical_site_id`, `source_id`, `country_code=IN` |
| Time | `timestamp_utc`, `available_at_utc`: explicit UTC completed-window end and receipt/availability; `interval_seconds`: native cadence |
| Location | `latitude`, `longitude`: WGS84 degrees; fixed surveyed `elevation_m`, `elevation_datum=EGM96`; unknown/ellipsoid heights masked |
| Source interpretation | `pressure_reference=station`; unresolved/sea-level pressure masked; `climate_zone` is registry grouping, not an A/B predictor |
| Raw | T °C, RH %, P hPa, PM2.5/10 µg/m³, wind m/s in existing canonical column names; missing PM is null, never zero |
| Temporal | Reused 1/3/6/12/24h lags, 1h differences, 6/24h mean/std; native 10/30/60/360/1440min endpoint changes and rolling min/max/mean/std, without duplicate hourly aliases |
| Meteorological | Reused Magnus dewpoint, depression, vapor-pressure deficit, heat index; approximate absolute humidity; pressure minus prior-24h mean and pressure tendencies hPa/min |
| Particulate | Reused PM2.5/PM10 ratio and channel tendencies/rolling windows; no identified smoke/dust source |
| Geography/context | GPS lat/lon/height for B–D, UTC hour/month sine/cosine, JJAS calendar proxy; GPS-derived regional routing and Köppen grouping for evaluation |

Unsupported 10/30min windows in hourly data stay NaN. Differences require contiguous valid history; gaps are not filled. Rolling features use the past/current window only. Delayed rows are conservatively omitted instead of backdated, even after arrival. Wind variability is not measured gusts; encoder pulse-to-m/s calibration is required before ingestion. No wind azimuth, rainfall, CAPE, soil state, `era5_*`, satellite or hidden-sensor value is a runtime input. INA219 health remains diagnostic.

Three targets: wind ≥10 m/s, temperature ≥35°C and RH ≥95%, each at **exactly t+6h in that completed hourly average**. They are not “any time in the next six hours,” gust warnings, official heatwaves or confirmed fog. Labels are separately stored, exact-time joined and missing future readings stay unknown. Existing input-generated Beijing event labels are never used. Physical reference/threshold provenance and raw archive hashes are in the reports/model manifest.

Independent event exports have a separate long schema (`labels.EVENT_FIELDS`): site, UTC interval/availability, target and definition version, source/version/raw SHA256, country, observed-evidence kind, monitored-negative verification, event group, and location/time uncertainty. Weak rules/modeled rain cannot pass as observed truth; absent events cannot become zeros. `validate_independent` and `require_disjoint_events` are tested admission utilities, **not a finished event association/training pipeline**. Rights and observation adjudication still require source-registry review. Never feed these label fields into `features.build`.

## Split and metric contract

No row sampling caps. Physical sites are deduplicated before whole-station roles; training is ≥20 km from held-out and validation sites. Fit: 2023–June 2024 training stations. Selection report: July/August validation stations. Calibration: September/October at those validation stations. Test: November/December at separate test stations. Entire global 72h blocks belong to one role; boundary blocks are dropped, with an additional 24h-history and 6h-target purge. Blocks are proxies, not true storm identities; future event labels must additionally keep entire recorded event groups disjoint.

`national` holds out whole sites; `himalaya_holdout` holds out the predeclared 28–37°N, 72–90°E, QC-valid elevation ≥500m proxy. Himachal reporting uses a labeled rectangle proxy, not an official state boundary. Per-Köppen, elevation and GPS-region metrics retain coverage counts. Missing altitude remains unknown. No all-state/coastal/eastern-Himalaya validation is implied.

Precision, recall/F1, AP, meaningful ROC-AUC, Brier, reliability bins/ECE, confusion matrices, false-positive **hours** per monitored station-day and missed-positive-hour fraction are reported. The October 5 configuration uses 0.5. The offline configuration selects raw cutoffs on July/August validation only, before independent calibration/testing; unsupported thresholds stay null. Diagnostic 0.5 metrics are retained for comparison. Bootstrapped Brier intervals resample stations; they are neither prediction bands nor independent storm confidence. Constant training prevalence and current-measurement persistence are compared. Validation numbers are diagnostics; no parameters are chosen on the test. Archive probability calibration does not establish field reliability.

## Research demo

Make a replay input from one generated **real archive** station. This example contains training-period data and demonstrates the interface, not held-out forecast accuracy or live hardware.

```sh
python3 - <<'PY'
import json
import pandas as pd
from ml.india_sensor.features import METADATA
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
m = json.load(open('reports/india_sensor_phase/preparation.json'))
f = pd.read_parquet(m['files'][0]['features'])
f.iloc[:72][[*METADATA, *RAW_SENSOR_COLUMNS]].to_csv('/tmp/indra-sensor-demo.csv', index=False)
PY
python3 -m ml.india_sensor.predict --config configs/india_sensor_risk.json --input /tmp/indra-sensor-demo.csv --strategy B
```

For owner sensor replay, preserve the exact schema, use `source_id=indra_owner_nodes`, calibrated completed-hour means and at least 24h history at one fixed surveyed site. This is an explicit runtime-only source, not secretly added to archive training. Unavailable/invalid T/RH/wind, insufficient history or fitted-range violations refuse output. Artifact hashes are checked, no pickle is loaded, and uncalibrated heads return `probability=null` plus a named research score. Missing/uncalibrated experts fall back; model failure yields null and corrupted artifacts are rejected. These local-file checks do not authenticate nodes. The national-B offline C export and raw-hour preprocessing are host-tested and cross-compiled; see [interface and physical acceptance procedure](../../esp32/india_sensor/README.md). It is not hardware validated.

The existing A/B query-point weather demo and hidden-C scorer remain unchanged: see [NODE_COLLECTION_SPEC](../../reports/nwic_pipeline/NODE_COLLECTION_SPEC.md).

## Data that still requires authorized access

IMD hourly AWS/ARG/event exports need approved terms/permission. MOSDAC requires registered product access. OpenAQ needs an API key and each provider's rights. CDS needs a personal token/accepted product terms or manual ERA5 download ([existing request spec](../../reports/physics_phase/ERA5_DOWNLOAD.md)); ERA5 may be research context/labels but is excluded from this sensor-only fit. NASA IMERG/FIRMS and GSI/CWC inventories need appropriate authorized export, verified rights, label definitions/uncertainty and monitored negatives. None was downloaded here. NWIC/Delhi remain unresolved/quarantined; restricted CPCB stays separate. Country/source allowlists isolate China without moving legacy artifacts or breaking their tests.
