# Sensor Reference Guide - Aviation-Grade Weather Station

Professional meteorological sensors for IAF-compliant portable AWOS.

**Target Cost:** $18,749 (prototype) | $12,000-15,000 (production)

---

## Sensor Array (8 Parameters)

### 1. Vaisala HMP155 - Temperature / Humidity

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Vaisala (Finland) |
| **Type** | HUMICAP capacitive humidity + Pt100 RTD temperature |
| **Interface** | RS-485, 0-1V, 0-5V, 0-10V, or Pt100 4-wire |
| **Humidity Range** | 0-100% RH |
| **Humidity Accuracy** | +/-1% RH (0-90% RH at 15-25 C) |
| **Humidity Accuracy (extreme)** | +/-1.2% RH (-40 to +60 C) |
| **Temperature Range** | -80 to +60 C |
| **Temperature Accuracy** | +/-0.226 C (voltage, -80 to +20 C) |
| **Response Time** | 20s (63%), 60s (90%) |
| **Filter** | Sintered Teflon (removable) |
| **IP Rating** | IP66 (dust-tight, water jets) |
| **Supply Voltage** | 7-28V DC |
| **Power Consumption** | <4 mA (RS-485), 150 mA (warmed probe) |
| **Calibration** | NIST-traceable, 6-point factory |
| **Output (calculated)** | Dew point, frost point, mixing ratio, wet bulb |
| **Housing** | Polycarbonate (PC) |
| **Dimensions** | 279 x 40 mm |
| **Weight** | 93 g |
| **Use Case** | Aviation-grade temp/RH measurement |
| **Price** | ~$800 |

---

### 2. Vaisala PTB330 - Barometric Pressure

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Vaisala (Finland) |
| **Type** | BAROCAP silicon capacitive absolute pressure |
| **Interface** | RS-232, RS-485 |
| **Pressure Range (Class A)** | 500-1100 hPa |
| **Pressure Range (Class B)** | 50-1100 hPa |
| **Linearity (Class A)** | +/-0.05 hPa |
| **Linearity (Class B)** | +/-0.10 hPa |
| **Hysteresis** | +/-0.03 hPa |
| **Repeatability** | +/-0.03 hPa |
| **Accuracy (Class A)** | +/-0.10 hPa at 20 C |
| **Accuracy (Class B)** | +/-0.20 hPa at 20 C |
| **Total Accuracy (-40 to +60 C)** | +/-0.15 hPa (Class A) |
| **Long-term Stability** | +/-0.1 hPa/year |
| **Temperature Dependence** | +/-0.1 hPa (500-1100 hPa) |
| **Resolution** | 0.01 hPa (Class A), 0.1 hPa (Class B) |
| **Redundancy** | 1, 2, or 3 BAROCAP sensors |
| **Aviation Modes** | QNH, QFE (height-corrected pressure) |
| **WMO Codes** | Trend and tendency (3-hour history) |
| **Data Storage** | 1-year graphical trend history |
| **Display** | Multilingual graphical |
| **IP Rating** | IP65/IP66 |
| **Housing** | Corrosion-resistant |
| **Mounting** | Wall, DIN rail, or pole |
| **Use Case** | Professional meteorology, aviation altimetry |
| **Price** | ~$1,200 |

---

### 3. Gill WindSonic M - Wind Speed / Direction

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Gill Instruments (UK) |
| **Type** | 2-axis ultrasonic anemometer |
| **Interface** | RS232, RS422, RS485, SDI-12, NMEA 0183 |
| **Wind Speed Range** | 0-60 m/s (216 km/h, 116 knots) |
| **Speed Accuracy** | +/-2% RMSE at 12 m/s |
| **Speed Resolution** | 0.01 m/s (0.02 knots) |
| **Speed Response Time** | 0.25s |
| **Starting Threshold** | 0.01 m/s |
| **Wind Direction Range** | 0-359 degrees (no dead band) |
| **Direction Accuracy** | +/-3 degrees at 12 m/s |
| **Direction Resolution** | 1 degree |
| **Direction Response Time** | 0.25s |
| **Output Rate** | 0.25, 0.5, 1, 2, or 4 Hz |
| **Units** | m/s, knots, mph, kph, ft/min |
| **WMO Compliant** | Yes (gust measurement, rolling average) |
| **Operating Temp** | -40 to +70 C (with heating) |
| **Construction** | Hard-anodized aluminium alloy |
| **IP Rating** | IP66 |
| **Compliance** | BS EN 60945, UL 2218 Class 1 |
| **Hail Resistance** | Class 1 (falling ice) |
| **Salt Mist** | Tested per BS EN 60945 |
| **Power** | 9-30V DC |
| **Current** | <20 mA typical |
| **Weight** | 0.9 kg |
| **Mounting** | 1.75" (44.45 mm) pipe |
| **Use Case** | Aviation wind measurement, exposed environments |
| **Price** | ~$1,000 |

---

### 4. Vaisala PWD22 - Visibility / Fog Detection

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Vaisala (Finland) |
| **Type** | Forward scatter present weather detector |
| **Interface** | RS-232, RS-485 |
| **Operating Principle** | Forward scatter (MOR measurement) |
| **Visibility Range (MOR)** | 10-20,000 m |
| **Calibration Reference** | Transmissometer |
| **Precipitation Types** | 7 types: rain, freezing rain, drizzle, freezing drizzle, sleet, snow, ice pellets |
| **Fog Detection** | Fog, light fog, haze (smoke, sand, dust) |
| **Precipitation Intensity** | Low, moderate, heavy |
| **Detection Sensitivity** | 0.05 mm/h or less (within 10 min) |
| **Sensor Element** | Dual RAINCAP capacitive |
| **Output Codes** | WMO 4680 (SYNOP), 4678 (METAR), NWS |
| **Supported Codes** | 49 different from WMO 4680 |
| **Supply Voltage** | 10-30V DC |
| **Operating Temp** | -40 to +60 C |
| **Optics Protection** | Downward-facing, hood-shielded lenses |
| **Hood Heaters** | Optional (wintry conditions) |
| **IP Rating** | IP65 |
| **Maintenance** | No moving parts, no consumables |
| **Global Installations** | Thousands (airports, ports, roads) |
| **Use Case** | Aviation visibility, fog warning, METAR reporting |
| **Price** | ~$4,500 |

---

### 5. Campbell Scientific CS135 - Cloud Ceiling

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Campbell Scientific |
| **Type** | LIDAR ceilometer |
| **Interface** | RS-232, RS-485 |
| **Technology** | Single-lens LIDAR (905 nm laser) |
| **Cloud Height Range** | 0-10 km |
| **Cloud Layers** | Up to 5 layers |
| **Vertical Visibility** | Yes |
| **Backscatter Profiles** | Raw data available |
| **Overlap** | Low altitude (compact design) |
| **Tilt Capability** | Up to 24 degrees (auto-corrected) |
| **Calibration** | Built-in stratocumulus-based |
| **Clock Verification** | Dual clock comparison |
| **Compliance** | ICAO, CAA (CAP437, CAP670, CAP746) |
| **Mixing Layer Height** | Optional (air quality, KNMI algorithm) |
| **Optical Isolation** | Full (transmitter/receiver) |
| **Sunlight Protection** | Immune to direct sunlight damage |
| **Heater** | Integrated |
| **Blower** | Integrated |
| **Radiation Shield** | Integrated |
| **Filter** | Detector protection from direct sunlight |
| **Operating Temp** | -40 to +60 C |
| **Laser Lifetime** | High MTBF |
| **Use Case** | Aviation cloud ceiling, ICAO compliance |
| **Price** | ~$3,000 |

---

### 6. Vaisala DRD11A - Precipitation Detection

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Vaisala (Finland) |
| **Type** | Capacitive rain detector |
| **Interface** | Analog (ON/OFF + intensity) |
| **Sensing Principle** | RAINCAP thick-layer capacitive |
| **Detection Threshold** | 0.05 cm2 wet surface |
| **Detection Method** | Droplet detection (not signal level) |
| **Intensity Categories** | Low, moderate, heavy (analogue) |
| **Delay Circuitry** | 2-minute interval between drops |
| **Heating** | Internal element to -15 C (+5 F) |
| **Snow Detection** | Via heating element (melting) |
| **Contamination Resistance** | Not affected by reasonable dirt/dust |
| **Coating** | Glass-coated sensing surface |
| **Supply Voltage** | 10-30V DC |
| **Operating Temp** | -40 to +60 C (heated to -15 C) |
| **Mounting** | Support arm (low enough for cleaning) |
| **Maintenance** | Free (no moving parts) |
| **Use Case** | Precipitation detection, rain/snow discrimination |
| **Price** | ~$1,500 |

---

### 7. Apogee SP-110 - Solar Radiation

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Apogee Instruments |
| **Type** | Silicon-cell pyranometer |
| **Spectral Range** | 360-1120 nm |
| **Measurement Range** | 0-2000 W/m2 |
| **Sensitivity** | ~0.06 mV per W/m2 |
| **Cosine Response** | <5% error at 75 deg zenith |
| **Stability** | <2% per year |
| **Response Time** | <1s |
| **Supply Voltage** | 3-5V |
| **Operating Temp** | -40 to +80 C |
| **Use Case** | Solar irradiance, evapotranspiration |
| **Price** | ~$300 |

---

### 8. Boltek LD-250 - Lightning Detection

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Boltek |
| **Type** | RF lightning detector |
| **Interface** | USB, RS-232 |
| **Detection Range** | 0-40 km (close), up to 480 km (distant) |
| **Distance Resolution** | 1 km |
| **Azimuth** | 0-359 degrees |
| **Flash Detection** | Cloud-to-ground, cloud-to-cloud |
| **Signal Processing** | RF emission analysis |
| **Alerts** | Audible + visual |
| **Antenna** | Built-in |
| **Software** | StormTracker (included) |
| **Use Case** | Storm tracking, approach warning |
| **Price** | ~$400 |

---

## Interface Map

```
Campbell Scientific CR1000Xe Data Logger
├── SDI-12 (C1-C4)
│   ├── HMP155 (via RS-485 adapter) - Temp/Humidity
│   └── WindSonic M - Wind Speed/Direction
├── RS-485
│   ├── PTB330 - Barometric Pressure
│   ├── PWD22 - Visibility/Fog
│   └── CS135 - Cloud Ceiling
├── Analog
│   ├── DRD11A - Precipitation
│   └── SP-110 - Solar Radiation
├── RS-232
│   └── LD-250 - Lightning
├── Ethernet
│   └── Network (LoRa/4G/Satellite gateway)
└── MicroSD
    └── Data storage

NVIDIA Jetson Orin Nano
├── Ethernet (from CR1000Xe)
├── USB (serial consoles)
├── GPIO (status LEDs)
└── WiFi (local hotspot for tablets)
```

---

## Power Budget

| Sensor | Active Current | Supply Voltage |
|--------|---------------|----------------|
| HMP155 | <4 mA (RS-485), 150 mA (warmed) | 7-28V DC |
| PTB330 | <100 mA | 10-30V DC |
| WindSonic M | <20 mA | 9-30V DC |
| PWD22 | <50 mA | 10-30V DC |
| CS135 | <15W (with heater) | 12V DC |
| DRD11A | <100 mA (heated) | 10-30V DC |
| SP-110 | <1 mA | 3-5V |
| LD-250 | <200 mA | 12V DC |
| Jetson Orin Nano | 7-25W (TDP) | 5V DC |

**Total system power:** ~50-80W peak, ~20-30W average
**Autonomy:** 7+ days (200Wh battery + 100W solar)

---

## Bill of Materials

| Category | Components | Cost (USD) |
|----------|-----------|------------|
| Meteorological Sensors | HMP155, PTB330, WindSonic M, PWD22, CS135, DRD11A, SP-110, LD-250 | 12,700 |
| Computing | Jetson Orin Nano 8GB, CR1000Xe | 2,249 |
| Communication | LoRa RAK7268, Quectel 4G, RockBLOCK satellite | 700 |
| Power | 100W solar, 200Wh LiFePO4, MPPT | 450 |
| Mechanical | IP67 enclosure, tripod, mounts | 1,000 |
| Development | Tools, testing equipment | 1,000 |
| Miscellaneous | Cables, connectors, shipping | 650 |
| **Total per Unit** | | **18,749** |

**Production cost (100+ units):** $12,000-15,000

---

## Comparison with Commercial AWOS

| Feature | This System | Vaisala AWOS | Military TAMMS |
|---------|------------|--------------|----------------|
| Cost | $18.7k | $150-300k | $80k+ |
| Weight | <50 lbs | N/A (fixed) | 300+ lbs |
| Deployment | <30 min, 1 person | 2-3 days, team | Hours, 2-3 people |
| AI Prediction | Yes (0-30 min) | No | No |
| Portable | Yes | No | Limited |
| Ruggedized | MIL-STD-810H | Outdoor rated | Military spec |
| Power | Solar+battery | AC mains | Generator |
| Connectivity | LoRa/4G/Sat | Ethernet | Legacy radio |

---

## References

1. Vaisala, "HMP155 User Guide (M210912EN-J)," 2026.
2. Vaisala, "PTB330 User Guide (M210855EN-E)," 2026.
3. Gill Instruments, "WindSonic Datasheet (1405-027 Issue 12)," 2025.
4. Vaisala, "PWD Series Datasheet (B210385EN)," 2026.
5. Campbell Scientific, "CS135 LIDAR Ceilometer Technical Description," 2020.
6. Vaisala, "DRD11A Datasheet (B010018EN-C)," 2026.
7. Apogee Instruments, "SP-110 Datasheet," 2024.
8. Boltek, "LD-250 Manual," 2023.
9. NVIDIA, "Jetson Orin Nano Super Datasheet," 2024.
10. Campbell Scientific, "CR1000Xe Product Manual," 2026.
