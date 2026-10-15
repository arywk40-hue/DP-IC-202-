# Incremental storm-risk research pipeline

Implemented 15 October 2026. This is a separate **ERA5-context research learner**;
it does not change the six-channel forecasting model, ESP32 firmware or dashboard.
The deployed six-sensor product still has no live online-learning connection.

## What runs

`scripts/online_storm_risk.py` uses `SGDClassifier(loss="log_loss")` and
`partial_fit` to update an existing binary classifier once per daily replay step.
Its first call explicitly supplies `classes=[0,1]`. `StandardScaler` is fitted
once on the initial mature training cohort and never refitted. Per-class sample
weights are `N / (2 * class_count)`, computed from that same cohort and fixed for
later batches. Cloudburst and snowstorm use separate files, model states and runs.

Every daily step follows this order:

1. Predict the day's feature rows using the previous model version. Append and
   flush those immutable scores to `predictions.csv`.
2. Reveal only labels whose `available_at` is no later than the actual replay
   issue clock. Score the original stored prediction, including delayed labels
   for earlier days.
3. Apply one `partial_fit` update to the newly revealed, previously unconsumed
   labels. Unknown labels and missing features never become negatives.
4. Record rolling diagnostic metrics and save date-named checkpoints every
   30 replay days, plus a final checkpoint.

The feature day and issue clock are recorded separately. A daily feature batch
is issued after the observation day ends and all its declared features are
available. With delayed ERA5 data, issuance can be much later than the event.
This is **retrospective contemporaneous classification**, not a cloudburst
advance-warning forecast. It establishes no warning lead time.

## Inputs

ERA5 NetCDF is read with xarray. Supported short/long variable aliases are listed
in `ml/hazard_context/online_data.py`. Required quantities are CAPE, CIN, total
column water vapour, 2 m temperature/dew point, surface pressure, 10 m u/v wind,
gust and boundary-layer height. Temperature is converted K → °C, pressure
Pa → hPa, and dewpoint depression is derived as T − Td. CIN remains in its
provider-supplied convention; no invented shear, gust or atmospheric column
variables are derived from the six surface sensors.

These are **ten context features**, not the six physical deployment channels.
All variables must have explicit compatible units. Missing variables, ambiguous
ensemble/version dimensions, overlapping exports and unsupported units are
rejected. Complete monthly exports or disjoint variable files on identical
coordinates are supported. Only requested nearest cells are loaded, with a
maximum matching distance of 25 km. Actual grid coordinates and matching
separation are retained; matching does not prove physical co-location. Rows are
bounded to 200,000 and requested sites to 200 per replay.

The label CSV requires:

```text
time,lat,lon,label,available_at
2024-07-01T00:00:00Z,31.71,76.93,1,2024-10-15T00:00:00Z
```

`time` is the **start of the outcome hour**, not a model issue time. Known labels
must be 0 or 1; blanks remain unknown. Explicit times must include a timezone.
Optional `target` must match the selected head. Duplicate identities are rejected.
If `available_at` is absent, `--label-delay-hours` is mandatory. That records an
assumption, not verified publication availability. An hourly label cannot be
available before its outcome hour ends. `--feature-delay-hours` is also mandatory;
actual as-issued ERA5 availability is not verified by this loader.

Choose `--label-role satellite_proxy` for IMERG-derived rain labels, including
those associated with reported incidents. For native half-hourly IMERG rates in
mm/hour, compute hourly accumulation as `0.5*rate_1 + 0.5*rate_2`; a single
half-hour's rate is not the observed hour's rainfall. A threshold in a 0.1°
satellite cell is not a verified local cloudburst measurement. IMERG Final
publication can be delayed by months, so do not assume next-day Final labels.

Snowstorm labels require a separate supplied occurrence definition/source;
rain-rate proxy labels are explicitly rejected for that target. The role
`observed_event_unverified` preserves an operator declaration without bypassing
the existing independent-event/monitoring admission gates. This script does not
verify incident identity, source rights, gauge evidence or complete dry-hour
coverage. `label=0` must be supplied from a justified monitoring scheme; an
absent incident record is not automatically a negative.

## Warm-up, reference and drift

Default warm-up is 30 observation days: the first 23 form the initial training
window and the last 7 form a **prequential reference tail**. Initial training
uses only rows/features/labels available by the training cutoff. At least ten
positive and ten negative mature labels are required; otherwise the run returns
`NOT_READY`. Rare events or months-delayed labels may require a much longer
warm-up. Extend the window rather than pretending labels arrived sooner.

The reference tail is predicted before each update. Its scores are not
in-sample warm-up predictions. The baseline Brier score is fixed only after all
finite reference predictions have mature labels and at least 24 are scored.
Until then, drift baseline status is explicitly waiting. Reference predictions
may inform later daily updates after their labels mature: this is prequential
assessment, not a fully frozen holdout.

`metrics.csv` records date, actual as-of clock, window endpoint, sample/positive
counts, unweighted Brier score and ROC-AUC. AUC is unavailable when both classes
are not present. The 30-day outcome window ends at the newest mature scored
outcome; it is not falsely labeled the latest live month when labels lag. A
warning is emitted when Brier exceeds the fixed reference by more than 0.05.
This warning does not automatically certify drift, calibrate probabilities or
publish an alert.

For a fully frozen later holdout, set `settings.holdout_start` in a new config
copy to a UTC midnight after warm-up. All updates stop at that observation-day
boundary, including delayed training labels. Holdout metrics contain holdout
predictions only. Event-group, geographic and season independence still require
separate cohort design; adjacent grid cells/hours do not establish independent
event samples.

All scores are named `cloudburst_risk_uncal` or `snowstorm_risk_uncal`. They are
**experimental, uncalibrated scores**, including after incremental updates.
Class balancing changes the fitted class prior; `predict_proba` does not make
these outputs calibrated real-event probabilities. No real hazard accuracy is
claimed by the pipeline's manifests or synthetic tests.

## Run and resume

Install the pinned `requirements-online-research.txt` into the project's isolated
Python environment. For files you have already obtained:

```sh
python scripts/online_storm_risk.py \
  --era5 /absolute/path/era5.nc \
  --labels /absolute/path/hourly_labels.csv \
  --target cloudburst --label-role satellite_proxy \
  --feature-delay-hours 120 \
  --output data/hazard_context/online_cloudburst_run
```

The numerical delay in that example is an explicit research assumption, not a
verified ERA5 publication schedule. Use the actual evidence for your source.
If the CSV has only the four required columns, additionally supply the justified
`--label-delay-hours`. For snowstorm, use its own labels and
`--target snowstorm --label-role observed_event_unverified`.

Configuration is `configs/online_storm_research_v1.json`. `--until` is an
exclusive timezone-aware UTC midnight; by default replay stops after the last
feature day. A later explicit cutoff can drain pending delayed labels without
inventing new observations. The final manifest reports unscored pending labels.

Checkpoint files preserve the estimator's optimizer state, fixed scaler,
weights, pending features, issued predictions, metrics, audit and model version.
Each has a SHA-256/sklearn-version manifest. Resume into a **new** output folder:

```sh
python scripts/online_storm_risk.py \
  --era5 /absolute/path/era5.nc --labels /absolute/path/updated_labels.csv \
  --target cloudburst --label-role satellite_proxy --feature-delay-hours 120 \
  --resume data/hazard_context/online_cloudburst_run/cloudburst_DATE_final.joblib \
  --until 2026-11-01T00:00:00Z \
  --output data/hazard_context/online_cloudburst_continuation
```

Resume requires the same configuration, target, evidence role and sklearn
version; completed observation days are not processed again. Load only trusted
local joblib files: this is not an endpoint for uploaded/downloaded pickle models.
Keep the original run manifest/checkpoints with the continuation's parent hash.
Private data, raw synthetic fixtures and working checkpoints stay in ignored
`data/hazard_context/`; they are not committed to GitHub.

## Engineering verification

```sh
python scripts/demo_online_storm.py --output data/hazard_context/new_online_demo
python -m pytest tests/test_online_storm.py -q
```

The demo uses ERA5-shaped synthetic fields and random synthetic labels, not actual
ERA5/IMERG or confirmed events. Each target's 100-day fixture issued 3,696 scores
and performed 78 update batches; 30-day and final checkpoints were written.
Those counts establish execution, not predictive accuracy. Tests check future
feature/label poisoning, prediction-before-update ordering, delayed-label
admission, fixed scaling, missing inputs, warm-up class gates, frozen holdout,
single-class AUC, drift threshold, NetCDF units and exact checkpoint resume.

Official API/source references:

- https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.SGDClassifier.html
- https://scikit-learn.org/1.7/modules/generated/sklearn.preprocessing.StandardScaler.html
- https://docs.xarray.dev/en/stable/generated/xarray.open_dataset.html
- https://gpm.nasa.gov/data/imerg
