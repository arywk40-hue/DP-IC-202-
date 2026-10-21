# INDRA project overview

Updated 21 October 2026. See [features](FEATURES.md), [current pipeline](MANDI_V2_PIPELINE.md), [submission steps](SUBMISSION_GUIDE.md) and [results](../reports/mandi_pipeline_v2/REPORT.md).

## Active numerical model

INDRA uses temperature, RH, pressure, PM2.5, PM10 and wind. Twenty-five hourly snapshots produce 66 causal current/lag/change/statistical features. The gateway combines six LightGBM residual heads, a 66→64→32→6 residual MLP, the retained v1 hybrid and persistence. Per-target convex weights were selected using August validation only. Outputs are six bounded numerical measurements at exactly +6h, not six intermediate hourly forecasts or future disaster probabilities.

The active `india_mandi_tabular_v2` profile checksums its weights and scaler. Missing history explicitly falls back to persistence; missing current channels produce unavailable outputs. The UI displays actual model identity and blend weights. Original v1 and compact firmware models remain preserved.

## Data and results

The v2 source has **35,520 complete hourly modeled positions**, October 2022–19 October 2026, from Open-Meteo/ECMWF IFS/CAMS for Mandi. It yields 33,570 training, 738 validation and 1,170 September–October test pairs after history and exact +6h split purging. Earlier test dates were previously examined; this is explicit retrospective reuse. No Chinese rows or weights enter this fitted pipeline. TabPFN's separately pretrained prior was tested as a bounded local diagnostic and is not in the active ensemble.

Against v1, v2 improves humidity and wind on the full test and five of six channels on the 210-pair new-date extension. Other errors regress. The report shows these differences rather than claiming universal improvement. No synchronized station or geographically independent Mandi accuracy is established. Weather/air grids differ, pressure is grid-surface pressure, and original issue-time API availability is unverified.

A separate synthetic PM experiment fills older archive gaps for simulation. Its flagged rows are excluded from v2 fitting and the reported accuracy benchmark. See `reports/mandi_synthetic_pm_v1/README.md`.

## Online learning and dashboard

The local React/FastAPI/SQLite dashboard shows nodes, source timestamps, measurements/history, +6h forecasts, components, risk evidence, cache/stale state and a model comparison workspace. A durable file-watching shadow learner saves forecasts before updating six SGD residual correctors on exact +6h outcomes. It uses fixed training scalers, isolates source/site identities, handles duplicates transactionally and rejects late historical forecasts for live scoring. Shadow learning does not automatically change published outputs.

The historical input has zero eligible live updates. A separate simulated timely-arrival replay completed 1,170 updates; its timing assumptions and errors are explicitly labelled. It is not a live sensor test.

## Submission boundaries

The source, versioned models, local dashboard and retrospective numerical tests form the project prototype. Current hazard rules abstain on modeled inputs. Cloudburst, flood, landslide and snowstorm probabilities require independent event/non-event evidence; synthetic pollution cannot supply it. Synthetic storm fixtures and the ERA5 research demonstration exercise software only. One Mandi grid cannot validate neighbour consensus or a spatial weather surface.

The active ensemble runs on the Python gateway. Physical ESP32 execution, sensor calibration, RF delivery and v2 edge export remain unverified. Public alerts and hardware RPC are disabled. Keep both services local. The [repository map](../README.md#repository-map) distinguishes active code from retained research without breaking immutable artifact paths.
