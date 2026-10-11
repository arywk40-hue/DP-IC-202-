# Mandi, India — six-channel modeled forecast v1

Training location: **Mandi (31.71 N, 76.93 E), India**. Training source: Open-Meteo
ECMWF IFS weather and CAMS global air-quality model grids, 2024-01-01 to 2026-10-10.
No Beijing observations, pretrained Beijing weights, or Chinese models were used.

**Research benchmark: modeled data, not measured station validation.** Pressure
is modeled grid-surface pressure; weather and PM use different grids. Original
issue-time availability is unverified. No independent-site or disaster-warning
accuracy is established. This bundle is not selected by existing ESP32 firmware.

| Files | Model | Inputs | Outputs |
| --- | --- | --- | --- |
| `teacher/<channel>.ubj` | Causal-history residual XGBoost | 66 features from the six channels; complete 24h history | Six independent +6h numeric forecasts |
| `esp32_student/<channel>.ubj` | Compact residual XGBoost | Six current channels; 16 depth-3 trees/head | Same six forecasts |
| `temporal_ridge.npz` | Standardized residual linear model | Same 66 causal features | Same six forecasts |
| `training_report.json`, `ridge_report.json` | Provenance, checksums, splits and validation choices | — | No executable pickle |

Order: temperature C, relative humidity %, pressure hPa, PM2.5 ug/m3, PM10 ug/m3,
wind m/s. The teacher/linear features are causal lags, deltas and trailing mean/std;
no extra physical channel, station ID, coordinates or future value is learned.

Train: before August 2026. Validation: August. Test: September through 10 October.
Six-hour labels are purged across selection boundaries. All methods use the same
complete-history test cohort. Weights, regularization and per-target selection
use validation only. Some test dates were previously inspected in other API
diagnostics; the October 7–10 subset is reported separately.

All six compact heads beat persistence MAE in this retrospective holdout, but
compact temperature, humidity and wind R2 remain negative. The richer offline
models perform better on this grid. This does not establish physical sensor skill.

[Executed report](../../../reports/india_mandi_phase/REPORT.md) ·
[Source manifest](../../../data/india_mandi_modeled/dataset_manifest.json) ·
[Commands](../../india_mandi/README.md) ·
[Separate C parity export](../../generated/india_mandi_modeled_6h_v1/c_export_report.json).

Attribution: Open-Meteo, ECMWF IFS and Copernicus Atmosphere Monitoring Service
(CAMS). API terms/source obligations remain applicable to future uses.
