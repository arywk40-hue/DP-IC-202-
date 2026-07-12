# Acceptance Test Checklist — Edge AI Weather Node

## Purpose

Define pass/fail criteria for 2-node prototype sign-off. Each test must pass on **both nodes** before field deployment.

---

## Test Categories

| Category | Tests | Criticality |
|----------|-------|-------------|
| Hardware Bring-up | 10 | 🔴 Blocking |
| Sensor Validation | 22 | 🔴 Blocking |
| ML Inference | 8 | 🔴 Blocking |
| Mesh Networking | 12 | 🔴 Blocking |
| Power & Battery | 8 | 🟡 High |
| Environmental | 6 | 🟡 High |
| Integration | 6 | 🟢 Medium |

---

## 1. Hardware Bring-up

| # | Test | Procedure | Pass Criteria |
|---|------|-----------|---------------|
| H1 | PCB Inspection | Visual + multimeter continuity | No shorts, correct components, clean solder |
| H2 | Power-On | Connect battery, measure 3.3V rail | 3.3V ± 0.1V, < 50 mA quiescent |
| H3 | Solar Charge | Connect panel, measure CN3065 output | 4.2V ± 0.05V at battery, charge LED on |
| H4 | ESP32 Boot | Power on, monitor serial @ 115200 | "System boot successful" within 3s |
| H5 | NVS Init | Check logs for NVS | "NVS initialized" |
| H6 | I2C Scan | Run `i2cdetect` equivalent in firmware | 5 devices found (0x76, 0x53, 0x62, 0x59, 0x03) |
| H7 | SPI Test | SX1276 register read (0x42 = 0x12) | Version register = 0x12 |
| H8 | UART Test | PMS5003 responds to passive cmd | Valid 32-byte frame, checksum OK |
| H9 | ADC Calibration | Read known voltage (3.3V/2 divider) | 1.65V ± 0.02V |
| H10 | 1-Wire Scan | DS18B20 presence pulse | Device detected, ROM read OK |

---

## 2. Sensor Validation

Each sensor: **Individual read** → **Range check** → **Continuous 10-min log**

| # | Sensor | Test | Pass Criteria |
|---|--------|------|---------------|
| S1 | BME280 Temp | Compare to reference thermometer | ±1.0°C (0–65°C) |
| S2 | BME280 Humidity | Compare to reference hygrometer | ±3% RH (20–80%) |
| S3 | BME280 Pressure | Compare to reference barometer | ±1.0 hPa |
| S4 | PMS5003 PM2.5 | Co-locate with reference monitor | ±10 μg/m³ or ±10% |
| S5 | PMS5003 PM10 | Co-locate with reference monitor | ±15 μg/m³ or ±15% |
| S6 | SCD41 CO2 | Exhale near sensor (40k ppm peak) | Responds > 5000 ppm, returns to 400-600 |
| S7 | SGP41 VOC | Isopropanol vapor near sensor | VOC index spikes > 200 |
| S8 | SGP41 NOx | Lighter flame near sensor | NOx index spikes > 100 |
| S9 | LTR-390 UV | Direct sun vs shade | UV index 0–11+, shade ≈ 0 |
| S10 | Anemometer | Hand-held anemometer comparison | ±0.5 m/s or ±10% |
| S11 | Wind Vane | Known directions (N/E/S/W) | ±22.5° (16 sectors) |
| S12 | SEN0575 Rain | Spray water / dry | Dry=0, Light=1, Mod=2, Heavy=3 |
| S13 | AS3935 Lightning | Piezo lighter clicks nearby | Distance 1–40 km, count increments |
| S14 | MICS-6814 CO | CO calibration gas (50 ppm) | 40–60 ppm reading |
| S15 | MICS-6814 NO2 | NO2 calibration gas (5 ppm) | 3–7 ppm reading |
| S16 | MICS-6814 NH3 | NH3 calibration gas (50 ppm) | 40–60 ppm reading |
| S16 | DS18B20 Enclosure | Compare to BME280 temp | ±0.5°C |
| S17 | Battery Monitor | Known voltage source (3.0–4.2V) | ±0.05V |
| S18 | All Sensors: Continuous | 10-min log at 1Hz (via debug) | No NaN, no comm errors, < 1% dropouts |
| S19 | Sensor Mask | Verify `sensor_mask` bits set correctly | All 13 bits populated after init |
| S20 | Derived Features | Compare firmware vs Python on same raw | All 14 features match within 1e-4 |
| S21 | Sensor Failure Graceful | Disconnect I2C sensor, observe | Other sensors continue, mask bit cleared |
| S22 | Power Cycling | Power off/on 5×, verify all init | All sensors re-init successfully |

---

## 3. ML Inference

| # | Test | Procedure | Pass Criteria |
|---|------|-----------|---------------|
| M1 | Model Load | `ml_init()` returns ESP_OK | All 4 classes, 16 trees each loaded |
| M2 | Normalization | Feed known raw vector, compare to Python | All 14 features match within 1e-4 |
| M3 | Single-Class Predict | `ml_predict(norm, 0, &out)` for wildfire | Matches Python `predict_proba` within 1e-4 |
| M4 | All Classes | Run all 4 classes, compare probabilities | All 4 match Python within 1e-4 |
| M5 | Confidence Sigmoid | `ml_confidence()` matches `1/(1+exp(-x))` | Within 1e-6 for x ∈ [-10, 10] |
| M6 | Alert Threshold | Synthetic hazard vector → alert queued | Alert queued iff confidence ≥ threshold |
| M5 | Inference Time | Measure `ml_last_inference_us()` | < 100 μs for 4 classes |
| M6 | RAM Usage | `ml_model_ram_usage()` | < 4 KB |
| M7 | Flash Usage | `ml_model_flash_usage()` | < 64 KB |
| M8 | Repeated Inference | 1000 inferences, no crash, stable time | All pass, time variance < 5% |

---

## 4. Mesh Networking

### Single Node

| # | Test | Procedure | Pass Criteria |
|---|------|-----------|---------------|
| N1 | Mesh Init | `mesh_init(node_id)` returns ESP_OK | Neighbor table empty, seq=0 |
| N2 | Heartbeat TX | `mesh_send_heartbeat()` → radio TX | Packet on air (SDR capture), seq increments |
| N3 | Heartbeat RX | Node B receives A's heartbeat | `mesh_receive()` returns ESP_OK, callback fired |
| N4 | Neighbor Table | After 2 heartbeats from B | B in table, RSSI/SNR populated |
| N5 | Neighbor Timeout | Stop B's heartbeats, wait 90s | B pruned from table |
| N6 | Duplicate Suppression | Send same (src, seq) twice | Second filtered, `duplicates_filtered++` |

### Two-Node Pair

| # | Test | Procedure | Pass Criteria |
|---|------|-----------|---------------|
| N7 | Alert Broadcast | Node A triggers wildfire alert | Node B receives, callback fires, logs alert |
| N8 | Alert Payload | Verify alert payload parsing | Class=0, confidence, pm25, temp, lightning |
| N9 | ACK Request | Unicast with `ACK_REQ` | ACK received, no retry |
| N10 | ACK Retry | Block ACK (faraday cage) | 3 retries with backoff, then drop |
| N11 | TTL Forwarding | 3 nodes in line (A-B-C), A broadcasts | C receives (TTL 5→3→1), B forwards |
| N12 | Mesh Stats | `mesh_get_stats()` | Counters match observed packets |

---

## 5. Power & Battery

| # | Test | Procedure | Pass Criteria |
|---|------|-----------|---------------|
| P1 | Active Current | Measure during sensor poll + ML | < 150 mA average |
| P2 | Deep Sleep Current | `esp_deep_sleep()` between polls | < 200 μA |
| P3 | Solar Charge | Full sun, measure battery current | > 500 mA into battery |
| P4 | Battery Read Accuracy | Compare ADC to multimeter | ±0.05V (3.0–4.2V) |
| P5 | Battery Level Logic | Simulate voltages | OK > 3.3V, Low 3.2–3.3V, Critical 3.0–3.2V |
| P6 | Critical Shutdown | Drain to 3.0V | Logs warning, enters deep sleep |
| P7 | Solar Priority | Battery + solar connected | Solar powers load, battery charges |
| P8 | 7-Day Autonomy | Simulated 60s polls + 1 alert/hr | Battery > 3.3V after 7 days (calc) |

---

## 6. Environmental

| # | Test | Procedure | Pass Criteria |
|---|------|-----------|---------------|
| E1 | Temperature Range | -10°C to +50°C (chamber) | All sensors functional, no crashes |
| E2 | Humidity | 90% RH, 40°C (condensing) | No sensor failure, BME280 recovers |
| E3 | Rain Ingress | Spray test (IP65 equivalent) | No water inside enclosure |
| E4 | Vibration | 5–50 Hz, 2g, 30 min/axis | No loose connectors, no solder cracks |
| E5 | UV Exposure | 72h UV lamp (simulated sun) | Enclosure no cracking, sensors OK |
| E6 | EMI | 433 MHz transmitter 1m away | No LoRa packet corruption |

---

## 7. Integration

| # | Test | Procedure | Pass Criteria |
|---|------|-----------|---------------|
| I1 | Full Cycle | Power on → 1 hour continuous | All tasks run, no watchdog resets |
| I2 | Alert End-to-End | Trigger wildfire (heat+lamp+smoke) | Alert TX → Mesh RX → Log on peer |
| I3 | Multi-Alert | Trigger all 4 hazards sequentially | All 4 alerts TX+RX, correct class IDs |
| I4 | OTA Update | `idf.py ota` via serial | New firmware boots, preserves NVS |
| I5 | NVS Persistence | Reboot, check node_id, calibration | Node ID same, sensor calibrations retained |
| I6 | Watchdog | Force task stall (infinite loop) | System resets, recovers to running |

---

## Test Execution Template

```
Test ID: S1
Name: BME280 Temperature Accuracy
Date: 2026-07-15
Operator: __________
Node: A / B (circle)

Equipment: Reference thermometer (NIST traceable)
Procedure: Co-locate node + reference for 10 min, log both

Results:
  Reference: 24.3°C, 24.4°C, 24.2°C (avg 24.3)
  Node:      24.1°C, 24.2°C, 24.0°C (avg 24.1)
  Delta:     0.2°C

PASS / FAIL  (circle)

Notes: ________________________________________

Sign-off: __________  Date: __________
```

---

## Sign-off Matrix

| Test Category | Node A | Node B | Date | Tester |
|---------------|--------|--------|------|--------|
| Hardware Bring-up | ☐ | ☐ | | |
| Sensor Validation | ☐ | ☐ | | |
| ML Inference | ☐ | ☐ | | |
| Mesh Networking | ☐ | ☐ | | |
| Power & Battery | ☐ | ☐ | | |
| Environmental | ☐ | ☐ | | |
| Integration | ☐ | ☐ | | |

**Overall Prototype Sign-off**: ☐ PASS / ☐ FAIL

**Lead Engineer**: ________________  **Date**: ________________

---

## Failure Handling

| Severity | Action |
|----------|--------|
| 🔴 Blocking | Fix before any field deployment |
| 🟡 High | Fix before multi-node pilot |
| 🟢 Medium | Log, fix in next firmware rev |

**No field deployment until all 🔴 tests pass on both nodes.**