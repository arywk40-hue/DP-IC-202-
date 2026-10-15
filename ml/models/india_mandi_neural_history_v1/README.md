# India/Mandi neural history forecast candidates

Two actual saved residual neural networks, trained on the existing Mandi-location
IFS/CAMS modeled data. Six physical channels, 66 causal history features, six
numerical +6h endpoints. They do not predict hazard classes.

- `residual_mlp_32`: 66 → 32 → 6, 2,342 trainable parameters.
- `residual_mlp_64_32`: 66 → 64 → 32 → 6, 6,566 trainable parameters.

Each folder contains `model.json` (ordered features, target order, source/config
checksums, chronological validation choices and training trace) and `weights.npz`
(weights, biases, training-only scaling and persistence blends). Use the verified
loader in `ml/india_mandi/neural.py`; archives load with `allow_pickle=False`.

Training/validation/test: 22,602 / 738 / 954 complete-history rows; six-hour label
purge at cutoffs. Test dates have been exposed in prior project work. Results are
retrospective modeled evidence, not new field accuracy. No synthetic data or
Chinese weights were used. No live online-learning worker or ESP32 export is
provided by these research artifacts. Existing deployed models are unchanged.

Full architecture/status: `docs/FORECAST_MODEL_IMPROVEMENT.md`.
Results: `reports/india_mandi_neural_history_v1/REPORT.md`.
Attribution: Open-Meteo, ECMWF IFS, Copernicus CAMS global.
