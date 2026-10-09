# Himalayan six-channel warning experiment — protocol v1

Implemented 9 October 2026. This is a tested labeling/training interface and a
research protocol. It has fitted no real hazard model and enables no deployed
warning. Institutional observations, admitted events and monitoring remain the
scientific bottleneck.

## Target and available software

`configs/himalayan_warning_v1.json` freezes the new experiment's six-hour window,
hourly cadence, 24-hour complete-input history, target definitions, spatial
association policy, metrics and validation alert budget. Its file SHA256 is
recorded in generated manifests and new model reports.

| Label | Meaning |
| --- | --- |
| 1 | Earliest independently admitted target-episode onset lies in `(issue, issue+6h]`, with its full timing-uncertainty interval inside that window |
| 0 | Compatible independently reviewed monitoring covers the whole future window, with no plausible event/candidate overlap or ongoing/post-event context |
| Unknown | Incomplete monitoring, unresolved event clock/location, ambiguous episode groups, timing at an uncertain boundary, or unavailable six-channel history |

All event sources still pass normal admission. Cloudburst requires independently
verified local one-hour gauge evidence of at least 100 mm/h; reported flood or
landslide occurrence is not automatically a cloudburst. Snowstorm requires
confirmed occurrence under a reviewed definition. Synthetic fixtures cannot
pass normal source admission or produce fitted research heads.

For an exact synthetic onset at 18:00 UTC, issue times 12:00–17:00 UTC are
positive if their histories are complete. At/after onset, they are unavailable
for early warning. A timing interval that crosses the issue time or six-hour
endpoint is also unavailable. Whole grouped episodes use the earliest target
onset so reactivation reports do not create post-onset precursor examples.

The original `exact_future_window` benchmark remains the default for backward
compatibility. Select `next_h_hours` explicitly for the new warning experiment.
Historical scores from the old mode are not scores for this new task.

## Inputs and monitoring

The predictor columns remain temperature, humidity, station pressure, PM2.5,
PM10 and wind. Coordinates/timestamps organize evidence; the new fitted
baseline excludes learned geographic features. No rainfall channel is added
to deployed inputs. Rainfall supplies cloudburst target evidence offline.

Use the canonical `ml.india_sensor.features.build` input contract. Every endpoint
from `t−24h` through `t` must contain valid measurements of all six channels at
the exact hourly cadence: **25 hourly endpoints** for a complete 24-hour span.
Missing PM, off-reference pressure, gaps and delayed observations remain
unavailable. This matches the existing baseline's 24-hour derived features;
a future raw-sequence architecture will have its own explicit window shape.

The v1 association radius is 20 km. Reviewed negative monitoring must cover
that radius; a single dry point gauge cannot establish a 20-km event-free area.
This is a conservative nearby-event experiment, not confirmation of conditions
at the sensor or a validated Mandi-wide warning. A different target location
or radius requires a separately versioned protocol and data-coverage review.

Compatible intervals from the same reviewed source/definition can join at a
shared endpoint. A one-second gap or a change in outcome definition prevents
claiming complete coverage. Unresolved nearby candidate events block negatives.

## Commands when reviewed data is available

Raw files and derived rows should live under the Git-ignored
`data/hazard_context/` directory. These are example paths, not acquired data.

```sh
python3 -m ml.hazard_context.cli warning-labels \
  --events data/hazard_context/events.jsonl \
  --stations data/hazard_context/stations.csv \
  --observations data/hazard_context/six_channel_observations.csv \
  --monitoring data/hazard_context/monitoring.json \
  --config data/hazard_context/reviewed_sensor_config.json \
  --warning-protocol configs/himalayan_warning_v1.json \
  --output data/hazard_context/warning_labels_v1.csv
```

The command writes labels plus a provenance manifest with source/config hashes,
protocol snapshot and positive/negative/unknown counts. It does not fit a model.
The sensor config must explicitly approve the acquired observation sources;
the old NOAA profile alone does not approve new institutional data.

```sh
python3 -m ml.hazard_context.cli train-hazards \
  --events data/hazard_context/events.jsonl \
  --stations data/hazard_context/stations.csv \
  --observations data/hazard_context/six_channel_observations.csv \
  --monitoring data/hazard_context/monitoring.json \
  --config data/hazard_context/reviewed_sensor_config.json \
  --label-mode next_h_hours \
  --warning-protocol configs/himalayan_warning_v1.json \
  --output results/hazards/next6h-v1
```

Use a fresh output directory. The sensor horizon/history/cadence must agree
with the protocol. Warning matching limits come from the protocol; they cannot
silently differ through `--matching-config`.

Admission/support is checked again on eligible warning labels after incomplete
histories are masked. The existing conservative event/site/year/district and
negative-day screens still apply, followed by per-role episode support and
whole-group/site/time isolation. Existing 2024 benchmark split dates are not
a suitable final split merely because they are already configured: freeze
coverage-appropriate dates in a versioned sensor config before model selection.

## Alert evaluation and model comparison

The conventional baseline reuses the small XGBoost fitter. Its model-weighting
candidates are selected by the existing validation F2/AP procedure. The new
**alert cutoff** is selected separately using validation episode recall within
the frozen budget of **one false-alert episode per 100 eligible monitored
negative site-days**, requiring at least three validation positive groups and
ten eligible negative site-days. Ties favor lower false-alert rate and a higher
cutoff. The tested candidate grid is 41 validation score quantiles plus 1.0.
If support/budget is unsatisfied, no cutoff is supplied. These are experimental
choices, not an operational safety standard.

Calibration uses its separate role; final testing never retunes the cutoff.
The original hourly threshold selection is retained in new head metadata for
traceability. New weights, if ever admitted, are named
`<target>_next_h_hours_research.ubj`, distinct from exact-window artifacts.

Episode evaluation collapses contiguous alerts, excludes unknown periods from
false-alert precision, reports achieved first-alert lead-time bounds and counts
each eligible negative issue interval once in the site-day denominator.
Overlapping six-hour target windows do not multiply monitoring days. This
denominator describes evaluated prediction opportunities, not all surveillance
time or all unevaluable/missing-sensor periods.

Once enough real evidence passes, compare no-alert/prevalence references, the
six-channel baseline, a four-weather-channel ablation on identical rows/splits,
and a small causal temporal model. No temporal model has been fitted by this
change. Choose it only if independent event/site performance improves. Model
export, board parity/latency and live sensors remain subsequent stages.

## Distinguish the two Mandi forecast tests

The older Himachal-file diagnostic has four weather channels and lacks PM.
The separate Open-Meteo test uses six API-modeled channels and 714 six-hour
forecast pairs. The compact Beijing model beat persistence MAE on two of those
six modeled targets. Its complete report is now committed in
`docs/reference/MODEL_TEST_RESULTS.md`; it is not an uncommitted result or an
observed six-channel IIT Mandi station test. Neither establishes Mandi hazard
warning skill. Keep both artifacts and their evidence descriptions separate.

## Institutional next action

The [request package](reference/IMD_HIMACHAL_DATA_REQUEST_PACKAGE.md) now includes
HPSPCB Mandi for PM archive availability and more explicit HPSDMA log/coverage
questions. Fill its identity/supervisor fields and obtain the institution's
authorized signed undertaking. No emails, enrolment, signatures or orders have
been submitted by this software update.

## Executed verification

The full repository test suite passed **189 tests plus 14 subtests**, with the
optional research and operational dependencies available. Lint and diff checks
passed. The end-to-end synthetic CLI fixture is recorded in
`reports/hazard_context_phase/warning_window_contract.json`.

That fixture generates six ready pre-onset examples only through its unit-only
constructor override. Normal CLI admission produces zero positive labels and
blocks training: no model weights are created. This verifies interfaces and
evidence gates, not Himalayan event accuracy. Local fixture CSVs remain under
Git-ignored `results/`.
