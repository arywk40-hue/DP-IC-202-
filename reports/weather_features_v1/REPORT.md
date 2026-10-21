# Parameter maps and weather classification — implemented prototype

21 October 2026. API/UI 0.5.0. Both requested features are implemented in the
local gateway/dashboard; real spatial/event validation remains unavailable.

## Delivered

- Six geographic parameter maps with units, source timestamps, explicit support
  and selectable map overlays. IDW estimates never extend outside supported
  geometry; two locations support only a segment.
- Ten simultaneous weather sensor-pattern categories using saved LightGBM / MLP
  models. Native-history, missing-input and training-domain checks are active.
- Twelve-location synthetic showcase, isolated from the actual downloaded Mandi
  grid. Separate source and synthetic-training notices remain visible.
- Existing v2 six-hour measurement forecasting and shadow learning stay intact.

## Actual synthetic classifier comparison

16,000 training / 4,000 validation / 4,000 test episodes. Splits are by independent
seven-snapshot episode, not by overlapping rows of the same history. A fresh test
seed 404 was reserved after initial engineering fixture checks; blend weights and
thresholds use validation only. Raw synthetic arrays stay local.

| Saved candidate | Synthetic exact match | Synthetic macro-F1 |
| --- | ---: | ---: |
| LightGBM | 0.99725 | 0.998674 |
| MLP 13→64→32→10 | 0.95925 | 0.979458 |
| Validation-selected blend | 0.99750 | 0.998743 |

These measure recovery of explicit proxy rules from generated sensor histories.
They do **not** establish 99.75% accuracy on actual weather, cloudbursts or storms.
Per-category precision/recall/F1/support and AUC are in
[classification_results.json](classification_results.json). Input examples,
actual model outputs (including abstentions/misses) and map ranges/support are in
[integration_results.json](integration_results.json).

## Tested boundaries

Known-point interpolation and midpoint arithmetic; geographic hull masks; line
versus area geometry; per-channel missingness; duplicate grid cells; mixed sources;
asynchronous timestamps; stale data; complete native history; domain abstention;
artifact tampering; saved-store migration; all six HTTP layers; desktop/mobile
parameter selection and overlay rendering. Software checks and original artifact
integrity are recorded in [verification.json](verification.json).

The Mandi archive still has one location, so it has point data rather than an
area map. More synchronized locations with the six channels are needed for a
measured multi-node map. There is no mountain/elevation correction or independent
interpolation accuracy test. Scores remain uncalibrated; no real event labels
were added, no flood/landslide predictor is claimed, and no physical-board/RF
test or public warning service is established.

Run: `.venv/bin/python scripts/run_himachal_demo.py --offline --weather-demo --db data/himachal/weather_demo.sqlite --port 8082`.
Open http://127.0.0.1:8082. Full instructions and category definitions:
[guide](../../docs/PARAMETER_MAPS_AND_WEATHER_CATEGORIES.md).
