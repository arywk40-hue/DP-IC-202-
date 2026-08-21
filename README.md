# Edge AI Weather Station — ML Pipeline

On-device hazard classification for a solar-powered environmental monitoring
node: XGBoost trained offline in Python, exported to a plain C header for
inference on an ESP32-S3 (14 derived features → 4 hazard classes: wildfire,
flood, storm, air quality).

This repo now contains **only the ML pipeline** — the firmware, hardware docs,
and papers that used to live alongside it have been removed.

## Repository Structure

```
ml/
├── prepare_dataset.py       # CSV → features + labels
├── train_model.py           # XGBoost training, optional C export
├── convert_to_c.py          # JSON models → C header
├── streamlit_app.py         # Local model demo/inspector
├── requirements.txt
├── model/                   # Trained XGBoost JSON models + stats
│   ├── xgboost_wildfire.json
│   ├── xgboost_flood.json
│   ├── xgboost_storm.json
│   ├── xgboost_air_quality.json
│   ├── feature_names.json
│   ├── normalization.json
│   └── metrics.json
├── dataset/
│   └── weatherHistory.csv   # Szeged/Hungary weather data (original baseline)
├── real_india_data/         # Alternate pipeline: real India weather+AQ data
│   ├── merge_real_dataset.py
│   ├── prepare_dataset_real.py
│   ├── metadata.json
│   ├── model_data.h         # Distinct trained model — not yet promoted
│   └── README.md
├── kriging/
│   └── kriging.py           # Spatial interpolation for multi-node coverage
├── docs/
│   ├── ML_PIPELINE.md       # Training & export guide
│   └── ML_INFERENCE.md      # Model format, inference API
└── generated/
    └── model_data.h         # Auto-generated C header (see note below)
```

## Quick Start

```bash
cd ml/
pip install -r requirements.txt

# Prepare data
python prepare_dataset.py --input dataset/weatherHistory.csv --output data/

# Train and export to C
python train_model.py --data data/ --output model/ --export-c --c-output ./generated/model_data.h
```

See [ml/docs/ML_PIPELINE.md](ml/docs/ML_PIPELINE.md) for the full walkthrough
and [ml/docs/ML_INFERENCE.md](ml/docs/ML_INFERENCE.md) for the generated
header format and inference API.

## Two Datasets, Two Models

- **Baseline** (`ml/dataset/`, `ml/model/`, `ml/generated/`): trained on the
  Szeged/Hungary `weatherHistory.csv` that shipped with the project.
- **Real India data** (`ml/real_india_data/`): a self-contained alternate
  pipeline trained on 543 real Indian weather/air-quality locations
  (Aug–Oct 2023). Its `model_data.h` is a real, distinct trained model — see
  [ml/real_india_data/README.md](ml/real_india_data/README.md) for what's
  real vs. still synthetic in its features, and note it hasn't been promoted
  anywhere yet.

## Author

**Ariyan Bhakat**
