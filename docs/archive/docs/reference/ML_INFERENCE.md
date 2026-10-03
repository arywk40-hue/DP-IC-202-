> Archived evidence / superseded guide. Original path: `docs/reference/ML_INFERENCE.md`. Protocol-specific results are preserved; use [PROJECT_OVERVIEW.md](../../../PROJECT_OVERVIEW.md) for current scope.

# INDRA model inference reference

## Six-hour measurement forecast

The retained `uci_beijing_6h` forecast has six regression outputs: temperature,
relative humidity, pressure, PM2.5, PM10, and wind speed six hours after the
input reading. Its ESP32 student accepts the same six measured values in that
order and has six independent 16-tree, depth-3 XGBoost heads. The teacher uses
causal history features for offline benchmarking. The training source is the
UCI Beijing Multi-Site Air Quality dataset; neither Indian field accuracy nor
physical ESP32 timing has been measured. The generated C header is
`ml/models/uci_beijing_6h/esp32_student/export/indra_six_sensor_forecast.h`.

The full source, split, model weights, metrics, and export checksum are in
`ml/models/uci_beijing_6h/training_report.json` and its export report.
The `india_cpcb_5sensor_6h` and `india_cpcb_pm_6h` directories are separate
reduced-input research profiles, not replacements for the six-input release.

```bash
python3 -m ml.six_sensor_forecast.train
python3 -m ml.six_sensor_forecast.export
python3 -m unittest discover -s tests
```

## Event-rule classifier experiment

`ml/event_classifier/` contains a distinct twelve-head, binary XGBoost
experiment. It uses the same six physical sensor channels plus eleven
quantities derived from them: dew point, vapour pressure deficit, heat index,
PM2.5/PM10 ratio, one-hour and six-hour pressure change, one-hour temperature,
PM2.5, PM10, and humidity change, and a six-hour PM2.5 rising flag. Several
features need up to six hours of history; a single sensor snapshot cannot
provide the full input vector.

The labels are deterministic conditions calculated from these inputs. They are
**not observed event ground truth**. Reported precision, recall, F1, and AUC
measure how well a student imitates those conditions on future-time and
held-out Beijing stations. They do not measure detection of actual rain,
blizzards, smoke, or other hazards in Himachal Pradesh. No event classifier is
included in the default ESP32 firmware.

The model files and `event_training_report.json` are in
`ml/models/uci_beijing_event_rules_6sensor/`. The optional C export is
`esp32_student/export/indra_event_classifier.h`; it accepts 17 finite values
and returns twelve rule-match scores in the order recorded in the report. A
skipped rule returns zero and is explicitly marked in the report.

```bash
python3 -m ml.event_classifier.train
python3 -m ml.event_classifier.export
```

The exporter compiles the header and checks C predictions against XGBoost.
This parity check does not establish weather-event accuracy or board timing.

## Spatial interpolation experiment

`ml/event_classifier/heatmap.py` interpolates measured channels from two or
more sensor nodes with inverse-distance weighting. With three or more nodes,
it attempts ordinary kriging when `pykrige` is installed and falls back to
inverse-distance weighting if kriging fails. Event-score maps first classify
the supplied nodes, then interpolate their rule scores. The implementation
expects planar `x, y` coordinates; latitude and longitude require a suitable
local projection before use. It has no independent spatial validation.

See [event experiment details](../../../../ml/event_classifier/README.md) and
[rule limitations](../../../../ml/event_classifier/EVENT_RELIABILITY.md).

## Deployment preparation update

`ml/event_classifier/predict.py` verifies model checksums and suppresses event
scores unless seven complete consecutive observations are present. Untrained
heads return NaN in Python and null in serial JSON.

Heatmaps now require synchronized timezone-aware node snapshots and real
history for event inference. Strategy A classifies nodes then interpolates;
strategy B interpolates all seven raw history slices then classifies grid cells.
Use `strategy="both"` to compare them. Extrapolation outside node geometry is
masked by default. See `docs/PROTOTYPE_READINESS.md` for commands and field
validation requirements. These changes do not convert rule scores into
validated hazard probabilities or six-hour hazard forecasts.
