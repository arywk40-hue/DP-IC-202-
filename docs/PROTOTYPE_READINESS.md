# Prototype readiness and field deployment gates

The retained models are ready for a supervised software/ESP32 bench prototype.
Field hazard alert deployment is not approved by the available evidence.
No model weights were retrained as part of this preparation; preserving their
provenance prevents silently changing model behavior without validation.

## Fixed software gaps

- Event inference checks model hashes, feature order and objective.
- Inference requires seven complete consecutive hourly readings. An interior
  history gap now suppresses scores in Python, as in the ESP32 runtime.
- Heatmaps never fill missing temporal features with zeros. Untrained heads
  remain unavailable.
- Strategy A classifies measured nodes then interpolates scores. Strategy B
  interpolates all seven raw history slices then derives features and classifies
  each cell. Both can be compared on the same grid.
- Nodes must have distinct finite coordinates and synchronized explicit times.
  Raw observations are checked against physical ranges. Out-of-range values
  cannot produce apparently valid event maps.
- By default, maps mask cells outside the node convex hull. Two nodes support
  only their connecting segment. Explicit extrapolation remains experimental.
- Independent-field evaluation supports exact six-hour matching, persistence
  comparisons, per-station measurement errors, and chronological event-score
  calibration. Test labels never fit the calibration model.

## Reproduce the bench prototype

```sh
python3 -m unittest tests.test_field_validation tests.test_spatial_readiness tests.test_event_classifier tests.test_esp32_ml_integration tests.test_six_sensor_forecast tests.test_midpoint -v
python3 -m ml.deployment.readiness
python3 -m ml.deployment.audit_himachal
python3 -m ml.event_classifier.heatmap --input reports/deployment/synthetic_nodes.json --strategy both --extent 0 100 0 100 --grid-size 10 --idw-only --output reports/deployment/synthetic_heatmap
```

The map command produces `maps.npz` and `manifest.json`. The fixture is explicitly
synthetic; this demonstrates software operation, not field accuracy. Coordinates
are planar meters in a shared local projection, not latitude/longitude.
Real node JSON uses the same structure: x, y, timestamp_utc, the six canonical
channels and seven `history` dictionaries. Default CLI strategy is A.

ESP32 builds, upload commands and automated physical replay are in
[the ML integration guide](../esp32/ml_integration/README.md). No new hardware
execution is claimed by this update. LoRa integration remains deferred per the
ML-first scope; it is not tested by these host checks.

## What the existing Himachal files support

The fresh audit in `reports/deployment/himachal_readiness.json` fingerprints all
four supplied CSVs and checks units, duplicates and broad physical ranges.
There are 43,909 exact station/coordinate/time matches after screening, including
2,047 at AWS IIT Mandi. These are four-channel matches, not a six-channel dataset.
Wind is converted from km/h to m/s; mb is numerically hPa. Pressure reference,
repeated values and source timezone remain unresolved.

Missing PM channels must not be filled with arbitrary constants, borrowed from
a distant city, or inferred from AQI and then presented as observed readings.
The earlier missing-PM diagnostic is not a valid production evaluation.

## Independent field evaluation

The six-hour forecast can be tested without event labels. Once a verified
six-channel file exists, use `ml.deployment.evaluate_forecast` before local
retraining. It rejects incomplete/out-of-range rows, naive timestamps and
unverified source declarations. Each test forecast is paired only with an
observation from the same station at exactly `t + 6 hours`; the saved student
is compared with the unchanged-current-value (persistence) baseline.

`observations.csv` must have exactly `timestamp_utc,location_id,temperature_c,relative_humidity_pct,pressure_hpa,pm25_ug_m3,pm10_ug_m3,wind_speed_mps`.
Every timestamp needs an explicit UTC offset, and all six measurements must be
observed at the same location and hour. The provenance JSON needs
`observation_source`, `timezone_verified: true`, `units_verified: true`, and
`pressure_reference: "station"`, supported by the provider's metadata.
Choose and freeze the test start before inspecting model errors:

```sh
python3 -m ml.deployment.evaluate_forecast --observations observations.csv --provenance provenance.json --test-start 2025-01-01T00:00:00Z --output reports/deployment/local_forecast_test.json
```

The date is an example. The four Himachal weather files cannot be passed to
this command as a six-input test because neither PM channel is present. The
Indian five-channel experiment also lacks verified station pressure. Potential
particulate routes are the [CPCB data repository](https://airquality.cpcb.gov.in/AQI_India/)
and [government hourly AQI data](https://www.data.gov.in/catalog/real-time-air-quality-index),
but neither source has yet yielded verified, colocated hourly PM2.5 **and** PM10
measurements for AWS IIT Mandi. AQI values or other-town PM must not be used as
substitutes. The IIT Mandi environmental-engineering lab
[lists a PM2.5 sampler](https://scene.iitmandi.ac.in/teaching_labs_details/environmental-engineering-lab),
which is a possible inquiry route, not evidence of hourly PM10 coverage.

For board testing, no ESP32 serial port was visible during the latest local
check. Once a board is connected, follow the upload and replay commands in
[the ML integration guide](../esp32/ml_integration/README.md); the generated
`results/esp32_board_test.json` will contain measured inference latency.

For event validation, collect independently recorded positive and negative
examples with timestamps and sites. Unknown labels stay blank. The current
rainfall file contains only wet records, so it cannot supply negative examples.

Prepare three files after obtaining observations:

1. `observations.csv`: timestamp_utc, location_id, temperature_c,
   relative_humidity_pct, pressure_hpa, pm25_ug_m3, pm10_ug_m3, wind_speed_mps.
   Use verified UTC or explicit UTC offsets, matching hourly station samples.
2. `labels.csv`: timestamp_utc, location_id and the twelve event-name columns
   in `ml/event_classifier/features.py`. Use independently observed 0/1 labels;
   leave unknown labels blank. Do not use the input-derived rules as ground truth.
3. `provenance.json`: observation_source, label_source,
   independent_event_labels=true, timezone_verified=true, units_verified=true,
   pressure_reference="station". These declarations need supporting source
   evidence; the evaluator cannot independently certify a user declaration.

Choose a cutoff before inspecting test results, then run:

```sh
python3 -m ml.deployment.field_validation --observations observations.csv --labels labels.csv --provenance provenance.json --test-start 2025-01-01T00:00:00Z --output reports/deployment/field_evaluation.json
```

The date above is an example, not a prescribed cutoff. Calibration fits only
pre-cutoff records. It needs at least 20 positives and 20 negatives; this is a
minimum software guard, not proof of adequate sample size or independent events.
Post-cutoff Brier score, AUC, precision/recall and false positives/negatives are
reported, alongside uncalibrated metrics. Correlated hours are not independent
weather episodes. Review performance by site/season and on untouched sites,
and quantify uncertainty before any release decision. The report does not
automatically approve deployment or install calibration into ESP32 firmware.

## Gates that still require evidence

| Claim | Required evidence |
| --- | --- |
| Accurate Mandi forecasting | Aligned six-channel local holdouts, acceptable per-variable errors and persistence comparison |
| Reliable actual hazards | Independent observed events; per-class false-alarm/miss analysis across time and sites |
| Six-hour hazard warning | Future-event targets, a separately trained model and lead-time evaluation; current event model is contemporaneous |
| All twelve events work | Adequate positives/negatives and held-out evidence for skipped/rare classes; no synthetic positives presented as field data |
| Calibrated probability | Calibration learned separately and evaluated on untouched independent observations |
| Spatially validated heatmap | Withhold real node observations and evaluate reconstruction; both synthetic-strategy agreement and interpolation are insufficient |
| Physical deployment | On-board replay, inference timing, power/sensor checks; LoRa packet loss/delivery testing when that integration resumes |

`reports/deployment/readiness.json` records all twelve classes and their data
sparsity flags. Its alert gates remain closed. Dust has no positive examples in
the saved evaluation splits; the cold-front rule has only twelve training
positives. A trained model file is not sufficient evidence of reliability.

## Newly downloaded independent rainfall source

The official hourly Himachal rainfall download has 166,355 rows. Matching it
with the screened weather data gives 1,431 candidate rows, including 45 at
IIT Mandi. However, the entire rainfall file contains no zero-rainfall rows;
all matched examples are wet. It cannot support binary detection validation
or calibrated rain probabilities without independently observed dry periods.
See [source details](../data/field_sources/README.md) and the reproducible
`ml.deployment.audit_rainfall` command. This is progress in acquiring independent
measurements, not evidence that the model now detects real rain reliably.

## Field-trial preparation update

The ML integration firmware now exposes build/model identity, boot IDs,
monotonic record sequences, original measurements and forecast timestamps.
The serial recorder journals accepted and rejected records with host reception
times, enforces the intended build ID, and quarantines stale observations.
See the integration guide for commands. This closes traceability and logging
gaps but does not provide live sensor drivers, LoRa transport, calibrated
hazard warnings or physical device validation. Board/sensor models, wiring,
site and the first deployment mode still need to be specified.
