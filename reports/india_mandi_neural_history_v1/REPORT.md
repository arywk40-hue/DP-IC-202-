# Mandi numerical forecast architecture comparison

Retrospective modeled-grid benchmark; not observed station accuracy or hazard validation.
All models use the same complete-history rows, chronological splits and exact +6h targets. All new preprocessing fits training rows only.
Neural heads share two alternatives: 66 → 32 → 6 and 66 → 64 → 32 → 6, ReLU hidden layers, residual outputs, train-only scaling and validation-selected persistence blends.
The 66 features come from six channels and up to 24 hours of causal history. No coordinates, time-of-day or new physical channels are learned inputs.

MAE in each channel's physical units; lower is better. Choices are made on validation, not on this test table.

| Target | Persistence | XGB student | XGB history teacher | Ridge | MLP 32 | MLP 64/32 | Validation choice | Choice test MAE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| temperature_c | 4.8331 | 3.7926 | 1.7724 | 1.2724 | 1.4029 | 1.3506 | residual_mlp_64_32 | 1.3506 |
| relative_humidity_pct | 18.9686 | 14.1338 | 7.8542 | 7.0027 | 7.0272 | 6.8190 | teacher | 7.8542 |
| pressure_hpa | 1.6804 | 1.4844 | 1.0429 | 0.9467 | 0.9516 | 0.9455 | temporal_ridge | 0.9467 |
| pm25_ug_m3 | 10.1762 | 8.4077 | 6.9577 | 7.0209 | 7.1338 | 7.3370 | teacher | 6.9577 |
| pm10_ug_m3 | 12.6751 | 10.5534 | 9.3210 | 9.2795 | 9.1892 | 9.8697 | teacher | 9.3210 |
| wind_speed_mps | 0.5945 | 0.4642 | 0.3215 | 0.3415 | 0.2979 | 0.3158 | residual_mlp_64_32 | 0.3158 |

Rows by split: `{"train": 22602, "validation": 738, "future_test": 954, "fresh_future_test": 90}`.

The September/October evaluation period has been examined in earlier project work. Reusing it is an architecture diagnostic, not a newly untouched accuracy test. A future monitored holdout is still required.
Current dashboard/ESP32 weights are preserved. Neural candidates are isolated research artifacts, with no promotion, on-device export or live-learning worker.
Epoch-wise partial_fit here is offline training; it does not mean the deployed system learns from incoming readings.
Rain/snowstorm/cloudburst event labels, calibrated probabilities and physical board/radio validation are still missing.
Source attribution: Open-Meteo, ECMWF IFS and CAMS global. PM and weather are different modeled grids; pressure is grid surface pressure.
