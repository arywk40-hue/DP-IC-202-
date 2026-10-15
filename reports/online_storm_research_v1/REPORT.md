# Online storm research verification — 15 October 2026

Implemented daily incremental SGD log-loss learning with a fixed warm-up scaler
and class weights, delayed-label admission, prediction-before-update records,
a prequential reference tail, rolling diagnostics, drift warnings, frozen holdout
and resumable dated checkpoints. These are separate ERA5-context research heads.

| Synthetic target stream | Issued scores | Mature scored labels | Incremental batches | Final model version |
| --- | ---: | ---: | ---: | ---: |
| Cloudburst placeholder | 3,696 | 3,696 | 78 | 79 |
| Snowstorm placeholder | 3,696 | 3,696 | 78 | 79 |

**Engineering evidence only.** Synthetic random labels and ERA5-shaped fields
were used; no observed event detection accuracy, warning lead time or calibrated
probability is established. No Brier/AUC value is presented as real model skill.
Raw fixture NetCDF/CSVs, diagnostics and joblib files remain local and ignored.

Each stream saved checkpoints for 2024-02-22 and 2024-03-23, plus the final
2024-04-11 state. Resuming through the public CLI from the first checkpoint
reproduced predictions, metrics, coefficients, intercepts and optimizer steps
exactly. Nine focused tests passed. Full working-tree suite: 294 tests and 172
subtests passed; three pre-existing dependency/deprecation warnings remained.
That working tree includes the separate unfinished Phase F runtime tests.
All 129 protected model/handoff files retained their hashes.

The live six-sensor forecasting model, dashboard and ESP32 do not update from
this research replay. Independent hazard labels/monitoring, real input exports,
as-issued feature/label availability and field validation are still needed.

Code and raw source-manifest hashes: [verification.json](verification.json).
Usage and evidence limits: [guide](../../docs/ONLINE_STORM_RESEARCH.md).
