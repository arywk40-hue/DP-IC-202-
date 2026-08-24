# ML Pipeline — Training & Export Guide

## Overview

```
Raw Data → prepare_dataset.py → train_model.py → convert_to_c.py → Firmware Headers
```

| Script | Purpose | Output |
|--------|---------|--------|
| `prepare_dataset.py` | CSV → features + labels | `data/features.csv`, `data/labels.csv` |
| `train_model.py` | Train 4× XGBoost binary classifiers | `model/xgboost_*.json`, `normalization.json` |
| `convert_to_c.py` | JSON → C headers | `model_data.h`, `normalization.h`, `model_metadata.h` |

---

## Quick Start

```bash
cd ../          # from ml/docs/ into ml/
pip install -r requirements.txt

# Prepare real weather data
python prepare_dataset.py --input dataset/weatherHistory.csv --output data/

# Train on real data
python train_model.py --data data/ --output model/ --export-c --c-output ./generated/model_data.h
```

---

## Data Format

### Input CSV (raw weather data)

Expected columns (flexible naming):

| Standard Name | Accepted Aliases |
|---------------|------------------|
| `temperature` | `temp`, `air_temp` |
| `humidity` | `rh`, `relative_humidity` |
| `pressure` | `barometric_pressure`, `bp` |
| `wind_speed` | `wind_kph`, `wspd` |
| `pm25` | `pm2_5`, `pm25_concentration` |
| `co2` | `co2_ppm` |
| `lightning_distance` | `lightning_dist`, `ldist` |

### Prepared Features (`features.csv`)

14 columns in fixed order (must match firmware):

| Index | Feature | Source |
|-------|---------|--------|
| 0 | `temp_current` | Raw |
| 1 | `humidity_current` | Raw |
| 2 | `pressure_current` | Raw |
| 3 | `wind_speed_current` | Raw |
| 3 | `pm25_current` | Raw |
| 5 | `co2_current` | Raw |
| 6 | `lightning_dist_current` | Raw |
| 7 | `temp_humidity_ratio` | temp / max(hum, 1) |
| 8 | `pressure_trend` | 6-sample linear slope |
| 9 | `heat_index` | temp + 0.5×humidity |
| 10 | `dew_point` | temp - (100-hum)/5 |
| 11 | `fire_risk_index` | Heuristic (temp>30, hum<35, wind>5, pm25>40) |
| 12 | `flood_risk_index` | Heuristic (pres<1005, hum>85, wind>8) |
| 13 | `lightning_threat` | max(0, (40-dist)/40) |

### Labels (`labels.csv`)

4 binary columns (one-vs-rest):

| Column | Positive Condition |
|--------|-------------------|
| `wildfire` | temp>30 & hum<35 & wind>5 & pm25>40 |
| `flood` | pres<1000 & hum>85 & wind>8 |
| `storm` | lightning<15 & pres<1005 |
| `air_quality` | pm25>75 \| co2>550 |

---

## Training Details (`train_model.py`)

### XGBoost Parameters (ESP32-optimized)

```python
params = {
    'objective': 'binary:logistic',
    'eval_metric': 'logloss',
    'max_depth': 4,           # Shallow = fast inference
    'min_child_weight': 2,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'learning_rate': 0.1,
    'gamma': 0.1,
    'reg_alpha': 0.1,
    'reg_lambda': 1.0,
    'tree_method': 'hist',    # Fast training
    'seed': 42,
}
num_boost_round = 16          # 16 trees/class = ~64 trees total
early_stopping_rounds = 5
```

### Data Splits

- Train: 72%
- Validation: 8% (early stopping)
- Test: 20% (final evaluation)

### Normalization

Z-score computed on **training set only**:

```python
mean = X_train.mean(axis=0)
std = X_train.std(axis=0)
std[std == 0] = 1.0
X_norm = (X - mean) / std
```

Saved to `model/normalization.json` for `convert_to_c.py`.

---

## C Export (`convert_to_c.py`)

### Parsing XGBoost JSON

- Loads `xgboost_{class}.json` via `xgb.Booster`
- `model.get_dump(dump_format='json')` → parse tree structure
- Converts to flat node arrays (pre-order traversal)

### Generated Headers

#### `model_data.h` (~200 KB)

```c
#define NUM_CLASSES 4
#define NUM_FEATURES 14
#define MAX_NODES_PER_TREE 32

#define WILDFIRE_NUM_TREES 16
#define FLOOD_NUM_TREES 16
// ...

typedef struct {
    int8_t feature_idx;   // -1 = leaf
    float threshold;
    int16_t left_child;
    int16_t right_child;
    float leaf_value;
} xgb_node_t;

typedef struct {
    uint8_t num_nodes;
    xgb_node_t nodes[MAX_NODES_PER_TREE];
} xgb_tree_t;

// Tree arrays per class
static const xgb_tree_t WILDFIRE_TREE_0 = { ... };
static const xgb_tree_t *WILDFIRE_TREES[16] = { ... };

// Normalization constants (from training)
static const float NORM_MEAN[14] = { ... };
static const float NORM_STD[14]  = { ... };

// Inference functions (inline for speed)
static inline void normalize_features(float *f, int n);
static inline float xgb_tree_inference(const xgb_tree_t *t, const float *f);
static inline void xgb_model_inference(
    const float *raw,
    float *out_wildfire, float *out_flood,
    float *out_storm, float *out_air_quality
);
```

#### `normalization.h`

```c
static const float NORM_MEAN[14] = { ... };
static const float NORM_STD[14]  = { ... };

static inline void normalize_features(float *features, int num_features) {
    for (int i = 0; i < num_features && i < 14; i++) {
        features[i] = (features[i] - NORM_MEAN[i]) / NORM_STD[i];
    }
}
```

#### `model_metadata.h`

```c
static const char *FEATURE_NAMES[14] = { "temp_current", ... };
static const char *HAZARD_CLASS_NAMES[4] = { "wildfire", "flood", "storm", "air_quality" };
static const float ALERT_THRESHOLDS[4] = { 0.70f, 0.70f, 0.75f, 0.65f };
```

---

## Firmware Integration

### In `ml.c`

```c
#include "model_data.h"
#include "normalization.h"
#include "model_metadata.h"

esp_err_t ml_predict(const float *features, uint8_t class_id, float *output) {
    // 1. Copy raw features
    float norm[ML_FEATURE_COUNT];
    for (int i = 0; i < ML_FEATURE_COUNT; i++) norm[i] = features[i];
    
    // 2. Normalize (uses generated constants)
    normalize_features(norm, ML_FEATURE_COUNT);
    
    // 3. Run full model inference (all 4 classes)
    float wf, fl, st, aq;
    xgb_model_inference(norm, &wf, &fl, &st, &aq);
    
    // 4. Return requested class
    switch (class_id) {
        case 0: *output = wf; break;
        case 1: *output = fl; break;
        case 2: *output = st; break;
        case 3: *output = aq; break;
    }
    return ESP_OK;
}
```

### In `main.c` (sensor_ml_task)

```c
float features[ML_FEATURE_COUNT];
compute_derived_features(&reading, features);

float norm[ML_FEATURE_COUNT];
ml_normalize(features, norm);

for (int cls = 0; cls < NUM_HAZARD_CLASSES; cls++) {
    float raw_out;
    ml_predict(norm, cls, &raw_out);
    float conf = ml_confidence(raw_out);
    
    if (conf >= hazard_thresholds[cls]) {
        queue_alert(cls, conf, &reading);
    }
}
```

---

## Reproducing Results

### Fixed Seed

All randomness uses `seed=42`:
- Data generation
- Train/val/test split
- XGBoost training

### Exact Match Requirements

For firmware inference to match Python exactly:

1. **Feature order** must be identical (see table above)
2. **Normalization** uses training-set mean/std (not full dataset)
3. **Tree structure** parsed without modification
4. **Sigmoid** applied to sum of tree outputs: `1/(1+exp(-sum))`
5. **Float32** precision throughout

### Verification

```bash
# In Python
python -c "
import xgboost as xgb
import numpy as np
model = xgb.Booster()
model.load_model('model/xgboost_wildfire.json')
dtest = xgb.DMatrix(X_test[:5])
print('Python:', model.predict(dtest))
"

# In firmware (add test to ml.c)
float test_features[14] = { ... };
ml_normalize(test_features, norm);
ml_predict(norm, 0, &out);
print('Firmware:', out);
# Should match within 1e-5
```

---

## Performance Targets

| Metric | Target | Typical |
|--------|--------|---------|
| Inference time (4 classes) | < 100 μs | ~50 μs |
| Flash usage | < 64 KB | ~45 KB |
| RAM (runtime) | < 4 KB | ~2 KB |
| Wildfire F1 | > 0.90 | 0.95+ |
| Flood F1 | > 0.85 | 0.90+ |
| Storm F1 | > 0.90 | 0.94+ |
| Air Quality F1 | > 0.90 | 0.96+ |

---

## Adding Real Data

1. Place CSV in `data/raw/weather_*.csv`
2. Run `prepare_dataset.py --input data/raw/ --output data/`
3. Verify label distribution: `python -c "import pandas as pd; df=pd.read_csv('data/labels.csv'); print(df.sum())"`
4. Retrain: `train_model.py --data data/ --output model/ --export-c ...`
5. Flash firmware and field-test

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: xgboost` | `pip install xgboost` |
| Feature count mismatch | Check `FEATURE_NAMES` order matches firmware |
| Accuracy too low | Increase `num_boost_round`, check label quality |
| Firmware inference differs | Verify `NORM_MEAN/STD` match `normalization.json` exactly |
| Export fails | Ensure `normalization.json` exists in model dir |