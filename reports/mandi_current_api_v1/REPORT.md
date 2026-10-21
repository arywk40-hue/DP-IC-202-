# Latest fetched Mandi model-grid test

Six-hour numerical forecasts against later API model values. No station or hazard accuracy is claimed.

Source: 2026-09-21T00:00:00+00:00 to 2026-10-20T23:00:00+00:00; 720 complete hourly positions.

No models were fitted, tuned or promoted using this snapshot.

## recent_30_days_reused_dates — 690 pairs

| Target | Model MAE | Persistence MAE | MAE skill vs persistence |
| --- | ---: | ---: | ---: |
| temperature_c | 1.5219 | 5.6703 | 73.2% |
| relative_humidity_pct | 7.2720 | 21.5971 | 66.3% |
| pressure_hpa | 0.9542 | 1.9159 | 50.2% |
| pm25_ug_m3 | 6.3033 | 9.7900 | 35.6% |
| pm10_ug_m3 | 8.3467 | 12.3978 | 32.7% |
| wind_speed_mps | 0.3160 | 0.5659 | 44.2% |

## targets_after_previous_archive — 24 pairs

| Target | Model MAE | Persistence MAE | MAE skill vs persistence |
| --- | ---: | ---: | ---: |
| temperature_c | 1.0996 | 7.8000 | 85.9% |
| relative_humidity_pct | 5.1665 | 24.1250 | 78.6% |
| pressure_hpa | 0.7061 | 2.3125 | 69.5% |
| pm25_ug_m3 | 4.0968 | 8.7708 | 53.3% |
| pm10_ug_m3 | 5.0207 | 9.0750 | 44.7% |
| wind_speed_mps | 0.2027 | 0.5625 | 64.0% |

Targets after the earlier archive end extend the existing test; the full 30-day cohort reuses previously examined dates. Historical API values can be revised. New-date results are small-sample diagnostics, not evidence for automatic retraining.

MAE uses each channel's native unit. Full RMSE/R² and provenance are in metrics.json.

Attribution: Open-Meteo, ECMWF IFS, Copernicus CAMS.
