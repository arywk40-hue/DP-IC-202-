# Mandi v2: expanded tabular pipeline and delayed-label learning

Client date: 21 October 2026 (Asia/Kolkata). Numerical +6h research forecasts only.

Source expanded from 24,336 to **35,520 complete hourly modeled positions**, October 2022–19 October 2026.
Cohorts: {'train': 33570, 'validation': 738, 'future_test': 1170}. Training ends before August, selection uses August only, test begins September.
Exact +6h labels are purged at boundaries. Older 2017/2020/early-2022 PM probes were empty; no missing PM was fabricated.
Weather and air use different provider grids. This is not synchronized IMD station or real-event validation.

## Implemented model

- Expanded-data six-head LightGBM: two leaf-count configurations per target, up to 500 rounds; chronological early stopping.
- Expanded-data shared residual MLP: 66→64→32→6, up to 100 epochs; train-only scalers and chronological validation.
- Retained v1 neural/tree/ridge hybrid and persistence are explicit comparison/rollback components.
- Per-target nonnegative prediction blends sum to one. Their MAE optimization receives validation arrays only.
- New versioned artifacts are in `ml/models/india_mandi_tabular_v2/`; original v1 weights and C exports are preserved.
- The default gateway registry selects v2. Both profiles remain loadable; firmware is separate.

## Frozen comparison — MAE, lower is better

V2 improves humidity/wind on the full test but regresses on several other channels. It is not universally better.
All model weights were fixed before test scoring; no per-target switch was chosen using test errors. V1 trained on a shorter history, so this is a pipeline/data comparison, not an isolated algorithm trial.

### Full reused test plus extension (1,170 pairs)

| Target | Retained v1 | LightGBM | New MLP | Selected v2 |
| --- | ---: | ---: | ---: | ---: |
| temperature_c | 1.3346 | 1.7556 | 1.3190 | 1.4264 |
| relative_humidity_pct | 7.1751 | 7.9928 | 6.5342 | 6.8214 |
| pressure_hpa | 0.9279 | 1.1297 | 0.9234 | 0.9412 |
| pm25_ug_m3 | 6.5085 | 6.7508 | 6.5678 | 6.5932 |
| pm10_ug_m3 | 8.5604 | 8.9047 | 8.8533 | 8.6987 |
| wind_speed_mps | 0.3170 | 0.3114 | 0.2962 | 0.3019 |

### New-date extension, 11–19 October (210 pairs)

| Target | Retained v1 | LightGBM | New MLP | Selected v2 |
| --- | ---: | ---: | ---: | ---: |
| temperature_c | 1.4265 | 1.8955 | 1.4808 | 1.5581 |
| relative_humidity_pct | 7.9264 | 9.4454 | 7.0078 | 7.6834 |
| pressure_hpa | 0.9038 | 1.0205 | 0.9852 | 0.8967 |
| pm25_ug_m3 | 4.8795 | 4.6472 | 4.9991 | 4.6681 |
| pm10_ug_m3 | 6.5806 | 6.0677 | 6.4645 | 6.0595 |
| wind_speed_mps | 0.3264 | 0.3419 | 0.3029 | 0.3134 |

The extension was not used to fit/choose weights. It is still a retrospective modeled-value check, not an operational issue-time replay or field accuracy. Full MAE/RMSE/R² and validation choices: `results.json`.

## TabPFN: actual local bounded benchmark

Local TabPFN v2 used 512 deterministic training-context rows and the same 96 deterministic test rows for every comparator. It uses residual targets, physical bounds, one estimator and CPU. Telemetry was disabled; no hosted inference or checkpoint redistribution. Its small training context makes this a bounded diagnostic, not a full-data ranking or production selection.

| Target | TabPFN MAE | V2 on identical 96 rows |
| --- | ---: | ---: |
| temperature_c | 1.3619 | 1.4142 |
| relative_humidity_pct | 7.2976 | 7.0888 |
| pressure_hpa | 0.9083 | 0.9839 |
| pm25_ug_m3 | 6.0164 | 6.0599 |
| pm10_ug_m3 | 9.3954 | 8.2706 |
| wind_speed_mps | 0.3590 | 0.2806 |

Receipt, baseline subset metrics, checkpoint identity and timing: `tabpfn.json`. TabPFN is not an active ensemble component. Its pretrained prior is separate from the India-fitted models.

## Online learning: implemented, with two explicitly separate modes

**Live shadow worker:** `scripts/online_mandi_worker.py --input ... --state ... --watch-seconds 5`. It reads actual hourly arrivals, stores immutable base/shadow forecasts, waits for an exact +6h label available by processing time, scores before updating, and persists six SGDRegressor checkpoints transactionally. Scalers remain fixed from offline training. Duplicate labels do not update twice; site/source/calibration identities separate state. Conflicting revisions fail closed. Missing hours/channels do not become zero or nearest-hour labels.

Only hourly snapshots are supported by this worker; it explicitly skips high-rate native data. Use a reviewed hourly aggregation upstream rather than relabeling minute readings.

Late historical forecasts are ineligible for live learning/evaluation. The displayed offline forecast is unchanged by shadow updates. A shadow improvement is not automatic promotion. The live state is separate from simulation.

**Research replay:** `online_replay.json` simulates timely arrivals on the test period with frozen offline weights. It completed 1,170 matured updates and retained 6 pending forecasts. Original API issue-time availability is unverified, so this is a retrospective prequential diagnostic, not a live or independent holdout receipt. Its rolling table covers the last 720 scored forecasts.

| Target | Frozen base MAE | Shadow MAE |
| --- | ---: | ---: |
| temperature_c | 1.5310 | 1.4545 |
| relative_humidity_pct | 7.1739 | 6.7350 |
| pressure_hpa | 0.9455 | 0.8065 |
| pm25_ug_m3 | 6.3748 | 5.9148 |
| pm10_ug_m3 | 8.3620 | 8.0726 |
| wind_speed_mps | 0.3159 | 0.2918 |

## UI and local operation

API/PWA version 0.4.0 invalidates old caches. The model workspace shows data coverage, 66-feature contract, per-channel v1/v2 errors with regressions, cohort selection, live-shadow counts, drift warning and separately labelled simulated replay. Node telemetry shows actual model identity and blend weights. Hazard cards remain experimental current-condition rules, not numerical forecast targets.

Run the backend with the current input and a dedicated live-state database:

```sh
.venv/bin/python -m server.dashboard --observations data/himachal/live_hourly.json --ui apps/indra-himachal-ui/dist --db data/himachal/mandi_dashboard.sqlite --online-state data/himachal/mandi_v2_online_live.sqlite --port 8080
# Optional file-watching learner in a separate terminal:
.venv/bin/python scripts/online_mandi_worker.py --input data/himachal/live_hourly.json --state data/himachal/mandi_v2_online_live.sqlite --watch-seconds 5
```

Keep both services local. No calibrated hazard probabilities, physical sensor/RF success, hybrid edge export or field skill is established.

Attribution: Open-Meteo, ECMWF IFS, CAMS. [LightGBM](https://lightgbm.readthedocs.io/en/v4.6.0/) and [TabPFN](https://github.com/PriorLabs/TabPFN) are separate third-party components; TabPFN v2 weights retain their own license/attribution.

## Final software checks

339 Python tests and 172 subtests passed, with three dependency warnings.
Two frontend contract tests and ten desktop/mobile fixture tests passed.
The actual local Mandi browser check passed on desktop/mobile and the backend's
built UI, including the configured shadow learner. All 129 protected artifacts
and 108 frozen export identities retained their original hashes.
See [verification receipt](verification.json).

The separately generated [synthetic PM dataset](../mandi_synthetic_pm_v1/README.md)
has 50,376 older hourly rows with explicit gap-fill flags. It is excluded from
this v2 fit and every reported test cohort. Its QA is not forecast or event accuracy.
