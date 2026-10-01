# uci_beijing_5sensor_6h

Source: UCI Beijing Multi-Site Air Quality (501).

Forecast horizon: six hours. Inputs/outputs: `temperature_c`, `relative_humidity_pct`, `pm25_ug_m3`, `pm10_ug_m3`, `wind_speed_mps`.

Role: Matched-input Beijing baseline for Indian transfer testing.

No pressure model is included. `teacher/` contains temporal offline heads;
`esp32_student/` contains compact heads. A `<measurement>.ubj` file forecasts
that measurement in its named unit. Source hashes, split dates, excluded
sensors, validation selection and metrics are in `training_report.json`.

| Target | Fitted rows | Student residual weight |
|---|---:|---:|
| temperature_c | 219,191 | 1.0 |
| relative_humidity_pct | 219,188 | 0.75 |
| pm25_ug_m3 | 216,849 | 0.5 |
| pm10_ug_m3 | 217,557 | 0.75 |
| wind_speed_mps | 219,194 | 1.0 |

A zero residual weight means persistence; it must not be described as learned
forecast improvement. Read [paired Indian results](../../evaluation/INDIA_RESULTS.md)
before choosing a candidate. Research only; no automatic deployment promotion.
