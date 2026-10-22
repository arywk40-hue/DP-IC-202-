# Evaluation entry points

| Script | Role | Data/model scope |
| --- | --- | --- |
| `test_weather_features.py` | Retest the saved category model and all six spatial HTTP layers | Synthetic proxy recovery only; does not retrain or establish event accuracy |
| `train_weather_categories.py` | Offline LightGBM/MLP synthetic-pattern fitting | Independent episode splits, validation-selected blend/thresholds; refuses overwrite |
| `train_mandi_v2.py` | Active v2 acquisition/train/frozen-evaluation entry point | Expanded LightGBM/MLP/legacy ensemble; `--prepare`, `--train`, `--evaluate` |
| `online_mandi_worker.py` | Actual hourly arrival watcher or explicit research replay | Durable exact +6h delayed-label SGD shadow state; no automatic output promotion |
| `benchmark_tabpfn_mandi.py` | Optional isolated local TabPFN v2 benchmark | 512 training-context / 96 test rows; separate runtime; no hosted inference |
| `generate_mandi_synthetic_pm.py` | Flagged older-archive PM gap filling | Simulation only; `--verify --reproduce` audits the saved version without overwriting |
| `fetch_mandi_data.py` | Download latest 30 completed UTC days separately | Six Mandi IFS/CAMS channels + rain/snow/gust context; local ignored snapshots, no retraining |
| `test_mandi_submission.py` | Retained v1 submission: seven candidates and historical dashboard replay | Six-channel frozen Mandi model-grid source; no fitting, no China models |
| `test_india_mandi.py` | Retained baseline/acquisition workflow | Six modeled Mandi channels, newly Mandi-trained weights, existing Indian research profiles; no China models |
| `test_models.py` | Historical comprehensive audit | Archived feature contracts and foreign/Indian comparisons; retained to reproduce the earlier report |
| `download_copernicus_mandi.py` | Ten-year archive acquisition | ERA5 2016–2025 monthly requests; dry run by default, no model or hazard-label changes |

Use `train_mandi_v2.py --evaluate` for current project results. The retained
`test_mandi_submission.py` reproduces v1 results; `test_india_mandi.py --prepare`
acquires the older baseline source. The historical script is not
an independent Himalayan hazard evaluator. Raw downloads, recovered Git files
and local working outputs remain ignored. Neither script invents event truth.

Copernicus account setup, portal selections and request-size batching:
[download guide](../docs/reference/COPERNICUS_MANDI_DOWNLOAD.md).

The connected teammate dashboard starts with `run_himachal_demo.py --offline`. `import_dashboard_observations.py` atomically refreshes its store from reviewed native snapshots. See [integration guide](../EVERYTHING.md#source-88c6383f55c9).

`compare_forecast_architectures.py` evaluates the saved Mandi history neural candidates against persistence/XGBoost/ridge. `predict_neural_forecast.py` runs an actual saved neural model on hourly six-channel histories. [Architecture and online-learning status](../EVERYTHING.md#source-0e64d996660f).

`online_storm_risk.py` runs/resumes a daily ERA5-context SGD learner with delayed labels, fixed scaling and uncalibrated scores. `demo_online_storm.py` exercises it with explicitly synthetic NetCDF/labels. [Online research guide](../EVERYTHING.md#source-2ecdaa4bae5d). This is separate from six-sensor live forecasting.
