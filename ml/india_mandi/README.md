# India-only Mandi six-channel forecast benchmark

This is the primary numerical testing workflow. It fits from scratch on modeled
values at Mandi and compares existing Indian CPCB research profiles. It never
loads Beijing weights or observations. Independent Himalayan hazards remain a
separate data-gated experiment in `ml/hazard_context`.

```sh
# Existing local dataset and fitted bundle: test only, no network/retraining.
python3 scripts/test_india_mandi.py --offline
# Fresh checkout: retrieve ignored raw snapshots, then test committed weights.
python3 scripts/test_india_mandi.py --prepare
# New versioned config/path: fit only after choosing chronological cutoffs.
python3 scripts/test_india_mandi.py --config YOUR_NEW_CONFIG.json --prepare --train
# Optional compact C export and compiled-host parity; never flashes hardware.
python3 scripts/test_india_mandi.py --offline --export
```

The frozen profile is `configs/mandi_modeled_forecast_v1.json`. Existing model
outputs cannot be overwritten by `--train`; choose a new versioned path. Cached
dataset/config hashes are checked. The supported source location is Mandi,
India, and modeled evidence cannot be promoted to field or hazard validation.

- Six snapshot inputs; 66 causal-history features for teacher/linear models.
- Train before August 2026, selection in August, future test September–October.
- Same complete-history cohorts and horizon purge for comparison.
- Separate later October 7–10 subset; no geographic holdout at the single grid.
- Metrics: MAE/RMSE/R2 and persistence skill; numeric accuracy/F1 are undefined.
- Lower MAE does not imply positive R2 or reliable field performance.
- `reports/india_mandi_phase/REPORT.md` and `results.json` contain results/examples.

Pressure reference, global CAMS resolution, different model grids and original
issue-time availability limit the result. Full observed Mandi six-channel and
independent-event testing still requires the institutional data requests.
