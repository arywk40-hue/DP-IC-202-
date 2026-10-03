# Documentation consolidation verification — 3 October 2026

This pass changed documentation only. It did not retrain models, alter data, change firmware or run authenticated downloads.

## Executed in this pass

- Recursively inventoried all `.md`/`.mmd` files, including hidden/ignored files except Git internals: **43 original Markdown files, zero standalone Mermaid files**. Preserved all originals at their existing or recorded archive destinations. Four original inline Mermaid blocks were extracted verbatim to archive `.mmd` files.
- Rebased local Markdown links after 13 moves. Checked existence of all local link/image targets and heading anchors; external websites were not rechecked. Original names, modification times, hashes, classifications and actions are in [the manifest](documentation_manifest.json).
- Checked the four core-target overview tables against the two-neighbor rows in [results.csv](../reports/two_node_phase/results.csv) and the printed [report](../reports/two_node_phase/REPORT.md). Core MAE values retain the report's three decimals; persistence retains CSV precision. No new performance measurements were added.
- Ran `/tmp/indra-data-venv/bin/python -m pytest -q`: **97 passed, eight subtests passed in 10.57 s**, one existing pandas `verify_integrity` deprecation warning. Temporary log: `/tmp/indra-doc-tests.log`.
- Ran the physics-only demo and the learned-model demo on `reports/two_node_phase/examples/readings.json`, using `data/two_node_training/national5km/k2/model.json` for the latter. Both completed, returned status/contributor information and withheld unchecked bands. These are **synthetic software examples**, not field observations. Temporary outputs: `/tmp/indra-doc-demo-physics.json`, `/tmp/indra-doc-demo-model.json`.

## Not executed or established

Clean-environment dependency installation, NOAA reacquisition/full retraining, ERA5/IMD/OpenAQ access, field calibration/scoring, physical ESP32 execution, a fresh firmware build, hardware soak or security clearance were not run in consolidation. Earlier compile/evaluation claims are attributed to their original reports. No new claim of model accuracy, field uncertainty coverage, commercial clearance or invention novelty was made.

The overview is Markdown, not a paginated PDF. Its short sections and compact tables target approximately 6–8 pages; exact pagination depends on rendering. The two overview diagrams received source/syntax inspection, not a Mermaid renderer run. Archive diagrams preserve originals rather than asserting all historical syntax has been rendered.
