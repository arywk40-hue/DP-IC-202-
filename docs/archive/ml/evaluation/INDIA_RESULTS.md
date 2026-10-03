> Archived evidence / superseded guide. Original path: `ml/evaluation/INDIA_RESULTS.md`. Protocol-specific results are preserved; use [PROJECT_OVERVIEW.md](../../../PROJECT_OVERVIEW.md) for current scope.

# Indian climate evaluation and training results

## What was trained

Two Indian research model profiles were fitted on the downloaded CPCB-derived
station observations. They use only available channels from the funded six
measurements. Every pressure column remains excluded; no pressure model was
fine-tuned or validated on India. Dehradun temperature with the unit `degree`
also remains excluded. No unavailable value was filled with a constant.

| Family | Inputs/outputs | Source and role |
|---|---|---|
| `india_cpcb_5sensor_6h` | Temperature, humidity, PM2.5, PM10, wind | Indian teacher and ESP32 student |
| `india_cpcb_pm_6h` | PM2.5, PM10 | Indian particulate-only teacher and student |
| `uci_beijing_5sensor_6h` | Same five-channel profile | Matched-input Beijing transfer baseline |
| `uci_beijing_pm_6h` | Same particulate-only profile | Matched-input Beijing transfer baseline |
| `uci_beijing_6h` | Original six measurements including pressure | Original saved model, unchanged |

The matched Beijing models use the same selection/training procedure as the
Indian variants. They are new baseline fits, not the original six-input model.
The original model has zero complete six-input Indian rows available. Its
low-level NaN-input stress-test scores are retained in the JSON report as
diagnostics outside its supported complete-input deployment contract; they
are not the primary comparison shown here.

## Dataset and split

- Canonical source: 368,462 rows from seven sampled stations. This is not the
  entire national archive. All stored input values originate in measurements.
- Five-channel complete current readings occur only at Guwahati, Srinagar,
  Jodhpur and Baddi. Bengaluru has no simultaneous five-channel coverage.
- Five-channel model fitting: 75,289–76,861 rows per target from the three
  development stations. PM-only fitting: 127,064–127,072 rows per target.
- Training labels end before 2022-07-01 UTC. Validation inputs start then and
  labels end before 2023-01-01. Future test is January–March 2023.
- Baddi (`HP001`) is excluded entirely from fitting and validation, and tested
  in January–March 2023. It is a single unseen Himachal station, not Mandi.
- Six-hour labels crossing split boundaries are purged. Missing future
  measurements remain unknown. Every comparison uses identical eligible rows.
- Source timezone is assumed to be Asia/Kolkata, documented rather than
  claimed as provider-confirmed. Hourly interval END is the availability time;
  UTC times therefore fall at :30. Features support consistent hourly offsets.
- The Indian source gives hourly interval measurements; aggregation equivalence
  with the Beijing hourly source has not been independently established.
- Source is a secondary CPCB compilation, publisher license CC BY-NC-SA 4.0.
  Metadata and hashes are in `data/india_cpcb_research/dataset_manifest.json`.

## Five-input ESP32 student: future-time test

Lower MAE is better. Units are °C, humidity percentage points, µg/m³ for both
particulate channels, and m/s. These are research forecast errors, not accuracy percentages.

| Target | Test rows | Persistence MAE | Matched Beijing student | Indian student | Indian teacher |
|---|---:|---:|---:|---:|---:|
| temperature_c | 3,592 | 5.148 | 4.412 | 4.336 | 1.982 |
| relative_humidity_pct | 3,592 | 16.520 | 14.696 | 14.433 | 7.938 |
| pm25_ug_m3 | 3,468 | 56.436 | 52.130 | 45.610 | 31.147 |
| pm10_ug_m3 | 3,459 | 109.126 | 93.255 | 87.193 | 61.615 |
| wind_speed_mps | 3,591 | 0.419 | 0.584 | 0.349 | 0.295 |

## Baddi: station held out entirely

| Target | Test rows | Persistence MAE | Matched Beijing student | Indian student | Indian teacher |
|---|---:|---:|---:|---:|---:|
| temperature_c | 1,705 | 1.727 | 1.709 | 1.672 | 1.309 |
| relative_humidity_pct | 1,597 | 14.048 | 12.457 | 13.186 | 10.018 |
| pm25_ug_m3 | 1,689 | 46.660 | 43.427 | 40.503 | 35.352 |
| pm10_ug_m3 | 1,684 | 80.769 | 70.527 | 69.072 | 58.745 |
| wind_speed_mps | 1,705 | 0.834 | 0.673 | 0.665 | 0.580 |

The Indian student improves all five pooled future-time MAEs and four of five
Baddi MAEs versus the matched Beijing student. **Baddi humidity regresses**
(13.186 versus 12.457 percentage points). The Indian temporal teacher improves
all five versus its matched teacher baseline in both pooled test splits.

## Two-input PM-only student

| Target | Future persistence | Future Beijing student | Future Indian student | Baddi Beijing student | Baddi Indian student |
|---|---:|---:|---:|---:|---:|
| pm25_ug_m3 | 36.851 | 35.753 | 36.851 | 46.127 | 48.820 |
| pm10_ug_m3 | 66.730 | 64.758 | 64.972 | 78.969 | 79.696 |

**The PM-only student is not an improvement over the matched Beijing student.**
Its PM2.5 validation-selected blend weight is zero, so that head outputs
persistence. It is retained as a measured candidate/fallback experiment, not
promoted as a better release. The teacher benefits from history, but that
accuracy must not be attributed to the compact current-input student.

## Architecture and inference

Profiles are validated, ordered subsets of the original six channels. Temporal
features use current readings, lags, changes and rolling statistics only from
the selected channels. ESP32 students still use 16 depth-3 trees per head.
Validation chooses direct residual supervision versus 50% teacher-assisted
supervision, and the persistence blend weight. Test data is never used for
selection. Profile names and feature order are stored with the saved models.

Raw CSV inference keeps the canonical six columns for interoperability; ignored
channels may be NaN. The exported C function accepts exactly five or two floats
according to `INDRA_FORECAST_INPUTS`, in the order printed in each header.

## Reproduce from the repository root

```bash
python3 -m ml.six_sensor_forecast.audit_india --download
python3 -m ml.six_sensor_forecast.prepare_india
python3 -m ml.six_sensor_forecast.train --data data/india_cpcb_research --output ml/models/india_cpcb_5sensor_6h --sensors temperature_c relative_humidity_pct pm25_ug_m3 pm10_ug_m3 wind_speed_mps --validation-start 2022-07-01T00:00:00Z --test-start 2023-01-01T00:00:00Z --holdout-locations HP001
python3 -m ml.six_sensor_forecast.train --data data/india_cpcb_research --output ml/models/india_cpcb_pm_6h --sensors pm25_ug_m3 pm10_ug_m3 --validation-start 2022-07-01T00:00:00Z --test-start 2023-01-01T00:00:00Z --holdout-locations HP001
python3 -m ml.six_sensor_forecast.train --data data/uci_beijing_air_quality --output ml/models/uci_beijing_5sensor_6h --sensors temperature_c relative_humidity_pct pm25_ug_m3 pm10_ug_m3 wind_speed_mps
python3 -m ml.six_sensor_forecast.train --data data/uci_beijing_air_quality --output ml/models/uci_beijing_pm_6h --sensors pm25_ug_m3 pm10_ug_m3
python3 -m ml.six_sensor_forecast.evaluate_india
python3 -m ml.six_sensor_forecast.export --model ml/models/india_cpcb_5sensor_6h --observations data/india_cpcb_research/observations.csv --output ml/models/india_cpcb_5sensor_6h/esp32_student/export
python3 -m ml.six_sensor_forecast.export --model ml/models/india_cpcb_pm_6h --observations data/india_cpcb_research/observations.csv --output ml/models/india_cpcb_pm_6h/esp32_student/export
python3 -m unittest discover -s tests
pio run -d esp32/model_test -e esp32-s3-model-test -e india-five-sensor-test -e india-pm-test
```

For saved-model inference choose the Indian model explicitly:

```bash
python3 -m ml.six_sensor_forecast.predict --input data/india_cpcb_research/observations.csv --model ml/models/india_cpcb_5sensor_6h --kind student --output /tmp/india_forecasts.csv
```

## Limits and release status

These are research candidates under documented source assumptions, not a
perfect or India-wide validated model. No Mandi field data, on-board physical
execution, or storm/flood classification is established. Original Beijing
artifacts remain unchanged. Only a broader frozen multi-station, multi-season
evaluation plus local sensor validation can support stronger deployment claims.

Full paired MAE/RMSE/R² and per-station results: [india_transfer_report.json](../../../../ml/evaluation/india_transfer_report.json).

## Completed verification

- Ten unit/integration tests passed, including five-/two-input fitting, saved
  inference, C export, invalid sensor profiles and India UTC half-hour alignment.
- Indian five-input C parity: 3,730 valid cases and 15 invalid-input rejections.
- Indian two-input C parity: 2,659 valid cases and 6 invalid-input rejections.
- All three ESP32-S3 test environments compiled successfully; Indian build
  evidence is in each candidate's `esp32_build_report.json`.
- Batch inference inspected all 368,462 canonical Indian rows: 101,680 produced
  five-input forecasts; 266,782 correctly returned `MISSING_CURRENT_SENSOR`.
- All new saved-model/export hashes and documentation links were verified.
- Physical board execution and flashing were not performed.
