# Latest fetched Mandi model-grid test

Six-hour numerical forecasts against later API model values. No station or hazard accuracy is claimed.

Source: 2026-09-25T00:00:00+00:00 to 2026-10-24T23:00:00+00:00; 720 complete hourly positions.

No models were fitted, tuned or promoted using this snapshot.

## recent_30_days_reused_dates — 690 pairs

Issue times: 2026-09-26T00:00:00+00:00 to 2026-10-24T17:00:00+00:00; target-valid times: 2026-09-26T06:00:00+00:00 to 2026-10-24T23:00:00+00:00.

| Target | Model MAE | Persistence MAE | MAE skill vs persistence |
| --- | ---: | ---: | ---: |
| temperature_c | 1.5087 | 5.8629 | 74.3% |
| relative_humidity_pct | 7.3611 | 22.4638 | 67.2% |
| pressure_hpa | 0.9513 | 1.9077 | 50.1% |
| pm25_ug_m3 | 5.7096 | 9.5978 | 40.5% |
| pm10_ug_m3 | 7.4676 | 12.0165 | 37.9% |
| wind_speed_mps | 0.3244 | 0.5754 | 43.6% |

## targets_after_previous_archive — 120 pairs

Issue times: 2026-10-19T18:00:00+00:00 to 2026-10-24T17:00:00+00:00; target-valid times: 2026-10-20T00:00:00+00:00 to 2026-10-24T23:00:00+00:00.

| Target | Model MAE | Persistence MAE | MAE skill vs persistence |
| --- | ---: | ---: | ---: |
| temperature_c | 1.2725 | 7.4017 | 82.8% |
| relative_humidity_pct | 7.0331 | 26.8250 | 73.8% |
| pressure_hpa | 0.6751 | 1.9833 | 66.0% |
| pm25_ug_m3 | 5.2287 | 11.3242 | 53.8% |
| pm10_ug_m3 | 6.0862 | 12.2167 | 50.2% |
| wind_speed_mps | 0.3189 | 0.6468 | 50.7% |

Targets after the earlier archive end extend the existing test; the full 30-day cohort reuses previously examined dates. Historical API values can be revised. New-date results are small-sample diagnostics, not evidence for automatic retraining.

MAE uses each channel's native unit. Full RMSE/R² and provenance are in metrics.json.

Attribution: Open-Meteo, ECMWF IFS, Copernicus CAMS.
