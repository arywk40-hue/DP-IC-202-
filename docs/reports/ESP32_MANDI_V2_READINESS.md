# INDRA Mandi v2 ESP32 readiness

**Status:** software build is ready for a physical smoke test after confirming the board matches the configured target. No firmware was flashed during this verification.

## What the firmware includes

- Six-hour, six-channel forecast using the frozen `india_mandi_tabular_v2` ensemble: LightGBM, MLP, legacy hybrid and persistence blend.
- The 66 causal features are built from 25 consecutive hourly sensor rows (current row plus 24 hours of history).
- Ten current synthetic sensor-pattern scores, explicitly not event probabilities.
- Six-hour cloudburst-like, flash-flood and landslide scenario fractions for drier, central and wetter assumptions. These are seeded synthetic simulation fractions, not calibrated probabilities, warnings or evidence of real hazard accuracy.
- Serial commands `INFO`, `SELFTEST` and `RESET`; input is timestamp plus the six measurements in the documented order.

The firmware requires hourly input at exactly one-hour intervals. Forecast inference reaches full 25-row history after 24 hours of warmup; pattern and scenario results can be available after seven rows when the readings are within model bounds. It does not read physical sensors directly, perform online learning, connect to Open-Meteo or use LoRa.

## Verification completed

| Check | Result |
| --- | --- |
| Frozen model export and source hashes | Passed |
| C++ host parity: forecast | 8 Mandi windows; maximum absolute difference `0.000120304779294` |
| C++ host parity: synthetic patterns | 32 episodes; maximum absolute difference `3.29729672455e-08` |
| Firmware self-test fixture | Passed; synthetic software fixture only |
| Scenario repeatability/bounds | Passed on 4 cases; firmware RNG `indra_xorshift64star_boxmuller_v1` |
| Jaipur Windstorm/Andhi C++ Parity | Passed; exact match in `test_esp32_jaipur_runtime_c_parity` |
| PlatformIO `esp32-s3-mandi-v2` | Passed; 2,967,109 / 3,342,336 bytes app flash, 19,916 / 327,680 bytes static RAM |
| PlatformIO `esp32-s3-mandi-v2-usb` | Passed; 2,964,357 / 3,342,336 bytes app flash, 20,148 / 327,680 bytes static RAM |
| Physical flash, boot, serial output and sensor data | Pending |

The configured PlatformIO target is `esp32-s3-devkitc-1` (N8, no PSRAM). The currently visible serial adapter is CP2102 (`10C4:EA60`), which does not identify the ESP32 module. Confirm the exact board and flash configuration before selecting the upload environment. A previous upload attempt failed to connect and wrote no firmware.

## Flash after board confirmation

From the repository root, use the regular UART build for CP2102 UART wiring, or the USB CDC build only when connected through the ESP32-S3 native USB port:

```sh
PLATFORMIO_CORE_DIR=/private/tmp/indra-platformio pio run -d esp32/ml_integration -e esp32-s3-mandi-v2 -t upload --upload-port /dev/cu.usbserial-0001
```

The board must be in serial download mode. After flashing, open a 115200-baud serial monitor, confirm `INFO` reports the Mandi model IDs and `self_test_passed: true`, run `SELFTEST`, and send at least 25 correctly spaced rows before judging full forecast output. Record measured inference latency and sensor readings from the actual board. Until that run happens, do not claim physical ESP32 validation.

## Reproduce software checks

```sh
MPLCONFIGDIR=/private/tmp/indra-mpl .venv/bin/python esp32/ml_integration/tools/export_mandi_v2.py
MPLCONFIGDIR=/private/tmp/indra-mpl .venv/bin/python esp32/ml_integration/tools/test_mandi_v2_parity.py
PLATFORMIO_CORE_DIR=/private/tmp/indra-platformio pio run -d esp32/ml_integration -e esp32-s3-mandi-v2 -e esp32-s3-mandi-v2-usb
```

See [ESP32 Mandi integration](../../esp32/ml_integration/README.md) for the model inputs, output schema, and detailed command protocol.
For comprehensive multi-profile hardware deployment across all three firmware variants (Inference, Sensor Hub, and Mesh), see [ESP32 Deployment Specification](ESP32_DEPLOYMENT_SPECIFICATION_AND_READINESS.md).
