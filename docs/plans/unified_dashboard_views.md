# Active dashboard data scope

The dashboard uses one runtime source: Open-Meteo's weather and air-quality APIs
queried at the Mandi, Himachal Pradesh model-grid point (31.71° N, 76.93° E).
It consumes temperature, relative humidity, surface pressure, PM2.5, PM10 and
wind speed, then displays six-hour numerical forecasts from the active Mandi
model.

These values are modeled grid estimates, not measurements from a physical
station or INDRA hardware. Historical Mandi training data and model artifacts
remain available for reproducibility; they are not additional live dashboard
feeds.

One API grid point cannot support an area heatmap. The parameter-map view stays
available but reports that more synchronized locations are needed. The active
dashboard includes the synthetic-trained current sensor-pattern model and the
six-hour cloudburst, flash-flood and landslide scenario simulator. Pattern scores
are not event probabilities. Scenario percentages are conditional fractions under
documented simulated rainfall, soil and catchment assumptions, not calibrated
probabilities or confirmed hazard forecasts. Separate ERA5 storm-risk runs,
imported local snapshots and hardware command controls are not active dashboard feeds.
The earlier ERA5 storm-run reader and UI panel remain isolated under
`ml/storm_risk/research_ui/` and `ui/src/research/`.

Start locally from the repository root:

```sh
.venv/bin/python server/scripts/run_mandi_api.py --port 8080
```

The service refreshes every 15 minutes by default. If Open-Meteo is unavailable,
it labels the connection offline and can show only the last saved Mandi API
snapshot; it does not substitute demo readings.

## Hazard simulation output contract

The current sensor-pattern model uses seven exact consecutive hours: six canonical
channels plus their one-hour changes and six-hour pressure change (13 model features).
Its categories come from synthetic engineering proxy labels; each score means similarity
to those patterns. The model has 24,000 synthetic episodes (16,000 train, 4,000 validation,
4,000 test), zero independent real-event labels, and no calibrated probabilities.

The six-hour cloudburst, flash-flood and landslide scenario engine accepts only complete,
correctly spaced six-channel history. It emits per-target fractions under three named,
paired assumption families. The range is sensitivity to assumed rain, soil, drainage,
catchment and susceptibility inputs; it is neither a confidence interval nor event
probability. Each response includes observation and forecast times, modeled-grid source
and cell, coordinates, pressure reference, config/code hashes, deterministic seed,
draw count, source registry, parameter provenance and unknown drivers. `field_validated`
and `calibrated` are false and public alerts are disabled.

Research mapping in `ml/configs/himalayan_synthetic_scenarios_v1.json` distinguishes a
published threshold/method from a threshold transferred across regions and from engineering
assumptions used only for sensitivity. In particular, the Uttarakhand cloudburst threshold,
Nepal landslide intensity-duration relation and Rational Method equation do not supply
Mandi event probabilities. The Manali case and WMO guide identify context and missing
drivers; they do not set numerical priors. PM2.5 and PM10 remain in the six-channel input
contract and pattern model but do not drive the scenario rain generator.

With the current single modeled-grid point, parameter maps show a location only. An area
heatmap requires synchronized readings from multiple spatially distinct sites; synthetic
or interpolated locations are not presented as measurements.

Run the API/ML contract checks and dashboard checks from repository root:

```sh
.venv/bin/python -m pytest ml/tests/test_hazard_scenarios.py server/tests/test_dashboard_integration.py -q
npm test --prefix ui
INDRA_E2E_PORT=8091 npm run test:e2e --prefix ui
```
