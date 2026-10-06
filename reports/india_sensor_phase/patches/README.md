# Ordered review patches

These patches describe changes **already present** in this workspace, based on `ccbf56f` (`main` at the start of this phase). Do not reapply them here. This is the historical October 5 snapshot; commits/push happen in the subsequent [offline phase](../../offline_phase/REPORT.md). Model files and generated matrices remain local/ignored; the source, configs, tests and evidence are available for review.

1. [01-audit-plan.patch](01-audit-plan.patch): audit/capabilities/India source plan and configuration.
2. [02-sensor-data-features.patch](02-sensor-data-features.patch): source admission, normalized rows, causal features and separate labels.
3. [03-regional-models.patch](03-regional-models.patch): buffered/site/time splits, A–D models/calibration, metrics, safe research inference and pinned runtime.
4. [04-regression-tests.patch](04-regression-tests.patch): synthetic contract/causality/provenance/fallback/artifact tests.
5. [05-documentation.patch](05-documentation.patch): executed report/tables, exact commands, documentation index/inventory and clarified hardware specification.

Large JSON evidence files (`../preparation.json`, `../results.json`, `../model_manifest.json`, `../verification.json`) remain separate files rather than being duplicated into enormous patches. [manifest.json](manifest.json) records patch hashes and file membership. [REPORT.md](../REPORT.md) distinguishes measured results, synthetic contract tests and pending field/disaster evidence.
