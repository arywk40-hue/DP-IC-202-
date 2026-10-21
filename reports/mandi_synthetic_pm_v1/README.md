# Mandi synthetic PM gap-fill experiment

Generated and verified 21 October 2026. **Simulation data, not historical PM
measurements or recovered API truth.** No active forecasting model was retrained.

## Saved data

Local ignored CSV: `data/himachal/synthetic_pm_v1/dataset.csv`.
Coverage: 1 January 2017 00:00–30 September 2022 23:00 UTC, **50,376 hourly rows**.

| Item | Result |
| --- | ---: |
| Hours originally missing both PM channels | 48,984 |
| Hours retaining original API PM values | 1,392 |
| Complete six-channel output rows | 50,376 |
| Missing output measurements | 0 |
| Synthetic PM2.5 > PM10 violations | 0 |

Temperature, humidity, grid-surface pressure and wind remain exactly as downloaded.
Every existing PM value is preserved. `pm25_is_synthetic`, `pm10_is_synthetic`
and `evidence_kind` distinguish simulated channels from original modeled values.
The raw source, cached responses, generator weights and CSV remain local; only
code, configuration and compact receipts belong in Git.

## Generator

Two LightGBM regressors learn log(1+PM2.5) and log(1+coarse PM), where coarse PM
is max(PM10−PM2.5, 0). Inputs are the four weather channels plus cyclic Indian
local-hour and annual calendar features. Paired residual innovations with learned
autoregressive memory add reproducible temporal and cross-channel variation.
Simulated PM is bounded to 0–5,000 µg/m³ and fine PM cannot exceed PM10.

Only **33,600 reference rows before 1 August 2026** fit the generator. Validation
and test PM values are excluded. Generation refuses validation/test-era output.
The reference is the existing Mandi modeled grid, not measurements from a
pollution monitor. Using later training-era patterns to fill 2017–2022 is
experimental backcasting: emission changes, actual historical peaks and local
topographic variation cannot be reconstructed by this method.

## Verification and use

[Manifest](manifest.json) records source/dataset hashes and generator settings.
[Verification](verification.json) confirms the seeded draw reproduced, original
values survived and source hashes matched. [Quality diagnostics](quality.json)
check completeness, bounds and variability; these do not validate realism.

```sh
# First generation; uses cached API responses when available:
.venv/bin/python scripts/generate_mandi_synthetic_pm.py
# Verify an existing version and repeat the seeded draw without overwriting it:
.venv/bin/python scripts/generate_mandi_synthetic_pm.py --verify --reproduce
```

Configuration: `configs/mandi_synthetic_pm_v1.json`. Generation refuses to
overwrite an existing dataset; choose a new output/version for changed settings.

Use this dataset for missing-channel pipeline checks or a separately labelled
augmentation experiment. The active v2 fit and all reported holdout scores
exclude it. A future augmented model must be compared on the same untouched,
non-synthetic targets; do not select it by scoring against its own generated PM.
Synthetic PM does not add rainfall observations or verified cloudburst, flood,
landslide, storm or snowstorm labels.

Attribution: Open-Meteo, ECMWF IFS, Copernicus Atmosphere Monitoring Service
(CAMS). Source terms/attribution are retained in the local source manifest.
