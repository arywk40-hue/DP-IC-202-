# INDRA: six-channel India and Himalayan research

Updated 11 October 2026. The primary scope is **six environmental channels plus
causal history/derived features**, numerical six-hour forecasting for India/Mandi,
and independently labeled Himalayan hazard research. The source code, fitted
numeric models and evaluation workflow are implemented. Physical field skill
and operational disaster warnings remain unverified.

## Current outputs and status

| Component | Inputs | Output | Evidence/status |
| --- | --- | --- | --- |
| Mandi numerical forecast | Six channels; compact snapshot or 24h causal history | T/RH/P/PM2.5/PM10/wind at exact +6h | Newly fitted India-location modeled-data benchmark; no China data/weights |
| Independent Himalayan warning experiment | Same six channels/history; external records as offline labels | Cloudburst, storm, flash-flood, landslide, snowstorm onset within next 6h | Label/training gates implemented; no admitted real training corpus or fitted head |
| Indian measurement-threshold research | Four available weather measurements plus history/site metadata; PM inactive | +6h high wind, hot temperature, near-saturated humidity | Existing NOAA India research weights; these are measurement thresholds |
| Current-weather spatial research | Previously implemented node/query estimation | Same-time estimates between nodes | Secondary experiment retained in the spatial guide |

The six physical channels, in order, are temperature C, relative humidity %,
station pressure hPa, PM2.5 ug/m3, PM10 ug/m3 and wind m/s. The numerical Mandi API
benchmark uses **modeled grid-surface pressure**, not verified station pressure.
Do not mistake its data kind for calibrated six-channel field measurements.

## Latest India-only numerical test

[Full report and examples](../reports/india_mandi_phase/REPORT.md).
The source has 24,336 hourly modeled positions, 2024-01-01 through 2026-10-10.
Training: before August 2026. Validation: August. Test: September–10 October,
954 complete-history forecast pairs. October 7–10 is also reported separately
(90 pairs). Labels are purged across time boundaries. There is no independent
geographic test at this single requested grid location.

MAE is in the target's units; lower is better. The final column was selected
using validation only, before test scoring.

| Target | Persistence MAE | Compact MAE | Selected-history/model MAE | Selected kind |
| --- | ---: | ---: | ---: | --- |
| `temperature_c` | 4.833 | 3.793 | 1.772 | teacher |
| `relative_humidity_pct` | 18.969 | 14.134 | 7.854 | teacher |
| `pressure_hpa` | 1.680 | 1.484 | 0.947 | temporal_ridge |
| `pm25_ug_m3` | 10.176 | 8.408 | 6.958 | teacher |
| `pm10_ug_m3` | 12.675 | 10.553 | 9.321 | teacher |
| `wind_speed_mps` | 0.595 | 0.464 | 0.322 | teacher |

All six compact heads beat persistence MAE in this retrospective test. Compact
temperature, humidity and wind still have negative R2, so relative improvement
is not a sufficient quality certificate. The history teacher and temporal
linear comparison perform better on this grid. No field accuracy or disaster
probability is inferred from these results.

Sources: Open-Meteo/ECMWF IFS weather and CAMS global PM. Weather and air use
different grids; global CAMS is approximately 45 km and 3-hourly beneath the
hourly API output. Original issue-time availability is unverified. The results
measure retrospective modeled-value prediction, not an operational forecast
made with only information originally available at issue time.

## How to run the current scope

```sh
# With local source snapshots: test only, no retraining or China models.
python3 scripts/test_india_mandi.py --offline
# Fresh checkout: download the local ignored source, then test committed weights.
python3 scripts/test_india_mandi.py --prepare
# Host-verify the compact Mandi C header; no physical board execution.
python3 scripts/test_india_mandi.py --offline --export
```

[Full command guide](../ml/india_mandi/README.md).
Use the project Python dependencies in a compatible isolated environment.
`--train` needs a new versioned model/config path; it refuses existing outputs.
The older comprehensive `scripts/test_models.py` is a historical comparison,
not the default India/Mandi workflow.

## Model and file organization

| Path | Role |
| --- | --- |
| `configs/model_catalog.json` | Model names, countries, training sources, input/output scope |
| `configs/mandi_modeled_forecast_v1.json` | Frozen Mandi source periods, split dates and fit candidates |
| `ml/india_mandi/` | India-only acquisition and numeric comparison |
| `ml/models/india_mandi_modeled_6h_v1/` | Teacher/student per-channel UBJ files, linear NPZ, reports/checksums |
| `ml/generated/india_mandi_modeled_6h_v1/` | Separate India/Mandi compact C export and compiled-host parity |
| `reports/india_mandi_phase/` | Current numerical test, review and verification evidence |
| `ml/hazard_context/`, `configs/himalayan_warning_v2.json` | Independent-event next-six-hour research pipeline |
| `ml/india_sensor/`, `ml/models/india_sensor_v1/` | Earlier India weather-threshold experiment |
| `ml/models/india_cpcb_*` | Reduced-input Indian observational comparisons |
| `ml/models/uci_beijing_*`, `ml/event_classifier/` | Historical foreign/rule references; excluded from current accuracy run |
| `docs/archive/`, `docs/SPATIAL_RESEARCH_OVERVIEW.md` | Prior reports and spatial scope, retained for provenance |

Model filenames identify the target channel and units. Existing artifact paths
are retained to protect hashes and reproducibility; role/country labels prevent
mixing incompatible experiments. Raw CSV/API responses remain local and ignored.

## What real Indian evidence remains missing

The supplied Himachal files have four channels and unresolved pressure/clock/QC
issues. The CPCB secondary set has five channels, excludes pressure and assumes
its timezone; Mandi is absent. NOAA observations have no PM. None establishes
an observed complete six-channel Mandi hazard corpus.

[Himalayan warning protocol](HIMALAYAN_WARNING_PROTOCOL.md) and
[institutional request package](reference/IMD_HIMACHAL_DATA_REQUEST_PACKAGE.md)
define the next evidence steps. Cloudburst requires verified local hourly gauge
intensity; flash flood/landslide/snowstorm require independent occurrence records.
All need matched causal observations and monitored non-event periods. API rain
and artificial samples cannot establish these outcomes.

The prepared sensor readout and existing firmware tests are documented in
[ESP32 integration](../esp32/ml_integration/README.md). That legacy integration
still selects retained Beijing forecast/rule weights; it must not be described
as physical testing of the new Mandi model. The separate India threshold smoke
firmware and new Mandi C header also remain unverified on a physical board.
Actual device variant, wiring, calibration, verified UTC and recorded board
parity/latency are needed for live six-channel testing.

For the retained four-core/current-weather spatial experiments, use
[SPATIAL_RESEARCH_OVERVIEW.md](SPATIAL_RESEARCH_OVERVIEW.md). They do not override
the six-channel primary task or supply independent Himalayan event truth.
