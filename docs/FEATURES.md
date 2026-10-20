# INDRA features — current implementation

Status: 21 October 2026. This is the feature list for the project submission.
"Implemented" describes software; its evidence column states what has been tested.

## Product and research features

| Feature | What is provided | Evidence and limitation |
| --- | --- | --- |
| Six-channel input | Temperature, RH, pressure, PM2.5, PM10, wind, units and timestamps | Canonical range/QC checks; no seventh physical channel |
| Six-hour numerical forecast | Six endpoint values at t+6h from the active neural/tree/ridge ensemble | Tested against 954 later Mandi API/model values; not measured station accuracy |
| History and fallback | 66 causal features, 24h history; explicit persistence warm-up or missing-input status | Gap/missing-channel and no-future-dependence tests |
| Dashboard telemetry | Node list/map, six values/mini-histories, forecasts, model identity, coefficients, source and timestamps | Local backend/browser integration; Mandi replay is historical and stale |
| Data quality and source | Units, pressure reference, source class, calibration identities and availability | Modeled source cannot silently become physical station evidence |
| Current rain/snowstorm/cloudburst rule cards | Experimental current-condition matches and evidence/abstention | Synthetic contract tests; not calibrated probabilities or six-hour hazard predictions |
| Storm sequence | Six-hour pressure fall and native 15-minute rebound/cooling/washout sequence | Requires appropriate cadence/source; hourly Mandi API cannot provide 15-minute evidence |
| Anomaly detection | Bounded six-channel engineering detector and Python/C parity | Tested separately; not wired as a validated live dashboard alarm |
| Neighbour inference | Registration, health, authenticated consensus and radio simulation modules | Engineering tests only; live radios and dashboard corroboration remain incomplete |
| Spatial estimates | Retained node interpolation experiments and separate ERA5 feature grids | The active node heatmap is unavailable; one Mandi grid cannot validate interpolation |
| ERA5 risk research panel | Optional owner-generated scores, anomaly markers and feature grids | Available example is synthetic engineering data, not actual Mandi event accuracy |
| Offline/cache operation | Versioned cache, stale notices and unavailable states | Does not manufacture current readings or physical acknowledgements |
| ESP32 research | Separate compiled C exports and firmware applications | Host/build receipts exist; physical execution and hybrid edge export remain untested |
| Online learning | Separate delayed-label ERA5 SGD research replay | No live six-sensor learner updates dashboard/ESP32 weights |
| Hardware commands/alerts | Explicitly disabled RPC and public notifications | No live sensor bridge or public warning service |

## Six input/output channels

| Order | Input name | Unit | Label/output |
| --- | --- | --- | --- |
| 1 | `temperature_c` | °C | Same measurement at exact +6h |
| 2 | `relative_humidity_pct` | % | Same measurement at exact +6h |
| 3 | `pressure_hpa` | hPa | Same measurement at exact +6h |
| 4 | `pm25_ug_m3` | µg/m³ | Same measurement at exact +6h |
| 5 | `pm10_ug_m3` | µg/m³ | Same measurement at exact +6h |
| 6 | `wind_speed_mps` | m/s | Same measurement at exact +6h |

Station inputs require station pressure; the Mandi API source explicitly retains
modeled grid-surface pressure. Coordinates identify the displayed source location;
they are not learned inputs to the active numerical model.

## Derived features

For each channel the numerical model uses: current value; 1/3/6/12/24h lags;
1h difference; trailing 6/24h means and standard deviations. That is **11 per
channel, 66 total**. No future rows or filled gaps are allowed.

The separate native feature engine implements hourly/15-minute/six-hour changes,
rates and statistics, dew point, frost point, vapour-pressure deficit, NWS heat
index, PM2.5/PM10 ratio, washout proxies, wind/RH-change flags and seasonal context.
These estimates retain missing/domain/calibration states. They do not add sensors
or turn pollutant washout into measured precipitation. Actual source availability
is respected; a retrospectively downloaded file is not treated as known earlier.

## What the Mandi run tests

Seven comparisons use the same 954 labels: persistence, compact XGBoost, history
XGBoost, ridge, MLP32, MLP64→32 and the fixed active hybrid. Report MAE/RMSE/R²
per target; do not claim a general accuracy percentage or retune on this test.
The local replay uses the last 25 actual API positions with their original dates,
source retrieval time and separate weather/PM cell IDs. Hazard rules correctly
abstain on that modeled source. Artificial multi-node fixtures cannot establish
Mandi-wide, spatial or disaster prediction skill.

See [test results](../reports/submission/2026-10-21/REPORT.md) and
[submission steps](SUBMISSION_GUIDE.md).
