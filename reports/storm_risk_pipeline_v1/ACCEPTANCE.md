# Storm-risk software acceptance audit

2026-10-15, Asia/Kolkata. Scope: the supplied experimental ERA5 pipeline spec,
preserved in `docs/reference/STORM_RISK_IMPLEMENTATION_SPEC.md`.

| Requirement | Authoritative evidence | Result |
| --- | --- | --- |
| Local ERA5 ingestion, actual-name/unit checks, UTC/configured region/years | `storm_risk/data/era5_loader.py`; `test_data_evidence.py` | Implemented and tested |
| 24-hour lags, changes, trailing extrema, derived wind/dew point | `storm_risk/features/`; `test_no_future_leakage.py` | 588 ordered features; future perturbation and gap tests pass |
| Explicit confirmed labels; monitored zeros; two-source event records; exclusions | `storm_risk/data/labels.py`; `test_data_evidence.py` | Source/time/location/magnitude checks; unknown hours never become zero |
| Date splits, chronological inner validation, boundary and shared-event purging | `storm_risk/data/splits.py`; `pipeline.merge_outcomes`; isolation tests | Test data excluded from all fitted stages |
| Ridge, XGBoost and fixed-epoch MLP | `storm_risk/models/`; actual saved local bundle | Three heads fitted on the synthetic fixture only |
| Nonnegative ensemble coefficients summing to one, selected only on calib | `models/ensemble.py`; fit spies and local artifact audit | Passed |
| Optional calib-only isotonic/Platt mapping, minimum class counts | `calibration/calibrate.py`; `test_calibrator_skip.py` | Skip path writes method `none` and keeps risk columns |
| Brier, counted reliability bins and Murphy components | `validation/metrics.py`, `reliability.py`; `test_reliability_bins.py` | Includes explicit binning remainder |
| Whole-day bootstrap, at least 1,000 draws and fixed seed | `validation/bootstrap.py`; deterministic test and report | Passed; synthetic numerical diagnostics withheld |
| All configured gate criteria and failed-condition report | `validation/gate.py`; `report.json` | Gate false on synthetic evidence, as required |
| Training-only month-wise anomaly thresholds, separate flags | `anomaly/anomaly.py`; `test_anomaly_flags.py` | Passed; uncovered months marked unavailable |
| Distinct-neighbour confirmation within a trailing window, no future use | `confirmation/neighbour.py`; `test_neighbour_confirmation.py` | Passed, including missing-hour and future-perturbation checks |
| Optional SGD daily predict-before-update, frozen scaler/weights, delayed labels | `models/online.py`; `test_online_predict_before_update.py` and actual-run audit | Passed; test rows never update the learner |
| Rolling diagnostics, drift flags and dated online checkpoints | Local run `online_metrics.csv`, `online_audit.json`, `checkpoints/` | Written; synthetic Brier/AUC values withheld |
| Joblib models/scaler/weights/mapper/settings, report and scores | Local `outputs/storm_pipeline_submission_v2/`; SHA checks in receipt | Written and verified |
| Feature NPZ per sampled timestamp plus latest per-feature PNG | Local `heatmaps/`, manifest and digest audit | 1,440 timestamp arrays; 21 PNGs |
| UI anomalies, neighbour-confirmed status, maps, scores, warnings and gate | `StormRiskPanel.jsx`; three read-only backend endpoints; six browser checks | Connected and tested on desktop/mobile |
| No uncalibrated scores presented as percentages or event certainty | UI label/browser assertions; risk-column checks on actual run | Passed for this pipeline |
| Complete report even if inputs/gate fail | Missing-input CLI run and unit test | NOT_READY report/CSV written, exit 2 |
| Seven mandatory named tests | `tests/storm_risk/test_*.py` | All present and passing; extra data/API tests also pass |
| Repository regression and original artifact preservation | `verification.json` | 309 tests + 172 subtests; 129 protected files unchanged |
| End-to-end run on real ERA5 if present | Repo and Downloads scan including ignored files | Conditional check: no real ERA5 available; only synthetic NetCDF fixtures found |
| No restricted-portal downloads or model-generated event labels | Local-only loader/label path and source inspection | No new network acquisition; synthetic labels are explicitly fixture-only |

The software acceptance above does not establish a validated cloudburst model.
Confirmed real event/negative records and ERA5 inputs are still needed to fit
and evaluate an empirical run. Physical ESP/radio execution and promotion of
the six-channel numerical neural ensemble remain separate unfinished work.
