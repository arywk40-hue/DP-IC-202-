# India research export and physical acceptance procedure

**Confidential: do not publish before IP review. NOT HARDWARE VALIDATED.**

This is the national B same-node six-hour measurement-threshold model. It does not implement two-node spatial interpolation or enable field/disaster alerts. Full server interpolation, corridors and hidden-C scoring retain their existing interfaces.

## Offline interface

`export/indra_india_model.h`: `indra_india_predict(x,raw,prob,flags,status)` uses 72 ordered float32 engineered features listed in `export_manifest.json`. Three outputs, in manifest order: future high wind (10 m/s), hot temperature (35°C), near saturation (95% RH), each at exact issue time +6h completed-hour mean. `raw` is an uncalibrated research score; `prob` stays NaN when calibration is unavailable. `flags=-1` means no validated cutoff. Status values distinguish invalid core, range refusal, archive calibration and uncalibrated output. Calibration is archive-only. Infinities refuse; optional missing features use NaN. Outputs require no heap allocation or I/O.

`export/indra_india_preprocess.h`: zero-initialize `indra_hour_history`, then call `indra_hour_push(history,stamp,available,raw,station_pressure,latitude,longitude,height,x)`. Raw channel order is T °C, RH %, station P hPa, PM2.5/PM10 µg/m³, wind m/s. T/RH/wind are required for prediction; PM is optional. Timestamps are explicit UTC completed-hour ends (2020–2037), epoch seconds, aligned on whole hours, with `available==stamp` for this idealized archive contract. Duplicate, late, out-of-order and off-grid packets refuse. Return 2 means warm-up; predict only on return 1 after ≥24h history span. Missing hours remain gaps. A 26-row history consumes at most 848 bytes. Minute telemetry must be aggregated into verified completed-hour windows first; minute/gust skill is not established.

Coordinates are fixed surveyed WGS84; height is verified orthometric EGM96 sensor elevation, not raw Neo-M8N ellipsoid altitude. Unknown height is NaN. `station_pressure=0` masks pressure and all its history-derived features. Never submit sea-level pressure as station pressure. Floating telemetry quantization can alter decisions near thresholds; checked tree parity is a separate engineered-feature contract. Host preprocessing tests use `rtol=1e-5, atol=0.002`; primary raw tree export errors are below 5e-5.

```sh
# Host verification and source export (requires prepared local archive/models)
python3 -m ml.india_sensor.export --config configs/india_sensor_offline.json
python3 -m pytest -q tests/test_india_export.py
# Compile only; no board required. This firmware sends synthetic hourly fixtures.
pio run -d esp32/india_sensor
```

The committed smoke harness uses a nonblocking millis timer, fixed arrays and no sensor/network drivers. The repeated synthetic stream prints research scores/status; it is a test firmware, not deployment firmware. BME280/PMS7003 drivers, encoder hardware capture, GPS, INA219 and RTC acquisition remain separate integration work. No pin map is invented before wiring is specified. INA219 values belong to health telemetry, not weather model inputs.

## Requires hardware — record all as pending

1. Verify power/wiring/pins and each part's model/firmware serial. Calibrate BME280 offsets and PMS7003 response side-by-side; measure encoder pulse-to-m/s response and counter rollover for the actual rotor/600 PPR convention. PPR alone is not a wind calibration or wind direction.
2. Compare RTC and GPS UTC against an independent clock; measure drift, outage behavior and completed-window timestamps. Survey sensor heights and shelter/exposure. Apply the retained [A/B/C offset and rotation protocol](../../reports/nwic_pipeline/NODE_COLLECTION_SPEC.md), freezing offsets before hiding C.
3. Upload the smoke harness using `pio run -d esp32/india_sensor -t upload`; observe `pio device monitor -d esp32/india_sensor -b 115200`. Compare serial model/features against host fixtures, including gaps, missing PM, bad core, duplicate UTC, OOD and withheld calibration. Archive board/toolchain identity and logs; compilation alone passes none of these checks.
4. Measure inference latency distribution, stack high-water/minimum free heap, CPU/watchdogs, worst-case serial blocking and reboot behavior at intended cadence. The linker reports 19,612 static RAM /319,309 flash bytes; runtime stack/heap is unmeasured. Exercise long-running loss/recovery, sensor-stuck/disconnect, encoder overflow, RTC/GPS failure and power loss. Record watchdog resets and all refused packets.
5. Measure actual INA219 power against a reference meter; verify radio/authentication and replay protection before remote ingestion. Existing local source/hash checks authenticate neither nodes nor messages.
6. Run outdoor A/B plus hidden C, rotate each instrument into the hidden role, use only frozen offsets and score untouched sessions. Predeclare acceptable error/coverage/false-alarm budgets, retain failures, and do not enable disaster alerts from threshold forecasts. Long-duration reliability and any real-world alert validation remain pending.
