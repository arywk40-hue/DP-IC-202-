# Quick Start Guide — Low-Cost Edge AI Weather Node

## Repository Layout

```
Dp/
├── proposal/          # LaTeX design practicum proposals (3 projects)
├── implementation/    # IEEE paper — ESP32-S3 + LoRa mesh implementation
├── firmware/          # ESP-IDF bring-up tree and hardware drivers
├── code/              # ML training and export scripts
├── docs/              # Sensor reference + quick start
└── README.md
```

Current state: the hardware driver tree exists, but the application-level firmware
integration is still in progress. Use the docs below to track the missing pieces.

## Compile in 5 Minutes (Overleaf)

1. Go to https://www.overleaf.com
2. Upload `proposal/design_practicum_proposals.tex`
3. Click Recompile

## Compile Locally

```bash
cd proposal/
pdflatex design_practicum_proposals.tex
pdflatex design_practicum_proposals.tex  # twice for TOC

cd ../implementation/
pdflatex edge-ai-weather-mesh-main.tex
```

## Implementation Summary

The `implementation/` folder contains the IIT Mandi IEEE-style paper:

| Component | Detail |
|-----------|--------|
| **Compute** | ESP32-S3 with 8MB PSRAM |
| **Sensors** | 12-parameter suite (BME280, PMS5003, SCD41, AS3935, etc.) |
| **AI** | XGBoost on-device via exported C headers (~50 μs/inference) |
| **Comms** | LoRa SX1276 mesh at 865 MHz, 10 km range |
| **Cost** | ~₹19,130 per node, ~₹50,000 for 2-node prototype pair |

## Key Design Decisions

- **Wind sensing:** Generic analog anemometer + wind vane (~₹2,300) instead of branded
  SparkFun kit (₹9,589) — keeps per-node cost in ₹19k territory
- **Edge AI over cloud:** All inference runs on-device; only event-driven alerts
  transmitted via LoRa mesh
- **Zero-cloud survivability:** Fully operational during cellular/internet blackouts

## Scaling Path

The 2-node prototype validates single-node sensing and inter-node mesh handoff.
Production scaling to 20+ nodes uses the same per-node BOM with projected 20–30%
savings from a custom 4-layer PCB.

## Files to Read

1. `implementation/edge-ai-weather-mesh-main.tex` — Full system architecture
2. `docs/SENSORS.md` — Detailed sensor specs and interface map
3. `firmware/components/sensors/include/bme280.h` — Sensor driver interface example
4. `firmware/components/lora/src/sx1276.c` — LoRa driver implementation
5. `code/ml/train_model.py` — XGBoost training pipeline
6. `docs/PROJECT_STATUS.md` — Gap review and current status
7. `docs/FOUR_MONTH_BUILD_PLAN.md` — 6-person build plan
