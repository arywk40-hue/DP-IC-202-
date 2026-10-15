# Forecast architecture and online-learning status

Status: 15 October 2026. The deployed dashboard still uses the saved compact
Mandi XGBoost student. Two additional neural models are trained, saved and
benchmarked as isolated research candidates.

## Architecture implemented in this experiment

The same six channels feed the existing causal feature builder. It produces
66 numerical features from current values, lags, changes and trailing means/stds.
Complete inference requires 25 consecutive hourly snapshots spanning 24 hours.
Missing hours/channels are not filled. Coordinates and additional atmospheric
variables are not introduced as learned inputs.

Two shared multi-output neural architectures were fitted:

- **66 → 32 → 6**, with 2,342 learned weights/biases.
- **66 → 64 → 32 → 6**, with 6,566 learned weights/biases.

These are feed-forward networks over causal history features, not recurrent
networks or TCNs. ReLU hidden layers feed six residual predictions. Feature and
residual means/stds fit training rows only. Each endpoint is
`physical_clip(current + validation_selected_weight * residual)`.

The optimizer is Adam. Epoch selection uses the fixed chronological validation
period, not sklearn's random early-stopping split. Per-target persistence blends
are also selected on validation. The test period does not select epochs,
architecture, targets or blend weights.

Both candidates were compared with persistence, the saved six-input XGBoost
student, the existing 66-feature XGBoost teacher and temporal ridge on identical
rows. Feature/history differences mean improvement against the snapshot student
cannot be attributed solely to changing the learning algorithm. The teacher and
ridge are the matched history comparisons.

Data: the existing 24,336 hourly Mandi-location Open-Meteo/IFS/CAMS modeled rows,
2024-01-01 through 2026-10-10. Complete training/validation/test cohorts contain
22,602 / 738 / 954 rows. The six-hour target horizon is purged at the partition
boundaries. This is one location's retrospective modeled grid, not independently
measured Indian station accuracy. Previously examined September/October dates
remain a reused benchmark, not a new untouched test.

Results, including every candidate and physical-unit MAE/RMSE/R², are saved in
[the comparison report](../reports/india_mandi_neural_history_v1/REPORT.md) and
[JSON results](../reports/india_mandi_neural_history_v1/results.json).

Weights and normalization are stored in bounded, checksum-verified NumPy archives
under `ml/models/india_mandi_neural_history_v1/`; no pickle/joblib loading is used.
Original trained models and exports remain byte-for-byte unchanged. The neural
candidates have no ESP32 export, quantization or on-board execution receipt.
They are not automatically substituted into the active dashboard/firmware.

## Reproduce and run inference

Use the pinned `requirements-himachal.txt` environment. No new library is needed.

```sh
python scripts/compare_forecast_architectures.py
```

This evaluates the already saved neural candidates and checks the original data
manifest. The local raw observations must be present. `--train` fits a new
versioned experiment once and refuses to overwrite an existing model folder;
use a new configuration/output version for another training experiment.

Run a saved neural model on a six-channel hourly observation CSV:

```sh
python scripts/predict_neural_forecast.py \
  --input data/india_mandi_modeled/observations.csv \
  --output data/himachal/neural_prediction.csv
```

Input columns are `location_id`, timezone-aware `timestamp_utc`, and the six
canonical channel names. First-day/incomplete histories produce unavailable
predictions and an explicit status. The output has six numerical endpoints at
+6h plus a metadata receipt. It does not emit hazard classes or probabilities.

## Is online learning implemented?

**No live online-learning loop is implemented.** Recording, importing, plotting
and refreshing observations do not change learned weights. The new benchmark's
`partial_fit` calls implement offline training epochs over the historical
training partition; they do not wire online learning into the product.

For numerical +6h forecasts, a supervised update needs the actual six-channel
observation at exactly the forecast's target time, available no earlier than
six hours after its issue. A new input alone is not a training label, and the
model's own prediction is not ground truth.

A suitable next implementation is a gateway-side shadow learner or bounded
residual correction layer, with a frozen base model and scaler. It needs:

1. Persistent forecast records keyed by station/registration, issue/target time
   and exact model version; calibrated units, clock and source QC.
2. Exact delayed truth matching, duplicate prevention and gaps/missing-channel
   abstention. Keep modeled, synthetic and physical observations separate.
3. Training-only updates after labels mature; score each issued forecast before
   applying its update. Monitor drift and error against the frozen model and
   persistence. Preserve an independent future monitoring cohort.
4. Versioned checkpoints, shadow comparison, promotion criteria and rollback.
   Keep candidate updates off the ESP32 until size/parity/board tests pass.

Online hazard learning additionally requires independently observed event
outcomes and monitored negative periods. Threshold rules, high risk scores and
satellite candidate flags do not automatically supply verified cloudburst or
snowstorm labels.

## Work still needed for completion

- Connect the physical ESP32 telemetry bridge and verify clock, units, pressure,
  calibration and complete native histories.
- Evaluate the selected architecture on new measured Mandi data, then decide
  whether to promote a host model or build and verify a compact edge export.
- Implement and replay-test the delayed-label shadow update service before
  enabling live adaptation.
- Obtain independent hazard labels and coverage evidence for rain, snowstorm,
  cloudburst, flash flood and landslide claims. Train/calibrate/evaluate each
  supported target separately; the current risk rules remain experimental.
- Finish the remaining network, spatial and deployment phases recorded in
  `docs/plans/INDRA_HIMACHAL_PLAN.md`; dashboard integration alone is not
  completion of the full product.

Implementation reference: sklearn supports multi-output MLP regression and
incremental fitting via `partial_fit`; using that API inside an offline training
script does not create a deployed learning service:
https://scikit-learn.org/1.7/modules/generated/sklearn.neural_network.MLPRegressor.html
