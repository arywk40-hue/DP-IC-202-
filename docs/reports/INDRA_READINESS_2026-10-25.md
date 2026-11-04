# INDRA readiness review — 25 October 2026

This review records the live Mandi API check, a frozen six-hour forecast evaluation, interface checks, and the limits that still require field data or hardware. Open-Meteo weather and CAMS values are modeled-grid estimates, not physical sensor readings.

## A. Software completed and verified

### Live Mandi feed and dashboard

- Queried Open-Meteo at requested coordinates **31.71° N, 76.93° E**. The active dashboard returned 91 hourly rows, with five future hours excluded and latest valid time **2026-10-25 18:00 UTC**. Retrieval time was **2026-10-25 18:13:54 UTC**.
- Weather model: ECMWF IFS, returned grid cell **31.669594° N, 76.942444° E**. Air-quality source: CAMS Global, returned grid cell **31.700005° N, 76.899994° E**. These grids are close but distinct; the feed does not claim physical co-location.
- All six canonical channels were present with expected units: temperature (°C), relative humidity (%), grid surface pressure (hPa), PM2.5 and PM10 (µg/m³), and wind speed (m/s). Pressure reference is `grid_surface`.
- The dashboard had 25 of 25 required hourly history rows and returned a six-hour forecast from model profile `india_mandi_tabular_v2` (SHA-256 `79eae97fa522973e69db6b8ef825e849534e26060c00f132d4fe6b9482486fc6`). Its API adapter identifies the source as `modeled_grid`.
- Provider failure behavior is covered by the automated UI and backend tests: the application reports the failed/offline state and does not invent demo or synthetic readings.
- The six-hour hazard-pattern outputs remain uncalibrated pattern scores. Cloudburst, flash-flood and landslide values are deterministic synthetic scenario fractions, not event probabilities or warnings. `field_validated=false`, `calibrated=false`, and public alerts are disabled.
- At the verified snapshot, the scenario simulator returned these fractions of simulated outcomes under the named assumptions:

| Scenario target | Drier case | Central case | Wetter case |
| --- | ---: | ---: | ---: |
| Cloudburst-like rainfall | 0.0488% | 0.0977% | 0.6836% |
| Flash flood | 0.1465% | 1.8555% | 10.7422% |
| Landslide | 0.1465% | 1.5137% | 5.9082% |

  These percentages are simulation outcome fractions only. They are not real-event probabilities; the run seed and configuration hash are recorded in the live-feed receipt.
- One Mandi point produces no area-map layers. The UI requires at least three synchronized locations for an area map; it shows the single point and explains this limit. A future multi-site feed must provide the six channels, coordinates, source identity and synchronized timestamps for each location.

Detailed machine-readable evidence: [live feed verification](../../ml/reports/mandi_live_check/2026-10-25/current_feed_verification.json) and [desktop/mobile browser check](../../ml/reports/mandi_live_check/2026-10-25/live_browser.json).

### Six-hour forecast evaluation

The frozen `india_mandi_tabular_v2` model was compared to persistence on a downloaded Open-Meteo archive covering **2026-09-25 00:00 through 2026-10-24 23:00 UTC**. All 720 hourly positions had all six channels. No model was fitted, tuned or promoted on this snapshot. The data is a retrospective modeled-grid reference, not station truth; original forecast-issue availability was not verified.

The latest five target days after the previous archive end provide **120 pairs** (target times 2026-10-20 00:00 through 2026-10-24 23:00 UTC). The complete 30-day cohort has 690 pairs but reuses dates examined before. The evaluator excluded 24 rows without ready history, 6 rows without a complete +6-hour target and 570 ready rows whose targets predate or equal the previous archive end. There were no missing channel values in the downloaded snapshot.

| Target | MAE | RMSE | Persistence MAE | MAE skill vs persistence |
| --- | ---: | ---: | ---: | ---: |
| Temperature (°C) | 1.2725 | 1.7205 | 7.4017 | 82.8% |
| Relative humidity (percentage points) | 7.0331 | 10.2582 | 26.8250 | 73.8% |
| Surface pressure (hPa) | 0.6751 | 0.8422 | 1.9833 | 66.0% |
| PM2.5 (µg/m³) | 5.2287 | 7.0095 | 11.3242 | 53.8% |
| PM10 (µg/m³) | 6.0862 | 8.2392 | 12.2167 | 50.2% |
| Wind speed (m/s) | 0.3189 | 0.4339 | 0.6468 | 50.7% |

This five-day later-target cohort extends the previous archive comparison without selecting weights on these rows. It is a small, retrospective comparison against the same provider's modeled grid. It does **not** establish independent station accuracy, real-time forecast skill, deployment readiness or Mandi field accuracy. The provider may revise archive values. Full R², hashes, source manifest and exclusions are in [metrics.json](../../ml/reports/mandi_live_check/2026-10-25/metrics.json); a readable summary is in [REPORT.md](../../ml/reports/mandi_live_check/2026-10-25/REPORT.md).

### Checks run

- Python: `.venv/bin/python -m pytest ml/tests server/tests -q` — **362 passed, 164 subtests passed**, 3 warnings (dependency deprecation/compatibility warnings).
- UI: `npm test --prefix ui` — **3 passed**.
- UI production build: `npm run build --prefix ui` — **passed**.
- Browser E2E: `INDRA_E2E_PORT=8095 npm run test:e2e --prefix ui` — **18 passed**, desktop and mobile.
- Live browser check: `node ui/tests/verify-live-mandi.mjs` — **passed** at 1440×1000 and 390×844, six channels displayed, no browser errors, no unsupported map layers.
- ESP32-S3 firmware compile: `PLATFORMIO_CORE_DIR=/private/tmp/indra-platformio pio run -d esp32/ml_integration -e esp32-s3-ml -e esp32-s3-ml-usb` — **both environments passed**. A temporary PlatformIO core directory was used because the pre-existing user-level core directory has incompatible ownership.

### ESP32-S3 interface status

The six-channel order and units in `ml/six_sensor_forecast/contract.py` match the serial input contract: `unix_seconds,temperature_c,relative_humidity_pct,pressure_hpa,pm25_ug_m3,pm10_ug_m3,wind_speed_mps`. Bounds are −60–85 °C, 0–100%, 300–1100 hPa, 0–5000 µg/m³ for each particulate channel, and 0–100 m/s. The interface expects UTC Unix seconds and exact hourly spacing for history; event inference warms up over seven hourly observations (six elapsed hours). USB serial is 115200 baud.

Build command: `PLATFORMIO_CORE_DIR=/private/tmp/indra-platformio pio run -d esp32/ml_integration -e esp32-s3-ml -e esp32-s3-ml-usb`. The checked-in firmware currently exports the UCI Beijing compact forecast/event artifacts, not the Mandi hybrid profile. This firmware interface has no live sensor drivers or LoRa transport. No physical board was connected during this review, so flashing, sensor accuracy, physical output and on-board latency are unverified.

## B. Requires new data or independent event labels

- Longer untouched chronological and geographically independent evaluation of all six forecast channels, preferably against station observations with verified units, timestamps and provenance. The current five-day later-target period is useful as a diagnostic, but too short to establish field performance.
- Independent, dated local event and non-event records matched to the observations that precede the event. Cloudburst, flash-flood, landslide and snowstorm accuracy and probability calibration cannot be established from synthetic episodes or rule-generated labels.
- More synchronized real locations to create an area heatmap. Until then, the map remains a single point.
- If hazard outputs remain in the project, retain their synthetic-scenario label, assumptions and unknown drivers. Do not present scenario fractions as actual event chances or public warnings.

## C. Requires physical hardware

- Connect and identify the ESP32-S3 board and six sensor channels; flash firmware and verify readings, timestamp cadence, output parsing and reconnect/error handling.
- Measure inference latency, memory/uptime and sensor calibration on the actual board. The current Mandi hybrid profile is not the firmware's exported profile and needs a compatible embedded implementation/export before claiming the same model runs on ESP32.
- Add and test radio/network transport only if the final device design uses it; no LoRa path is included in the current ML integration firmware.

## Preserved artifacts and scope

No datasets, model weights, reports or research code were deleted or retrained for this review. The downloaded Mandi archive and live API responses are local ignored data, with provenance and SHA-256 receipts. No push or deployment was performed. This review verifies the current software paths and records the remaining evidence required for field and hazard claims.
