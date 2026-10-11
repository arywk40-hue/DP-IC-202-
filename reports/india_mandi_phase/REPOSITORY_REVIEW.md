# Repository review and organization

Reviewed the tracked/unignored inventory, parsed every Python/JSON file, checked
active guide links and model-catalog paths, and reviewed the numerical, India,
independent-hazard and firmware paths. Full file counts are in repository_review.json.

The prior main guide emphasized four-core spatial interpolation. It is preserved
as docs/SPATIAL_RESEARCH_OVERVIEW.md. The primary README/overview/index now cover
six channels, India/Mandi numeric testing and independently labeled Himalayan
hazards. docs/ARCHITECTURE.md describes implemented code; configs/model_catalog.json
identifies source countries, datasets and compatible outputs.

The new primary tester is scripts/test_india_mandi.py. The historical complete
audit remains scripts/test_models.py. Existing frozen paths/weights were preserved;
no evidence was discarded or renamed across incompatible source contracts.

Mandi numerical models now have source-named teacher/student files and a numeric
linear artifact. New C output has a distinct versioned namespace; existing
firmware was not silently switched. Raw source CSV/JSON snapshots are ignored.

Verification: 195 tests plus 14 subtests passed, no skips; lint/diff checks passed.
All 13 new trained numeric weight artifacts stayed unchanged during evaluation.
Compiled C parity passed; this does not constitute physical board execution.

Remaining: measured complete six-channel Mandi observations; independently
verified hazard events and monitoring; board/wiring/wind calibration/UTC details;
physical parity/latency and a sensor-to-hourly-runtime bridge. The modeled-grid
benchmark must not be presented as sensor field accuracy or disaster detection.
