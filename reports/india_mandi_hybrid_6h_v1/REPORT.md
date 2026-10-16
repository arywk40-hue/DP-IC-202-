# Active Mandi neural hybrid

Six numerical +6h endpoints from six channels and 24h causal history.
Validation selects neural architecture and convex prediction coefficients. No existing learned weight is rewritten.
Mandi-location modeled grids; this is not measured station or hazard validation. The test period was examined previously.

| Target | Neural choice | Neural weight | XGB history weight | Ridge weight | Test hybrid MAE | Persistence MAE |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| temperature_c | residual_mlp_64_32 | 0.40 | 0.35 | 0.25 | 1.3063 | 4.8331 |
| relative_humidity_pct | residual_mlp_64_32 | 0.50 | 0.50 | 0.00 | 6.9332 | 18.9686 |
| pressure_hpa | residual_mlp_32 | 0.35 | 0.15 | 0.50 | 0.9255 | 1.6804 |
| pm25_ug_m3 | residual_mlp_64_32 | 0.40 | 0.55 | 0.05 | 6.8923 | 10.1762 |
| pm10_ug_m3 | residual_mlp_32 | 0.40 | 0.55 | 0.05 | 8.9972 | 12.6751 |
| wind_speed_mps | residual_mlp_64_32 | 0.90 | 0.10 | 0.00 | 0.3128 | 0.5945 |

Warm-up uses clearly named persistence. Missing current channels produce unavailable forecasts.
The backend selects exact hourly snapshots at the current observation phase; no interpolated or filled history is used.

## Active integration and reproducibility

- Active backend: `server/dashboard.py`, API 0.3.0. The dashboard displays the
  actual predictor identity, warm-up status, history count and blend coefficients.
- Frozen artifacts: `ml/models/india_mandi_hybrid_6h_v1/profile.json` and
  `ensemble_weights.json`. Original neural/tree/ridge weights are referenced by
  path and checksum; they are not rewritten. No raw dataset is needed for inference.
- Selection: 22,602 training / 738 validation / 954 reused future-test rows.
  Neural choice is selected first per target, then the convex blend, using only
  validation MAE. Blend selection never receives test labels. The frozen source
  and split configuration must match the saved components. No field or hazard
  accuracy is established by these modeled-data metrics.
- Shipping/batch parity: maximum absolute error **0.0** on this cohort.
- Live preview checks: ports 8080 and 8082 both returned `HYBRID_READY`, the
  new profile and 25/25 snapshots; their Chrome pages displayed the actual model.
  Node demo-04 returned explicitly named persistence warm-up. These preview
  inputs are synthetic engineering fixtures, not actual Mandi weather.
- Existing SQLite predictions are recomputed from retained history on profile
  migration. No old compact prediction is relabelled as a neural forecast.
- API-versioned browser caches invalidate the old 0.2.0 responses.

See `verification.json`, `live_preview_verification.json`, and the desktop/mobile
screenshots beside this report. New local physical sensor evaluation, hybrid edge
export/board execution and independent hazard labels remain separate work.
