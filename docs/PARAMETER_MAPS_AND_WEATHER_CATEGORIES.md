# Six parameter maps and sensor weather categories

Implemented in dashboard/API **0.5.0**. Both features operate on the same six
channels: temperature, RH, pressure, PM2.5, PM10 and wind. The existing numerical
+6h forecast remains a separate task and retains its v2 weights.

## Run the complete demonstration

```sh
.venv/bin/python scripts/run_himachal_demo.py --offline --weather-demo --db data/himachal/weather_demo.sqlite --port 8082
```

Open **http://127.0.0.1:8082**. The banner explicitly says SYNTHETIC DEMO.
Twelve geographically distinct synthetic locations exercise maps, complete and
incomplete histories, and multiple weather patterns. They are not measurements
from twelve Mandi stations. The real downloaded Mandi grid remains on :8080.

1. View the six parameter maps together. Each shows values in its own unit.
2. Click a parameter card to select and enable its geographic map overlay.
3. Select a node. Its telemetry includes numerical forecasts and a separate
   **Sensor weather categories** panel with ten category scores.
4. Example nodes: demo-05 heat stress, demo-06 fog, demo-07 frost,
   demo-08 dust, demo-10 hot/dry/windy, demo-11 snowstorm and demo-12
   overlapping rain/rainstorm/cloudburst-like patterns. Demo-04 lacks history
   and must show an unavailable classification. Predictions, including misses,
   are recorded in the report rather than replacing model outputs with rules.

## Parameter heatmaps

`ml/himachal/parameter_maps.py` converts geographic coordinates to a common
local east/north metre projection, then interpolates each channel with
inverse-square distance weighting (IDW). The legacy route name contains
"kriging", but response metadata identifies the actual IDW method; no kriging
or uncertainty claim is made.

- One location: readings only, no area surface.
- Two locations or collinear locations: their connecting segment only.
- Three or more noncollinear locations: cells wholly inside the contributing
  locations' convex hull. Outside cells remain null; no extrapolation occurs.
- Missing values change support for that channel, not the other five channels.
- Only exact synchronized latest timestamps are combined. Other nodes and
  duplicate positions/source cells are listed as excluded. Source classes and
  pressure references cannot be mixed.
- The local approximation is limited to a 100 km extent. There is no elevation,
  mountain-barrier or wind-direction transport correction. Model grids are not
  relabelled as physical stations. Historical/stale maps retain that status.

Colors span each map's numerical range, not hazard severity. Interpolation is
an estimate between points, not an observation or a validated spatial forecast.
Only one downloaded Mandi location is currently available, so its area map
correctly remains unavailable until more synchronized locations are supplied.

APIs:

```text
GET /api/parameter-heatmaps?resolution=24
GET /api/kriging/heatmap?channel=temperature_c&resolution=24
GET /api/nodes/{id}/telemetry
```

The first returns all six layers with units, supported-cell masks, coordinates,
source/timestamp and exclusions. The second returns the selected layer as
GeoJSON polygons or a line; resolution is bounded to 8–40.

## Weather category model

Saved model: `ml/models/himachal_sensor_patterns_v1/`. It has ten LightGBM binary
heads and a shared **13→64→32→10 sigmoid MLP**. Each category's tree/neural blend
and decision threshold were chosen on validation only. Models load numerical
arrays/text with checksums, never executable pickle.

Inputs are six current values, six one-hour changes, and six-hour pressure
change: **13 features from six physical channels**. Six complete hours of native
history are required. For hourly input this is seven snapshots at t−6h through t.
Minute/quarter-hour data must be complete at its own native cadence; missing
samples are not interpolated into classification history. Missing/out-of-domain
data abstains. Archived observations are classified as historical conditions
after import, not as information known at their original observation time.

The model supports overlapping patterns:

| Category | Engineering proxy definition used for labels |
| --- | --- |
| Rain-like | RH ≥85%, pressure falls ≥1.5 hPa/6h, T >3°C, PM2.5/PM10 fall ≥5/10 µg/m³ in one hour |
| Rainstorm | RH ≥80%, pressure falls ≥3 hPa/6h, cooling ≥3°C/h, wind ≥10 m/s, T >3°C |
| Snowstorm | T ≤1°C, RH ≥85%, wind ≥9 m/s, pressure falls ≥3 hPa/6h |
| Heat stress / heatwave-like | T ≥35°C; instantaneous, not a sustained regional heatwave definition |
| Fog-like | RH ≥95%, wind <1.5 m/s, T ≤25°C |
| Frost-like | T ≤0°C, wind <2 m/s |
| Dust storm | Wind ≥8 m/s, PM10 ≥250, PM2.5/PM10 ≤0.35, RH <40% |
| Smoke / pollution | PM2.5 ≥150, PM2.5/PM10 ≥0.7, RH <60% |
| Hot/dry/windy | T ≥30°C, RH ≤25%, wind ≥5 m/s |
| Cloudburst-like | RH ≥90%, pressure falls ≥1.5 hPa/h, cooling ≥2°C/h, wind ≥10 m/s, PM washout ≥5/10 µg/m³/h |

These are explicit **research proxy definitions, not official event definitions**.
PM washout does not measure precipitation. Cloudburst-like scores cannot establish
100 mm/h rainfall. Snowstorm, fog and smoke matches do not confirm those events.
Flood and landslide outcomes are not inferred from these categories.

## Synthetic data, results and probabilities

Training/validation/test contain **16,000 / 4,000 / 4,000 independent synthetic
episodes**, generated with separate seeds. Each episode has seven six-channel
snapshots. The generator covers broad background conditions plus overlapping
weather-pattern scenarios; train-only scaling is used. Data remains ignored at
`data/himachal/weather_patterns_v1/synthetic_episodes.npz`. This is separate from
the older synthetic PM archive and from downloaded Mandi forecast training data.

Two classifiers were actually fitted and compared. The selected blend recovered
the synthetic proxy labels with **0.9975 exact match and 0.998743 macro-F1**.
These are synthetic definition-recovery metrics, not measured weather accuracy.
Independent episode splitting does not establish independent real-world events.
No real event examples or monitored non-event periods entered this model.

Scores are in [0,1], displayed as **sensor-pattern scores**. They are not calibrated
probabilities of rainstorms, cloudbursts, fires or other real events. Synthetic
oversampling changes category priors. A value of 0.8 does not establish an 80%
event chance. Multiple categories can match; no match is not a safety certificate.
`probability` remains null and public alerts remain disabled.

## Reproduce and inspect

```sh
.venv/bin/python scripts/test_weather_features.py
.venv/bin/pytest -q tests/test_weather_features.py
```

The first retests the committed model without retraining and saves compact
classification/map results. Training code is `scripts/train_weather_categories.py`;
it refuses to overwrite an existing model version. Preserve old versions when
running a new training experiment. Both v2 numerical forecasting and older event
models remain unchanged. The original three evidence-gated rule cards are shown
separately from the new synthetic-trained classification.

Results: [feature report](../reports/weather_features_v1/REPORT.md),
[classifier comparison](../reports/weather_features_v1/classification_results.json),
[API/scenario results](../reports/weather_features_v1/integration_results.json).
