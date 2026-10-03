# Model family: uci_beijing_6h

**Dataset:** UCI Beijing Multi-Site Air Quality (501), DOI 10.24432/C5RK5G,
420,768 source observations, 12 stations, 2013–2017, CC BY 4.0.
**Task:** six-hour-ahead measurement regression using only six sensor channels.

## File naming

The family directory identifies the dataset and prediction horizon. The
`teacher/` and `esp32_student/` directories identify the model role. Each
`<target>.ubj` file is one trained XGBoost regression head; filenames preserve
the output measurement and unit. Both roles use the same dataset and splits.

| Head filename (inside either role directory) | Forecast output | Fitted rows |
|---|---|---:|
| `temperature_c.ubj` | temperature_c at t + 6 hours | 219,191 |
| `relative_humidity_pct.ubj` | relative_humidity_pct at t + 6 hours | 219,188 |
| `pressure_hpa.ubj` | pressure_hpa at t + 6 hours | 219,192 |
| `pm25_ug_m3.ubj` | pm25_ug_m3 at t + 6 hours | 216,849 |
| `pm10_ug_m3.ubj` | pm10_ug_m3 at t + 6 hours | 217,557 |
| `wind_speed_mps.ubj` | wind_speed_mps at t + 6 hours | 219,194 |

## Model roles

- `teacher/`: temporal offline models using 66 causal features derived exclusively
  from the six measurements. Used for benchmarking and student supervision.
- `esp32_student/`: compact models with exactly six current inputs, 16 trees per
  head, maximum depth 3. These are the models exported to the ESP32.
- `esp32_student/export/indra_six_sensor_forecast.h`: all six student heads as
  standalone C, with the saved residual blend weights and physical clipping.

## Reports

- `training_report.json`: exact source provenance, feature order, split dates,
  model file paths/checksums, fitted rows and validation/test metrics.
- `esp32_student/export/c_export_report.json`: generated header hash and host
  Python/C parity results.
- `esp32_build_report.json`: isolated ESP32 build evidence and hardware-test status.

The C export is a forecast model, not verified storm/flood detection. Beijing
scores do not establish India field accuracy. See [ARCHITECTURE.md](../../../docs/archive/ARCHITECTURE.md)
for measured accuracy, limitations, reproduction and board-test instructions.
