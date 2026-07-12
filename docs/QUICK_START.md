# Quick Start Guide - Edge AI Weather Station

## Repository Layout

```
Dp/
├── proposal/          # LaTeX proposals (compile these)
├── implementation/    # IIT Mandi reference implementation
├── docs/              # This guide + research docs
└── references/        # IAF requirement PDF
```

## Compile in 5 Minutes (Overleaf)

1. Go to https://www.overleaf.com
2. Upload these 2 files from `proposal/`:
   - `design_practicum_proposals.tex`
   - `project5_hardware_weather_station.tex`
3. Click Recompile
4. Download PDF

## Compile Locally (Mac)

```bash
cd /Users/ariyanbhakat/Desktop/Dp/proposal
pdflatex design_practicum_proposals.tex
pdflatex design_practicum_proposals.tex  # twice for TOC
```

## Implementation Reference

The `implementation/` folder contains the IIT Mandi IEEE paper:
- **Compute:** ESP32-S3 with 8MB PSRAM
- **Sensors:** 12-parameter suite (BME280, PMS5003, SCD41, AS3935, etc.)
- **AI:** XGBoost on-device via micromlgen
- **Comms:** LoRa SX1276 mesh at 865 MHz
- **Cost:** INR 19,130 per node (~$228)

## Project 5 Sensor Specs (Verified)

| Sensor | Model | Key Specs | Price |
|--------|-------|-----------|-------|
| Temp/Humidity | Vaisala HMP155 | ±1% RH, -80 to +60°C | $800 |
| Barometer | Vaisala PTB330 | ±0.10 hPa, QNH/QFE | $1,200 |
| Wind | Gill WindSonic M | 0-60 m/s, ±2%, ultrasonic | $1,000 |
| Visibility | Vaisala PWD22 | 10-20,000 m, forward scatter | $4,500 |
| Cloud Ceiling | Campbell CS135 | 10 km LIDAR, ICAO | $3,000 |
| Precipitation | Vaisala DRD11A | RAINCAP, heating -15°C | $1,500 |
| Edge AI | Jetson Orin Nano | 67 TOPS, 8GB LPDDR5 | $249 |
| Data Logger | Campbell CR1000Xe | -40 to +70°C, 24-bit | $2,000 |

## Pitch Talking Points

### Hook
"60% of military aviation accidents are weather-related. Forward bases have zero visibility forecast. This project builds the first portable edge AI weather station that predicts fog 30 minutes ahead, costs 10x less, and deploys in 30 minutes."

### Key Differentiators
1. Edge AI nowcasting (0-30 min ahead)
2. Tactical portability ($15k, <50 lbs)
3. Physics-informed AI (42% accuracy boost)
4. Autonomous operation (7+ days solar)
5. IAF requirement (Compendium #49)

### IIT Mandi Validation
The implementation architecture is validated by IIT Mandi's ESP32-S3 + LoRa mesh node at INR 19,130 per unit with 12-parameter sensing and on-device XGBoost inference.

## Files to Read

1. `proposal/design_practicum_proposals.tex` - Full proposal
2. `implementation/edge-ai-weather-mesh-main.tex` - Implementation paper
3. `references/Problem_49_Portable_Automatic_Weather_Station.pdf` - IAF requirement
4. `docs/WEATHER_STATION_SUMMARY.md` - Quick summary
5. `docs/RESEARCH_SUMMARY.md` - Research sources
