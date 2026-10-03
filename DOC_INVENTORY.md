# Documentation inventory and change manifest

Inventory taken before edits on 3 October 2026. **43 original `.md` files, zero standalone `.mmd` files**; four inline Mermaid blocks were found. Recursive filesystem enumeration included hidden/ignored files and the generated pytest note, excluding `.git` internals. Dates below are filesystem modification timestamps with local UTC offset, not evidence dates or Git commit dates.

“Current” can mean a valid narrow artifact/source reference, not deployment readiness. “Superseded” means replaced as project guidance, not invalidated numerical evidence. No standalone duplicate files were found; duplicated architecture/result explanations were consolidated in the overview. [Machine-readable manifest](docs/documentation_manifest.json) preserves original hashes and destinations.

## Original inventory

| Original path | One-line purpose | Last modified (before edits) | Classification | Current path |
|---|---|---|---|---|
| `.pytest_cache/README.md` | Generated pytest cache instructions; not project documentation | 2026-10-03T13:57:48+05:30 | current (generated cache; excluded from project guidance) | [.pytest_cache/README.md](.pytest_cache/README.md) |
| `ARCHITECTURE.md` | Original six-hour Beijing forecast architecture, export and compile evidence | 2026-09-10T11:08:35+05:30 | superseded | [docs/archive/ARCHITECTURE.md](docs/archive/ARCHITECTURE.md) |
| `INVENTION_NOTES.md` | Evidence-only technical distinctions and prior-art/IP research needs | 2026-10-03T13:58:58+05:30 | current | [INVENTION_NOTES.md](INVENTION_NOTES.md) |
| `README.md` | Former project entry point for the six-hour forecast release contract | 2026-10-01T23:48:45+05:30 | superseded | [docs/archive/ROOT_README.md](docs/archive/ROOT_README.md) |
| `data/field_sources/README.md` | NWIC rainfall acquisition, wet-only coverage and matching limitations | 2026-09-29T17:10:06+05:30 | current | [data/field_sources/README.md](data/field_sources/README.md) |
| `data/himachal_weather_audit/MODEL_DIAGNOSTIC.md` | Unsupported missing-PM forecast stress test on supplied Himachal data | 2026-09-11T17:23:50+05:30 | current reference; historical protocol | [data/himachal_weather_audit/MODEL_DIAGNOSTIC.md](data/himachal_weather_audit/MODEL_DIAGNOSTIC.md) |
| `data/himachal_weather_audit/README.md` | Four supplied NWIC weather-file counts, overlap and unresolved QC | 2026-09-11T17:16:07+05:30 | current | [data/himachal_weather_audit/README.md](data/himachal_weather_audit/README.md) |
| `data/imd_north_access/IMD_DATA_REQUEST.md` | Unsent IMD historical-data request with variables and access questions | 2026-09-11T14:47:09+05:30 | current | [data/imd_north_access/IMD_DATA_REQUEST.md](data/imd_north_access/IMD_DATA_REQUEST.md) |
| `data/imd_north_access/README.md` | IMD catalogue/API access receipts; no acquired observations | 2026-09-11T14:47:09+05:30 | current reference; historical protocol | [data/imd_north_access/README.md](data/imd_north_access/README.md) |
| `data/india_cpcb_research/README.md` | Restricted CPCB-derived temporal research data and explicit assumptions | 2026-09-10T11:07:49+05:30 | current | [data/india_cpcb_research/README.md](data/india_cpcb_research/README.md) |
| `data/india_delhi_station_samples/README.md` | Delhi 15-minute source audit; unresolved units and timestamps | 2026-10-01T23:30:51+05:30 | current | [data/india_delhi_station_samples/README.md](data/india_delhi_station_samples/README.md) |
| `data/india_delhi_station_samples/SOURCE_VERIFICATION.md` | Evidence for unresolved Delhi pressure units and clock conventions | 2026-10-01T23:30:51+05:30 | current | [data/india_delhi_station_samples/SOURCE_VERIFICATION.md](data/india_delhi_station_samples/SOURCE_VERIFICATION.md) |
| `data/india_station_audit/README.md` | Seven CPCB station samples, source rights and channel availability | 2026-09-10T11:08:35+05:30 | current reference; historical protocol | [data/india_station_audit/README.md](data/india_station_audit/README.md) |
| `data/uci_beijing_air_quality/README.md` | Pinned Beijing forecast/event source, units, license and provenance | 2026-09-10T09:25:02+05:30 | current | [data/uci_beijing_air_quality/README.md](data/uci_beijing_air_quality/README.md) |
| `docs/MODEL_INPUTS_AND_OUTPUTS.md` | Earlier forecast/event/heatmap interfaces and sensor-rule definitions | 2026-09-29T17:39:32+05:30 | superseded | [docs/archive/docs/MODEL_INPUTS_AND_OUTPUTS.md](docs/archive/docs/MODEL_INPUTS_AND_OUTPUTS.md) |
| `docs/PROTOTYPE_READINESS.md` | Earlier forecast/event bench and field gates; not current spatial protocol | 2026-10-01T23:48:45+05:30 | superseded | [docs/archive/docs/PROTOTYPE_READINESS.md](docs/archive/docs/PROTOTYPE_READINESS.md) |
| `docs/reference/ML_INFERENCE.md` | Earlier forecast/event inference and planar heatmap reference | 2026-09-28T12:13:17+05:30 | superseded | [docs/archive/docs/reference/ML_INFERENCE.md](docs/archive/docs/reference/ML_INFERENCE.md) |
| `esp32/ml_integration/README.md` | Serial ESP32 forecast/event build, replay, telemetry and field capture | 2026-10-01T15:54:49+05:30 | current | [esp32/ml_integration/README.md](esp32/ml_integration/README.md) |
| `esp32/model_test/README.md` | Isolated forecast model ESP32 compile/upload instructions | 2026-09-11T16:50:05+05:30 | current | [esp32/model_test/README.md](esp32/model_test/README.md) |
| `ml/evaluation/INDIA_RESULTS.md` | Historical restricted Indian temporal transfer/Baddi measurements | 2026-09-11T16:50:05+05:30 | superseded | [docs/archive/ml/evaluation/INDIA_RESULTS.md](docs/archive/ml/evaluation/INDIA_RESULTS.md) |
| `ml/event_classifier/EVENT_RELIABILITY.md` | Why learned sensor-rule matches are not real hazard probabilities | 2026-09-28T12:13:17+05:30 | current | [ml/event_classifier/EVENT_RELIABILITY.md](ml/event_classifier/EVENT_RELIABILITY.md) |
| `ml/event_classifier/README.md` | Event-rule training/export interface and limitations | 2026-09-25T23:29:39+05:30 | current | [ml/event_classifier/README.md](ml/event_classifier/README.md) |
| `ml/models/india_cpcb_5sensor_6h/README.md` | Retained india_cpcb_5sensor_6h model profile, artifact contract and research limitations | 2026-09-10T11:07:49+05:30 | current | [ml/models/india_cpcb_5sensor_6h/README.md](ml/models/india_cpcb_5sensor_6h/README.md) |
| `ml/models/india_cpcb_pm_6h/README.md` | Retained india_cpcb_pm_6h model profile, artifact contract and research limitations | 2026-09-10T11:07:49+05:30 | current | [ml/models/india_cpcb_pm_6h/README.md](ml/models/india_cpcb_pm_6h/README.md) |
| `ml/models/uci_beijing_5sensor_6h/README.md` | Retained uci_beijing_5sensor_6h model profile, artifact contract and research limitations | 2026-09-10T11:07:49+05:30 | current | [ml/models/uci_beijing_5sensor_6h/README.md](ml/models/uci_beijing_5sensor_6h/README.md) |
| `ml/models/uci_beijing_6h/README.md` | Retained uci_beijing_6h model profile, artifact contract and research limitations | 2026-09-10T09:25:03+05:30 | current | [ml/models/uci_beijing_6h/README.md](ml/models/uci_beijing_6h/README.md) |
| `ml/models/uci_beijing_event_rules_6sensor/README.md` | Retained uci_beijing_event_rules_6sensor model profile, artifact contract and research limitations | 2026-09-25T23:36:59+05:30 | current | [ml/models/uci_beijing_event_rules_6sensor/README.md](ml/models/uci_beijing_event_rules_6sensor/README.md) |
| `ml/models/uci_beijing_pm_6h/README.md` | Retained uci_beijing_pm_6h model profile, artifact contract and research limitations | 2026-09-10T11:07:49+05:30 | current | [ml/models/uci_beijing_pm_6h/README.md](ml/models/uci_beijing_pm_6h/README.md) |
| `reports/nwic_pipeline/INDIA_PLAN.md` | Earlier sampled India extension plan and acceptance gates | 2026-10-03T12:45:37+05:30 | superseded | [docs/archive/reports/nwic_pipeline/INDIA_PLAN.md](docs/archive/reports/nwic_pipeline/INDIA_PLAN.md) |
| `reports/nwic_pipeline/INDIA_REPORT.md` | Sampled India spatial results, NWIC quarantine and source coverage | 2026-10-03T13:28:08+05:30 | superseded | [docs/archive/reports/nwic_pipeline/INDIA_REPORT.md](docs/archive/reports/nwic_pipeline/INDIA_REPORT.md) |
| `reports/nwic_pipeline/NODE_COLLECTION_SPEC.md` | Current A/B/C collection, calibration, rotation and scoring protocol | 2026-10-03T14:55:12+05:30 | current | [reports/nwic_pipeline/NODE_COLLECTION_SPEC.md](reports/nwic_pipeline/NODE_COLLECTION_SPEC.md) |
| `reports/nwic_pipeline/patches/README.md` | Historical patch ordering and already-applied warning | 2026-10-03T13:29:32+05:30 | current | [reports/nwic_pipeline/patches/README.md](reports/nwic_pipeline/patches/README.md) |
| `reports/physics_phase/ERA5_DOWNLOAD.md` | Current exact authorized ERA5-Land prerequisites and join caveats | 2026-10-03T14:15:38+05:30 | current | [reports/physics_phase/ERA5_DOWNLOAD.md](reports/physics_phase/ERA5_DOWNLOAD.md) |
| `reports/physics_phase/PLAN.md` | Prior physics implementation plan | 2026-10-03T13:40:14+05:30 | superseded | [docs/archive/reports/physics_phase/PLAN.md](docs/archive/reports/physics_phase/PLAN.md) |
| `reports/physics_phase/REPORT.md` | Earlier 32-neighbor full-hour physics results and band failures | 2026-10-03T14:17:01+05:30 | superseded | [docs/archive/reports/physics_phase/REPORT.md](docs/archive/reports/physics_phase/REPORT.md) |
| `reports/physics_phase/patches/README.md` | Physics patch scopes, application warning and verification receipt | 2026-10-03T14:18:42+05:30 | current | [reports/physics_phase/patches/README.md](reports/physics_phase/patches/README.md) |
| `reports/practicum/RESULTS.md` | Measured 32-neighbor practicum tables/figures with current demo routing | 2026-10-03T15:02:54+05:30 | current reference; historical protocol | [reports/practicum/RESULTS.md](reports/practicum/RESULTS.md) |
| `reports/review/DATASETS_AND_PIPELINE.md` | Original dataset inventory and unified long-form design | 2026-10-03T11:26:15+05:30 | superseded | [docs/archive/reports/review/DATASETS_AND_PIPELINE.md](docs/archive/reports/review/DATASETS_AND_PIPELINE.md) |
| `reports/review/REVIEW.md` | Original focused code/security review and synthetic ensemble evidence | 2026-10-03T11:37:21+05:30 | superseded | [docs/archive/reports/review/REVIEW.md](docs/archive/reports/review/REVIEW.md) |
| `reports/two_node_phase/PLAN.md` | Completed exactly-two-node implementation plan | 2026-10-03T14:41:10+05:30 | superseded | [docs/archive/reports/two_node_phase/PLAN.md](docs/archive/reports/two_node_phase/PLAN.md) |
| `reports/two_node_phase/REPORT.md` | Latest uncapped K=2–5 archive scores, losses and corridor eligibility | 2026-10-03T15:09:53+05:30 | current | [reports/two_node_phase/REPORT.md](reports/two_node_phase/REPORT.md) |
| `reports/two_node_phase/examples/README.md` | Synthetic CLI fixtures; no physical weather validation | 2026-10-03T15:06:12+05:30 | current | [reports/two_node_phase/examples/README.md](reports/two_node_phase/examples/README.md) |
| `reports/two_node_phase/patches/README.md` | Two-node patch scopes, already-applied warning and verification receipt | 2026-10-03T15:25:20+05:30 | current | [reports/two_node_phase/patches/README.md](reports/two_node_phase/patches/README.md) |

## Created

- `DOC_INVENTORY.md` (this file).
- `docs/PROJECT_OVERVIEW.md`, `docs/README.md`, `docs/DATA_LICENSES.md`, `docs/DOCUMENTATION_VERIFICATION.md`.
- `docs/archive/README.md`, `docs/documentation_manifest.json`.
- Replacement root `README.md` routing to the single overview; the former README was moved, not discarded.
- `docs/archive/diagrams/ARCHITECTURE__1.mmd`: verbatim extraction from `ARCHITECTURE.md`.
- `docs/archive/diagrams/reports__nwic_pipeline__INDIA_REPORT__1.mmd`: verbatim extraction from `reports/nwic_pipeline/INDIA_REPORT.md`.
- `docs/archive/diagrams/reports__physics_phase__REPORT__1.mmd`: verbatim extraction from `reports/physics_phase/REPORT.md`.
- `docs/archive/diagrams/reports__review__REVIEW__1.mmd`: verbatim extraction from `reports/review/REVIEW.md`.

## Moved original files

- `ARCHITECTURE.md` → `docs/archive/ARCHITECTURE.md`.
- `README.md` → `docs/archive/ROOT_README.md`.
- `docs/MODEL_INPUTS_AND_OUTPUTS.md` → `docs/archive/docs/MODEL_INPUTS_AND_OUTPUTS.md`.
- `docs/PROTOTYPE_READINESS.md` → `docs/archive/docs/PROTOTYPE_READINESS.md`.
- `docs/reference/ML_INFERENCE.md` → `docs/archive/docs/reference/ML_INFERENCE.md`.
- `ml/evaluation/INDIA_RESULTS.md` → `docs/archive/ml/evaluation/INDIA_RESULTS.md`.
- `reports/nwic_pipeline/INDIA_PLAN.md` → `docs/archive/reports/nwic_pipeline/INDIA_PLAN.md`.
- `reports/nwic_pipeline/INDIA_REPORT.md` → `docs/archive/reports/nwic_pipeline/INDIA_REPORT.md`.
- `reports/physics_phase/PLAN.md` → `docs/archive/reports/physics_phase/PLAN.md`.
- `reports/physics_phase/REPORT.md` → `docs/archive/reports/physics_phase/REPORT.md`.
- `reports/review/DATASETS_AND_PIPELINE.md` → `docs/archive/reports/review/DATASETS_AND_PIPELINE.md`.
- `reports/review/REVIEW.md` → `docs/archive/reports/review/REVIEW.md`.
- `reports/two_node_phase/PLAN.md` → `docs/archive/reports/two_node_phase/PLAN.md`.

## Updated original files

- `INVENTION_NOTES.md`.
- `data/himachal_weather_audit/MODEL_DIAGNOSTIC.md`.
- `data/imd_north_access/README.md`.
- `data/india_cpcb_research/README.md`.
- `data/india_station_audit/README.md`.
- `esp32/ml_integration/README.md`.
- `esp32/model_test/README.md`.
- `ml/event_classifier/README.md`.
- `ml/models/india_cpcb_5sensor_6h/README.md`.
- `ml/models/india_cpcb_pm_6h/README.md`.
- `ml/models/uci_beijing_5sensor_6h/README.md`.
- `ml/models/uci_beijing_6h/README.md`.
- `ml/models/uci_beijing_event_rules_6sensor/README.md`.
- `ml/models/uci_beijing_pm_6h/README.md`.
- `reports/physics_phase/patches/README.md`.
- `reports/practicum/RESULTS.md`.

## Unchanged original files

- `.pytest_cache/README.md`.
- `data/field_sources/README.md`.
- `data/himachal_weather_audit/README.md`.
- `data/imd_north_access/IMD_DATA_REQUEST.md`.
- `data/india_delhi_station_samples/README.md`.
- `data/india_delhi_station_samples/SOURCE_VERIFICATION.md`.
- `data/uci_beijing_air_quality/README.md`.
- `ml/event_classifier/EVENT_RELIABILITY.md`.
- `reports/nwic_pipeline/NODE_COLLECTION_SPEC.md`.
- `reports/nwic_pipeline/patches/README.md`.
- `reports/physics_phase/ERA5_DOWNLOAD.md`.
- `reports/two_node_phase/REPORT.md`.
- `reports/two_node_phase/examples/README.md`.
- `reports/two_node_phase/patches/README.md`.

No documentation files were deleted: archived guides retain their bodies and protocol evidence, with archive notices and rebased links. Narrow current references received only scope corrections/link repairs where needed. Data, model artifacts, firmware, tests, raw source receipts, result CSV/JSON, patch snapshots and Python code were left unchanged by consolidation.




## New documentation inventory

Dates are current filesystem timestamps. Original inventory dates above remain frozen.

| Path | One-line purpose | Last modified | Classification |
|---|---|---|---|
| [DOC_INVENTORY.md](DOC_INVENTORY.md) | Complete original/new inventory and created/moved/unchanged manifest | 2026-10-03T16:32:56+05:30 | current |
| [README.md](README.md) | Verbatim original inline Mermaid diagram; historical reference | 2026-10-03T16:22:40+05:30 | current |
| [docs/DATA_LICENSES.md](docs/DATA_LICENSES.md) | Recorded source rights and training-view admission gates | 2026-10-03T16:22:40+05:30 | current |
| [docs/DOCUMENTATION_VERIFICATION.md](docs/DOCUMENTATION_VERIFICATION.md) | Checks run during consolidation and explicit unverified work | 2026-10-03T16:31:03+05:30 | current |
| [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | Single current project guide and reconciled evidence | 2026-10-03T16:32:17+05:30 | current |
| [docs/README.md](docs/README.md) | Short index of main guide, retained references and archive | 2026-10-03T16:22:40+05:30 | current |
| [docs/archive/README.md](docs/archive/README.md) | Archive scope and original-path mapping instructions | 2026-10-03T16:22:40+05:30 | current |
| [docs/archive/diagrams/ARCHITECTURE__1.mmd](docs/archive/diagrams/ARCHITECTURE__1.mmd) | Verbatim original inline Mermaid diagram; historical reference | 2026-10-03T16:22:40+05:30 | superseded; archived original diagram |
| [docs/archive/diagrams/reports__nwic_pipeline__INDIA_REPORT__1.mmd](docs/archive/diagrams/reports__nwic_pipeline__INDIA_REPORT__1.mmd) | Verbatim original inline Mermaid diagram; historical reference | 2026-10-03T16:22:40+05:30 | superseded; archived original diagram |
| [docs/archive/diagrams/reports__physics_phase__REPORT__1.mmd](docs/archive/diagrams/reports__physics_phase__REPORT__1.mmd) | Verbatim original inline Mermaid diagram; historical reference | 2026-10-03T16:22:40+05:30 | superseded; archived original diagram |
| [docs/archive/diagrams/reports__review__REVIEW__1.mmd](docs/archive/diagrams/reports__review__REVIEW__1.mmd) | Verbatim original inline Mermaid diagram; historical reference | 2026-10-03T16:22:40+05:30 | superseded; archived original diagram |
