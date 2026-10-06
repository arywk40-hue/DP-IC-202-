# India sensor phase: what was built and what the evidence shows

**Confidential: do not publish before IP review.** Executed 5 October 2026. [Main guide](../../docs/PROJECT_OVERVIEW.md); [audit, capability matrix and dataset strategy](../../docs/INDIA_SENSOR_RISK_PLAN.md); [exact commands and feature/schema contract](../../ml/india_sensor/README.md).

The existing two-node weather interpolation ensemble and firmware were preserved. This phase adds an India-only, sensor-compatible **same-node forecast research benchmark**, not a disaster detector or between-node risk model. Independent cloudburst/flood/landslide/fire/storm labels are absent, so those heads deliberately remain unavailable.

## Completed in separate patches

1. Audit and configuration: inventory of reusable features, weak event rules, source rights and missing capabilities; cloudburst feasibility and Indian/Himalayan data plan.
2. Data/features/labels: reuse the canonical weather contract and NOAA archive; clean-source gate, physical-site deduplication, suspect pressure/height masking, causal native windows and separate future-label/provenance files. Unknown PM stays missing.
3. Split/models/inference: whole-site 20 km buffers, whole 72h time-block roles and 24h history/6h target purge; compare A sensor/time, B +GPS/height, C mountain calibration, D GPS/height experts with national fallback. Uncalibrated probabilities are withheld; range violations refuse.
4. Tests and evidence: metrics, per-climate/elevation/geographic-proxy breakdowns, bootstrap intervals, replay demo and documentation. Hardware specification clarified without claiming installed sensor verification.

## Actual data and protocol

Prepared **1,515,461 rows at 374 physical sites**, from all previously acquired 375 NOAA 2024 files and 360 2023 files. One exact alias was resolved. **1,497,056 rows at 373 sites** retain current T/RH/wind. Missing future observations reduce each target further. No row sampling caps. Files acquired cover 2023/2024; the last completed bucket ends 2025-01-01 00:00 UTC, which is not an extra year of training.

At 27 sites, suspect height/pressure is masked using the existing prior-cutoff QC. This includes Mandi: catalog/SRTM disagreement does not establish its actual sensor altitude. These sites may contribute T/RH/wind, but no untrusted altitude or pressure is restored. ISO-IN/bounding-box source screening is not a verified India border.

Fit ends June 2024 (includes 2023); selection July/August; calibration September/October; test November/December. Whole sites remain disjoint from fitting, with 20 km buffers. Boundary 72h blocks and crossing history/targets are purged. These blocks are proxies; future real-event experiments must additionally hold out complete adjudicated event groups.

| Scope | Fit sites | Selection/calibration sites | Nominated test sites | Eligible fit rows before target mask | Eligible test rows before target mask |
|---|---:|---:|---:|---:|---:|
| national | 216 | 55 | 74 | 625976 | 25011 |
| himalaya_holdout | 276 | 71 | 13 | 816420 | 4727 |

National target scoring covers **41 sites**, not all 74 nominated sites. Whole-Himalaya scoring covers **11 of 13** nominated sites: 2,680 wind, 2,651 temperature and 2,643 RH pairs. The national test has only two mountain-proxy sites/238 pairs. Himachal is a rectangle proxy: seven sites/~1,350 pairs in the mountain holdout; no official state-boundary or Mandi field claim. Köppen zones BWk/Cfa/Cwa/Cwb cover that holdout; national scores cover Am/Aw/BSh/BWh/Cfa/Cfb/Cwa/Cwb, with as few as eight Cfa pairs. Coastal/state and Eastern-Himalayan skill remain insufficiently established.

Targets are thresholds at the **exact t+6h completed-hour average**: wind ≥10 m/s, T ≥35°C, RH ≥95%. They are not next-six-hour occurrence, gust, official heatwave, fog or rainfall labels. Hourly data cannot supply 10/30-minute trends or true gusts. PM targets are not trained here.

## Results: losses as well as wins

All numbers below are from real NOAA observations. Brier is squared score/probability error (lower is better); tables use eight significant digits. Wind lacks enough calibration positives, so its values are **uncalibrated-score diagnostics**, not released probabilities. Full-precision metrics, AP, recall/F1, confusion matrices, calibration bins and per-zone/elevation coverage are in [results.json](results.json); all methods and 95% station-bootstrap intervals are in [RESULTS.md](RESULTS.md).

| Scope / future measurement | A | B | C | D | Persistence | Fit prevalence |
|---|---:|---:|---:|---:|---:|---:|
| national / high_wind_measurement_at_6h | 0.00011235216 | 0.00011236372 | 0.00011236372 | 0.00011236372 | 0.00027998656 | 0.00011233911 |
| national / hot_measurement_at_6h | 0.0036471663 | 0.0035164754 | 0.0035164754 | 0.0032258171 | 0.0065223503 | 0.010365441 |
| national / near_saturation_measurement_at_6h | 0.042115334 | 0.042836264 | 0.042836264 | 0.042084828 | 0.10333577 | 0.067556965 |
| himalaya_holdout / high_wind_measurement_at_6h | 1.5050955e-07 | 8.0348713e-08 | 8.0348713e-08 | 8.0348713e-08 | 0 | 4.81961e-07 |
| himalaya_holdout / hot_measurement_at_6h | 2.7516262e-06 | 2.7880826e-06 | 2.7880826e-06 | 2.7880826e-06 | 0 | 0.0084867889 |
| himalaya_holdout / near_saturation_measurement_at_6h | 0.087715432 | 0.088100106 | 0.088100106 | 0.088100106 | 0.23117669 | 0.11044566 |

Adding geography worsens national RH Brier (B versus A) and Himalayan RH/temperature Brier. D slightly improves national RH Brier and hot-temperature Brier, but detects **zero of 61 hot positive hours** at 0.5. National wind has two positives, both missed. Himalayan wind/hot tests have **zero positives**: persistence scores 0, and model detection skill cannot be assessed. Small Brier alone is not a useful warning system.

C falls back to B in every head because mountain calibration lacks the required classes. D also uses B for the held-out mountain domain. Consequently, no measurable Himachal-specific improvement is established. National RH D recall is about 30.5%; persistence recalls about 33.2% with many more false-positive hours. Confidence intervals are wide/overlap; these descriptive wins do not justify choosing a deployable model.

False alarms count positive **hours per monitored station-day**, not independent alerts/storms. Intervals bootstrap whole stations (200 replicates); shared storms and serial dependence remain. They are metric intervals, not 80/90% weather bands. Offline test diagnostics include eligible forecasts even where the research serving range guard would refuse.

## Verified and not verified

- Run: real Indian archive preparation; final stricter A–D national/whole-Himalaya training/calibration/evaluation; JSON model/hash metadata; archive replay with uncalibrated wind probability withheld and disaster probabilities null.
- Run: 112 tests plus eight subtests passed; 15 new tests cover source/country isolation, causal prefixes, gaps, native cadence, pressure/datum, delayed data, geometry/resource validation, separate future labels, observed-negative admission, event-group disjointness, split purge, calibration fallback, deterministic fitting, OOD refusal, expert fallback, missing/corrupt artifact handling and fail-closed inference. Fixtures are synthetic contract evidence, not meteorological validation.
- Run: Ruff new-code checks and CI-equivalent lint; compile checks. Existing host/C parity tests pass in the full suite. CI on GitHub and PlatformIO/device builds were not rerun in this phase.
- Pending: independent historical disaster labels/monitored negatives; event association/training after admission; authorized IMD/MOSDAC/OpenAQ/CDS access; NWIC/Delhi metadata/rights; PM data approval; minute/gust streams; real INDRA field sessions; official state/coastal/belt boundaries; node authentication; new ESP32 export/soak/latency.

Runtime: Python 3.13.11, NumPy 2.5.2, pandas 2.3.3, sklearn 1.9.0, XGBoost 3.3.0, Arrow 23.0.0. Deprecation warnings from the current NumPy/pandas combination and sandbox Arrow CPU-detection warnings were observed; no test failed. Original dependency environments were not replaced. Local model files/matrices are ignored by Git; versioned reports preserve hashes and feature/target/split metadata.

## What is needed next

1. Run the retained calibrated A/B/hidden-C collection protocol; survey sensor heights and calibrate encoder counts to wind m/s. Add a calibrated timestamped rain gauge if local rain-rate confirmation is required.
2. Obtain authorized Indian hourly rain/event exports with complete monitored dry periods, event definitions, location/time uncertainty, source rights and whole-event IDs. Sparse wet-only NWIC rain cannot create negatives.
3. Resolve NWIC clock/pressure/license and Mandi/Kala Amb elevation/pressure with independent station metadata; keep unresolved values quarantined.
4. Acquire official region boundaries and enough Himalayan/monsoon extreme-event sites/years; add untouched season/year and field tests. Calibration must cover independent positives, not merely many correlated hours.
5. Admit PM sources only after time/unit/rights checks, keeping non-commercial training separate. External rain/satellite/reanalysis may support labels/research, never silently enter this sensor-only runtime.
6. Only then compare independently labeled event strategies, choose warning thresholds on validation and test false-alarm episodes/misses; consider distillation and authenticated ESP32 deployment after field performance is established.

## Source map / changed files

- Audit/science/dataset/capability evidence: [INDIA_SENSOR_RISK_PLAN.md](../../docs/INDIA_SENSOR_RISK_PLAN.md), original source registry/rights and the retained old reports. IMD-published cloudburst definition requires measured intense local rain; pressure/humidity alone cannot confirm it. [IMD MAUSAM](https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/5084).
- Pipeline: [config](../../configs/india_sensor_risk.json), [prepare.py](../../ml/india_sensor/prepare.py), [features.py](../../ml/india_sensor/features.py), [labels.py](../../ml/india_sensor/labels.py). Existing `ml/datasets/`, forecast/event equations and spatial split utilities are reused.
- Models/protocol: [splits.py](../../ml/india_sensor/splits.py), [train.py](../../ml/india_sensor/train.py), [metrics.py](../../ml/india_sensor/metrics.py), [predict.py](../../ml/india_sensor/predict.py), [evaluate.py](../../ml/india_sensor/evaluate.py).
- Reproduction: [commands](../../ml/india_sensor/README.md), [pinned runtime](../../requirements-india-sensor.txt), [tests](../../tests/test_india_sensor.py), [verification receipt](verification.json), [preparation manifest](preparation.json), [model manifest](model_manifest.json).
- Small existing-file edits: `.gitignore`, CI lint scope, docs index/overview/inventory, user-specified parts in `NODE_COLLECTION_SPEC.md`. No source/raw data, working weights, firmware or prior result tables were moved/deleted.
- Reviewable ordered patches: [patch index](patches/README.md). They describe edits already present; do not reapply to this workspace. No commit/push was made for this new phase.
