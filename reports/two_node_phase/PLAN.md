# Two-node phase plan

1. Add configurable geodesic A–B corridor distances/end limits; keep hull mode for 3–5-node comparison.
2. Make neighbor count explicit in archive features and train 2/3/4/5-neighbor residual models, with exactly K QC-valid core-weather nodes and identical held-out-site/episode splits. Report all archive rows, common-row comparisons and deployment geometry separately.
3. Evaluate physics versus residual, IDW, nearest and node mean. Calibrate/check/audit bands using whole blocks inside the declared serving geometry. Sparse/failed bands remain unavailable.
4. Export bounded JSON residual model parameters and verify predictions against sklearn; no pickle or ESP32 execution claim.
5. Add A/B JSON-input demo, predeployment side-by-side corrections, A/B/C role-rotation hidden-sensor scorer, and update node collection spec. Keep C values out of prediction features and fit offsets only from the calibration session.
6. Run tests and archive evaluation, produce small patches and concise verified/unverified report. No physical field data is presumed available.
