> Archived evidence / superseded guide. Original path: `reports/physics_phase/PLAN.md`. Protocol-specific results are preserved; use [PROJECT_OVERVIEW.md](../../../PROJECT_OVERVIEW.md) for current scope.

# Ordered, separate patches

1. Shared pressure-height reduction, temperature lapse correction and dewpoint interpolation; documented assumptions and fail-closed station QC.
2. All-hour NOAA preparation with source hashes, UTC hour-END availability and raw QC; download public 2023 station-year files where available. Screen every 2024 source station, preserve exclusions and alias rules.
3. Vectorized neighbor-only physics features and gradient-boosting/MLP residual ensemble. Include zero residual in a validation-MAE shrinkage gate. Guarantee applies only to the selection set, never to future unknown labels.
4. Whole 72-hour-block calibration, independent episode checking, 80/90% and distance-bin coverage. No unchecked nominal band in serving output; old row-wise bands disabled.
5. Capped-versus-all-hour/all-year national and Himalaya-proxy experiments, same QC/baselines/chronological episodes, error bars and losses; ERA5 availability audit/ablation if files exist.
6. Evidence-only invention notes (no novelty/patentability assertion), practicum tables/figures/limitations and executable demo. List unavailable evidence explicitly.

This is server training/inference. ESP32 distillation, actual storm segmentation, independent 1–20 km mesh field validation and a patent prior-art search are separate unverified work.
