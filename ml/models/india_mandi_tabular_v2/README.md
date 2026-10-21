# Active Mandi tabular ensemble v2

Default gateway profile: `india_mandi_tabular_v2`. Numerical six-channel +6h model,
not a hazard classifier. See [pipeline guide](../../../docs/MANDI_V2_PIPELINE.md)
and [results](../../../reports/mandi_pipeline_v2/REPORT.md).

- Inputs: 25 consecutive hourly snapshots of the six channels; 66 causal features.
- Training source: 35,520 Mandi API/model positions, October 2022–October 2026;
  33,570 training rows before August, 738 validation rows, 1,170 test pairs.
- Components: expanded-data LightGBM residual heads, expanded residual MLP,
  retained v1 hybrid and persistence. Validation selects each target’s convex blend.
- `lightgbm/*.txt`: six tree heads in LightGBM text format.
- `neural/weights.npz`: neural weights/biases, normalization and residual weights.
- `neural/model.json`: architecture, source, feature order and artifact checksum.
- `ensemble_weights.json`: four nonnegative endpoint coefficients per target.
- `online_scaler.npz`: frozen training scalers for the separate SGD shadow learner.
- `profile.json`: runtime contract, hashes and legacy-profile identity.

Keep the retained v1 component model directories when deploying; this profile
references their checksummed predictor. Inference requires LightGBM 4.6.0 and
`requirements-dashboard.txt`, not raw data, PyTorch or TabPFN. No executable pickle
is loaded. Missing history uses explicit persistence; missing current inputs are
unavailable. All original learned artifacts and embedded headers remain intact.

V2 has mixed test results; it is not uniformly better than v1. TabPFN was only a
bounded local comparison and is not part of this runtime. Online checkpoints
stay in ignored local SQLite state and do not silently alter these offline weights.
There is no v2 ESP32 export or field/hazard validation receipt.
