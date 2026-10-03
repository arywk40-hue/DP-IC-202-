# uci_beijing_pm_6h

Source: UCI Beijing Multi-Site Air Quality (501).

Forecast horizon: six hours. Inputs/outputs: `pm25_ug_m3`, `pm10_ug_m3`.

Role: Matched-input Beijing baseline for Indian transfer testing.

No pressure model is included. `teacher/` contains temporal offline heads;
`esp32_student/` contains compact heads. A `<measurement>.ubj` file forecasts
that measurement in its named unit. Source hashes, split dates, excluded
sensors, validation selection and metrics are in `training_report.json`.

| Target | Fitted rows | Student residual weight |
|---|---:|---:|
| pm25_ug_m3 | 216,931 | 0.5 |
| pm10_ug_m3 | 217,639 | 0.5 |

A zero residual weight means persistence; it must not be described as learned
forecast improvement. Read [paired Indian results](../../../docs/archive/ml/evaluation/INDIA_RESULTS.md)
before choosing a candidate. Research only; no automatic deployment promotion.
