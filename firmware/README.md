# INDRA ESP32-S3 Firmware

INDRA is a sensor-only weather node. It has no CO2, lightning, rain, or wind-direction sensor, and never replaces unavailable data with zero or generated values.

| Module | Interface | ESP32-S3 pins |
| --- | --- | --- |
| BME280, INA219, DS3231 | shared I2C | SDA GPIO8, SCL GPIO9 |
| PMS7003 | UART1 | RX GPIO17, TX GPIO18 |
| Neo-M8N | UART2 | RX GPIO15, TX GPIO16 |
| 600-PPR encoder | interrupt | GPIO4 |

Pins, sampling, and wind calibration live in `lib/IndraSensors/src/BoardConfig.h`. Cross TX/RX on both UARTs and calibrate `kWindMetersPerRevolution` against the installed rotor.

```bash
python3 -m pip install platformio
pio test -d firmware -e native
pio run -d firmware -e esp32-s3-devkitc-1
pio test -d firmware -e esp32-s3-devkitc-1
pio run -d firmware -e esp32-s3-devkitc-1 --target upload
pio device monitor -d firmware --baud 115200
```

Serial emits a JSON record every five seconds. The firmware reports model status `NOT_READY`: the existing promoted model needs CO2 and lightning, while no independently validated real-data `sensor_only_v1` model is bundled.
