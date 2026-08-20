# Quick Start Guide — Low-Cost Edge AI Weather Node

## Repository Layout

```
Dp/
├── ml/                # All ML work — data, training, models, ML docs
├── other/
│   ├── proposal/      # LaTeX design practicum proposals (3 projects)
│   ├── implementation/# IEEE paper — ESP32-S3 + LoRa mesh implementation
│   ├── firmware/      # ESP-IDF bring-up tree and hardware drivers
│   └── docs/          # Sensor reference + quick start (you are here)
└── README.md
```

Current state: **All 3 firmware prompts complete** — sensor drivers, ML inference, task orchestration, mesh comms.

## Compile in 5 Minutes (Overleaf)

1. Go to https://www.overleaf.com
2. Upload `proposal/design_practicum_proposals.tex`
3. Click Recompile

## Compile Locally

```bash
cd ../../proposal/      # from other/docs/guides/ into other/proposal/
pdflatex design_practicum_proposals.tex
pdflatex design_practicum_proposals.tex  # twice for TOC

cd ../implementation/
pdflatex edge-ai-weather-mesh-main.tex
```

## ML Model Training & Export

```bash
cd ../../../ml/          # from other/docs/guides/ into ml/
pip install xgboost scikit-learn pandas numpy

# Generate synthetic dataset (20k samples) and train
python prepare_dataset.py --generate-synthetic --samples 20000 --output ./data/
python train_model.py --data ./data/ --output ./model/ --export-c --c-output ../other/firmware/components/ml/include/model_data.h

# Or in one step:
python train_model.py --data ./data/ --output ./model/ --export-c --c-output ../other/firmware/components/ml/include/model_data.h
```

## Firmware Build (requires ESP-IDF v5.x)

```bash
cd ../../firmware/       # from other/docs/guides/ into other/firmware/
idf.py set-target esp32s3
idf.py build
idf.py flash
```

## Implementation Summary

| Component | Detail |
|-----------|--------|
| **Compute** | ESP32-S3 with 8MB PSRAM, dual-core FreeRTOS |
| **Sensors** | 12-parameter suite (BME280, PMS5003, SCD41, AS3935, SGP41, MICS-6814, LTR-390, SEN0575, Anemometer, DS18B20, Battery ADC) |
| **AI** | XGBoost 16-tree × 4-class model, on-device inference (~50 μs/inference) |
| **Comms** | LoRa SX1276 mesh at 865 MHz, 10 km range, multi-hop |
| **Cost** | ~₹19,130 per node, ~₹50,000 for 2-node prototype pair |

## Firmware Architecture

```
firmware/
├── main/
│   └── main.c              # app_main, hardware init, FreeRTOS task creation
├── components/
│   ├── common/             # Shared types (sensor_reading_t, feature_vector_t)
│   ├── sensors/            # 11 sensor drivers (I2C, UART, ADC, 1-Wire)
│   ├── ml/                 # XGBoost inference engine (auto-generated model_data.h)
│   ├── lora/               # SX1276 SPI driver
│   └── mesh/               # Multi-hop mesh (CRC, neighbor table, forwarding)
```

### Task Architecture (main.c)
- **sensor_ml_task** (Core 0, prio 5, 4KB stack): Polls all 11 sensors → builds 14-feature vector → runs ML inference → queues alerts
- **mesh_comms_task** (Core 1, prio 4, 4KB stack): LoRa RX loop → mesh_receive() → drains alert queue via mesh_send()

## Key Design Decisions

- **Wind sensing:** Generic analog anemometer + wind vane (~₹2,300) instead of branded SparkFun kit (₹9,589)
- **Edge AI over cloud:** All inference runs on-device; only event-driven alerts transmitted via LoRa mesh
- **Zero-cloud survivability:** Fully operational during cellular/internet blackouts

## Scaling Path

The 2-node prototype validates single-node sensing and inter-node mesh handoff.
Production scaling to 20+ nodes uses the same per-node BOM with projected 20–30%
savings from a custom 4-layer PCB.

## Files to Read

1. `other/implementation/edge-ai-weather-mesh-main.tex` — Full system architecture
2. `other/docs/reference/SENSORS.md` — Detailed sensor specs and interface map
3. `other/firmware/main/main.c` — Application entry point and task orchestration
4. `other/firmware/components/sensors/` — All 11 sensor driver implementations
5. `other/firmware/components/ml/src/ml.c` — XGBoost inference engine
6. `other/firmware/components/lora/src/sx1276.c` — LoRa driver implementation
7. `ml/train_model.py` — XGBoost training pipeline
8. `ml/convert_to_c.py` — Model-to-C header converter
9. `other/docs/planning/PROJECT_STATUS.md` — Gap review and current status
10. `other/docs/planning/FOUR_MONTH_BUILD_PLAN.md` — 6-person build plan