# Decentralized Edge AI Environmental Hazard Network — Low-Cost IoT Prototype

## Overview

A two-node prototype of a decentralized, solar-powered Edge AI environmental
monitoring network. Each node is built around the **ESP32-S3** with a **12-parameter
sensor suite**, on-device **XGBoost inference**, and **LoRa (865 MHz) multi-hop mesh**
communication — enabling hyper-local microclimate monitoring and early hazard
detection (flash floods, wildfire smoke) without relying on cellular infrastructure.

**Total build cost (2-node pair):** ~₹50,000 (including shared NRE and contingency)
**Per-node BOM:** ~₹19,130

The node pair validates both single-node sensing performance and inter-node LoRa mesh
handoff, establishing the foundation for scaling into a full swarm-intelligence
environmental network across mountainous topography.

Current repo status:

- `firmware/` contains the ESP-IDF hardware tree and driver layer.
- `code/ml/` contains the training and export scripts.
- The missing pieces are tracked in [docs/PROJECT_STATUS.md](./docs/PROJECT_STATUS.md)
  and [docs/FOUR_MONTH_BUILD_PLAN.md](./docs/FOUR_MONTH_BUILD_PLAN.md).

## Repository Structure

```
Dp/
├── implementation/                    # IEEE-format implementation paper
│   ├── edge-ai-weather-mesh-main.tex # Full system architecture & cost analysis
│   └── edge-ai-weather-mesh-paper.pdf
├── proposal/                         # Design practicum project proposals (3 projects)
│   └── design_practicum_proposals.tex
├── firmware/                         # ESP-IDF bring-up tree and hardware drivers
│   ├── main/
│   └── components/
├── code/
│   └── ml/
│       ├── train_model.py            # XGBoost training script
│       └── convert_to_c.py           # Model export helper
├── docs/
│   ├── SENSORS.md                    # Full low-cost sensor reference
│   ├── QUICK_START.md               # Compilation & quick reference
│   ├── PROJECT_STATUS.md             # Repo review and gap list
│   └── FOUR_MONTH_BUILD_PLAN.md      # 6-person execution plan
└── README.md
```

## System Architecture

### Compute Core
- **ESP32-S3-WROOM-1** with 8MB PSRAM, hardware vector acceleration
- ULP coprocessor for continuous low-power sensor polling
- Dual-core FreeRTOS: Sensor/ML on Core 0, Mesh comms on Core 1

### Sensor Array (12 Parameters)

| Category | Components |
|----------|-----------|
| Core Met | BME280, wind speed/direction, DS18B20, SEN0575 (rain), LTR-390 (UV) |
| Air Quality | PMS5003 (PM2.5/PM10), SGP41 (VOC/NOx), SCD41 (CO2), MICS-6814 (CO/NO2/NH3) |
| Hazard | AS3935 lightning detector (1–40 km) |
| System | Battery voltage (ADC), enclosure temp (DS18B20) |

### Edge AI
- XGBoost trained offline in Python and exported to embedded C headers
- 16 shallow trees (max depth 4), 14 derived features, ~50 μs per inference
- Event-driven alerts — no raw telemetry transmitted

### Communication
- LoRa SX1276 (RFM95W) at 865 MHz ISM band
- Multi-hop mesh routing (Meshtastic/RadioHead)
- ~10 km range in mountainous terrain, zero-cloud survivability

### Power
- 18650 Li-ion + 5W solar panel + CN3065 charge controller
- FDM 3D-printed Stevenson screen (PETG)
- Estimated 5–7 day autonomy with solar recharge

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

## How to Compile

```bash
# Proposal document
cd proposal/
pdflatex design_practicum_proposals.tex
pdflatex design_practicum_proposals.tex

# Implementation paper
cd implementation/
pdflatex edge-ai-weather-mesh-main.tex

# ML model training
cd code/ml/
pip install xgboost scikit-learn pandas numpy
python train_model.py --data ./data/ --output ./model/
python convert_to_c.py --model ./model/ --output ../firmware/path/to/model_data.h  # update to the final include path

# Firmware build
cd firmware/
idf.py build
idf.py flash
```

## Scaling Scope

This two-node prototype validates the core architecture. The same per-node rate
(~₹19,130) scales linearly to larger deployments:

- **20-node mesh network:** ~₹3.83 Lakhs — full valley coverage with multi-hop
  redundancy
- **Production PCB** (custom 4-layer, integrating sensor ICs directly): projected
  20–30% per-node cost reduction
- **Baseline nodes** (excluding gas sensors): ₹13,530/node for mass spatial
  coverage at strategic choke points
- **Federated learning** across the mesh enables collaborative model improvement
  without central infrastructure

## Author

**Ariyan Bhakat** — Department of Engineering

Implementation reference: **Abhinav P. Nair**, Department of Electrical Engineering, IIT Mandi

---

**Generated:** July 2026
