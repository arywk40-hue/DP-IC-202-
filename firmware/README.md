# ESP32-S3 Firmware

This PlatformIO project compiles the promoted 14-feature edge model for an
ESP32-S3 DevKitC-1. It currently provides a deterministic model smoke test;
sensor drivers and field alert transport are separate follow-up work.

## Requirements

- Python 3.10 or newer
- PlatformIO Core
- ESP32-S3 DevKitC-1 or a compatible ESP32-S3 board

Install PlatformIO:

```bash
python3 -m pip install platformio
```

## Host Tests

```bash
pio test -e native
```

## Build and Flash

```bash
pio run -e esp32-s3-devkitc-1
pio run -e esp32-s3-devkitc-1 --target upload
pio device monitor --baud 115200
```

The smoke firmware prints one JSON prediction every five seconds.

## Test on the ESP32-S3

Connect the board over USB and run:

```bash
pio test -e esp32-s3-devkitc-1
```

The same inference checks run on the target and report through serial.

## Model Contract

The firmware compiles
`ml/generated/model_data_india_26_masked_distilled_edge.h`. The build fails at
compile time if the model no longer has exactly 14 ordered features and four
hazard outputs. Inputs containing NaN or infinity are rejected before
inference.

The hard-coded feature vector in `src/main.cpp` is a smoke-test vector near the
training mean. Replace it with a sensor adapter only after units and feature
derivations match the training contract exactly.

