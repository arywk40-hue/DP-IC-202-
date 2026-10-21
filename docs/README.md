# INDRA documentation index

The primary scope is six channels plus features, India/Mandi forecasting, and
independently labeled Himalayan hazards. Start with the current guides:

- [Active Mandi v2 and online-learning workflow](MANDI_V2_PIPELINE.md), [new report](../reports/mandi_pipeline_v2/REPORT.md).

- [Submission guide](SUBMISSION_GUIDE.md) and [feature/status list](FEATURES.md).
- [Current seven-model Mandi test](../reports/submission/2026-10-21/REPORT.md): active hybrid, complete comparison and replay evidence.
- [Dashboard setup](HIMACHAL_DASHBOARD_INTEGRATION.md) and [hybrid architecture](FORECAST_MODEL_IMPROVEMENT.md).

- [Project overview](PROJECT_OVERVIEW.md): current scope, modeled benchmark and remaining work.
- [Implemented architecture](ARCHITECTURE.md): code/data/model flow and deployment boundary.
- [Model catalog](../configs/model_catalog.json): countries, datasets, channels and target roles.
- [India/Mandi results](../reports/india_mandi_phase/REPORT.md) and [commands](../ml/india_mandi/README.md): retained compact/history baseline test; the current hybrid comparison is above.
- [Himalayan warning protocol](HIMALAYAN_WARNING_PROTOCOL.md): next-six-hour onset labels, evidence gates and metrics.
- [Cloudburst/storm event prediction update](HIMALAYAN_EVENT_PREDICTIONS.md): expanded v2 protocol and observed storm-report evidence.
- [Evidence acquisition review](reference/HIMALAYAN_EVIDENCE_PROGRESS.md) and [institutional request package](reference/IMD_HIMACHAL_DATA_REQUEST_PACKAGE.md).
- [Low-cost source check](reference/FREE_DATA_SOURCE_REVIEW.md): verified access routes, Baddi PM lead and remaining Mandi coverage gap.
- [Ten-year Copernicus download](reference/COPERNICUS_MANDI_DOWNLOAD.md): 2016–2025 selections, request-size batching and private API setup.
- [Data rights](DATA_LICENSES.md): source-specific rules remain applicable.
- [ESP32 integration](../esp32/ml_integration/README.md): existing legacy runtime; new Mandi model has host C parity only.

Research references retain their original evidence categories:

- [India weather-threshold pipeline](../ml/india_sensor/README.md), [offline results](../reports/offline_phase/RESULTS.md): NOAA weather inputs with PM inactive.
- [CPCB five-channel forecast](../ml/models/india_cpcb_5sensor_6h/README.md): Indian secondary observations; pressure excluded.
- [Prior complete-model audit](reference/MODEL_TEST_RESULTS.md): historical foreign/Indian and rule-proxy comparisons.
- [Spatial research overview](SPATIAL_RESEARCH_OVERVIEW.md), [two-node evidence](../reports/two_node_phase/REPORT.md): same-time estimation, secondary scope.
- [Archive](archive/README.md), [inventory](../DOC_INVENTORY.md), [source documentation](../data/india_mandi_modeled/README.md).

Older reports remain reproducible references. Their four-channel or foreign-model
results are not six-channel Indian hazard validation. Model/raw data paths have
not been renamed or removed where code and immutable manifests depend on them.
