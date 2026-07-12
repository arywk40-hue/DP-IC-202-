# Documentation Index

## 📁 Repository Documentation Structure

```
docs/
├── index.md                    # This file
├── architecture/               # System architecture & design
│   └── SYSTEM_ARCHITECTURE.md  # Hardware/software architecture
├── guides/                     # How-to guides
│   ├── QUICK_START.md          # 5-minute setup & build
│   ├── BUILD_GUIDE.md          # Detailed build instructions
│   ├── FLASH_GUIDE.md          # Flashing & debugging
│   └── ML_PIPELINE.md          # Training & exporting models
├── reference/                  # Technical reference
│   ├── SENSORS.md              # Sensor specs, pin map, interface
│   ├── MESH_PROTOCOL.md        # Mesh packet format, routing
│   ├── ML_INFERENCE.md         # XGBoost model format, API
│   ├── FIRMWARE_API.md         # Component APIs, error codes
│   └── PIN_MAP.md              # ESP32-S3 GPIO assignments
└── planning/                   # Project planning & tracking
    ├── PROJECT_STATUS.md       # Current status, completed prompts
    ├── FOUR_MONTH_BUILD_PLAN.md # 6-person execution plan
    └── ACCEPTANCE_TESTS.md     # Test checklist for sign-off
```

---

## 📖 Quick Navigation

### Getting Started
| Document | Description |
|----------|-------------|
| [QUICK_START.md](guides/QUICK_START.md) | 5-minute build, flash, and run |
| [BUILD_GUIDE.md](guides/BUILD_GUIDE.md) | Detailed ESP-IDF build instructions |
| [FLASH_GUIDE.md](guides/FLASH_GUIDE.md) | Flashing, monitoring, debugging |

### Architecture & Design
| Document | Description |
|----------|-------------|
| [SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md) | Full system: hardware, firmware, ML, mesh |
| [MESH_PROTOCOL.md](reference/MESH_PROTOCOL.md) | Packet format, routing, ACK, heartbeat |

### Reference
| Document | Description |
|----------|-------------|
| [SENSORS.md](reference/SENSORS.md) | 11 sensors: specs, pins, interfaces |
| [ML_INFERENCE.md](reference/ML_INFERENCE.md) | XGBoost model format, inference API |
| [FIRMWARE_API.md](reference/FIRMWARE_API.md) | Component APIs, common types, errors |
| [PIN_MAP.md](reference/PIN_MAP.md) | ESP32-S3 GPIO assignments |

### Project Management
| Document | Description |
|----------|-------------|
| [PROJECT_STATUS.md](planning/PROJECT_STATUS.md) | Completed prompts, current gaps |
| [FOUR_MONTH_BUILD_PLAN.md](planning/FOUR_MONTH_BUILD_PLAN.md) | 6-person, 4-month execution plan |
| [ACCEPTANCE_TESTS.md](planning/ACCEPTANCE_TESTS.md) | Hardware/software test checklist |

---

## 🎯 Firmware Component Overview

| Component | Path | Responsibility |
|-----------|------|----------------|
| `common` | `firmware/components/common/` | Shared types, error codes |
| `sensors` | `firmware/components/sensors/` | 11 sensor drivers (I2C/UART/ADC/1-Wire) |
| `lora` | `firmware/components/lora/` | SX1276 SPI driver |
| `mesh` | `firmware/components/mesh/` | Multi-hop mesh (CRC8, TTL, ACK, heartbeat) |
| `ml` | `firmware/components/ml/` | XGBoost inference + auto-generated model |

### Task Architecture (`main.c`)
- **Core 0** — `sensor_ml_task` (prio 5): Poll sensors → 14 features → ML → queue alerts
- **Core 1** — `mesh_comms_task` (prio 4): LoRa RX → mesh_process → heartbeat → drain alert queue

---

## 🤖 ML Pipeline (Real Data Only)

```bash
cd code/ml/
pip install -r requirements.txt

# Prepare real weather data
python prepare_dataset.py --input dataset/weatherHistory.csv --output data/

# Train on real data
python train_model.py --data data/ --output model/ --export-c --c-output ../firmware/components/ml/include/model_data.h
```

Generated headers (in `firmware/components/ml/include/`):
- `model_data.h` — 4 classes × 16 trees × 32 nodes, inline inference
- `normalization.h` — Z-score constants + `normalize_features()`
- `model_metadata.h` — Feature/class names, alert thresholds

---

## 🔧 Build Commands

```bash
# Firmware (requires ESP-IDF v5.x)
cd firmware/
idf.py set-target esp32s3
idf.py build
idf.py flash monitor

# Documents
cd proposal/ && pdflatex design_practicum_proposals.tex
cd implementation/ && pdflatex edge-ai-weather-mesh-main.tex
```

---

## 📊 Current Status

| Prompt | Deliverable | Status |
|--------|-------------|--------|
| 1 | Firmware entrypoint + FreeRTOS dual-core tasks | ✅ |
| 2 | 11 sensor drivers (I2C, UART, ADC, 1-Wire) | ✅ |
| 3 | ML pipeline (train, export, inference) | ✅ |
| 4 | Mesh networking (CRC8, TTL, ACK, heartbeat) | ✅ |
| 5 | Data workflow, calibration, acceptance tests | 🔄 Next |

---

*Last updated: July 2026*