# ESP32-S3 Mandi model integration

The default PlatformIO environment is now the **Mandi v2 model**. The earlier `esp32-s3-ml` and `esp32-s3-ml-usb` environments remain in the repository for reference, but they build the compact Beijing artifacts and should not be selected for the Mandi device test.

## What this firmware contains

- The frozen `india_mandi_tabular_v2` six-channel +6-hour ensemble. It uses the saved LightGBM, residual neural, legacy history-XGBoost/ridge hybrid and validation-selected blend weights.
- The same 66 ordered causal features derived from the latest 25 exact hourly readings (current plus 24 hours of history).
- `himachal_sensor_patterns_v1` outputs from its trained LightGBM and neural components. Its scores were trained on synthetic proxy labels; they are pattern scores, not event probabilities.
- Cloudburst-like rainfall, flash-flood and landslide scenario fractions under the saved drier, central and wetter assumptions. These are Monte Carlo fractions from synthetic rainfall and assumed latent hydrology; they are not calibrated event probabilities, measured forecasts or alerts. The serial record says `field_validated: false`, `calibrated: false` and `public_alerts_enabled: false`.

The scenario port uses the assumptions in `ml/configs/himalayan_synthetic_scenarios_v1.json`; its config SHA-256 is emitted with each result. It uses the firmware RNG `indra_xorshift64star_boxmuller_v1`, so its fractions are reproducible on this implementation but need not numerically match Python's NumPy RNG output. Unknown rainfall footprint, soil wetness, slope susceptibility, catchment area and drainage capacity are returned with the result.

The export runs only inference. It does not train, learn online, fetch Open-Meteo, read physical sensors or use LoRa. A host or sensor controller must send the six measurements over USB serial. The only supported input channel order is temperature (°C), relative humidity (%), grid/station pressure (hPa), PM2.5 (µg/m³), PM10 (µg/m³) and wind speed (m/s). Firmware bounds are −60..85, 0..100, 300..1100, 0..5000, 0..5000 and 0..100 respectively. Input timestamps are UTC Unix seconds and must advance by exactly one hour; a missing hour resets warmup.

## Generate and verify the export

Run these commands from the repository root after installing the ML dependencies:

```sh
MPLCONFIGDIR=/private/tmp/indra-mpl .venv/bin/python esp32/ml_integration/tools/export_mandi_v2.py
MPLCONFIGDIR=/private/tmp/indra-mpl .venv/bin/python esp32/ml_integration/tools/test_mandi_v2_parity.py
PLATFORMIO_CORE_DIR=/private/tmp/indra-platformio pio run -d esp32/ml_integration -e esp32-s3-mandi-v2 -e esp32-s3-mandi-v2-usb
```

The export script hash-checks the frozen forecast components, pattern model and scenario configuration before emitting `generated/mandi_v2/`. The parity program compiles and runs the C++ implementation against Python: it checks an embedded self-test vector, eight chronological Mandi forecast windows, 32 synthetic pattern episodes and repeatable bounded scenario fractions. The tests are software checks; they do not replace a connected-board run.

The configured build target is ESP32-S3 DevKitC-1 N8. Both firmware variants compile and fit its default application partition: about **2.97 MB of 3.34 MB** app space and **20 KB of 320 KB** static RAM. The connected USB adapter reports CP2102 (VID:PID 10C4:EA60); this does not identify the ESP32 board or its flash/PSRAM configuration. Confirm the exact board before flashing. Physical flash, serial execution time, sensor readings and sensor calibration are not yet verified.

## Serial protocol

At 115200 baud, send one line per exact hourly observation:

```text
unix_seconds,temperature_c,relative_humidity_pct,pressure_hpa,pm25_ug_m3,pm10_ug_m3,wind_speed_mps
```

For example, a reading begins like `1767225600,20,50,1013,35,60,2`. Send `INFO`, `SELFTEST` or `RESET` for device commands. The forecast returns persistence warmup until 25 readings are buffered. Pattern scores and hazard scenarios can be available after seven hourly readings, if values also fall within the synthetic models' input domains. `latency_us` includes on-device calculation only when measured on physical hardware; host values are not board latency.

The flash command after the device is ready in serial download mode is:

```sh
PLATFORMIO_CORE_DIR=/private/tmp/indra-platformio pio run -d esp32/ml_integration -e esp32-s3-mandi-v2 -t upload --upload-port /dev/cu.usbserial-0001
```

Use the standard command after confirming the board target. If automatic reset does not enter download mode, use the manual environment: hold BOOT, tap RESET/EN, release BOOT, then run this upload command without reset-line toggling:

```sh
PLATFORMIO_CORE_DIR=/private/tmp/indra-platformio pio run -d esp32/ml_integration -e esp32-s3-mandi-v2-manual -t upload --upload-port /dev/cu.usbserial-0001
```

The CP2102 bridge identifies the serial adapter, not the exact board. Confirm chip and flash first; the connected device previously failed automatic upload and no firmware was written by that attempt.
