# INDRA Mandi submission test

Executed: 2026-10-20T19:23:44.064590+00:00

**Task:** six numerical measurements at +6h. **Evidence:** retrospective Mandi
API/model grids, not physical station or hazard accuracy. No model was retrained
and no ensemble weights were selected using this test.

Source: 24,336 hourly positions, 2024-01-01T00:00:00+00:00 to 2026-10-10T23:00:00+00:00.
Split counts: {'train': 22602, 'validation': 738, 'future_test': 954}. Six-hour targets are purged at split boundaries.
The September/October test is reused research evidence, not a new untouched holdout.

## All saved Mandi forecast candidates — test MAE

Lower is better. Columns have different physical units and must not be averaged directly.

| Model | T °C | RH percentage points | P hPa | PM2.5 µg/m³ | PM10 µg/m³ | Wind m/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| persistence | 4.8331 | 18.9686 | 1.6804 | 10.1762 | 12.6751 | 0.5945 |
| compact_xgboost | 3.7926 | 14.1338 | 1.4844 | 8.4077 | 10.5534 | 0.4642 |
| residual_mlp_32 | 1.4029 | 7.0272 | 0.9516 | 7.1338 | 9.1892 | 0.2979 |
| residual_mlp_64_32 | 1.3506 | 6.8190 | 0.9455 | 7.3370 | 9.8697 | 0.3158 |
| xgb_history | 1.7724 | 7.8542 | 1.0429 | 6.9577 | 9.3210 | 0.3215 |
| ridge_history | 1.2724 | 7.0027 | 0.9467 | 7.0209 | 9.2795 | 0.3415 |
| active_hybrid | 1.3063 | 6.9332 | 0.9255 | 6.8923 | 8.9972 | 0.3128 |

Full MAE/RMSE/R², persistence skill and row counts: [metrics.json](metrics.json).
Classification accuracy/F1 do not apply to these continuous targets. The deployed
hybrid is kept fixed even where an individual component has a lower test error.

## Inputs, labels and learned weights

Inputs, in order: temperature_c, relative_humidity_pct, pressure_hpa, pm25_ug_m3,
pm10_ug_m3, wind_speed_mps. The hybrid derives 66 causal features from 25 hourly
snapshots spanning 24 hours. Labels are the same six API values exactly +6h later.
Examples with input, prediction and later API values are included in metrics.json.

Learned MLP arrays/normalization, tree files and ridge arrays remain at their
original paths. The active profile records their checksums; per-target prediction
blend coefficients are recorded below. These are not hazard probabilities.

| Target | Selected MLP | Neural | History XGBoost | Ridge |
| --- | --- | ---: | ---: | ---: |
| temperature_c | residual_mlp_64_32 | 0.40 | 0.35 | 0.25 |
| relative_humidity_pct | residual_mlp_64_32 | 0.50 | 0.50 | 0.00 |
| pressure_hpa | residual_mlp_32 | 0.35 | 0.15 | 0.50 |
| pm25_ug_m3 | residual_mlp_64_32 | 0.40 | 0.55 | 0.05 |
| pm10_ug_m3 | residual_mlp_32 | 0.40 | 0.55 | 0.05 |
| wind_speed_mps | residual_mlp_64_32 | 0.90 | 0.10 | 0.00 |

## End-to-end Mandi replay

One historical node: `mandi-api-grid`; forecast status `HYBRID_READY`.
The replay keeps actual source retrieval time, modeled source class, different
weather/PM grid identities, no claimed calibration and grid-surface pressure.
It never shifts old dates to today or invents nodes, rainfall labels or 15-minute readings.
Forecast target times remain historical. Stale readings are explicitly marked.

**Expected abstention:** current hazard rules reject modeled sources as field
evidence. Their scores remain unavailable; this is a checked safety state, not
measured hazard accuracy. The native 15-minute storm sequence cannot be evaluated
from this hourly source. One grid cannot validate neighbour consensus or a spatial map.

## What the submission can claim

- Implemented six-channel hybrid forecasting, source/weight integrity checks and retrospective numerical comparison.
- Tested local backend/frontend, explicit missing-history fallback, stale/cache handling and unavailable hazard states.
- Separate engineered tests for anomaly, neighbour/radio simulation, spatial research and ERA5 pipeline execution.
- No calibrated cloudburst/storm/snowstorm probability, flood/landslide skill, physical ESP32/RF execution or live six-sensor learning.

Attribution: Open-Meteo, ECMWF IFS and Copernicus Atmosphere Monitoring Service (CAMS).
Weather/air grids differ; underlying CAMS is coarser than its hourly API representation.
Original issue-time data availability is unverified. This is a retrospective value forecast.
