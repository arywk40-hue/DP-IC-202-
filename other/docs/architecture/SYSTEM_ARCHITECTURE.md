# System Architecture — Edge AI Environmental Hazard Network

## Overview

Two-node prototype of a decentralized, solar-powered environmental monitoring network.
Each node: **ESP32-S3** + **12 sensors** + **on-device XGBoost** + **LoRa 865 MHz mesh**.
Cost: **~₹19,130/node**, **~₹50,000** for 2-node pair (incl. shared NRE).

---

## Hardware Block Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        ESP32-S3-WROOM-1                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │  Core 0  │  │  Core 1  │  │   ULP    │  │  8 MB PSRAM    │  │
│  │ Sensor/ML│  │  Mesh    │  │  Coproc  │  │  (model data)  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────────────┘  │
└───────┼──────────────┼──────────────┼────────────────────────────┘
        │              │              │
  ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
  │   I2C     │  │   SPI     │  │  UART/ADC │
  │  (400kHz) │  │  (10 MHz) │  │  (9600)   │
  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
        │              │              │
  ┌─────▼──────────────▼──────────────▼─────┐
  │           SENSOR ARRAY (12 params)      │
  ├──────────────┬──────────────┬────────────┤
  │ BME280       │ PMS5003      │ DS18B20    │
  │ T/H/P        │ PM2.5/10     │ Enclosure  │
  │ I2C 0x76     │ UART         │ 1-Wire     │
  ├──────────────┼──────────────┼────────────┤
  │ SCD41        │ SGP41        │ LTR-390    │
  │ CO2          │ VOC/NOx      │ UV Index   │
  │ I2C 0x62     │ I2C 0x59     │ I2C 0x53   │
  ├──────────────┼──────────────┼────────────┤
  │ MICS-6814    │ AS3935       │ Anemometer │
  │ CO/NO2/NH3   │ Lightning    │ + Wind Vane│
  │ ADC×3        │ I2C 0x03     │ ADC×2      │
  ├──────────────┼──────────────┼────────────┤
  │ SEN0575      │ Battery ADC  │            │
  │ Rain         │ (divider)    │            │
  │ ADC          │ ADC1_CH3     │            │
  └──────────────┴──────────────┴────────────┘

  ┌─────────────────────────────────────────┐
  │           LoRa RADIO (SX1276)           │
  │  865 MHz, SF7, 125 kHz, 17 dBm          │
  │  SPI + DIO0/DIO1 IRQ                    │
  └─────────────────────────────────────────┘
```

---

## Power Architecture

| Source | Spec | Role |
|--------|------|------|
| 18650 Li-ion | 3.0–4.2 V, 3000 mAh | Primary energy storage |
| 5 W Solar Panel | 5 V, 1 A peak | Daytime recharge |
| CN3065 | MPPT charger | Solar → battery |
| ESP32-S3 | 80 mA active, 10 µA deep sleep | Compute |
| Sensors | ~200 mA peak (PMS5003 fan) | Sensing |
| SX1276 | 120 mA TX, 1 µA sleep | Radio |

**Estimated autonomy**: 5–7 days on battery + solar recharge

---

## Firmware Architecture

### Dual-Core FreeRTOS Tasks

```
Core 0 (Protocol/App)          Core 1 (Radio/Comms)
┌─────────────────────────┐    ┌─────────────────────────┐
│ sensor_ml_task          │    │ mesh_comms_task         │
│  prio=5, stack=4KB      │    │  prio=4, stack=4KB      │
│                         │    │                         │
│ 1. Init all 11 sensors  │    │ 1. Init SX1276 + Mesh  │
│ 2. Loop (60s):          │    │ 2. Loop (50ms):        │
│    • Read sensors       │    │    • sx1276_received()? │
│    • Build 14 features  │    │      → mesh_receive()  │
│    • ML inference (4×)  │    │    • mesh_periodic()   │
│    • Queue alerts       │    │    • heartbeat (30s)   │
│                         │    │    • drain alert queue │
│                         │    │      → mesh_send()     │
└─────────────────────────┘    └─────────────────────────┘
              │                           │
              └──────────┬────────────────┘
                         │ FreeRTOS Queue (len=8)
                         ▼
              ┌─────────────────────────┐
              │    Alert Queue          │
              │  struct {               │
              │    payload[240]         │
              │    hazard_class (0-3)   │
              │    confidence (float)   │
              │    timestamp_ms         │
              │  }                      │
              └─────────────────────────┘
```

### Initialization Sequence (`app_main`)

1. `nvs_flash_init()` — persistent storage
2. `i2c_driver_install()` — sensors bus
3. `spi_bus_initialize()` — SX1276 bus
4. `uart_driver_install()` — PMS5003
5. Sensor drivers: BME280 → PMS5003 → DS18B20 → Anemometer → SEN0575 → LTR390 → SCD41 → SGP41 → MICS6814 → AS3935 → Battery
6. `ml_init()` — loads model constants
7. Create alert queue
8. Spawn `sensor_ml_task` (Core 0)
9. Spawn `mesh_comms_task` (Core 1)
10. Main loop: health logging (30s)

---

## ML Pipeline

### Feature Vector (14 elements)

| Index | Feature | Source | Derived |
|-------|---------|--------|---------|
| 0 | temp_current | BME280 | — |
| 1 | humidity_current | BME280 | — |
| 2 | pressure_current | BME280 | — |
| 3 | wind_speed_current | Anemometer | — |
| 4 | pm25_current | PMS5003 | — |
| 5 | co2_current | SCD41 | — |
| 6 | lightning_dist_current | AS3935 | — |
| 7 | temp_humidity_ratio | — | temp/humidity |
| 8 | pressure_trend | — | linear slope (6-sample) |
| 9 | heat_index | — | temp + 0.5×humidity |
| 10 | dew_point | — | Magnus approx |
| 11 | fire_risk_index | — | temp>30, hum<35, wind>5, pm25>40 |
| 12 | flood_risk_index | — | pres<1005, hum>85, wind>8 |
| 13 | lightning_threat | — | (40-dist)/40 |

### Model

- **Algorithm**: XGBoost binary classification (one-vs-rest × 4 hazards)
- **Trees/class**: 16, **max depth**: 4
- **Inference**: ~50 μs on ESP32-S3 (iterative, no recursion)
- **Export**: `convert_to_c.py` → `model_data.h` (trees + z-score)

### Hazard Classes & Thresholds

| Class | Threshold | Key Features |
|-------|-----------|--------------|
| Wildfire | 0.70 | temp, humidity, wind, pm25, fire_risk |
| Flood | 0.70 | pressure, humidity, wind, flood_risk |
| Storm | 0.75 | lightning_dist, pressure, pressure_trend |
| Air Quality | 0.65 | pm25, co2, voc, nox |

---

## Mesh Networking

### Topology

- **Decentralized** peer-to-peer
- **Flooding** with TTL (default 5 hops)
- **Duplicate suppression**: 64-entry (src_id, seq_num) cache
- **Heartbeat**: 30s broadcast for neighbor discovery
- **ACK/retry**: 3 retries, exponential backoff (500ms → 1s → 2s)

### Packet Format

```
[version:4|flags:4] [src_id:4] [dest_id:4] [seq:4] [ts:4] [ttl:1] [len:1] [rsv:1] [payload:N] [crc8:1]
  1 byte                 4 bytes     4 bytes    4 bytes  4 bytes  1      1      1       N bytes    1 byte
```

**Flags**: `ACK_REQ=0x01`, `ACK=0x02`, `ALERT=0x04`

### Alert Payload (broadcast)

```
[class_id:1] [confidence:4] [pm25:4] [temp:4] [lightning_dist:4] = 17 bytes
```

---

## Cost Breakdown (2-Node Prototype, July 2026)

| Category | Per Node | 2 Nodes |
|----------|----------|---------|
| Compute & Radio | ₹1,499 | ₹2,998 |
| Core Meteorological | ₹4,960 | ₹9,920 |
| Particulate & Gases | ₹7,500 | ₹15,000 |
| Specialized Sensing | ₹1,800 | ₹3,600 |
| Power Architecture | ₹1,370 | ₹2,740 |
| Fabrication | ₹2,000 | ₹4,000 |
| **Subtotal** | **₹19,129** | **₹38,258** |
| Shared NRE & Contingency | — | ₹11,742 |
| **Total** | **₹19,129** | **₹50,000** |

---

## Scaling Path

| Scale | Nodes | Cost | Use Case |
|-------|-------|------|----------|
| Prototype | 2 | ₹50,000 | Validate sensing + mesh |
| Valley pilot | 20 | ~₹3.8L | Full coverage + redundancy |
| Production PCB | 100+ | -30%/node | Custom 4-layer, integrated ICs |
| Baseline (no gas) | — | ₹13,530/node | Mass spatial coverage |

---

## References

1. Bosch Sensortec, *BME280 Datasheet*, 2020
2. Espressif, *ESP32-S3 Datasheet*, 2023
3. Semtech, *SX1276 Datasheet*, 2020
4. Nair, A.P., *Decentralized Edge AI Environmental Hazard Network*, IIT Mandi, 2026