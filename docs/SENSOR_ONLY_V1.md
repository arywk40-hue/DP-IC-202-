# INDRA sensor_only_v1 contract

This is a new, unpromoted contract. It preserves every existing model. The status and checksum are respectively `NOT_READY` and `NOT_READY-no-trained-model`.

| Index | Feature | Unit / derivation |
| ---: | --- | --- |
| 0 | `temperature_c` | BME280, degrees Celsius |
| 1 | `relative_humidity_pct` | BME280, percent |
| 2 | `pressure_hpa` | BME280 pressure / 100 |
| 3 | `wind_speed_mps` | encoder pulses / 600 × calibrated meters/revolution / time |
| 4 | `pm25_ug_m3` | PMS7003 atmospheric PM2.5 |
| 5 | `pressure_trend_hpa_per_hour` | real-pressure delta × 3,600,000 / elapsed ms |
| 6 | `dew_point_c` | Magnus formula |
| 7 | `heat_index_c` | NOAA polynomial, otherwise air temperature |
| 8-9 | `hour_sin`, `hour_cos` | sin/cos(2pi × RTC hour / 24) |
| 10-11 | `day_of_year_sin`, `day_of_year_cos` | sin/cos(2pi × (day - 1) / 365) |
| 12-13 | `latitude_deg`, `longitude_deg` | Neo-M8N WGS84 decimal degrees |

PM1.0, PM10, GPS altitude and INA219 measurements are telemetry only. Missing, stale, invalid, non-finite and out-of-range inputs are rejected. Two real pressure samples are required before calculating trend.

`ml/sensor_only_v1/train.py` rejects unlabelled data and makes a disjoint holdout covering recent time and held-out geographic cells. `check_feature_parity.py` compares the firmware and Python feature vectors. It records `NOT_READY`; no model is trained until suitable labelled field data and independent validation exist, so Python/C **prediction** parity cannot yet be claimed.
