# Separate physics-phase review patches

Changes are already applied in the workspace. **Do not apply them again here.** These patches are relative to the earlier India-phase implementation, not the repository's original HEAD (many prior-phase files were already untracked). No commits were made; previous user changes were preserved.

| Order | Patch | Scope |
|---|---|---|
| 1 | `01-physics-baselines.patch` | Reference pressure, lapse T, dewpoint RH and valid contributor counts |
| 2 | `02-full-hour-ingestion-qc.patch` | All-hour/year acquisition, raw lineage, coordinate/dewpoint and height/pressure QC; ignore large local arrays |
| 3 | `03-batched-spatial-features.patch` | Nearest-current contexts, physical features, masks and exact lagged baseline |
| 4 | `04-residual-ensemble-serving.patch` | Boosting/NN residuals, selection gate, OOD/failure fallback and guarded serving |
| 5 | `05-episode-bands-legacy-suppression.patch` | Block calibration/check/audit, interval withholding, disable unchecked legacy p90 |
| 6 | `06-full-hour-evaluation.patch` | Whole-station/buffer and Himalaya archive experiments |
| 7 | `07-independent-audit-comparison.patch` | Identical-full-test capped comparison, later band revocation, persistence and geometry coverage |
| 8 | `08-regression-tests.patch` | Regression and numerical/feature/guard/calibration tests |
| 9 | `09-evidence-and-download-notes.patch` | Tested phase dependencies, exact CDS request generator, report and evidence-only invention notes |
| 10 | `10-practicum-and-demo.patch` | Reproducible measured tables/figures and synthetic safety demo |

Each patch passed `git apply --check`, clean application in a temporary tree containing the prior-phase versions, and byte-for-byte comparison with the workspace. [Verification](../verification.json) records hashes and actual environment versions.

Generated NOAA files, hour/feature arrays and raster caches remain local and ignored. Acquisition receipts, all-hour manifest, station QC, monthly CDS request JSON, measured experiment JSON/CSV, demo JSON and PNG/PDF figures are separate reproducible artifacts, not embedded into the small code patches. See [report](../../../docs/archive/reports/physics_phase/REPORT.md) and [practicum](../../practicum/RESULTS.md). No authenticated downloads were attempted.
