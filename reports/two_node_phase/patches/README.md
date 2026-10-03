# Small two-node phase patches

Already applied in the workspace; **do not apply again here**. Patches are relative to the completed physics phase, not original Git HEAD. No commits made; earlier unrelated changes preserved.

1. `01-segment-corridor.patch`: spherical segment/cross-track/endpoint distances and configurable refusal.
2. `02-exact-neighbor-training-view.patch`: exactly K complete-core contributors, query exclusion, neighbor IDs, optional query slope excluded from deployment model view.
3. `03-two-node-serving-and-refusal.patch`: automatic corridor for two inputs, strict A/B wrapper, model/interval compatibility, incomplete-channel behavior and band withholding.
4. `04-bounded-json-model.patch`: bounded numeric tree/NN export and inference without pickle, including missing-only splits.
5. `05-held-station-neighbor-evaluation.patch`: uncapped K=2/3/4/5 experiments, identical test-row comparisons, geometry-specific episode calibration and JSON parity checks.
6. `06-offsets-and-hidden-sensor-scoring.patch`: frozen relative calibration offsets and hidden A/B/C scorer with raw/corrected truth, availability and losses.
7. `07-node-calibration-rotation-spec.patch`: colocated procedure, offset limitations, physical middle-position rotation and command/schema contract.
8. `08-input-demo-and-fixtures.patch`: A/B JSON input demo and explicitly synthetic fixture generator.
9. `09-regression-tests.patch`: corridor edge cases, hidden truth isolation, calibration failures, JSON parity and interval/model compatibility.
10. `10-report-and-practicum-links.patch`: measured tables/figures generator, training-pair support and updated practicum links.

Each passed `git apply --check`, application in a temporary prior-phase tree, and byte-for-byte comparison with the workspace. [Verification](../verification.json) records hashes, tests and unverified work.

Generated JSON models, feature arrays and predictions stay local in ignored `data/two_node_training/`. Reports/CSV/PNG/PDF, source/model hashes and synthetic CLI outputs are separate reproducible artifacts, not embedded binary patches. Run the evaluator and report generator to reproduce them. The generated model JSON is server-side; ESP32 runtime and real A/B/C field performance remain unverified.
