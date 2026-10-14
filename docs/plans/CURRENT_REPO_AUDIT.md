# Repository audit and export verification — Phase A

Baseline: `6bcda6b689868682cabfd95808eeb611dcb4aed3`. Supplied review dated
14 October 2026. Its complete package is preserved in
[the reference directory](../reference/indra_review_2026_10_14/README.md).
Every supplied package file matches its manifest SHA-256 and byte length.
The supplied root prompt and package prompt are byte-identical.

## Existing scope and preserved work

The active Indian numerical experiment is `india_mandi_modeled_6h_v1`: six
numerical targets at exactly +6 hours, using retrospective IFS/CAMS grids.
Station pressure and modeled grid-surface pressure have different source roles.
This benchmark is not field weather accuracy or a trained disaster detector.
The CPCB five-channel and two-PM experiments, NOAA India measurement-threshold
heads, and historical Beijing forecasts/current-rule imitation remain separate.
All catalogued training metadata/reports, fitted artifacts and shipping C headers
were inventoried; their original bytes are protected in `PROTECTED_PATHS.json`.

Current primary README, PROJECT_OVERVIEW and ARCHITECTURE agree about these
boundaries. Older 12-sensor/five-class descriptions under `docs/archive` are
historical, not the current contract. `MODEL_INPUTS_AND_OUTPUTS.md` describes
the retained legacy wrapper and its separate source roles, not Mandi deployment.
No `master/kriging` or current frontend/package.json was found. No AGENTS.md was
found in this checkout or its ancestors. The teammate UI/backend is external
and will be supplied later; new work is isolated until its exact paths can be
inventoried and protected.

## Actual firmware selection

| Firmware environment | Included model/export |
| --- | --- |
| `model_test:esp32-s3-model-test` | Beijing six-channel numerical forecast |
| `model_test:india-five-sensor-test` | CPCB five-channel numerical forecast |
| `model_test:india-pm-test` | CPCB two-PM numerical forecast |
| `ml_integration:esp32-s3-ml` / `esp32-s3-ml-usb` | Beijing numerical forecast and current-rule classifier |
| `india_sensor:india-sensor-research` | NOAA India future measurement-threshold heads and hourly preprocessing |
| `operational_node:operational-driver-preparation` | Sensor/packet preparation; no fitted ML header, physical mode disabled |
| Mandi active export | Separate host C export; not selected by the above firmware |

This audit does not switch any firmware to a different dataset/model.

## Closing the committed-export gap

`configs/committed_exports_v1.json` freezes all existing model artifacts/reports,
export reports/headers, generator sources and one synthetic contract CSV. The
catalog points to that versioned manifest. `ml.deployment.verify_exports` checks
identities before loading models, compiles each **committed** header, compares
it with frozen UBJ weights and regenerates into temporary folders. No original
dataset, training run, network connection or board is required.

Coverage includes every tree split and adjacent float32 thresholds, reachable
leaf paths, physical bounds, channel-wise NaN/+Inf/-Inf and just-outside limits,
null pointers, missing-branch behavior, calibration/threshold/status checks for
India measurement heads, and explicit alias contracts. Forecast aliasing passes;
the legacy event function rejects same-buffer calls. India serving uses distinct
arrays. Existing raw-to-hourly C preprocessing parity and deployment-wrapper
unavailable-head tests remain in the regression suite. Test fixtures are
software contracts and are not added to empirical training/evaluation.

Two compatibility cases are explicit:

1. Three older numerical headers predate country/evidence macros. Regeneration
   omits exactly those two named metadata lines for those named profiles. Every
   other byte must match; no numerical expression is normalized or rewritten.
2. The India threshold export receipt records metadata hash `70049f74…`, while
   the bundled metadata is `a6c95777…`. The exact original receipt and bundled
   metadata remain unchanged. Both hashes and this discrepancy are frozen in
   the new profile. The original receipt's referenced metadata bytes have not
   been recovered. Fresh verification instead checks the bundled metadata,
   exact weight identities, raw/calibrated outputs, flags and statuses, and
   requires both generated headers to reproduce byte-for-byte. The UBJ models
   have positional inputs; their feature names/order come from this hash-checked
   bundled metadata, not embedded UBJ names.

This is explicit legacy compatibility, not a claim that the historical metadata
receipt was correct. Future artifact changes need a new reviewed export identity.
No trained weight, historical report or existing header was modified.

## Executed checks

An isolated Python 3.13.0 host environment uses `requirements-physics.txt`,
`requirements-hazard-context.txt`, `requirements-operational.txt`, XGBoost 3.1.1
and Ruff 0.16.10. These are CI experiment pins, separate from historical training
pins. CI also runs on Python 3.11; this local run does not establish 3.11 execution.

- Existing baseline: **206 passed, 14 subtests passed**, 70.14 seconds.
- Ruff `ml tests esp32/ml_integration/tools --select E9,F63,F7,F82`: passed.
- Offline committed-export CLI: six profiles passed. Detailed rows, threshold
  counts, error maxima and identities are in the
  [fresh verification receipt](../../reports/deployment/committed_export_verification.json).
- Existing pandas deprecation and NumPy/netCDF binary-size warnings persist.
  Sandboxed Arrow CPU-cache probes also print permission diagnostics; parity
  checks complete. No demonstrated prediction failure follows from these warnings.

Expanded regression suite: **209 passed, 124 subtests passed**, 25.16 seconds.
Header, weight, report and generator tamper checks passed. Protected artifact
hashes remain unchanged. Physical execution, RF operation, local independent hazard
data, empirical calibration/accuracy and field power remain NOT_TESTED/NOT_READY.
