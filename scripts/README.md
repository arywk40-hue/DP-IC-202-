# Evaluation entry points

| Script | Role | Data/model scope |
| --- | --- | --- |
| `fetch_mandi_data.py` | Download latest 30 completed UTC days separately | Six Mandi IFS/CAMS channels + rain/snow/gust context; local ignored snapshots, no retraining |
| `test_mandi_submission.py` | **Current submission: seven saved candidates and historical dashboard replay** | Six-channel frozen Mandi model-grid source; no fitting, no China models |
| `test_india_mandi.py` | Retained baseline/acquisition workflow | Six modeled Mandi channels, newly Mandi-trained weights, existing Indian research profiles; no China models |
| `test_models.py` | Historical comprehensive audit | Archived feature contracts and foreign/Indian comparisons; retained to reproduce the earlier report |
| `download_copernicus_mandi.py` | Ten-year archive acquisition | ERA5 2016–2025 monthly requests; dry run by default, no model or hazard-label changes |

Use `test_mandi_submission.py` for current project results and `test_india_mandi.py --prepare` for source acquisition. The historical script is not
an independent Himalayan hazard evaluator. Raw downloads, recovered Git files
and local working outputs remain ignored. Neither script invents event truth.

Copernicus account setup, portal selections and request-size batching:
[download guide](../docs/reference/COPERNICUS_MANDI_DOWNLOAD.md).

The connected teammate dashboard starts with `run_himachal_demo.py --offline`. `import_dashboard_observations.py` atomically refreshes its store from reviewed native snapshots. See [integration guide](../docs/HIMACHAL_DASHBOARD_INTEGRATION.md).

`compare_forecast_architectures.py` evaluates the saved Mandi history neural candidates against persistence/XGBoost/ridge. `predict_neural_forecast.py` runs an actual saved neural model on hourly six-channel histories. [Architecture and online-learning status](../docs/FORECAST_MODEL_IMPROVEMENT.md).

`online_storm_risk.py` runs/resumes a daily ERA5-context SGD learner with delayed labels, fixed scaling and uncalibrated scores. `demo_online_storm.py` exercises it with explicitly synthetic NetCDF/labels. [Online research guide](../docs/ONLINE_STORM_RESEARCH.md). This is separate from six-sensor live forecasting.
