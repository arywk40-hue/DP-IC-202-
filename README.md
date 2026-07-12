# Edge AI Portable Weather Station - Design Practicum

## Overview

This repository contains the design practicum project for an **Edge AI-Enabled Portable Automatic Weather Station with Hyperlocal Forecasting for Military Aviation**. The project is based on IAF Compendium Challenge #49 and follows the implementation architecture from IIT Mandi's Decentralized Edge AI Environmental Hazard Network.

## Repository Structure

```
Dp/
├── README.md                              # This file
├── proposal/                              # Project proposals and LaTeX documents
│   ├── design_practicum_proposals.tex     # Main compilable document (all projects)
│   └── project5_hardware_weather_station.tex  # Project 5 detailed section
├── implementation/                        # Reference implementation (IIT Mandi)
│   ├── edge-ai-weather-mesh-main.tex      # IEEE paper - ESP32-S3 + LoRa mesh
│   ├── edge-ai-weather-mesh-paper.pdf     # Compiled PDF
│   └── edge-ai-weather-mesh.zip           # Source files
├── code/                                  # Firmware and ML code
│   ├── firmware/                          # ESP32-S3 firmware
│   │   ├── src/
│   │   │   ├── main.c                     # Main entry point (FreeRTOS tasks)
│   │   │   ├── sensor_pipeline.c          # 12-sensor drivers + feature computation
│   │   │   ├── ml_pipeline.c              # XGBoost inference engine
│   │   │   └── mesh_comm.c               # LoRa SX1276 mesh communication
│   │   └── lib/
│   │       ├── sensor_pipeline.h          # Sensor HAL and data structures
│   │       ├── ml_pipeline.h              # ML inference API
│   │       └── mesh_comm.h               # Mesh packet structures
│   └── ml/                                # Machine learning tools
│       ├── train_model.py                 # XGBoost training (Python)
│       ├── convert_to_c.py                # Model conversion to C header
│       └── model/                         # Trained models (generated)
├── docs/                                  # Documentation and guides
│   ├── QUICK_START.md                     # Quick start and pitch guide
│   ├── RESEARCH_SUMMARY.md                # Web research and gap analysis
│   ├── WEATHER_STATION_SUMMARY.md         # Project 5 detailed summary
│   ├── SENSORS.md                         # Low-cost sensors (IIT Mandi)
│   └── SENSORS_AVIATION.md                # Aviation-grade sensors (Project 5)
└── references/                            # Reference documents
    └── Problem_49_Portable_Automatic_Weather_Station.pdf  # IAF requirement
```

## Projects

### Main Project: Edge AI Portable Weather Station (Project 5)
- **Domain:** Meteorology, Defense, Edge AI, Sensors
- **Innovation:** First portable AWOS-grade station with edge AI nowcasting
- **Budget:** $18,749 (prototype) | **Timeline:** 9-10 months
- **IAF Alignment:** Compendium Challenge #49

### Additional Proposals (in `proposal/`)
| Project | Domain | Budget | Timeline |
|---------|--------|--------|----------|
| 1 - Energy | Sustainability, IoT | $3,300 | 7-9 mo |
| 2 - Accessibility | AI, Mobile | $1,724 | 5-7 mo |
| 3 - Agriculture | Blockchain | $3,500 | 8-10 mo |

## Implementation Architecture (from IIT Mandi)

The implementation follows the **Decentralized Edge AI Environmental Hazard Network** architecture:

### Compute Core
- **ESP32-S3-WROOM-1** with 8MB PSRAM
- Hardware-accelerated 128-bit vector math
- 45 programmable GPIO pins
- Ultra-Low-Power (ULP) coprocessor

### Sensor Array (12 Parameters)

| Category | Component | Interface |
|----------|-----------|-----------|
| Temp/Hum/Pressure | Bosch BME280 | I2C |
| Wind Speed/Dir | Generic Anemometer + Wind Vane | Analog/Digital |
| Precipitation | DFRobot SEN0575 (piezo) | Analog |
| UV Index | LTR390 | I2C |
| PM2.5 / PM10 | Plantower PMS5003 | UART |
| CO2 | Sensirion SCD41 | I2C |
| VOC / NOx | Sensirion SGP41 | I2C |
| Multi-gas | MICS-6814 (CO, NO2, NH3) | Analog |
| Lightning | AS3935 (0-40 km) | I2C/SPI |
| Enclosure temp | DS18B20 | 1-Wire |
| Battery voltage | Onboard ADC divider | Analog |

### Edge AI
- XGBoost models trained offline in Python (`code/ml/train_model.py`)
- Model converted to C header via `code/ml/convert_to_c.py`
- On-device inference on ESP32-S3 (~50 μs per prediction)
- 16 shallow trees (max depth 4) per hazard class
- 14 normalized features, binary sigmoid output
- Event-driven alerts (not raw telemetry)

### Communication
- **LoRa SX1276 (RFM95W)** at 865 MHz
- Multi-hop mesh routing (Meshtastic/RadioHead)
- 10 km range in mountainous terrain
- Zero-cloud survivability

### Power
- 18650 Li-ion cell + 5W solar panel
- CN3065 charge controller
- FDM 3D-printed Stevenson screen (PETG)

### Cost Breakdown

| Category | Components | Cost (INR) |
|----------|-----------|------------|
| Compute & Radio | ESP32-S3, RFM95W, passives | 1,499 |
| Core Meteorological | BME280, Anemometer + Wind Vane, DS18B20, SEN0575, LTR390 | 4,960 |
| Particulate & Gases | PMS5003, SGP41, MICS-6814, SCD41 | 7,500 |
| Specialized Sensing | AS3935 | 1,800 |
| Power Architecture | 18650, 5W solar, CN3065 | 1,370 |
| Fabrication | PCB, PETG, coating | 2,000 |
| **Total per Node** | | **19,130** |

## Key Differences from Commercial Stations

| Feature | Traditional Station | Edge AI Mesh Node |
|---------|-------------------|-------------------|
| Data Resolution | Macro-level (>50 km) | Hyper-local microclimates |
| Processing | Passive cloud telemetry | Edge inference (XGBoost) |
| Connectivity | Wi-Fi/4G (fails in storms) | LoRa mesh (zero-cloud) |
| Bandwidth | High (raw data streams) | Event-driven alerts only |
| Deployment | Static, heavy, professional | Portable, solar, rapid |

## How to Compile

### Proposal Documents
```bash
cd proposal/
pdflatex design_practicum_proposals.tex
pdflatex design_practicum_proposals.tex  # Run twice for TOC
```

### Implementation Paper
```bash
cd implementation/
pdflatex edge-ai-weather-mesh-main.tex
```

### Or use Overleaf
1. Upload `proposal/design_practicum_proposals.tex` and `proposal/project5_hardware_weather_station.tex`
2. Click Recompile

### ML Model Training
```bash
cd code/ml/
pip install xgboost scikit-learn pandas numpy
python train_model.py --data ./data/ --output ./model/
python convert_to_c.py --model ./model/ --output ../firmware/lib/model_data.h
```

### Firmware Build (ESP-IDF)
```bash
cd code/firmware/
idf.py build
idf.py flash
```

## Research Sources

- **Vaisala sensors:** HMP155, PTB330, PWD22, DRD11A (verified specs)
- **Campbell Scientific:** CS135 ceilometer, CR1000Xe data logger
- **Gill Instruments:** WindSonic M ultrasonic anemometer
- **NVIDIA:** Jetson Orin Nano Super (67 TOPS, $249)
- **ESP32-S3:** IIT Mandi implementation (12 sensors, LoRa mesh)
- **ACM 2026:** Edge AI for aviation traffic forecasting
- **IAF Compendium:** Challenge #49 - Portable Automatic Weather Station

## Author

**Ariyan Bhakat**
Department of Engineering

With implementation reference from:
**Abhinav P. Nair**
Department of Electrical Engineering, IIT Mandi

---

**Generated:** July 2026
**Research Sources:** 40+ papers and manufacturer specifications
