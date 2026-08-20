# Hardware Wiring Reference — ESP32-S3 Edge AI Weather Node

## Complete GPIO-to-Component Mapping

Based on firmware source code (`firmware/main/main.c`, `docs/reference/PIN_MAP.md`, sensor drivers).

| Module | VCC | GND | Interface | ESP32 GPIO | Pull-up / Level Shift | Notes |
|--------|-----|-----|-----------|------------|----------------------|-------|
| **ESP32-S3-WROOM-1** | 3.3V | GND | — | — | — | Core module, 8MB PSRAM |
| **BME280** | 3.3V | GND | I2C (SDA/SCL) | GPIO 21 / 22 | 4.7kΩ to 3.3V (both) | Addr 0x76 (primary), 0x77 (alt) |
| **LTR-390UV** | 3.3V | GND | I2C (SDA/SCL) | GPIO 21 / 22 | 4.7kΩ to 3.3V (both) | Addr 0x53 |
| **SCD41** | 3.3V | GND | I2C (SDA/SCL) | GPIO 21 / 22 | 4.7kΩ to 3.3V (both) | Addr 0x62 |
| **SGP41** | 3.3V | GND | I2C (SDA/SCL) | GPIO 21 / 22 | 4.7kΩ to 3.3V (both) | Addr 0x59 |
| **AS3935** | 3.3V | GND | I2C (SDA/SCL) | GPIO 21 / 22 | 4.7kΩ to 3.3V (both) | Addr 0x03 |
| **PMS5003** | 5V | GND | UART1 (TX/RX) | GPIO 17 (TX) / 18 (RX) | — | 9600 8N1; separate 5V rail with 470μF cap |
| **SX1276 (RFM95W)** | 3.3V | GND | SPI2_HOST | SCK=10, MOSI=11, MISO=12, CS=13, RST=14, DIO0=5, DIO1=6 | — | 10 MHz SPI Mode 0; manual CS on GPIO 13; DIO0 IRQ |
| **DS18B20** | 3.3V | GND | 1-Wire | GPIO 4 | 4.7kΩ to 3.3V | Parasitic power not used |
| **Anemometer (Wind Speed)** | 5V | GND | ADC2_CH0 | ADC2_CH0 (GPIO 1*) | — | 0-5V → level shift to 3.3V or use voltage divider |
| **Wind Vane (Direction)** | 5V | GND | ADC2_CH1 | ADC2_CH1 (GPIO 2*) | — | 0-5V analog; level shift required |
| **SEN0575 (Rain)** | 3.3V | GND | ADC2_CH2 | ADC2_CH2 (GPIO 3*) | — | Piezo output; 3.3V compatible |
| **MICS-6814 CH1 (CO)** | 5V (heater) / 3.3V (sensor) | GND | ADC2_CH3 | ADC2_CH3 (GPIO 4*) | — | Heater 38mA @ 5V; sensor 3.3V logic |
| **MICS-6814 CH2 (NO₂)** | 5V (heater) / 3.3V (sensor) | GND | ADC2_CH4 | ADC2_CH4 (GPIO 5*) | — | — |
| **MICS-6814 CH3 (NH₃)** | 5V (heater) / 3.3V (sensor) | GND | ADC2_CH5 | ADC2_CH5 (GPIO 6*) | — | — |
| **Battery Monitor** | VBAT (3.0-4.2V) | GND | ADC1_CH3 | ADC1_CH3 (GPIO 4**) | 100kΩ + 100kΩ divider | 2:1 divider measures 0-6.6V → 0-3.3V |

---

## Critical Notes

### ADC Channel Mapping
- ADC2 channels 0-5 are **logical channel numbers**, not physical GPIOs. The actual GPIO pins depend on the ESP32-S3 datasheet Table 4-3 mapping.
- Wi-Fi must be **disabled** (`CONFIG_WIFI_ENABLED=n` in sdkconfig) because ADC2 is shared with Wi-Fi and cannot be used simultaneously.

### Power Supply Requirements
| Rail | Voltage | Current Capability | Components |
|------|---------|-------------------|------------|
| 3.3V | 3.3V | ≥ 500 mA | ESP32-S3, all I2C sensors, SX1276 logic, DS18B20, SEN0575 |
| 5V | 5V | ≥ 300 mA | PMS5003 fan (100 mA), MICS-6814 heater (38 mA × 3 = 114 mA), Anemometer |
| VBAT | 3.0-4.2V | — | 18650 Li-ion via CN3065 solar charger |

### Level Shifting Required
- **Anemometer / Wind Vane**: 5V analog output → must use voltage divider or level shifter to 3.3V before ADC2
- **PMS5003 UART**: 5V logic → ESP32-S3 UART1 is 3.3V tolerant (input-only pins), but TX from ESP32 to PMS5003 RX should use level shifter or series resistor
- **MICS-6814**: Heater requires 5V; sensor signal is 3.3V compatible

### Pull-up Resistors
- **I2C Bus**: 4.7kΩ to 3.3V on both SDA (GPIO 21) and SCL (GPIO 22) — place close to ESP32, not at sensors
- **DS18B20 1-Wire**: 4.7kΩ to 3.3V on DQ (GPIO 4)
- **SX1276 DIO0/DIO1**: Internal pull-up enabled in firmware (GPIO_PULLUP_ENABLE)

### Boot Strapping Pins (Must Not Be Driven Low at Boot)
| GPIO | Function | Constraint |
|------|----------|------------|
| GPIO 0 | Boot mode | Must be LOW for download mode; HIGH/Float for normal boot |
| GPIO 1 | TX0 / USB-JTAG | Used for flashing/debug; do not connect external load |
| GPIO 3 | RX0 / USB-JTAG | Used for flashing/debug; do not connect external load |
| GPIO 45 | — | Not on ESP32-S3 WROOM-1 |
| GPIO 46 | — | Not on ESP32-S3 WROOM-1 |

**Note**: GPIO 4 (DS18B20) is used for 1-Wire. It is NOT a boot strapping pin on ESP32-S3.

### Reserved / Input-Only GPIOs
- GPIO 34-39: Input only (no output driver) — not used in this design
- GPIO 45-46: Not exposed on WROOM-1 module

---

## Wiring Diagram (Text Representation)

```
                              ┌─────────────────────────┐
                              │     ESP32-S3-WROOM-1    │
                              │      (8MB PSRAM)        │
                              └───────────┬─────────────┘
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        │                                 │                                 │
        ▼                                 ▼                                 ▼
   ┌─────────┐                       ┌─────────┐                       ┌─────────┐
   │  I2C0   │                       │  SPI2   │                       │  UART1  │
   │ SDA=21  │                       │ SCK=10  │                       │ TX=17   │
   │ SCL=22  │                       │ MOSI=11 │                       │ RX=18   │
   └────┬────┘                       │ MISO=12 │                       └────┬────┘
        │                            │ CS=13   │                            │
        │                            │ RST=14  │                            │
        │                            │ DIO0=5  │                            │
        │                            │ DIO1=6  │                            │
        │                            └────┬────┘                            │
        │                                 │                                 │
        ▼                                 ▼                                 ▼
┌───────────────────────┐         ┌───────────────┐               ┌───────────────┐
│  I2C Sensor Bus       │         │  SX1276/      │               │  PMS5003      │
│  4.7kΩ pull-ups       │         │  RFM95W LoRa  │               │  Particulate  │
├───────────────────────┤         │  865 MHz      │               │  Matter       │
│ BME280     @ 0x76     │         │  SF7, 125kHz  │               │  9600 8N1     │
│ LTR-390    @ 0x53     │         │  17 dBm       │               │  5V supply    │
│ SCD41      @ 0x62     │         └───────────────┘               └───────────────┘
│ SGP41      @ 0x59     │
│ AS3935     @ 0x03     │
└───────────────────────┘

┌───────────────────────┐
│  1-Wire (GPIO 4)      │
│  4.7kΩ pull-up        │
├───────────────────────┤
│ DS18B20 (enclosure)   │
└───────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    ADC Channels (Analog)                         │
├──────────────────────────────────────────────────────────────────┤
│ ADC2_CH0 (GPIO 1*) → Anemometer Wind Speed   (5V→3.3V divider)  │
│ ADC2_CH1 (GPIO 2*) → Wind Vane Direction      (5V→3.3V divider)  │
│ ADC2_CH2 (GPIO 3*) → SEN0575 Rain Sensor      (3.3V native)     │
│ ADC2_CH3 (GPIO 4*) → MICS-6814 CH1 (CO)       (3.3V native)     │
│ ADC2_CH4 (GPIO 5*) → MICS-6814 CH2 (NO₂)      (3.3V native)     │
│ ADC2_CH5 (GPIO 6*) → MICS-6814 CH3 (NH₃)      (3.3V native)     │
│ ADC1_CH3 (GPIO 4**) → Battery Voltage Divider (2:1, 100k+100k)  │
└──────────────────────────────────────────────────────────────────┘

* ADC2 channel-to-GPIO mapping per ESP32-S3 datasheet Table 4-3
** ADC1_CH3 is fixed to GPIO 4
```

---

## Assembly Checklist

- [ ] ESP32-S3 module soldered with correct orientation
- [ ] 3.3V regulator (≤500 mA) connected to ESP32 VDD and all I2C sensors
- [ ] 5V regulator (≤300 mA) connected to PMS5003, MICS-6814 heater, anemometer
- [ ] CN3065 solar charger → 18650 holder → battery voltage divider (100k+100k) → ADC1_CH3
- [ ] I2C pull-ups (4.7kΩ) on SDA/SCL near ESP32
- [ ] DS18B20 1-Wire pull-up (4.7kΩ) on GPIO 4
- [ ] SX1276 SPI wiring: SCK/MOSI/MISO/CS/RST/DIO0/DIO1
- [ ] SX1276 DIO0 pull-up enabled, antenna connected (868 MHz tuned)
- [ ] PMS5003 UART: ESP32 TX (GPIO 17) → PMS5003 RX (level shift), PMS5003 TX → ESP32 RX (GPIO 18, 3.3V tolerant)
- [ ] Anemometer/Wind Vane: 5V supply, signal through voltage divider to ADC2
- [ ] SEN0575: 3.3V supply, signal to ADC2_CH2
- [ ] MICS-6814: 5V heater supply, 3.3V sensor supply, 3 channels to ADC2_CH3/4/5
- [ ] All sensor addresses verified (I2C scan: 0x76, 0x53, 0x62, 0x59, 0x03)
- [ ] No shorts between 3.3V, 5V, VBAT, GND rails
- [ ] Conformal coating on exposed PCB areas (except antenna, sensor openings)

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-08-11 | 1.0 | Initial wiring table derived from firmware source and PIN_MAP.md |