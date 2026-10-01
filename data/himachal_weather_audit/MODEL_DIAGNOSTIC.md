# Himachal missing-PM model diagnostic

Tested the unchanged `uci_beijing_6h` ESP32 student against observations exactly six hours later. No retraining or tuning was performed. All four weather inputs were present; both particulate inputs were NaN. Direct XGBoost missing-value routing was exercised for this offline diagnostic. Normal production inference rejects these incomplete inputs; this is not a validated six-input deployment test.

Evaluated 32,281 pairs across 12 stations, after excluding all duplicate keys and applying broad physical ranges. Input CSV and model-report hashes, per-station scores, RMSE and R² are in [model_diagnostic.json](model_diagnostic.json). Station coordinates and original timestamps were joined exactly; timezone was not assumed. No interpolation was used.

## All evaluated stations

Errors below are MAE (mean absolute error); lower is better. Persistence predicts the current observation unchanged six hours ahead. There is no single classification accuracy percentage for these continuous measurements.

| Measurement | Model MAE | Persistence MAE | MAE reduction |
|---|---:|---:|---:|
| Temperature (°C) | 4.150 | 4.485 | 7.46% |
| Humidity (percentage points) | 12.737 | 13.094 | 2.72% |
| Pressure (hPa) | 2.304 | 1.799 | -28.10% |
| Wind speed (m/s) | 1.257 | 1.112 | -12.98% |

## AWS IIT Mandi

Evaluated 1,152 pairs.

| Measurement | Model MAE | Persistence MAE |
|---|---:|---:|
| Temperature (°C) | 5.325 | 5.306 |
| Humidity (percentage points) | 16.721 | 14.560 |
| Pressure (hPa) | 4.699 | 3.926 |
| Wind speed (m/s) | 1.011 | 1.033 |

## Interpretation

Temperature and humidity modestly outperform persistence in pooled MAE; pressure and wind do not. At IIT Mandi, temperature is essentially unchanged, humidity and pressure are worse, and wind is slightly better by MAE. All four IIT Mandi R² values are negative. The baseline itself is weak here, so small relative gains do not demonstrate adequate forecasts. Pooled R² can reflect differences between stations and should not be presented as percentage accuracy.

Pressure reference, sensor freezing and spikes remain unresolved. A sensitivity check excludes pairs with pressure exactly 925 or 1021.5 hPa at either endpoint (heuristic values, not certified missing codes). It leaves 24,216 pairs; pressure and wind still lose to persistence by MAE. This does not establish that the remaining observations are clean.

Missing particulate inputs and uncertain telemetry quality prevent attributing the errors solely to climate differences. No PM accuracy, C-export execution, physical sensor test or hardware performance was measured. Model artifacts and the six-input deployment requirement remain unchanged.

## Reproduce

```bash
python3 -m ml.six_sensor_forecast.evaluate_himachal
```
