# ESP32-S3 model-only test

Builds the retained `uci_beijing_6h/esp32_student` model. It runs a fixed six-input
test vector and prints forecasts and inference latency. It has no sensor drivers
or application logic. The model header is included directly from
`ml/models/uci_beijing_6h/esp32_student/export/`.

From the repository root:

```bash
pio run -d esp32/model_test
# After connecting the intended board (upload replaces its current application):
pio run -d esp32/model_test -e esp32-s3-model-test -t upload --upload-port /dev/cu.YOUR_ESP32_PORT
pio device monitor --port /dev/cu.YOUR_ESP32_PORT --baud 115200
```

Input order: temperature °C, humidity %, pressure hPa, PM2.5 µg/m³,
PM10 µg/m³, wind m/s. Output order is identical, forecast six hours ahead.

The test input `[20, 50, 1013, 35, 60, 2]` should produce approximately
`[18.554806, 56.758118, 1012.819641, 41.744591, 72.887955, 1.689997]`.

Host parity and cross-compilation are verified. Physical flashing and on-device
latency remain untested until a board is connected. Status remains
`OFFLINE_RESEARCH_ONLY`; these are measurement forecasts, not hazard alarms.

## Indian research profile builds

`pio run -d esp32/model_test` builds the original six-input baseline by default.
The reduced-input experiments do not satisfy the required six-input contract.
Use an explicit environment to select a research build:

- `-e esp32-s3-model-test`: original six-input Beijing baseline.
- `-e india-five-sensor-test`: five-input Indian model; excludes pressure.
- `-e india-pm-test`: Indian two-input experiment; PM2.5 is a persistence fallback.

Each build includes exactly one model header; input and output array lengths
follow its profile. Both Indian exports pass host Python/C parity. Read
[Indian test results](../../ml/evaluation/INDIA_RESULTS.md) before choosing a
candidate; neither is an India-wide or Mandi-validated deployment release.
