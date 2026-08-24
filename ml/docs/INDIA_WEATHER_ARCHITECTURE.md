# India Weather Hazard ML Architecture

## 1. Objective

Build a weather and environmental hazard model that can eventually run on the
ESP32-S3, while training and validating it on substantially larger India-
focused data.

The work is deliberately split into two stages:

1. **Baseline stage:** combine and validate the data already in this repository.
2. **Scale-up stage:** replace weak or synthetic signals with larger, real India
   weather, air-quality, and event data, then retrain and compare against the
   baseline.

The baseline is a learning and integration test. Its scores must not be
presented as evidence of India-wide operational performance.

## 2. Current repository inputs

| Asset | Current role | Limitation |
|---|---|---|
| `ml/dataset/weatherHistory.csv` | Raw hourly weather baseline | Szeged/Hungary, not India |
| `code/ml/data/dataset.csv` | Prepared 14-feature dataset | Contains four extra forecast labels and synthetic sensors |
| `ml/real_india_data/metadata.json` | India dataset/model metadata | Source CSV is not currently present in the repo |
| `ml/model/` | Existing 14-feature, four-hazard models | Random-split baseline; likely optimistic evaluation |
| `ml/prepare_dataset_v2.py` | Improved 22-feature preparation | Must be aligned with C export before deployment |
| `ml/train_model_v2.py` | Temporal CV, tuning, SHAP pipeline | Can train more trees/features than current exporter supports |

The canonical first-stage targets are the existing four hazards:

- wildfire
- flood
- storm
- air quality

The extra labels in `code/ml/data/dataset.csv` (`rain_forecast`, `temp_rise`,
`temp_drop`, and `wind_warning`) should be treated as a separate forecasting
task until their target definition and forecast horizon are documented.

## 3. Proposed end-to-end architecture

```text
Raw source files/APIs
        |
        v
Source adapters + schema validation + provenance
        |
        v
Canonical hourly observations
        |
        +--> quality checks, missingness, unit normalization
        |
        v
Feature builder
  - sensor-compatible features
  - temporal/context features
  - source availability flags
        |
        v
Time- and location-aware dataset split
        |
        +--> training/tuning only
        |        |
        |        v
        |   multi-task hazard model
        |        |
        |        v
        |   calibration + threshold selection
        |
        +--> untouched India holdout
                 |
                 v
       metrics, error slices, drift report
                 |
                 v
       export-compatible edge model
```

The key design decision is to keep ingestion and feature generation separate
from model training. That lets new India sources be added without changing the
model contract or silently changing the meaning of an existing feature.

## 4. Canonical data contract

Every source should be converted to one table with at least:

```text
location_id, latitude, longitude, timestamp_utc,
temperature_c, relative_humidity_pct, pressure_hpa,
wind_speed_mps, wind_direction_deg, precipitation_mm,
visibility_km, pm25_ug_m3, co2_ppm, lightning_distance_km,
source_name, source_version
```

Rules:

1. Store timestamps in UTC and retain the original timezone/source timestamp.
2. Preserve `location_id`, latitude, and longitude; do not concatenate rows
   without location and time identity.
3. Convert units once at ingestion. Record the conversion in metadata.
4. Keep missing values missing. Do not fill a missing PM2.5 or lightning value
   with synthetic data in the India production dataset.
5. Add per-field quality flags such as `is_imputed`, `is_observed`, and
   `source_available`.
6. Deduplicate by `(location_id, timestamp_utc)` using a documented priority
   order when sources overlap.

The current synthetic PM2.5, CO2, and lightning generation can remain in a
clearly named baseline adapter, but those rows must carry a synthetic-field
flag and must not be mixed indistinguishably with real sensor observations.

## 5. Dataset stages

### Stage A — repository baseline

Use the available prepared data to validate the complete pipeline:

- preserve the existing 14-feature contract first;
- train the four hazard heads;
- use chronological validation where timestamps are available;
- retain a final untouched holdout;
- measure missingness, class balance, and positive-event counts;
- compare the baseline model with simple rule-based labels and a naive model.

For a fair baseline comparison, run two experiments:

1. **Existing-data experiment:** the current prepared dataset and labels.
2. **Rebuilt-data experiment:** regenerate from raw data with the canonical
   adapter and explicit synthetic-field flags.

If the two results differ, the rebuilt pipeline becomes authoritative.

### Stage B — India scale-up

Add India data through adapters rather than editing the training script. The
scaled dataset should combine, where licensing and quality permit:

- station or gridded weather observations;
- precipitation and pressure time series;
- air-quality observations, especially PM2.5;
- lightning or severe-weather observations;
- geographic context such as elevation, land cover, and urban/rural class;
- event labels from official warnings, flood/fire records, or independently
  defined observation windows.

The first large weather backbone is IndiaWeatherBench, an IMDAA-based release
whose current dataset card describes 2000–2019 coverage, 6-hourly samples, an
approximately 256×256 India grid, and 43 channels with predefined train,
validation, and test periods. The complete archive is roughly 216 GB, so start
with a bounded HDF5 slice and validate the adapter before processing the full
archive. `ml/real_india_data/prepare_indiaweatherbench.py` performs nearest-grid
extraction for configured cities/stations, writes input hashes and units to a
manifest, and deliberately emits no hazard labels. Independent station/event
records must be joined before hazard fine-tuning.

The event joiner `ml/real_india_data/join_independent_events.py` requires a
verified source, event interval, and source coverage interval. Rows outside
coverage are kept unknown; they are not treated as negative examples. This is
required before comparing the larger teacher against the current heuristic-label
pilot.

#### How the sources are combined

The larger dataset is a keyed union, not an unrestricted row concatenation:

```text
(location_id, timestamp_utc)
        |
        +-- weather observation/features       -> backbone examples
        +-- IMD/event record                   -> storm label or UNKNOWN
        +-- OpenAQ PM2.5                        -> AQ value/label or UNKNOWN
        +-- fire/flood source                   -> corresponding label or UNKNOWN
```

Each hazard head has its own label mask. A row with no storm coverage can
train the weather backbone and the AQ head, but it cannot be used as a storm
negative. The offline objective is therefore:

```text
L = L_weather + Σ_h mask_h * L_hazard_h
```

where `mask_h` is 1 only when hazard `h` has an observed, quality-approved
label. This is the central rule for combining the heterogeneous India data.
The current edge implementation remains four independent XGBoost heads; the
masked shared encoder is the larger offline teacher to compare against it.

The first India model should be evaluated by both **time** and **geography**:

- train on earlier dates, test on later dates;
- hold out entire stations or districts;
- reserve at least one region/climate zone not used for training;
- report performance separately for monsoon, pre-monsoon, and post-monsoon
  periods where sample counts permit.

## 6. Feature and target design

### Edge-compatible feature set

Start with the existing 14 features so the current firmware contract remains
stable. Fix naming and units before adding anything:

```text
temperature, humidity, pressure, wind speed,
pm25, co2, lightning distance,
temperature/humidity ratio, pressure trend, heat index,
dew point, fire risk index, flood risk index, lightning threat
```

The v2 features (cyclical time and physical interactions) should be introduced
as a versioned `feature_schema_v2`, not silently appended to v1. Any feature
that is unavailable on the ESP32 must either be removed from the edge model or
have a precisely defined on-device approximation.

### Targets

Avoid using a derived risk feature to define the same target that the model is
then asked to predict. That creates label leakage and explains extremely high
baseline scores. For the scale-up model, define each target with a forecast
horizon, for example:

```text
input window: previous 6–24 hours
target: event occurs in the next 1–6 hours
```

Each target needs a written event rule, positive/negative window, source, and
uncertainty policy. If official event labels are unavailable, use weak labels
only for experimentation and report them as weakly supervised results.

## 7. Model architecture

### Training model

Use one shared temporal feature encoder followed by four hazard heads:

```text
normalized tabular/time-window features
              |
        shared XGBoost/GBDT representation
       /       |        |        \
 wildfire    flood    storm    air_quality
   head       head     head        head
```

For the immediate baseline, the practical implementation is four independent
XGBoost binary classifiers because it matches the current code and C exporter.
For the India scale-up, compare this against a shared multi-task model offline.
Keep the edge winner based on calibration, recall at an acceptable false-alarm
rate, model size, and inference latency—not accuracy alone.

Use class weighting or focal-style sampling for rare events. Select alert
thresholds on validation data only, then freeze them before final testing.

### Edge deployment contract

The exported model must specify:

- feature schema version and ordered feature names;
- unit for every feature;
- normalization mean/std;
- number of classes and class names;
- tree count, maximum depth, and maximum nodes;
- probability conversion and alert thresholds;
- a model checksum/version.

The C exporter must reject a model whose feature count, tree count, depth, or
class list exceeds the declared firmware limits. It must never silently truncate
trees or map unknown features to index zero.

## 8. Evaluation gates

### Gate 1 — pipeline correctness

- deterministic regeneration from the same input;
- no duplicate location/time rows;
- no future-derived features in the input window;
- no train/test overlap by timestamp or location;
- feature order and units verified automatically;
- synthetic fields clearly reported.

### Gate 2 — baseline model

- chronological test metrics for every hazard;
- precision, recall, F1, PR-AUC, Brier score, and calibration;
- confusion matrix and false alarms per day/station;
- results by season and weather regime;
- rule-based baseline comparison.

### Gate 3 — India scale-up

- held-out future period;
- held-out stations/regions;
- performance on rare positive events;
- robustness to missing sensors and source changes;
- drift report comparing training and deployment distributions.
- no head is promoted when its verified positive count or geographic coverage
  is below the minimum recorded in the experiment manifest;
- unknown-label rows are excluded per head, and the report includes the exact
  labeled row count and positive count for every hazard.

### Gate 4 — ESP32 release candidate

- prediction parity between Python and C on a fixed golden-vector suite;
- memory and flash budget measured on the target firmware;
- latency measured for all four heads;
- behavior tested with missing/out-of-range sensor values;
- model and feature schema version pinned.

## 9. Recommended implementation order

1. Create a versioned canonical schema and data manifest.
2. Add a baseline adapter for `ml/dataset/weatherHistory.csv` and the current
   prepared India data.
3. Rebuild features and labels into a new output directory; do not overwrite
   `ml/model/` or `ml/generated/`.
4. Add temporal and station-aware split utilities.
5. Train the 14-feature four-head baseline and generate an evaluation report.
6. Add leakage checks and Python-vs-C golden-vector tests.
7. Repair the exporter so schema/model-limit violations fail loudly.
8. Add real India sources through adapters and rerun the same report.
9. Only after the India holdout is stable, test v2 features and larger models
   offline; export a pruned edge-compatible variant separately.

## 10. First milestone

The first concrete milestone is **Baseline v1 reproducibility**:

```text
raw inputs -> canonical dataset -> 14 features -> 4 labels
           -> temporal/station split -> four models
           -> metrics + leakage report -> edge export validation
```

No India scale-up decision should be made until this milestone produces a
repeatable report and the model passes Python/C prediction parity checks.

## 11. Execution plan for this repository

The implementation sequence is:

1. **Available-data baseline:** run the existing 14-feature pipeline on the
   prepared 26-city data with a strict geo-temporal split. Keep its metrics as
   the integration baseline; do not mix the separate OpenAQ regression target
   into the four binary hazard labels.
2. **Weather backbone:** train the 56-city weather teacher, retaining the
   future-period and held-out-city metrics. This supplies a larger, India-wide
   representation and context features, but it is not itself a hazard label.
3. **Verified hazard teachers:** train the storm head from IMD best tracks and
   the AQ head from station-level OpenAQ joins. Train wildfire and flood heads
   only after an independent event source is joined; until then, keep their
   weak-label scores explicitly marked as provisional.
4. **Teacher comparison:** evaluate the masked/feature-rich offline teachers
   by future time, held-out city, and climate region. Report per-head labeled
   rows, positives, precision/recall/F1 or MAE/RMSE as appropriate, and false
   alarms per station-day.
5. **Edge distillation:** distill only the approved teacher outputs into the
   fixed 14-feature student, calibrate thresholds on validation data, export to
   C, and require the existing golden-vector parity gate.
6. **Promotion gate:** promote a hazard head only when its independent labels,
   geographic holdout, calibration, and Python/C parity all pass. A missing
   verified source is an explicit `NOT_READY` result, not a zero-filled label.

### Current evidence checkpoint

The repository has completed the baseline and the first scale-up experiments:

| Layer | Current evidence | Status |
|---|---|---|
| 14-feature four-head baseline | 26-city geo-temporal test; wildfire/flood/storm F1 ≈ 0.994–0.999, AQ F1 0.833 | integration baseline |
| India weather teacher | 56 cities; 112,448 rows; held-out-city/future split | usable context teacher |
| Verified storm teacher | IMD 1982–2020; 48 positives; F1 0.086 | `NOT_READY`, coverage too sparse |
| Verified flood teacher | IFI/IMD-derived 56-city join; 86,387 known rows; F1 0.305 | research-only, needs spatial validation |
| Independent AQ teacher | 4 cities; 701 daily rows; held-out-city MAE 28.20 | research-only, needs longer coverage |
| Edge export/parity | distilled 14-feature C model; maximum error about `3.1e-8` | passed |

The next required scale-up work is verified wildfire/flood event coverage and
longer, more geographically balanced AQ observations. Until those are added,
the architecture is planned and partially trained, but it is not an India-wide
hazard deployment model.

## 12. Reproducible runbook

Run the stages in this order from the repository root. Each output directory
is versioned so a later large-data run does not overwrite the baseline.

### A. Available-data baseline

```bash
python3 ml/real_india_data/train_india_pilot.py \
  --data ml/data_india_pilot/prepared_26 \
  --output ml/model_india_26_baseline_repro \
  --split-strategy geo-temporal \
  --holdout-fraction 0.2
```

### B. Larger India weather backbone

```bash
python3 ml/real_india_data/train_weather_teacher.py \
  --input ml/data_india_pilot/weather_56_cities.csv \
  --output ml/model_india_weather_teacher_56_geo_temporal_repro \
  --split-strategy geo-temporal \
  --holdout-fraction 0.2
```

The weather backbone is a next-day context task. It must not be described as
hazard accuracy; its output is used as teacher context for the hazard heads.

For a verified-event scale-up check, join the IMD intervals to the same
weather table and train the storm head separately:

```bash
python3 ml/real_india_data/join_independent_events.py \
  --weather ml/data_india_pilot/weather_56_cities.csv \
  --events ml/data_india_pilot/raw/imd_storm_events_2015_2020_56.csv \
  --output ml/data_india_pilot/imd_storm_labeled_56

python3 ml/real_india_data/train_verified_storm_weather.py \
  --weather ml/data_india_pilot/weather_56_cities.csv \
  --labeled-weather ml/data_india_pilot/imd_storm_labeled_56/weather_with_independent_labels.csv \
  --output ml/model_india_storm_weather_verified_56 \
  --holdout-fraction 0.2
```

The same generic trainer now supports the independent flood head. Its input
is the derived IFI event table, whose spatial policy is explicit city/district
token matching:

```bash
python3 ml/real_india_data/prepare_ifi_flood_events.py \
  --input ml/data_india_pilot/raw/India_Flood_Inventory_v3.csv \
  --locations ml/real_india_data/locations_56_cities.csv \
  --output ml/data_india_pilot/raw/ifi_flood_events_56.csv

python3 ml/real_india_data/join_independent_events.py \
  --weather ml/data_india_pilot/weather_56_cities.csv \
  --events ml/data_india_pilot/raw/ifi_flood_events_56.csv \
  --output ml/data_india_pilot/ifi_flood_labeled_56

python3 ml/real_india_data/train_verified_storm_weather.py \
  --weather ml/data_india_pilot/weather_56_cities.csv \
  --labeled-weather ml/data_india_pilot/ifi_flood_labeled_56/weather_with_independent_labels.csv \
  --output ml/model_india_flood_weather_verified_56 \
  --hazard flood \
  --holdout-fraction 0.2
```

### C. Heterogeneous masked hazard teacher

```bash
python3 ml/real_india_data/train_masked_teacher.py \
  --features ml/data_india_pilot/offline_prepared_26_teacher_context/features.csv \
  --labels ml/data_india_pilot/offline_prepared_26_teacher_context/labels.csv \
  --identifiers ml/data_india_pilot/offline_prepared_26_teacher_context/identifiers.csv \
  --verified-labels ml/data_india_pilot/imd_storm_labeled_26/weather_with_independent_labels.csv \
  --verified-hazard storm \
  --output ml/model_india_26_masked_verified_teacher_context
```

When larger verified event tables arrive, only the feature/label adapters and
the verified-label arguments should change. The split, masking, metrics, and
promotion gates remain fixed.

### D. Edge release candidate

Only after the teacher passes its independent-label gates, distill to the
fixed 14-feature contract, run `ml/convert_to_c.py`, and compare Python and C
predictions on the golden vectors. The generated header is a release
candidate only when the parity check, threshold calibration, and target-device
resource measurements all pass.

The current handoff can be reproduced with:

```bash
python3 ml/real_india_data/distill_masked_teacher.py \
  --edge-data ml/data_india_pilot/prepared_26 \
  --teacher-data ml/data_india_pilot/offline_prepared_26_teacher_context \
  --teacher ml/model_india_26_masked_verified_teacher_context \
  --edge-model ml/model_india_26 \
  --output ml/model_india_26_masked_distilled_edge \
  --alpha 0.2

python3 ml/convert_to_c.py \
  --model ml/model_india_26_masked_distilled_edge \
  --output ml/generated/model_data_india_26_masked_distilled_edge.h

python3 ml/real_india_data/check_c_parity.py \
  --header ml/generated/model_data_india_26_masked_distilled_edge.h \
  --model ml/model_india_26_masked_distilled_edge \
  --data ml/data_india_pilot/prepared_26/features.csv
```
