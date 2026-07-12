# Sensor Reference Guide - IIT Mandi Low-Cost Implementation

ESP32-S3 based Edge AI node with off-the-shelf breakout modules.

**Target Cost:** INR 19,055 (~$230) per node

---

## Sensor Array (12 Parameters)

### 1. Bosch BME280 - Temperature / Humidity / Pressure

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Bosch Sensortec |
| **Type** | Combined humidity, temperature, barometric pressure |
| **Interface** | I2C (0x76 or 0x77) |
| **Temperature Range** | -40 to +85 C |
| **Temperature Accuracy** | +/-1.0 C (0-65 C) |
| **Humidity Range** | 0-100% RH |
| **Humidity Accuracy** | +/-3% RH |
| **Pressure Range** | 300-1100 hPa |
| **Pressure Accuracy** | +/-1.0 hPa |
| **Resolution** | 0.01 C, 0.008% RH, 0.18 Pa |
| **Response Time** | 1s (humidity) |
| **Supply Voltage** | 1.71-3.6V |
| **Current** | 3.6 uA @ 1 Hz |
| **Package** | 2.5 x 2.5 mm LGA |
| **Use Case** | Core meteorological baseline |
| **Price** | ~INR 350 |

---

### 2. SparkFun Weather Meter Kit - Wind Speed / Direction

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | SparkFun (DAVIS Instruments components) |
| **Type** | Cup anemometer + wind vane |
| **Interface** | Analog/Digital |
| **Wind Speed Range** | 0-89 mph (0-40 m/s) |
| **Wind Speed Accuracy** | +/-1 mph |
| **Wind Direction** | 0-360 degrees |
| **Direction Resolution** | 16 directions (22.5 deg) |
| **Starting Threshold** | 1 mph |
| **Supply Voltage** | 5-12V |
| **Use Case** | Wind speed and direction measurement |
| **Price** | ~INR 2,500 |

---

### 3. DFRobot SEN0575 - Precipitation (Piezoelectric)

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | DFRobot |
| **Type** | Piezoelectric acoustic rain sensor |
| **Interface** | Analog |
| **Detection** | Droplet impact via acoustic sensing |
| **Advantage** | No leveling required (vs tipping bucket) |
| **Rain Intensity** | Light / Moderate / Heavy categories |
| **Supply Voltage** | 3.3-5V |
| **Use Case** | Precipitation detection and intensity |
| **Price** | ~INR 500 |

---

### 4. LTR-390UV - UV Index

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Lite-On (ams OSRAM) |
| **Type** | UV + Ambient light sensor |
| **Interface** | I2C (0x53) |
| **UV Range** | 0-22+ UV Index |
| **UV Resolution** | 0.06 UV Index |
| **Light Range** | 0.01-64k lux |
| **Supply Voltage** | 2.7-3.6V |
| **Current** | 70 uA active |
| **Use Case** | UV Index measurement |
| **Price** | ~INR 200 |

---

### 5. Plantower PMS5003 - Particulate Matter (PM2.5 / PM10)

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Plantower |
| **Type** | Laser scattering particulate sensor |
| **Interface** | UART (9600 baud) |
| **Particles** | PM1.0, PM2.5, PM10 |
| **Range** | 0-500 ug/m3 |
| **Resolution** | 1 ug/m3 |
| **Laser** | 780nm semiconductor |
| **Fan** | Internal micro-fan |
| **Supply Voltage** | 4.5-5.5V |
| **Current** | 100mA (fan on) |
| **Use Case** | Wildfire smoke, air quality |
| **Price** | ~INR 3,000 |

---

### 6. Sensirion SCD41 - CO2 (True NDIR)

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Sensirion |
| **Type** | Photoacoustic NDIR CO2 sensor |
| **Interface** | I2C (0x62) |
| **CO2 Range** | 400-5000 ppm |
| **CO2 Accuracy** | +/- (40 ppm + 5% of reading) |
| **Response Time** | 30s (T63) |
| **Supply Voltage** | 2.0-5.5V |
| **Current** | 17mA (avg) |
| **Package** | 10 x 10 x 7 mm |
| **Use Case** | True CO2 (not equivalent) |
| **Price** | ~INR 3,500 |

---

### 7. Sensirion SGP41 - VOC / NOx

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Sensirion |
| **Type** | Metal-oxide multi-gas sensor |
| **Interface** | I2C (0x59) |
| **VOC Range** | 0-1000 ppm (ethanol equiv) |
| **NOx Range** | 0-1000 (NO2 equiv) |
| **Raw Signal** | 16-bit VOC + NOx index |
| **Supply Voltage** | 1.8-5.5V |
| **Current** | 45mA (heater active) |
| **Use Case** | Air quality, combustion detection |
| **Price** | ~INR 2,000 |

---

### 8. MICS-6814 - Multi-Gas (CO, NO2, NH3)

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | SGX Sensortech (MiCS) |
| **Type** | Metal-oxide semiconductor gas sensor |
| **Interface** | Analog (3 channels) |
| **Gases Detected** | CO, NO2, NH3 (3 separate outputs) |
| **CO Range** | 1-1000 ppm |
| **NO2 Range** | 0.05-10 ppm |
| **NH3 Range** | 1-500 ppm |
| **Heater Resistance** | 33 ohm |
| **Supply Voltage** | 5V (heater), 3.3V (sensor) |
| **Response Time** | <30s |
| **Use Case** | Multi-gas hazard detection |
| **Price** | ~INR 500 |

---

### 9. AS3935 - Lightning Detection

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | ams (Austria Micro Systems) |
| **Type** | Lightning sensor (RF analysis) |
| **Interface** | I2C (0x03) or SPI |
| **Detection Range** | 1-40 km |
| **Distance Resolution** | 1 km steps |
| **Lightning Count** | 0-15 events |
| **Frequency Range** | 1-120 kHz (LF) |
| **Antenna** | Short wire (5-10 cm) |
| **Supply Voltage** | 2.4-5.5V |
| **Current** | 180uA (standby) |
| **Use Case** | Storm approach warning |
| **Price** | ~INR 800 |

---

### 10. DS18B20 - Enclosure Temperature

| Parameter | Value |
|-----------|-------|
| **Manufacturer** | Maxim Integrated |
| **Type** | Digital thermometer |
| **Interface** | 1-Wire |
| **Range** | -55 to +125 C |
| **Accuracy** | +/-0.5 C (-10 to +85 C) |
| **Resolution** | 9-12 bit configurable |
| **Supply Voltage** | 3.0-5.5V (or parasite power) |
| **Current** | 1mA (active) |
| **Use Case** | Internal enclosure temp, water ingress detection |
| **Price** | ~INR 100 |

---

### 11. ESP32-S3 - Battery Voltage Monitoring

| Parameter | Value |
|-----------|-------|
| **Method** | Onboard ADC with voltage divider |
| **ADC** | 12-bit SAR (0-3.3V) |
| **Divider Ratio** | 2:1 (measures 0-6.6V) |
| **Resolution** | ~1.6 mV per step |
| **Use Case** | 18650 cell voltage monitoring (3.0-4.2V) |
| **Price** | Included in ESP32-S3 |

---

## Interface Map

```
ESP32-S3 GPIO
├── I2C Bus (SDA/SCL)
│   ├── BME280 (0x76) - Temp/Hum/Pressure
│   ├── LTR-390 (0x53) - UV Index
│   ├── SCD41 (0x62) - CO2
│   ├── SGP41 (0x59) - VOC/NOx
│   └── AS3935 (0x03) - Lightning
├── UART
│   └── PMS5003 (RX/TX) - Particulate Matter
├── SPI
│   └── RFM95W SX1276 - LoRa Radio
├── 1-Wire
│   └── DS18B20 - Enclosure Temp
├── Analog (ADC)
│   ├── SEN0575 - Precipitation
│   ├── MICS-6814 CH1 - CO
│   ├── MICS-6814 CH2 - NO2
│   ├── MICS-6814 CH3 - NH3
│   ├── Weather Meter - Wind Speed
│   ├── Weather Meter - Wind Direction
│   └── Voltage Divider - Battery
└── Digital
    └── Weather Meter - Wind Direction (digital)
```

---

## Power Budget

| Sensor | Active Current | Sleep Current | Duty Cycle |
|--------|---------------|---------------|------------|
| BME280 | 3.6 uA | 0.1 uA | Continuous |
| PMS5003 | 100 mA | <20 uA | 1 min/hour |
| SCD41 | 17 mA | 1 uA | 1 min/hour |
| SGP41 | 45 mA | 56 nA | Continuous |
| MICS-6814 | 38 mA | 0.1 uA | Continuous |
| AS3935 | 180 uA | 1 uA | Continuous |
| DS18B20 | 1 mA | 750 nA | Every 30s |
| RFM95W | 120 mA (TX) | 1 uA | Event-driven |
| ESP32-S3 | 80 mA (active) | 10 uA | ULP + wake |

**Estimated battery life:** 5-7 days with 18650 cell + 5W solar

---

## Bill of Materials

| Category | Components | Cost (INR) |
|----------|-----------|------------|
| Compute & Radio | ESP32-S3 WROOM-1, RFM95W SX1276, passives | 1,430 |
| Core Meteorological | BME280, Weather Meter Kit, DS18B20, SEN0575, LTR390 | 3,350 |
| Particulate & Gases | PMS5003, SGP41, MICS-6814, SCD41 | 9,055 |
| Specialized Sensing | AS3935 | 935 |
| Power Architecture | 18650 cell, 5W solar panel, CN3065 | 2,380 |
| Fabrication | PCB (5x batch), PETG, conformal coating | 1,905 |
| **Total per Node** | | **19,055** |

**Baseline (no gas sensors):** INR 6,600 (remove SCD41, SGP41, MICS-6814)

---

## References

1. Bosch Sensortec, "BME280 Datasheet," 2020.
2. Espressif Systems, "ESP32-S3 Datasheet," 2023.
3. Plantower, "PMS5003 Datasheet," 2016.
4. Sensirion, "SCD41 Datasheet," 2021.
5. Sensirion, "SGP41 Datasheet," 2021.
6. ams, "AS3935 Datasheet," 2018.
7. Maxim Integrated, "DS18B20 Datasheet," 2019.
8. Semtech, "SX1276 Datasheet," 2020.
9. Nair, A.P., "Decentralized Edge AI Environmental Hazard Network," IIT Mandi, 2026.
