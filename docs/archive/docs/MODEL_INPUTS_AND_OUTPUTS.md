> Archived evidence / superseded guide. Original path: `docs/MODEL_INPUTS_AND_OUTPUTS.md`. Protocol-specific results are preserved; use [PROJECT_OVERVIEW.md](../../PROJECT_OVERVIEW.md) for current scope.

# INDRA: Model Inputs, Features, Predictions and Outputs

This document describes the currently implemented models and interfaces.

## 1. What the system does

INDRA uses **six environmental measurement channels** in two distinct ML models:

| Component | Question it answers | Output time |
| --- | --- | --- |
| Six-hour forecasting model | What will the six environmental measurements be six hours from now? | Future: input time + 6 hours |
| Event-rule classifier | Which learned weather/pollution sensor patterns match the current readings and recent history? | Current observation time |
| Spatial heatmap utility | What measurement values or event-rule scores can we estimate between measurement nodes? | Same time as the supplied node observations |

**The current system does not predict hazard events six hours ahead.** Its six-hour outputs are numerical measurements. Its event outputs describe current sensor-rule patterns.

## 2. The six physical input channels

Both models use the following channels, in this exact order:

| Position | Channel | Code name | Unit | Accepted software range |
| --- | --- | --- | --- | --- |
| 1 | Temperature | `temperature_c` | °C | −60 to 85 |
| 2 | Relative humidity | `relative_humidity_pct` | % | 0 to 100 |
| 3 | Station atmospheric pressure | `pressure_hpa` | hPa | 300 to 1100 |
| 4 | PM2.5 concentration | `pm25_ug_m3` | µg/m³ | 0 to 5000 |
| 5 | PM10 concentration | `pm10_ug_m3` | µg/m³ | 0 to 5000 |
| 6 | Wind speed | `wind_speed_mps` | m/s | 0 to 100 |

These are six measurement channels, not necessarily six separate physical devices. For example, one environmental sensor may provide temperature, humidity and pressure.

The ranges above reject obviously invalid inputs; they do not certify sensor calibration or accuracy. Use station pressure, not an undocumented sea-level-adjusted pressure. Convert wind speed from km/h to m/s by dividing by 3.6.

Timestamps and station/node identifiers organize records and history. They are not additional learned inputs to the compact forecasting model. Coordinates belong to the spatial layer, not the forecasting model.

## 3. Model A — Six-hour measurement forecast

### Input

The deployed-format **student model** accepts one complete current snapshot of the six channels. It does not need six hours of history.

Example input:

```text
[20, 50, 1013, 35, 60, 2]
```

Meaning: 20 °C, 50% humidity, 1013 hPa, 35 µg/m³ PM2.5, 60 µg/m³ PM10 and 2 m/s wind.

### Outputs

It returns six numerical predictions in the same order:

| Output | Meaning |
| --- | --- |
| Forecast temperature | Estimated temperature at t + 6 hours |
| Forecast relative humidity | Estimated humidity at t + 6 hours |
| Forecast pressure | Estimated pressure at t + 6 hours |
| Forecast PM2.5 | Estimated PM2.5 concentration at t + 6 hours |
| Forecast PM10 | Estimated PM10 concentration at t + 6 hours |
| Forecast wind speed | Estimated wind speed at t + 6 hours |

The saved software test vector above produces approximately:

```text
[18.554806, 56.758118, 1012.819641, 41.744591, 72.887955, 1.689997]
```

This is a software example, not an observed weather forecast at a deployment site. The output is one six-hour endpoint, not a forecast for every intervening hour. It does not include uncertainty intervals.

### Model structure and training

- Model family: XGBoost regression, not a neural network.
- Six independent output heads.
- Compact student: 16 trees per head, maximum depth 3, six current inputs.
- Predictions use a learned change from the current measurement, blended with persistence and bounded to accepted physical ranges.
- A larger **teacher** exists for offline benchmarking/training. It uses 66 causal features from current and historical values. It is not the compact six-input ESP32 student.
- Training source: UCI Beijing Multi-Site Air Quality, 420,768 hourly station records across 12 stations, 2013–2017. Humidity is derived from temperature/dew point in that source.
- Saved future-time and held-out-station tests beat persistence MAE on all six targets. This does not establish performance in Mandi.

Retained complete-input model: `ml/models/uci_beijing_6h/`.

## 4. Model B — Current event-rule classification

### Input history

The deployment inference path requires **seven complete consecutive hourly observations**, covering six hours from the first reading to the latest.

```text
Six-channel observations at t−6h, t−5h, …, t−1h, t
                         ↓
Six current values + eleven derived features
                         ↓
17 numerical model inputs
                         ↓
Twelve output positions, ten with trained heads
```

All eleven derived features are computed from the same six sensor channels. No additional physical sensor is introduced.

### The eleven derived features

The feature order below follows the six raw inputs in Section 2.

| Model position | Feature | Code name | Meaning |
| --- | --- | --- | --- |
| 7 | Dew point | `T_dew` | Derived from temperature and humidity using the Magnus formula; °C |
| 8 | Vapour pressure deficit | `VPD` | Derived atmospheric drying potential; kPa |
| 9 | Heat index | `HI` | Implemented temperature/humidity heat-index approximation; °C |
| 10 | Particulate ratio | `PM_ratio` | PM2.5 divided by PM10; undefined when PM10 is zero |
| 11 | One-hour pressure change | `dP_dt` | P(t) − P(t−1h); hPa over one hour |
| 12 | Six-hour pressure change | `dP_6h` | P(t) − P(t−6h); hPa over six hours |
| 13 | One-hour temperature change | `dT_dt` | T(t) − T(t−1h); °C over one hour |
| 14 | One-hour PM2.5 change | `dPM25_dt` | PM2.5(t) − PM2.5(t−1h); µg/m³ |
| 15 | One-hour PM10 change | `dPM10_dt` | PM10(t) − PM10(t−1h); µg/m³ |
| 16 | One-hour humidity change | `dRH_dt` | RH(t) − RH(t−1h); percentage points |
| 17 | Continuously rising PM2.5 | `pm25_mono_6h` | 1 when PM2.5 increases at every step of the seven-reading window; otherwise 0 for complete history |

The current model uses hourly changes. It does not measure fifteen-minute trends.

### Output classes and implemented label rules

The model has twelve ordered binary output slots. Each trained head returns a separate score between 0 and 1. Multiple heads may score highly at the same time: this is **multi-label**, not a single exclusive category.

The rules below describe the targets used to train the saved model, not independently verified definitions of actual hazards. `Δ` values refer to the intervals listed above.

| Output position | Event name / code | Implemented training-rule summary | Saved status |
| --- | --- | --- | --- |
| 1 | Light/moderate rain — `light_moderate_rain` | RH ≥ 85%, six-hour pressure change ≤ −1.5 hPa, T > 3 °C, PM2.5 and PM10 changes ≤ 0 | Trained |
| 2 | Severe rainstorm/squall — `severe_rainstorm_squall` | Six-hour pressure change ≤ −3.5 hPa, one-hour temperature change ≤ −3 °C, T > 3 °C, wind ≥ 10 m/s, PM changes ≤ 0 | **Untrained: no positive training labels** |
| 3 | Snowstorm/blizzard — `snowstorm_blizzard` | Six-hour pressure change ≤ −3 hPa, T ≤ 1 °C, RH ≥ 85%, wind ≥ 9 m/s, PM changes ≤ 0 | **Untrained: no positive training labels** |
| 4 | Freezing rain/sleet — `freezing_rain_sleet` | Falling pressure, RH ≥ 90%, −2 ≤ T ≤ 0.5 °C | Trained |
| 5 | Radiation fog — `radiation_fog` | T − dew point ≤ 2 °C, RH ≥ 95%, wind < 1.5 m/s, PM2.5 > 80 µg/m³ | Trained |
| 6 | Ground frost — `ground_frost` | T ≤ 0 °C, dew point ≤ 0 °C, wind < 2 m/s, non-falling pressure | Trained |
| 7 | Extreme heatwave — `extreme_heatwave` | T ≥ 35 °C **or** implemented heat index ≥ 41 °C | Trained |
| 8 | Wildfire/evaporative risk — `wildfire_evaporative_risk` | VPD ≥ 2.5 kPa, RH ≤ 25%, wind ≥ 5 m/s | Trained |
| 9 | Dust storm/haboob — `dust_storm_haboob` | Wind ≥ 8 m/s, PM2.5/PM10 ≤ 0.35, PM10 > 250 µg/m³, RH < 40% | Trained; sparse evidence |
| 10 | Smoke plume — `smoke_plume` | PM2.5 > 150 µg/m³, PM2.5/PM10 ≥ 0.70, RH < 60%, wind > 1.5 m/s | Trained |
| 11 | Smog/inversion trap — `smog_inversion_trap` | Wind < 1 m/s, pressure ≥ 1010 hPa, PM2.5 > 120 µg/m³ and continuously rising for six hours | Trained |
| 12 | Cold frontal passage — `cold_frontal_passage` | One-hour temperature change ≤ −4 °C, pressure change ≥ 1.5 hPa, wind ≥ 6 m/s, absolute humidity change ≥ 5 percentage points | Trained; sparse evidence |

The saved heatwave rule is an instantaneous 35 °C/heat-index rule, not the proposed region-specific, six-hour sustained rule. The saved squall rule does not implement the proposed fifteen-minute pressure-rebound sequence. These differences are preserved here so the document describes the actual model.

### What an event score means

A high score means the classifier strongly matches a **learned sensor-derived rule**. It is not a calibrated probability of a real event.

For example:

```text
smoke_plume score = 0.8
```

This does **not** establish an 80% chance of smoke or fire. The model was trained against rules calculated from the input measurements, not independently confirmed smoke/fire observations.

- Wildfire/evaporative risk does not locate or confirm an active fire.
- Fog, rain and frost scores do not replace direct observations of those events.
- The pressure threshold in the inversion rule is fixed at 1010 hPa; its suitability for high-altitude sites is not established.
- Dust has no positive rule examples in the saved evaluation splits; the cold-front head has only twelve positive training examples. A fitted head is not proof of reliability.

### Availability and architecture

- Saved classifier: one binary XGBoost head per trainable event, 16 trees per trained head, maximum depth 4.
- Training source: the Beijing observations, with sensor-rule-generated labels.
- The two skipped heads have no learned detector.
- The low-level exported C header returns zero for skipped heads. **The deployment wrapper replaces these with unavailable values** (`NaN` internally, `null` in serial JSON).
- The Python deployment predictor and heatmaps also retain unavailable scores rather than reporting them as negatives.
- A field calibration/evaluation tool exists, but the deployed scores have not been calibrated against independent local events.

Model artifacts: `ml/models/uci_beijing_event_rules_6sensor/`.

## 5. Spatial heatmap outputs

The heatmap utility takes two or more synchronized nodes with:

- Distinct planar `x, y` coordinates in one common local projection.
- A timezone-aware observation timestamp shared by all nodes.
- The six measurement channels.
- Seven consecutive hourly historical records when event maps are requested.

It can produce:

| Output | Contents |
| --- | --- |
| Feature maps | Six grids: temperature, humidity, pressure, PM2.5, PM10 and wind |
| Event maps | Twelve ordered grids, with unavailable values for untrained heads or insufficient history |
| Support mask | Grid cells supported by the node geometry |
| Strategy comparison | Mean absolute difference between strategies on cells where both produce scores |
| Manifest | Input provenance, timestamps, interpolation methods and experimental status |

**Strategy A:** classify each measured node using its history, then interpolate its event scores. This is the default.

**Strategy B:** interpolate each of the seven raw measurement time slices, derive features at each grid cell, then classify those cells.

Interpolation uses IDW, with optional ordinary kriging for at least three nodes when the dependency is available and fitting succeeds. Extrapolation outside the node geometry is masked by default. With two nodes, supported geometry is their connecting segment, not a validated two-dimensional area.

These are spatial estimates, not measured conditions at unsampled locations. Agreement between strategies is not a measure of real spatial accuracy. The CLI exports arrays in `maps.npz` plus `manifest.json`; it does not itself establish a validated dashboard or automatically render images.

## 6. Separate midpoint estimator

`ml/six_sensor_forecast/midpoint.py` accepts two complete, simultaneous six-channel endpoint snapshots and their geographic coordinates.

It returns:

1. The spherical geographic midpoint.
2. Six midpoint input estimates obtained by averaging the endpoint readings.
3. Six-hour forecasts produced from those estimated inputs by the existing student model.

This is an experimental interpolation-plus-forecast operation. Coordinates alone do not predict weather, and no terrain/elevation correction or independent midpoint accuracy has been established.

## 7. ESP32-S3 interface and outputs

The current integration application accepts serial input as:

```text
unix_seconds,temperature_c,relative_humidity_pct,pressure_hpa,pm25_ug_m3,pm10_ug_m3,wind_speed_mps
```

Example:

```text
1767225600,20,50,1013,35,60,2
```

The timestamp organizes hourly history; the six following values are the measured channels.

### Prediction record fields

| Field | Meaning |
| --- | --- |
| `protocol_version` | Serial record schema version |
| `boot_id`, `sequence` | Restart identity and record sequence |
| `build_sha256` | Source/configuration fingerprint for the selected firmware build environment |
| `measurements` | The six original input values |
| `timestamp_utc` | Input time as UTC Unix seconds |
| `forecast_timestamp_utc` | Input timestamp + 21,600 seconds |
| `status` | Input/history/inference state listed below |
| `research_only` | True: experimental outputs, not validated operational warnings |
| `history_rows` | Number of stored hourly observations, up to seven |
| `latency_us` | On-board time spent processing that input, when actually executed on hardware |
| `forecast_6h` | Six numerical measurement forecasts |
| `event_valid_mask` | Which event scores are available |
| `event_scores` | Twelve ordered event-score positions; unavailable values are `null` |

### Status values

| Status | Interpretation |
| --- | --- |
| `WARMING_UP` | Current readings are accepted and forecasts are available; event history is incomplete |
| `READY` | Forecasts and the ten trained event-rule scores are available; this is **not** a field-validation certificate |
| `FEATURES_UNAVAILABLE` | Forecasting can run, but event features are unavailable—for example, PM10 is zero and the ratio is undefined |
| `INVALID_INPUT` | Invalid timestamp or missing/nonfinite/out-of-range measurement; prediction is rejected |
| `OUT_OF_ORDER` | Timestamp duplicates or precedes the previous accepted reading; prediction is rejected |

When events are ready, `event_valid_mask` is **4089 (`0x0ff9`)**. Bits are zero-based; bits 1 and 2 are unset because output positions 2 and 3 are untrained. Otherwise the event mask is zero.

A missing or off-grid hour restarts event warmup. History is held in RAM and is lost after reboot. Send one observation per exact hourly interval; do not reinterpret high-frequency readings as consecutive hours.

Commands:

- `INFO`: report device, build/model identity and self-test state.
- `SELFTEST`: run the synthetic on-board reference test.
- `RESET`: clear stream history.

The application currently receives measurements through the serial ML interface. Live sensor drivers and LoRa transport are not provided by this integration application. ESP32 builds and host parity tests have passed; actual physical execution and latency still need a connected-board test.

## 8. Other trained profiles in the repository

| Profile | Inputs/outputs | Role |
| --- | --- | --- |
| `uci_beijing_6h` | All six channels | Retained complete-input forecast baseline |
| `india_cpcb_5sensor_6h` | Temperature, humidity, PM2.5, PM10, wind | Indian research model; pressure excluded |
| `india_cpcb_pm_6h` | PM2.5 and PM10 | Indian particulate-only research model |
| `uci_beijing_5sensor_6h` | Same five-channel subset | Matched comparison baseline |
| `uci_beijing_pm_6h` | PM2.5 and PM10 | Matched comparison baseline |

Reduced-input profiles are separate experiments. They do not replace the required six-input ESP32 integration model, and their existence does not prove validated six-channel performance in India.

## 9. What the current model does not establish

The present evidence does not establish:

- Accurate Mandi-wide or India-wide forecasting.
- Independently validated detection of the named hazards.
- Six-hour advance predictions of the twelve hazard classes.
- Working trained detectors for severe rainstorm and snowstorm.
- Calibrated real-event probabilities from the raw event scores.
- Independently validated spatial heatmaps or midpoint forecasts.
- Successful physical ESP32 operation, measured device latency, or LoRa delivery.

The supplied Himachal weather files have only four channels. The downloaded rainfall source adds candidate rainfall observations, but its absence of dry-hour records prevents treating missing observations as negative rain labels. No retraining can manufacture the missing ground truth.

## 10. Code and evidence references

Paths below are relative to the repository root:

- Six-channel contract: `ml/six_sensor_forecast/contract.py`
- Forecast inference: `ml/six_sensor_forecast/predict.py`
- Forecast results and architecture: `ml/models/uci_beijing_6h/training_report.json`
- Event features, output order and label rules: `ml/event_classifier/features.py`
- Verified history-aware event inference: `ml/event_classifier/predict.py`
- Event training results: `ml/models/uci_beijing_event_rules_6sensor/event_training_report.json`
- Spatial strategies: `ml/event_classifier/heatmap.py`
- Midpoint estimator: `ml/six_sensor_forecast/midpoint.py`
- ESP32 runtime: `esp32/ml_integration/include/indra_ml_runtime.h`
- ESP32 serial interface: `esp32/ml_integration/src/main.cpp`
- Build/upload guide: [ESP32 ML integration](../../../esp32/ml_integration/README.md)
- Validation requirements: [Prototype readiness](PROTOTYPE_READINESS.md)
