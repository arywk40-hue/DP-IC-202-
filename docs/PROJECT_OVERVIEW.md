# INDRA project overview

Updated 21 October 2026. See [features](FEATURES.md), [submission steps](SUBMISSION_GUIDE.md)
and [current test results](../reports/submission/2026-10-21/REPORT.md).

INDRA accepts six environmental channels: temperature, RH, pressure, PM2.5,
PM10 and wind. Its active gateway forecasts those six numerical measurements
at an exact six-hour endpoint. It does not predict the intervening six hourly
values or calibrated future disaster probabilities.

## Active architecture

25 hourly snapshots → 66 causal current/lag/change/statistical features → saved
residual MLP + history XGBoost + temporal ridge → validation-selected convex
blend per target → physical-range-bounded six-output forecast.

Saved MLPs use 66→32→6 and 66→64→32→6 architectures, with 2,342 and 6,566 learned
weights/biases. Feature/target scaling was fitted on training data only. Original
arrays, tree files and ridge weights are checksum-verified through the active
`india_mandi_hybrid_6h_v1` profile. All six outputs include a neural contribution.
Missing history uses explicitly labelled persistence; missing current channels
produce unavailable outputs. The dashboard displays the actual model and weights.

## Data and evaluation

The frozen Mandi source contains 24,336 hourly Open-Meteo/ECMWF IFS/CAMS modeled
positions from 1 January 2024 through 10 October 2026. Complete-history cohorts
are 22,602 training, 738 August validation and 954 September/October future-test
pairs. Six-hour labels are purged across split boundaries. Neural architecture
and blend coefficients were selected on validation only. The test was examined
previously and remains reused retrospective evidence, not a new untouched test.
No Chinese rows or pretrained weights enter the current evaluation.

The current submission compares both neural models, compact/history XGBoost,
ridge, persistence and the active hybrid on identical rows. MAE/RMSE/R² and
input/prediction/later-value examples are in the report. There is no independent
site test or calibrated six-channel Mandi station accuracy claim. Weather/air
cells differ, pressure is grid-surface pressure and API history does not establish
what would have been known at the original issue time.

## Dashboard and research boundaries

The local React/FastAPI/SQLite application shows node/source/timestamps, six
measurements and histories, six-hour forecasts, model components, risk evidence,
explicit unavailable values, offline cache and stale state. The Mandi replay
retains historical dates and actual retrieval time; current hazard rules abstain
on modeled sources. Synthetic rain/snow/cloudburst fixtures exercise separate
current-condition rules, not independently observed hazard prediction.

Anomaly/consensus/radio, spatial experiments, ERA5 risk models and delayed-label
online research have separate code/tests. They must not be described as a live,
validated six-sensor product. The available ERA5 fitted demonstration is synthetic.
One Mandi grid cannot validate neighbour consensus or a spatial weather surface.

The active hybrid runs on the Python gateway. Existing compact C exports and
separate firmware applications retain their original model identities. Physical
ESP32 execution, sensor calibration, radio delivery and hybrid edge export remain
unverified. Public alerts and hardware RPC are disabled.

## Submission status

The source, saved numerical model, local dashboard and retrospective modeled-data
testing form the present project prototype. Remaining empirical work requires
synchronized measured Mandi channels and independently observed event/non-event
records. Keep future hazard/field claims separate from software test passes.
The [repository map](../README.md#repository-map) distinguishes active code,
retained research and historical references without breaking immutable paths.
