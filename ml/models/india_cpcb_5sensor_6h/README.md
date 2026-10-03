# india_cpcb_5sensor_6h

Source: Indian CPCB secondary compilation, seven-station research subset.

Forecast horizon: six hours. Inputs/outputs: `temperature_c`, `relative_humidity_pct`, `pm25_ug_m3`, `pm10_ug_m3`, `wind_speed_mps`.

Role: Indian research candidate.

No pressure model is included. `teacher/` contains temporal offline heads;
`esp32_student/` contains compact heads. A `<measurement>.ubj` file forecasts
that measurement in its named unit. Source hashes, split dates, excluded
sensors, validation selection and metrics are in `training_report.json`.

| Target | Fitted rows | Student residual weight |
|---|---:|---:|
| temperature_c | 76,568 | 1.0 |
| relative_humidity_pct | 76,445 | 1.0 |
| pm25_ug_m3 | 75,485 | 0.75 |
| pm10_ug_m3 | 75,289 | 0.75 |
| wind_speed_mps | 76,861 | 0.75 |

A zero residual weight means persistence; it must not be described as learned
forecast improvement. Read [paired Indian results](../../../docs/archive/ml/evaluation/INDIA_RESULTS.md)
before choosing a candidate. Research only; no automatic deployment promotion.
