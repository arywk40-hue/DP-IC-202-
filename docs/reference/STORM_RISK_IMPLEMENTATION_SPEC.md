# Codex Implementation Spec: Storm-Risk Pipeline (Experimental)

## 0. Read this first

This project produces **experimental risk scores**, not calibrated probabilities. Until the validation gate in Section 7 passes on held-out, independently confirmed events, do not describe any output as a probability, chance, likelihood, or accuracy. This applies to code comments, column names, plots, logs, UI labels, and reports.

Rules that override everything else in this spec:

1. Every model output column ends in `_risk_uncal` unless the gate has passed (`calibrated: true` in the config-driven report).
2. Never create event labels from ERA5 or IMERG alone. Labels come only from the confirmed-events record (Section 4).
3. The test split is never used for fitting, weight selection, calibration, or threshold choice.
4. Features at time t use only data at or before t.
5. Parameters (thresholds, radii, N, gate thresholds, percentiles, paths, years) live in a config file. Do not hard-code them.
6. Synthetic data may be used for tests. Synthetic AUC or accuracy must never be reported as predictive skill.

## 1. Goals

- Ingest ERA5 hourly single-level NetCDF files for a configurable bounding box (default: all of India, 6.5 to 37.5 N, 68.0 to 97.5 E, 0.25 degree grid).
- Build 24-hour lagged features per variable.
- Train three base models (ridge, XGBoost, MLP) and combine them into an ensemble score.
- Compute anomaly flags and neighbour-confirmed scores as separate outputs.
- Run online learning (`SGDClassifier` with `partial_fit`) as an optional, separately reported mode.
- Calibrate only if the calibration rules and the validation gate allow it.
- Expose outputs to a UI: anomaly flags, neighbour-confirmation status, and feature heatmaps.

## 2. Repository layout

```
storm_risk/
  config/
    default.yaml            # all tunable parameters
    gate.yaml               # calibration and gate thresholds (separate file)
  data/
    era5_loader.py          # NetCDF -> xarray -> tidy DataFrame
    labels.py               # confirmed-events CSV -> labels with split column
    splits.py               # date-based train / calib / test assignment
  features/
    lagged.py               # 24-hour history: lags t-1..t-24, change, rolling max/min
    derived.py              # dewpoint depression, wind speed, etc.
  models/
    ridge_model.py
    xgb_model.py
    mlp_model.py
    ensemble.py             # non-negative weights fitted on calib split
    online.py               # SGDClassifier partial_fit loop (optional mode)
  calibration/
    calibrate.py            # isotonic or Platt; skipped if positives < min
  validation/
    metrics.py              # Brier, decomposition (Murphy 1973), skill score
    reliability.py          # binned reliability diagram data, bin counts
    bootstrap.py            # block bootstrap by day
    gate.py                 # validation gate, sets calibrated flag
  anomaly/
    anomaly.py              # month-wise percentile flags; stored separately
  confirmation/
    neighbour.py            # N-of-radius confirmation in 3-hour window
  viz/
    heatmaps.py             # feature heatmap arrays / PNG export
  io/
    outputs.py              # joblib checkpoints, JSON report, CSV writers
  cli.py                    # entry point: run pipeline stages
tests/
  test_no_future_leakage.py
  test_split_isolation.py
  test_calibrator_skip.py
  test_reliability_bins.py
  test_online_predict_before_update.py
  test_neighbour_confirmation.py
  test_anomaly_flags.py
```

Keep one function per step, each with a short docstring. Type hints on public functions.

## 3. Inputs

### 3.1 ERA5 files
- Files: `india_era5_monsoon_{year}.nc`, one per year, from the CDS request in the project notes.
- Variables (use these names as they appear in the NetCDF):
  - Precipitation: `tp` (total precipitation, metres; multiply by 1000 for mm), `cp` (convective), `lsp` (large-scale)
  - Thermodynamics: `t2m`, `d2m`, `sp`
  - Wind: `u10`, `v10`, `fg10` (10 m gust)
  - Instability and moisture: `cape`, `cin`, `tcwv`, `kx`, `tt` (K-index, total totals), `blh` (boundary layer height), `tcc` (total cloud cover), `tclw` (cloud liquid water)
- Check actual variable names with `xarray.open_dataset(...).data_vars` on first load and map them through a config dict. Fail with a clear error if a required variable is missing.
- Units: convert `tp`, `cp`, `lsp` to mm/h. Convert `t2m`, `d2m` from K to C. Store `sp` in hPa.
- Time axis: UTC. Keep it as-is; do not shift to local time without a config flag.

### 3.2 Confirmed-events labels
CSV columns: `time`, `lat`, `lon`, `label`, `split`.
- `label`: 1 for a confirmed event at that time and location window, 0 for confirmed non-event hours. Do not infer 0 from missing records.
- `split`: one of `train`, `calib`, `test`, assigned by date from config. Reject rows with any other value.
- If `label` has fewer than `min_positives` (config) in any split, the pipeline still runs but the report must list the shortfall as a warning.

Event record format (from the project validation record): `event_id, type, date_start, date_end, district, lat, lon, magnitude, magnitude_unit, source_1, source_2, confidence, notes, time_known`. Rows with empty `source_1` or `source_2` are excluded from validation-grade labels and written to a separate file.

## 4. Feature construction

For each grid cell and each base feature `f`:
- Lags `f_lag{k}` for k = 1..24 (value at t minus k hours).
- `f_change24 = f(t) - f(t-24)`.
- `f_rollmax24`, `f_rollmin24`: rolling max and min over t-23..t.

Also include the current value `f(t)`.

Rules:
- Use `shift(k)` with positive k along the time axis, computed per grid cell. Never use negative shifts or centred windows.
- Drop rows where the 24-hour history is incomplete, and report the number dropped.
- Derived features: dewpoint depression `t2m - d2m`, wind speed `sqrt(u10^2 + v10^2)`, wind direction (sin and cos).
- Scaling: fit `StandardScaler` on the warm-up window or train split only. Apply the same fitted scaler to all later data. Save it with the model.

## 5. Models

Train on the `train` split only. Use time-ordered validation inside the train split (last 20 percent by time as validation). Do not shuffle.

- **Ridge**: `sklearn.linear_model.RidgeClassifier` or logistic regression with L2, or linear regression with output clipped to [0, 1] for ranking. Config chooses the variant; record it in the report.
- **XGBoost**: `xgboost.XGBClassifier` with `scale_pos_weight` from the train split class ratio. Early stopping on the time-ordered validation set.
- **MLP**: `sklearn.neural_network.MLPClassifier`, small (for example, one hidden layer of 64 units), with early stopping disabled (since early stopping shuffles internally); instead, use a fixed epoch count from config.

### 5.1 Ensemble
- Ensemble score = weighted sum of the three base-model scores.
- Weights are non-negative and sum to 1. Fit them on the `calib` split only (for example, by a constrained least-squares or a grid search over the simplex).
- Store weights in the output JSON and in the joblib checkpoint.
- The ensemble output column is `ensemble_risk_uncal`. Base-model columns are `ridge_risk_uncal`, `xgb_risk_uncal`, `mlp_risk_uncal`.

## 6. Calibration

- Calibrator is fitted on the `calib` split only.
- If the `calib` split has fewer than `min_positives_calib` positives (default 30, from config), skip calibration. Write `calibration_method: "none"` in the report and keep all outputs as `_risk_uncal`.
- Otherwise use isotonic regression (`sklearn.isotonic.IsotonicRegression`, `out_of_bounds="clip"`). Platt scaling is an alternative selected by config. Record which method was used.
- Calibrated output columns are named `*_cal_prob` **only if** the gate passes. Otherwise they remain `*_risk_uncal`.

## 7. Validation gate (all on the `test` split)

Report the following in the JSON report:

1. Number of positive events and total samples in the test split.
2. Brier score and its decomposition (reliability, resolution, uncertainty), following Murphy (1973).
3. Reliability diagram data: bin edges, mean forecast per bin, observed frequency per bin, and **count per bin**. Bins with fewer than `min_bin_count` samples (config) are flagged as unreliable.
4. Brier skill score against climatology (the base event rate in the test split).
5. Block bootstrap 95 percent confidence intervals, resampling whole days (not single hours). Use at least 1000 resamples and a fixed seed from config.
6. The `calibrated` flag.

`calibrated` is `true` only if all of these hold, using thresholds from `gate.yaml`:
- Brier skill score lower CI bound above `bss_min`
- Reliability component (calibration error) below `reliability_max`
- Every populated bin meets `min_bin_count`
- Test split positives at least `min_positives_test`

If the flag is false, every output stays `_risk_uncal`, and the report lists which conditions failed. Do not hard-code the thresholds.

## 8. Neighbour confirmation

Function signature: `confirm_neighbours(score_grid, threshold, radius_deg, n_min, window_hours) -> bool array`

- A cell is confirmed at time t if at least `n_min` neighbouring cells within `radius_deg` also exceed `threshold` at some hour in the window [t-window_hours+1, t].
- `n_min`, `radius_deg`, `threshold`, and `window_hours` come from config (default window 3 hours).
- Do not use future hours in the window.
- Output column `neighbour_confirmed` (boolean). This is separate from the risk score. Do not add it into `_risk_uncal` values.

## 9. Anomaly flags

- For each feature and each calendar month, compute the percentile at `anomaly_percentile` (config, for example 99) from the climatology built on the `train` split only.
- Flag an hour if any feature exceeds its monthly threshold.
- Output columns: `anomaly_flag` (boolean) and `anomaly_features` (comma-separated names). Store these separately from risk scores.

## 10. Online learning (optional mode)

Use `SGDClassifier(loss="log_loss")` with `partial_fit`.
- First call passes `classes=[0, 1]`.
- Sample weights from the warm-up window class ratio.
- Process one day per batch in time order.
- **Predict on day t before updating on day t.** Record those predictions.
- Rolling 30-day Brier score and ROC-AUC, saved to CSV with the date.
- Drift warning when rolling Brier rises by more than 0.05 above its end-of-warm-up value (configurable).
- Checkpoint with `joblib` every 30 days, date in the filename.
- Output columns end in `_risk_uncal`.
- Online mode does not change the gate. Its outputs are reported separately from batch-model outputs.

## 11. Outputs

Write the following to `outputs/{run_id}/`:
- `ensemble_<train_end_date>.joblib`: models, scaler, ensemble weights, calibrator (or None), config snapshot.
- `scores.csv`: time, lat, lon, base and ensemble `_risk_uncal` columns, `neighbour_confirmed`, `anomaly_flag`, `anomaly_features`, `split`.
- `report.json`: sample counts, base rates, metrics, CIs, calibration method, `calibrated` flag, gate failures, warnings list (for example, too few positives, dropped rows, skipped calibration).
- `heatmaps/`: per-feature PNG and a `.npz` array per timestamp, for the UI.
- `online_metrics.csv` and `checkpoints/` when online mode runs.

Write the report even when the gate fails. Warnings are mandatory output, not optional logs.

## 12. UI connections

The UI must show:
- **Anomaly flags**: map or time-series markers from `scores.csv`.
- **Neighbour confirmation**: per-cell confirmed status, labeled "neighbour-confirmed (experimental)".
- **Feature heatmaps**: from `heatmaps/`.
- **Risk scores**: labeled "experimental risk score (uncalibrated)" while `calibrated` is false. Never show a percentage sign or the word "probability" in the UI in that state.
- **Warnings and gate status**: read from `report.json`. Show the calibrated flag and its failed conditions.

If no UI framework exists yet, add a minimal Streamlit app in `viz/app.py` that reads these outputs. Do not invent new data sources for the UI.

## 13. Tests (must pass)

1. `test_no_future_leakage`: perturb values at t+1 and confirm features at t do not change.
2. `test_split_isolation`: the test split is never passed to any `fit`, `partial_fit`, calibrator fit, or ensemble weight fit. Use a spy or mock to check.
3. `test_calibrator_skip`: with positives below `min_positives_calib`, calibration is skipped, the method is recorded as "none", and outputs keep `_risk_uncal`.
4. `test_reliability_bins`: sum of bin counts equals the number of test samples.
5. `test_online_predict_before_update`: for every day, predictions are recorded before `partial_fit` on that day.
6. `test_neighbour_confirmation`: a synthetic grid with a known cluster confirms only the expected cells, and never uses a future hour.
7. `test_anomaly_flags`: a value above the monthly percentile is flagged, and a value below is not.

Synthetic test data is allowed. Tests must not assert predictive accuracy.

## 14. Acceptance criteria

- `pytest` passes.
- The pipeline runs end to end on the synthetic fixture and on a real ERA5 file if one is present.
- `report.json` contains every field listed in Section 11, even when the gate fails.
- No output column lacks `_risk_uncal` unless `calibrated` is true.
- No string in code, logs, plots, or UI says "probability", "chance", or "accuracy" for uncalibrated outputs.
- Config changes (thresholds, radii, percentiles) do not require code edits.

## 15. Do not

- Do not download data from IMD, HPSPCB, or other restricted portals in code. Read local files only.
- Do not generate labels from ERA5 or IMERG thresholds and treat them as validation labels.
- Do not tune any parameter on the test split.
- Do not shuffle time-series data for splits or validation.
- Do not report synthetic-data scores as skill.
- Do not add hard-coded paths, years, or region bounds outside the config.

## 16. Open questions for the project owner

- Confirmed event records: how many validation-grade events exist, and in which years and districts?
- Snowstorm definition: replace the placeholder with the IMD or HPSDMA definition before any snowstorm labels are used.
- Target lead time: nowcast (same hour) or forecast (hours ahead)? This changes the label alignment.
- Which UI framework, if any, should be used?