# Cloudburst, flash-flood and landslide scenarios

Implemented 21 October 2026. The dashboard now has **Hazard scenarios** below
Weather patterns. It takes the same six measurement channels and six hours of
complete native history. There is no seventh sensor or invented rainfall input.

The new component is a **generative Monte Carlo model**, not another classifier
fitted to its own rules. It directly samples possible six-hour futures and reports
the fraction crossing each simulated target. It has no learned weights. Existing
forecast and weather-pattern weights are retained unchanged.

## What each output means

| Dashboard output | Synthetic outcome over the next six hours |
| --- | --- |
| Cloudburst rainfall threshold | At least one simulated rolling hour contains >=100 mm of rain. This does not establish the spatial footprint required to identify a real cloudburst. |
| Flash-flood runoff scenario | Simplified peak runoff exceeds an assumed drainage capacity. This is not a routed river forecast or confirmation of inundation. |
| Landslide rainfall trigger | A transferred intensity-duration threshold is exceeded on an assumed susceptible slope. This is not a geotechnical slope-failure prediction. |

For each target the API returns a central `scenario_fraction`, three separate
family fractions, an `assumption_range`, and a target-specific `*_risk_uncal` field.
A value of 0.20 means **20% of the generated worlds under that assumed setting**,
not a measured 20% chance of an event at Mandi. The range compares different
assumptions; it is not a confidence or credible interval. No family weights or
combined posterior are invented. A zero result does not establish safe conditions.

The API keeps `probability: null`, `calibrated: false`, `field_validated: false`
and `public_alerts_enabled: false`. Independent-event admission gates remain in
place. The six-hour numerical forecast, current pattern classification and these
future scenarios are separate tasks.

## Research basis and what was assumed

The reviewed sources support mechanisms and thresholds, **not a universal
P(hazard | temperature, humidity, pressure, PM2.5, PM10, wind)**. They are a bounded
source review, not a review of all published research.

1. Singh and Thapliyal (2022), [MAUSAM](https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/5084),
   DOI 10.54302/mausam.v73i1.5084: supplies the 100 mm/hour threshold and discusses
   upper-air conditions and radar. Those fields cannot be recovered from our six
   surface channels. The simulator uses the threshold, not purported paper-derived
   probabilities.
2. Dahal and Hasegawa (2008), [Geomorphology](https://doi.org/10.1016/j.geomorph.2008.01.014):
   supplies a Nepal lower-envelope relation `I = 73.90 D^-0.79`, intensity mm/h
   and duration hours. The paper reports its fit for 5 hours to 30 days; this
   implementation uses only 5- and 6-hour windows. The study lacks non-landslide
   rainfall records and estimates some subdaily rainfall. Its threshold is neither
   an occurrence probability nor a Mandi calibration. The wetness adjustment and
   susceptibility gate here are explicitly additional assumptions.
3. [TxDOT Hydraulic Design Manual](https://www.txdot.gov/content/txdotoms/us/en/manuals/des/hyd/chapter-4--hydrology/section-12--rational-method/procedure-for-using-the-rational-method.html):
   supplies the Rational Method relationship among rainfall, runoff coefficient,
   area and concentration time. With area in km² and rain in mm/h,
   `Q = C * I * A / 3.6` gives m³/s. Our time-varying runoff coefficient and
   capacity distributions are simplifications, not a calibrated hydrologic model.
4. [WMO Flash Flood Guidance guide](https://etrp.wmo.int/pluginfile.php/99357/mod_resource/content/1/BSMEFFG_UserGuide-opt.pdf?forcedownload=1):
   identifies catchment/drainage properties and soil water deficit as necessary
   influences. These are sampled as unobserved variables here. This implementation
   does not run WMO's FFG system.
5. [Manali Valley July 2023 study](https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/6447),
   DOI 10.54302/mausam.v75i4.6447: provides the regional terrain and circulation
   context. It supplies no numeric priors used in this simulator.

Every numerical prior is documented in
[`configs/himalayan_synthetic_scenarios_v1.json`](../configs/himalayan_synthetic_scenarios_v1.json).
Only the rainfall threshold and Nepal intensity-duration coefficients are taken
numerically from the cited studies. Rain-link coefficients, latent ranges and
family settings are **engineering assumptions**, not fitted research results.

## Pipeline

1. Validate the six channels, native cadence and complete past six-hour history.
   Bounds follow the existing synthetic pattern domain. Missing/off-grid data,
   nonfinite inputs and inconsistent particulate readings stop the estimate.
2. Derive current values, six one-hour differences and six-hour pressure change
   from seven exact hourly positions. No future observation is an input.
3. Use a documented logistic surface-weather link to sample whether a rainy
   episode exists. Its liquid-phase factor is `sigmoid((T-1)/2)`. PM channels
   are retained and validated but do not drive rain generation.
4. Sample lognormal rain intensity with temporally correlated half-hour variation:
   AR coefficient 0.75, log-variation scale 0.45, and the configured rate cap.
   Rain activity is shared within each six-hour world; these assumptions do not
   reconstruct a measured storm lifecycle. Half-hour resolution is native to the
   simulation; observed hourly rainfall is never split into fake measurements.
5. Generate paired drier/central/wetter worlds using common random numbers.
   Sample soil wetness, storage, runoff coefficient, catchment area, concentration
   time, drainage capacity and susceptibility. These are latent scenario variables,
   not measured extra channels. Soil wetness rises with simulated accumulation;
   drainage/evaporation during the short simulation are omitted.
6. Compute the three outcomes. The Nepal threshold is multiplied by the assumed
   factor `1.4 - 0.7 * wetness` and gated by assumed terrain susceptibility.
7. Count outcomes separately per family. Runtime uses 2,048 draws per family.
   Report Monte Carlo standard error, which covers sampling noise under the fixed
   assumptions only. It does not cover error in those assumptions.

Equal six-channel histories can produce very different outcomes when unmeasured
rainfall or drainage changes. The tests explicitly demonstrate this identifiability
limit. Changing a random seed does not create independent observational evidence.

## Generated dataset and verification

Run from the repository root:

```sh
.venv/bin/python scripts/generate_hazard_scenarios.py
.venv/bin/python -m pytest tests/test_hazard_scenarios.py -q
```

The default run creates **2,048 parent sensor histories × 128 latent worlds ×
3 assumption families = 786,432 synthetic six-hour futures**. Each world has three
binary synthetic outcomes. These are not 786,432 independent weather observations.
Parent histories deliberately oversample engineered weather regimes, so aggregate
synthetic outcome shares do not estimate Mandi climate frequencies.
All worlds belonging to one parent episode must stay together in any later ML
train/test split. No classifier is fitted or selected in this phase.

- Local dataset: `data/himachal/hazard_scenarios_v1/scenarios.npz` (ignored by Git).
- Results and provenance: [`reports/hazard_scenarios_v1/results.json`](../reports/hazard_scenarios_v1/results.json).
- Five fully synthetic examples: [`examples.json`](../reports/hazard_scenarios_v1/examples.json).
- Implementation: [`ml/himachal/hazard_scenarios.py`](../ml/himachal/hazard_scenarios.py).
- UI integration: the existing `/api/nodes/{id}/telemetry` response includes
  `hazardScenarios`. Persisted nodes are reassessed after the configuration changes.

Fresh-seed checks use 64 new parent episodes and two independent sets of 4,096
worlds per family. The average absolute fraction difference was **0.002081**
(0.208 percentage points), with a maximum of **0.026855** (2.686 points).
This measures numerical consistency of the simulator, not forecasting accuracy.
No observed-event accuracy is available; the results explicitly store it as null.

To view it locally, use the existing Mandi dashboard on port 8080 or the simulated
multi-location view on port 8082. Source labels and older-reading indicators remain
visible. These are Python/backend scenarios, not a new ESP32 firmware export.
