# Project Status and Gap Review

## What The Repo Already Does Well

- The concept is consistent across the README, sensor guide, proposal, and implementation paper.
- The target system architecture is clear: ESP32-S3, 12 sensors, local inference, and LoRa mesh.
- The low-cost BOM story is strong and well documented.
- The hardware work has started: the repo now contains an ESP-IDF tree with LoRa and sensor driver components.

## Main Gaps To Close

1. The firmware tree is still incomplete at the application level.
   - `firmware/main/CMakeLists.txt` exists, but the real application entrypoint and task orchestration still need to be completed.
   - The docs currently describe a more finished firmware stack than the repo actually contains.

2. The sensor subsystem is only partially reflected in the source tree.
   - The repository documents a 12-parameter node, but the implementation still needs full driver coverage, calibration, and validation for all sensors.
   - Wind, rain, gas, and lightning subsystems need the most integration work.

3. The ML pipeline is not yet end-to-end production ready.
   - The training script can fall back to synthetic data, which is fine for demo work but not enough for field validation.
   - The model export path still needs real training artifacts, verification, and a repeatable integration test.

4. Mesh communication needs full system testing.
   - The LoRa layer is present as a driver concept, but the repo still needs packet formats, heartbeat logic, forwarding rules, and fault handling validated in hardware.

5. The repo needs a realistic data and test workflow.
   - There is no documented dataset lifecycle, calibration log format, or acceptance test checklist yet.
   - Without that, the team will struggle to reproduce results across boards and field trials.

## What To Fill First

1. Complete the firmware bring-up path for a single node.
2. Lock the sensor map, pin map, power budget, and calibration procedure.
3. Create a repeatable data collection format and use real sensor data for training.
4. Validate LoRa packet exchange between two nodes before expanding the mesh.
5. Add field-test and acceptance criteria so the prototype can be signed off cleanly.

## Best Supporting Docs

- [4-Month Build Plan](./FOUR_MONTH_BUILD_PLAN.md)
- [Sensor Reference](./SENSORS.md)
- [Quick Start](./QUICK_START.md)
