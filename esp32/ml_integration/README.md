# ESP32-S3 ML integration test

Runs the retained six-hour forecast and the event-rule classifier together on
ESP32-S3. This is the ML integration stage: readings arrive through serial replay
or the portable `indra::Runtime::push(timestamp, readings)` API. Sensor drivers
and LoRa networking are separate work.

## Build and test

From the repository root:

```sh
python3 -m unittest tests.test_esp32_ml_integration tests.test_event_classifier tests.test_midpoint -v
pio run -d esp32/ml_integration -e esp32-s3-ml -e esp32-s3-ml-usb
```

The board target is ESP32-S3-DevKitC-1-N8 (8 MB flash, no PSRAM required).
Choose `esp32-s3-ml` for the USB-to-UART connector, or `esp32-s3-ml-usb` for
native USB CDC. PlatformIO produces a firmware.bin, bootloader.bin,
partitions.bin and firmware.elf under `.pio/build/<environment>/`.
Use PlatformIO upload to apply the correct flash layout.

Connect the board, find its actual port with `pio device list`, then run:

```sh
# Replace /dev/cu.YOUR_ESP32_PORT with the real board port.
# Upload replaces the existing application on that board.
pio run -d esp32/ml_integration -e esp32-s3-ml -t upload --upload-port /dev/cu.YOUR_ESP32_PORT
python3 esp32/ml_integration/tools/test_board.py --port /dev/cu.YOUR_ESP32_PORT
```

For native USB, select `-e esp32-s3-ml-usb`; the serial port may change after
flashing. The Python board test uses `pyserial` (installed with PlatformIO;
otherwise `python3 -m pip install pyserial`). Close other serial monitors first.
It writes `results/esp32_board_test.json`, including actual per-row inference
latencies, predictions, warmup behavior, and rejection checks. Seven synthetic
hourly records are replayed immediately; this tests timestamped logic without
waiting six wall-clock hours. These records are not field observations.

For manual interaction:

```sh
pio device monitor --port /dev/cu.YOUR_ESP32_PORT --baud 115200
```

Send `SELFTEST` to rerun the independent synthetic test, or `RESET` to clear
stream history. The firmware refuses stream inference if self-test fails.
On-board reference predictions are generated from the saved Python models:

```sh
python3 esp32/ml_integration/tools/generate_fixture.py
```

Regenerate and rerun parity tests whenever model artifacts change.

## Input and output contract

One newline-terminated CSV record:

```text
1767225600,20,50,1013,35,60,2
```

Order: UTC Unix seconds, temperature C, RH %, station pressure hPa,
PM2.5 ug/m3, PM10 ug/m3, wind m/s. Timestamps must increase; pass one
observation per exact hourly interval. Do not feed each high-frequency sensor
sample into this hourly model. Training has not validated arbitrary sub-hourly
aggregation schemes.

Each accepted snapshot produces six forecast values for timestamp + 6 hours.
Events require seven consecutive hourly readings: six raw channels plus eleven
derived quantities form the 17-value input. Gaps/off-grid intervals reset the
history; duplicate/out-of-order readings are rejected. No historical values
are synthesized. PM10=0 permits a forecast but makes the event ratio undefined
(`FEATURES_UNAVAILABLE`). Invalid/missing/out-of-range readings are rejected.
History is RAM-only and warms up again after reboot.

JSON output contains `status`, `timestamp_utc`, `history_rows`, `latency_us`,
`forecast_6h`, `event_valid_mask`, and `event_scores`. Null means unavailable.
Mask `0x0ff9` (4089) marks the ten trained event heads. Bits 1 and 2 are
unavailable, not negative predictions. During warmup the mask is zero.

Event score order:

1. Light/moderate rain
2. Severe rainstorm/squall — untrained
3. Snowstorm/blizzard — untrained
4. Freezing rain/sleet
5. Radiation fog
6. Ground frost
7. Extreme heatwave
8. Wildfire/evaporative risk
9. Dust storm/haboob
10. Smoke plume
11. Smog/inversion trap
12. Cold frontal passage

The outputs reproduce the existing learned sensor rules. They are not
calibrated real-world hazard probabilities. This integration preserves the
saved model definitions; the implemented rules and their limitations are
documented in [model inputs and outputs](../../docs/MODEL_INPUTS_AND_OUTPUTS.md).

## Verification boundary

Host tests compile the same C++ runtime used by the firmware and compare its
17 features, six forecasts, and ten available event scores with Python.
They exercise history gaps, duplicates, nonfinite/out-of-range inputs, PM10=0,
heat-index boundaries, and monotonic PM history. Firmware cross-compilation
checks both serial variants. Physical latency and real sensor performance
require the connected-board replay and field measurements.

If macOS cloud-cached Python bytecode stalls imports, use a local cache:
`PYTHONPYCACHEPREFIX=/private/tmp/indra-ml-pycache python3 ...`.

## Field-trial telemetry preparation

The firmware now supports `INFO`: protocol version, device ID, boot ID,
self-test state, model header hashes and a source/configuration fingerprint.
The fingerprint includes the selected PlatformIO environment, so native USB
and UART builds differ. It is not a signature or a hash of the flashed binary.
Each prediction echoes the six input measurements, forecast timestamp, boot ID,
sequence and build fingerprint. The replay test verifies identity and input echo.
For native USB include `--environment esp32-s3-ml-usb` when running test_board.py.

`tools/record_field.py` records sessions to a new append-only JSONL file and
flushes/fsyncs each record. It records device resets, rejects duplicate or
out-of-order sequences, preserves invalid records, and quarantines observations
older than two hours or over one minute in the future against the host clock.
Unknown event heads remain null. A passed INFO handshake and expected build
fingerprint are required before a record becomes an accepted observation.

```sh
python3 esp32/ml_integration/tools/record_field.py --port /dev/cu.YOUR_ESP32_PORT --station YOUR_STATION_ID --expected-build YOUR_VERIFIED_BUILD_SHA256 --output results/field/session-001.jsonl
```

Use the expected fingerprint recorded when building the intended environment,
not a value blindly trusted from an unknown device. After a build,
`include/build_identity.h` contains the fingerprint for the last environment
built; the board's INFO must match the intended environment. Do not run the
recorder and test_board.py/serial monitor on the same port simultaneously.
The recorder sends INFO once but never invents observations or generates alerts.
A new output filename is required for each run. An interrupted disk write can
leave a truncated final JSONL line; preserve it and exclude it during ingestion.

**Live sensor integration remains pending hardware details.** This firmware is
still a serial-input ML integration application, not an autonomous sensor node.
The recorder does not feed measurements into it. A sensor/controller integration
must supply real six-channel hourly snapshots and verified time before field use.
Record sensor IDs/calibration, placement, clock source and wiring separately.
No recorded experimental score is an operational hazard warning.
