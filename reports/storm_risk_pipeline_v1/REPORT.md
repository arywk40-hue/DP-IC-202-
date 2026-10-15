# Experimental storm-risk pipeline implementation report

The ERA5-context ridge/XGBoost/MLP ensemble pipeline is implemented and connected
to the existing dashboard through read-only report, score and feature-map APIs.
It is separate from the six-channel ESP numerical forecast.

Validation: **309 Python tests and 172 subtests pass**, two JavaScript contract
tests pass, and all six desktop/mobile browser checks pass. The production UI
build and lint pass. All 129 protected original artifacts remain unchanged.
See [verification.json](verification.json) and [acceptance audit](ACCEPTANCE.md).

## Engineering run

Local output: `outputs/storm_pipeline_submission_v2/`.

- Inputs: 60 days, four synthetic grid cells, 17 ERA5-shaped variables.
- Derived inputs: dewpoint depression, wind speed, direction sine and cosine.
- History: 24 causal hours, producing 588 ordered model features.
- Complete score rows: 5,664; incomplete initial history rows: 96.
- Base models: linear ridge, XGBoost and a 64-unit fixed-30-epoch MLP.
- Ensemble coefficients and all fitted weights are saved in the local joblib;
  the coefficient vector and artifact digest are in the verification receipt.
- Labels are independent random **synthetic engineering fixtures**, not observed
  Himalayan events and not thresholds generated from weather or satellite rain.

| Partition | Complete rows | Synthetic positive samples | Synthetic negative samples |
| --- | ---: | ---: | ---: |
| Train | 3,360 | 411 | 2,949 |
| Calib | 1,152 | 135 | 1,017 |
| Test | 1,152 | 135 | 1,017 |

These are partition inventory counts, not empirical performance. Unavailable
outcomes are purged before actual model/calibration fits; the fit audit records
their exact row IDs. The held-out gate remains **false**. Synthetic diagnostic
values are withheld from the exported report.

Feature maps: **1,440** hourly NPZ files and **21** latest per-feature PNGs.
The online replay writes **3,456** scores and performs **24** mature non-test
updates. Its scaler remains fixed, its test period is frozen, and its final
pending-label count is 92. Dated checkpoints are `2020-07-24.joblib` and
`2020-07-30_final.joblib`. No live learning service was started.

## Current boundaries

No real ERA5 file or independent confirmed-event dataset was available. The
real-input CLI therefore returns `NOT_READY` and writes a complete report rather
than manufacturing labels or weights. The default is a current-hour research
assessment, not demonstrated advance warning. Feature grids and neighbouring
grid agreement are modeled context, not independent physical sensor evidence.

The active six-channel node forecast still uses the compact Mandi XGBoost
student. Physical telemetry transport, neural edge promotion, live neighbour
corroboration and empirical Himalayan event validation are not completed by
this context-pipeline phase. Public notifications remain disabled.

Use the [run guide](../../storm_risk/README.md) for installation, configuration,
input schemas, reproducible commands and dashboard setup.
