# Edge AI Environmental Hazard Node

An offline XGBoost training pipeline and an ESP32-S3 inference target for four
environmental hazard signals: wildfire, flood, storm, and air quality.

The edge contract uses 14 ordered features and exports four binary XGBoost
heads as a plain C header. The repository keeps offline ML work and board
firmware in separate, testable areas.

## Repository Layout

| Path | Purpose |
|---|---|
| `ml/` | Data preparation, training, evaluation, distillation, and C export |
| `ml/generated/` | Generated edge-model headers |
| `firmware/` | PlatformIO application for ESP32-S3 |
| `tests/model/` | Host compiler smoke test for the promoted C model |
| `docs/REPOSITORY_STRUCTURE.md` | Boundaries and model promotion gates |

See [ml/README.md](ml/README.md) for the experiment layout and
[firmware/README.md](firmware/README.md) for build, flash, and board-test
instructions.

## Current Edge Release

The firmware consumes:

```text
ml/generated/model_data_india_26_masked_distilled_edge.h
```

This model passed the existing Python/C parity check. Several independently
labelled India hazard heads remain research-only because verified event
coverage and geographic validation are still limited. A successful firmware
build is not evidence that the model is ready for safety-critical deployment.

## Quick Checks

### ML export contract

```bash
cc -std=c99 -Iml/generated tests/model/test_model_smoke.c -lm -o /tmp/model_smoke
/tmp/model_smoke
```

### Firmware host tests

```bash
cd firmware
python3 -m pip install platformio
pio test -e native
```

### ESP32-S3 build

```bash
cd firmware
pio run -e esp32-s3-devkitc-1
```

### Flash and monitor

```bash
pio run -e esp32-s3-devkitc-1 --target upload
pio device monitor --baud 115200
```

The current board application runs a deterministic inference smoke test and
prints JSON probabilities over serial. Real sensor drivers are not wired into
this application yet.

## ML Pipeline

```bash
cd ml
python3 -m pip install -r requirements.txt
python3 prepare_dataset.py --input dataset/weatherHistory.csv --output data
python3 train_model.py --data data --output model --export-c \
  --c-output generated/model_data.h
```

The India pipeline and its evidence are documented in
[ml/docs/INDIA_WEATHER_ARCHITECTURE.md](ml/docs/INDIA_WEATHER_ARCHITECTURE.md).

## Author

**Ariyan Bhakat**

