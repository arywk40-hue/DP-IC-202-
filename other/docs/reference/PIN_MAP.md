# ESP32-S3 Pin Map — Edge AI Weather Node

## GPIO Assignment Summary

| GPIO | Function | Interface | Component | Notes |
|------|----------|-----------|-----------|-------|
| 0 | — | — | — | Boot strapping (keep low at boot) |
| 1 | — | — | — | TX0 (USB-JTAG) |
| 2 | — | — | — | — |
| 3 | — | — | — | — |
| 4 | DS18B20 | 1-Wire | Enclosure temp | Pull-up 4.7kΩ |
| 5 | DIO0 | GPIO (input) | SX1276 IRQ | RX_DONE interrupt |
| 6 | DIO1 | GPIO (input) | SX1276 IRQ | Optional |
| 7 | — | — | — | — |
| 8 | — | — | — | — |
| 9 | — | — | — | — |
| 10 | SCLK | SPI | SX1276 | SPI2_HOST |
| 11 | MOSI | SPI | SX1276 | SPI2_HOST |
| 12 | MISO | SPI | SX1276 | SPI2_HOST |
| 13 | CS | SPI | SX1276 | SPI2_HOST |
| 14 | RST | GPIO (output) | SX1276 | Active low reset |
| 15 | — | — | — | — |
| 16 | — | — | — | — |
| 17 | TX | UART1 | PMS5003 | 9600 8N1 |
| 18 | RX | UART1 | PMS5003 | 9600 8N1 |
| 19 | — | — | — | — |
| 20 | — | — | — | — |
| 21 | SDA | I2C0 | BME280, SCD41, SGP41, LTR390, AS3935 | 4.7kΩ pull-ups |
| 22 | SCL | I2C0 | BME280, SCD41, SGP41, LTR390, AS3935 | 4.7kΩ pull-ups |
| 23 | — | — | — | — |
| 24 | — | — | — | — |
| 25 | — | — | — | — |
| 26 | — | — | — | — |
| 27 | — | — | — | — |
| 28 | — | — | — | — |
| 29 | — | — | — | — |
| 30 | — | — | — | — |
| 31 | — | — | — | — |
| 32 | — | — | — | — |
| 33 | — | — | — | — |
| 34 | — | — | — | Input only |
| 35 | — | — | — | Input only |
| 36 | — | — | — | Input only |
| 37 | — | — | — | Input only |
| 38 | — | — | — | Input only |
| 39 | — | — | — | Input only |

---

## ADC Channels

| ADC | Channel | GPIO | Function | Component |
|-----|---------|------|----------|-----------|
| ADC2 | 0 | GPIO 1* | Wind speed | Anemometer |
| ADC2 | 1 | GPIO 2* | Wind direction | Wind vane |
| ADC2 | 2 | GPIO 3* | Rain (piezo) | SEN0575 |
| ADC2 | 3 | GPIO 4* | Gas CO | MICS-6814 CH1 |
| ADC2 | 4 | GPIO 5* | Gas NO₂ | MICS-6814 CH2 |
| ADC2 | 5 | GPIO 6* | Gas NH₃ | MICS-6814 CH3 |
| ADC1 | 3 | GPIO 4** | Battery voltage | Voltage divider (2:1) |

> **Note**: ADC2 channels conflict with Wi-Fi. Wi-Fi is disabled in `sdkconfig.defaults`, so ADC2 is fully available.
> 
> *GPIO numbers for ADC2 channels are logical channel numbers, not physical GPIOs. See ESP32-S3 datasheet Table 4-3 for ADC2 channel-to-GPIO mapping. The actual GPIO pins used for ADC2 inputs depend on the board layout.
> 
> **Battery uses ADC1_CH3 (GPIO 4) which does not conflict with Wi-Fi.

### ADC Configuration

```c
// All ADC2 channels
adc2_config_channel_atten(ADC2_CHANNEL_0, ADC_ATTEN_DB_12);  // Wind speed
adc2_config_channel_atten(ADC2_CHANNEL_1, ADC_ATTEN_DB_12);  // Wind dir
adc2_config_channel_atten(ADC2_CHANNEL_2, ADC_ATTEN_DB_12);  // Rain
adc2_config_channel_atten(ADC2_CHANNEL_3, ADC_ATTEN_DB_12);  // MICS CO
adc2_config_channel_atten(ADC2_CHANNEL_4, ADC_ATTEN_DB_12);  // MICS NO2
adc2_config_channel_atten(ADC2_CHANNEL_5, ADC_ATTEN_DB_12);  // MICS NH3

// ADC1 for battery
adc1_config_width(ADC_WIDTH_BIT_12);
adc1_config_channel_atten(ADC1_CHANNEL_3, ADC_ATTEN_DB_12);  // Battery
```

---

## I2C Bus (I2C0)

| Device | Address (7-bit) | Address (8-bit) | GPIO (SDA/SCL) |
|--------|-----------------|-----------------|----------------|
| BME280 | 0x76 (primary) / 0x77 | 0xEC / 0xEE | 21 / 22 |
| LTR-390UV | 0x53 | 0xA6 | 21 / 22 |
| SCD41 | 0x62 | 0xC4 | 21 / 22 |
| SGP41 | 0x59 | 0xB2 | 21 / 22 |
| AS3935 | 0x03 | 0x06 | 21 / 22 |

**Bus speed**: 400 kHz (Fast Mode)
**Pull-ups**: 4.7 kΩ to 3.3V on both SDA and SCL

---

## SPI Bus (SPI2_HOST)

| Signal | GPIO | SX1276 Pin |
|--------|------|------------|
| SCLK | 10 | SCK |
| MOSI | 11 | MOSI |
| MISO | 12 | MISO |
| CS | 13 | NSS |
| RST | 14 | RST (output, active low) |
| DIO0 | 5 | DIO0 (input, IRQ) |
| DIO1 | 6 | DIO1 (input, optional) |

**SPI Mode**: 0 (CPOL=0, CPHA=0)
**Clock**: 10 MHz
**CS Control**: Manual via GPIO 13

---

## UART (UART1)

| Signal | GPIO | PMS5003 Pin |
|--------|------|-------------|
| TX | 17 | RX (sensor receives) |
| RX | 18 | TX (sensor transmits) |

**Baud**: 9600, 8N1, no flow control

---

## 1-Wire

| Signal | GPIO | DS18B20 Pin |
|--------|------|-------------|
| DQ | 4 | DQ (with 4.7kΩ pull-up to 3.3V) |

---

## Power Supply Notes

| Rail | Voltage | Components |
|------|---------|------------|
| 3.3V | 3.3V | ESP32-S3, all I2C sensors, SX1276 logic |
| 5V | 5V | PMS5003 (fan), MICS-6814 heater, anemometer |
| VBAT | 3.0-4.2V | 18650 Li-ion (via CN3065 solar charger) |

**Battery Monitor**: Voltage divider (2:1) on ADC1_CH3 (GPIO 4)
- 100 kΩ + 100 kΩ = 2:1 divider
- Measures 0-6.6V → 0-3.3V ADC range
- 18650 range: 3.0V (empty) to 4.2V (full)

---

## Pin Conflicts & Resolutions

| Conflict | Resolution |
|----------|------------|
| ADC2 vs Wi-Fi | Wi-Fi disabled in sdkconfig |
| SPI CS vs GPIO | Manual CS control (GPIO 13) |
| UART1 vs Flash | UART1 pins not used by flash on ESP32-S3 |
| I2C multiple devices | All on same bus, different addresses |

---

## Board Layout Recommendations

1. **LoRa antenna**: Keep GPIO 5/6 (DIO0/1) traces short; antenna matching network per RFM95W datasheet
2. **I2C pull-ups**: Place 4.7kΩ close to ESP32, not at sensors
3. **ADC traces**: Keep analog traces away from SPI/UART switching lines
4. **Battery divider**: Place resistors close to ADC pin; add 0.1μF to ground
5. **PMS5003**: Separate 5V supply with 470μF capacitor near sensor
6. **MICS-6814**: Heater draws ~38mA at 5V; ensure 5V regulator can handle peak

---

## Firmware Pin Definitions (`main.c`)

```c
// I2C
#define I2C_MASTER_PORT      I2C_NUM_0
#define I2C_MASTER_SDA_IO    21
#define I2C_MASTER_SCL_IO    22
#define I2C_MASTER_FREQ_HZ   400000

// SPI (LoRa)
#define SPI_HOST             SPI2_HOST
#define SPI_MOSI_IO          11
#define SPI_MISO_IO          12
#define SPI_SCLK_IO          10
#define SPI_CS_IO            13
#define SPI_LORA_RST_IO      14
#define SPI_LORA_DIO0_IO     5
#define SPI_LORA_DIO1_IO     6

// UART (PMS5003)
#define UART_PORT            UART_NUM_1
#define UART_TXD_IO          17
#define UART_RXD_IO          18

// 1-Wire (DS18B20)
#define DS18B20_GPIO         4

// ADC2 channels (logical)
#define ADC_CH_WIND_SPEED       ADC2_CHANNEL_0
#define ADC_CH_WIND_DIR         ADC2_CHANNEL_1
#define ADC_CH_RAIN             ADC2_CHANNEL_2
#define ADC_CH_MICS_CO          ADC2_CHANNEL_3
#define ADC_CH_MICS_NO2         ADC2_CHANNEL_4
#define ADC_CH_MICS_NH3         ADC2_CHANNEL_5

// ADC1 channel
#define ADC_CH_BATTERY          ADC1_CHANNEL_3
```

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-12 | 1.0 | Initial pin map for 2-node prototype |