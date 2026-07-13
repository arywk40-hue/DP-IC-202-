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
| **2** | Sensor driver completion (11 sensor drivers: I2C, UART, ADC, 1-Wire) | ✅ Complete |
| **3** | ML pipeline (training, export, XGBoost inference) | ✅ Complete |
| **4** | Mesh networking layer (heartbeat, neighbor discovery, TTL forwarding, ACK handling, duplicate suppression, CSMA/CA + CAD) | ✅ Complete |
| **5** | Mesh secure send/receive API (AES-128-GCM encryption, fragmentation/reassembly, CSMA/CA, ACK/retry) | ✅ Complete |
| **6** | NVS session key + IV persistence (key provisioning, auto-generation, bootstrap detection) | ✅ Complete |
| **7** | Full LoRa parameter set + mode switch helpers (SX1276 extended API, mode switching) | ✅ Complete |
| **8** | Unit tests for crypto/mesh/fragmentation (crypto round-trip, mesh serialize/deserialize, fragmentation) | ✅ Complete |
| **9** | Benchmarks/flash/RAM report (size_report.py, benchmarks.sh) | ✅ Complete |
| **10** | Firmware build script + CI gate (build.sh, GitHub Actions CI) | ✅ Complete |
| **11** | Security design doc + API reference (SECURITY_ARCHITECTURE.md) | ✅ Complete |

## Remaining: Baseline Bring-Up Test

| Item | Description | Status |
|------|-------------|--------|
| **Bring-Up Test** | Two-node encrypted mesh bring-up with fragmentation round-trip, negative key test, range testing at 10m/100m/10km | 🔄 In Progress |

This is the final item before baseline acceptance per [ACCEPTANCE_TESTS.md](./ACCEPTANCE_TESTS.md).

---

## Completed Architecture

```
firmware/
├── main/
│   ├── main.c                    # App entry, sensor_ml_task (Core 0) + mesh_comms_task (Core 1)
│   ├── test_mesh_standalone.c    # MESH_TEST_MODE: sender/listener standalone test
├── components/
│   ├── common/                   # sensor_reading_t, feature_vector_t, error codes
│   ├── crypto/                   # AES-128-GCM (crypto.c), NVS key provisioning (key_provisioning.c)
│   ├── sensors/                  # 11 drivers: BME280, PMS5003, DS18B20, Anemometer, SEN0575, LTR390, SCD41, SGP41, MICS6814, AS3935, Battery
│   ├── lora/                     # SX1276 driver + CSMA/CA + full param API + mode switching
│   ├── mesh/                     # TTL flooding, CRC8, dup suppression, neighbor table, heartbeat, ACK/retry, fragmentation, AES-GCM integration
│   ├── ml/                       # XGBoost inference (model_data.h, normalization.h, iterative tree traversal)
│   └── ml/include/               # Auto-generated: model_data.h, normalization.h, model_metadata.h
```

---

## Verified Capabilities

| Capability | Verified |
|------------|----------|
| AES-128-GCM encryption/decryption with nonce from (source_id \|\| seq_num) | ✅ Unit tested |
| Packet fragmentation (≤240B payload, 6-byte frag header, 16B GCM tag) | ✅ Unit tested |
| CSMA/CA with CAD + exponential backoff + jitter | ✅ Implemented |
| Mesh TTL-based flooding with duplicate suppression (64-entry cache) | ✅ Implemented |
| Neighbor table with 90s timeout + heartbeat (30s interval) | ✅ Implemented |
| ACK/retry for unicast (3 retries, exponential backoff) | ✅ Implemented |
| NVS key provisioning (auto-gen on first boot, manual override via PROVISION_KEY_HEX) | ✅ Implemented |
| Key rotation API (incrementing key_id, grace period) | ✅ Implemented |
| Secure send/recv API (mesh_secure_send / mesh_set_secure_rx_callback) | ✅ Implemented |
| XGBoost inference (14 features, 4 classes, 16 trees/class, depth ≤4) | ✅ Implemented |
| 11 sensor drivers (I2C×5, UART×1, ADC×4, 1-Wire×1) | ✅ Implemented |
| Unit tests (crypto + mesh) | ✅ 27 tests |
| CI pipeline (build, lint, model verify, test, size report) | ✅ Configured |

---

## Next Steps

1. **Flash two nodes** with `CONFIG_MESH_TEST_MODE=y`, one as `sender`, one as `listener`
2. **Run bring-up test** per `docs/guides/LORA_BRINGUP.md`
2. **Record results** at 10m, 100m, and max range
3. **Complete ACCEPTANCE_TESTS.md** checklist
4. **Tag release** v1.0-baseline

---

## Best Supporting Docs

- [4-Month Build Plan](./FOUR_MONTH_BUILD_PLAN.md)
- [Sensor Reference](./SENSORS.md)
- [Quick Start](./QUICK_START.md)
- [Security Architecture](./SECURITY_ARCHITECTURE.md)
- [LORA Bring-Up Guide](../guides/LORA_BRINGUP.md)