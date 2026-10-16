# Active Mandi six-hour neural hybrid

Gateway profile `india_mandi_hybrid_6h_v1` is the dashboard default.

- Inputs: the fixed six environmental channels and 25 consecutive hourly
  snapshots spanning 24 hours; the shared builder derives 66 causal features.
- Outputs: six numerical measurements at observation time +6 hours.
- Components: saved residual MLPs (66→32→6 and 66→64→32→6), history XGBoost and
  temporal ridge. A validation-selected neural architecture and three convex
  prediction coefficients are stored per target in `ensemble_weights.json`.
- Provenance: Mandi-location IFS/CAMS modeled grids, India; no Beijing weights
  or observations. Existing learned components are referenced by relative path
  and SHA-256 in `profile.json`; keep those committed model directories when
  deploying. Inference needs no raw training CSV, downloads or credentials.
- Missing history: `WARMING_UP_PERSISTENCE`, current values copied explicitly.
  Missing current channels: `MISSING_CURRENT_SENSOR`, no six-channel forecast.
- Deployment: Python gateway only. No hybrid ESP32 export or board execution
  is claimed. This predicts measurements, not hazard probabilities.

Build: `python scripts/promote_mandi_hybrid.py --config configs/mandi_hybrid_forecast_v1.json`
requires the frozen local source data and refuses to overwrite this version.
For a new fit/selection, choose a new model/report output version. The dashboard
runs the committed artifacts directly via `ml.india_mandi.hybrid.Hybrid`.

Validation is August 2026; the 954-row September/October test is a reused
retrospective benchmark. See [results](../../../reports/india_mandi_hybrid_6h_v1/REPORT.md).
Field accuracy and new independent hazard-event validation remain unestablished.

The legacy `configs/model_catalog.json` is checksum-frozen for committed C export
verification. This gateway profile is registered separately by
`configs/mandi_hybrid_forecast_v1.json` and selected in `server/dashboard.py`.
