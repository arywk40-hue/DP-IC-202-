# Model index

The active gateway model is **`india_mandi_tabular_v2`**. Start there.

| Directory | Role | Training/evidence |
| --- | --- | --- |
| `india_mandi_tabular_v2` | Active expanded-data LightGBM/MLP/retained-hybrid ensemble | 35,520 Mandi modeled positions; delayed-label learner is separate shadow state |
| `india_mandi_hybrid_6h_v1` | Retained v1 baseline and rollback | Validation-selected prediction blend; no new fitting on the test set |
| `india_mandi_neural_history_v1` | MLP32 and MLP64→32 components | Frozen six-channel Mandi IFS/CAMS modeled history |
| `india_mandi_modeled_6h_v1` | History XGBoost/ridge components and compact baseline | Same frozen Mandi modeled source; compact C export is separate |
| `india_cpcb_5sensor_6h`, `india_cpcb_pm_6h` | Retained reduced-input Indian comparisons | CPCB secondary observations; not complete six-channel Mandi validation |
| `india_sensor_v1` | Retained Indian measurement-threshold research | NOAA weather; no active PM observations |
| `uci_beijing_*` | Historical foreign/rule comparisons only | Beijing/UCI; excluded from current Mandi accuracy evaluation |

Neural weights/biases and scalers are in NPZ files; tree heads use UBJ; ridge
coefficients/normalization use NPZ. The active `profile.json` records their paths
and SHA-256 identities; `ensemble_weights.json` records per-target coefficients.
No raw training CSV is needed for gateway inference.

Do not rename component files or refresh hashes to hide a changed artifact.
`configs/model_catalog.json` is retained byte-for-byte as part of frozen C export
verification; the active hybrid has its own profile/configuration. New training
requires a new version, provenance, chronological selection and evaluation.

See [current Mandi results](../../reports/submission/2026-10-21/REPORT.md) and
[features and limitations](../../docs/FEATURES.md). None of these numerical
models is a validated cloudburst/flood/landslide probability model.

Current sensor-pattern classifier: [`himachal_sensor_patterns_v1`](himachal_sensor_patterns_v1/README.md), a synthetic-trained ten-label LightGBM/MLP blend. It classifies current patterns, not future events or calibrated hazard probabilities. It is separate from the v2 numerical forecaster.
