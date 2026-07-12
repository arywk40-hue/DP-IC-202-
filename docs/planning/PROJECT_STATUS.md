# Project Status and Gap Review

## What The Repo Already Does Well

- The concept is consistent across the README, sensor guide, proposal, and implementation paper.
- The target system architecture is clear: ESP32-S3, 12 sensors, local inference, and LoRa mesh.
- The low-cost BOM story is strong and well documented.
- The hardware work has started: the repo now contains an ESP-IDF tree with LoRa and sensor driver components.

## Completed Prompts

| Prompt | Description | Status |
|--------|-------------|--------|
| **1** | Firmware app entrypoint & task orchestration (main.c) | ✅ Complete |
| **2** | Sensor driver completion (11 sensor drivers (I2C, UART, ADC, 1-Wire) | ✅ Complete |
| **3** | ML pipeline (training, export, XGBoost inference) | ✅ Complete |

## Main Gaps To Close

1. **Mesh communication needs full system testing** (Prompt 4)
   - The LoRa layer is present as a driver concept, but the repo still needs packet formats, heartbeat logic, forwarding rules, and fault handling validated in hardware.

2. **The repo needs a realistic data and test workflow** (Prompt 5)
   - There is no documented dataset lifecycle, calibration log format, or acceptance test checklist yet.
   - Without that, the team will struggle to reproduce results across boards and field trials.

## What To Fill Next

1. **Prompt 4**: Complete mesh networking layer — heartbeat, neighbor discovery, TTL forwarding, ACK handling, duplicate suppression
2. **Prompt 5**: Data workflow — dataset format, calibration logs, acceptance test checklist, CI integration

## Best Supporting Docs

- [4-Month Build Plan](./FOUR_MONTH_BUILD_PLAN.md)
- [Sensor Reference](./SENSORS.md)
- [Quick Start](./QUICK_START.md)