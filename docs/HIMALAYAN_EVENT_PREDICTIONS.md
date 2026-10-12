# Required Himalayan event outputs — 12 October 2026

Cloudburst and storm predictions are required project outputs. The numerical
six-hour Mandi forecast is a separate task; it does not finish the event models.

The current protocol is `configs/himalayan_warning_v2.json`: **cloudburst,
storm, flash flood, landslide and snowstorm**. Version 1 remains unchanged for
prior evidence. Next-H-hour CLI defaults now use v2. No real hazard head is fitted.

## Independent target evidence

| Target | Required evidence |
| --- | --- |
| Cloudburst | Verified local one-hour gauge intensity, event identity and timing |
| Storm | Confirmed thunderstorm/squall under a reviewed definition, onset, location and identity |
| Flash flood | Confirmed rapid flood episode and catchment/location |
| Landslide | Confirmed slope-failure occurrence with reviewed onset/location |
| Snowstorm | Independently confirmed snowstorm, beyond snowfall or cold/humid readings |

The same six channels and causal history are predictors. Rain, gust and incident
records provide offline outcomes; they do not add a physical deployed channel.
An onset in the next six hours does not guarantee six hours of achieved warning.

## New observed storm evidence

Audited existing Indian NOAA GHCNh station-year files for Mandi, Sundernagar,
Bhuntar, two Shimla IDs and Kangra, 2023/2024. NOAA describes these observed
fields in its [dataset documentation](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly).
Its [weather-code tables](https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh-present-weather-elements.pdf)
were downloaded, hashed and visually reviewed. Manual MW and automated AW codes
are interpreted separately; current and preceding-hour reports stay distinct.
AU combinations remain undecoded. Gust alone is not a thunderstorm label.

Found **869 distinct station/report timestamps**, including **26 at Mandi**.
These are not 869 independent storm episodes. Mandi's median report gap is
15 hours; several neighboring synoptic stations have three-hour gaps. Observed
report time is preserved separately from unknown episode onset. Unknown event
groups and timing/location uncertainty stay null. PM and verified continuous
non-event monitoring are absent.

Canonical candidates remain local/ignored in
`results/storm_evidence/ghcnh_hp_2023_24/candidates.jsonl`. Provenance/counts are
in `reports/hazard_context_phase/storm_observation_audit.json`.
**Admitted episodes: 0. Complete matched six-channel windows: 0. Models fitted: 0.**

```sh
python3 -m ml.hazard_context.storm_audit \
  --output results/storm-evidence-new-version \
  --audit-output reports/hazard_context_phase/storm-audit-new-version.json \
  --code-receipt results/storm_evidence/weather_codes.receipt.json
```

Use fresh paths; original station files are read-only and hashed.

## Fitting when evidence is admitted

Storm now requires confirmed occurrence in admission; a rain-gauge record
cannot admit it. Cloudburst retains verified local gauge evidence. Both route
into complete six-channel history, next-six-hour onset labels, whole-event/site
splits, validation alert budgets and event/lead-time evaluation.

```sh
python3 -m ml.hazard_context.cli train-hazards \
  --events data/hazard_context/reviewed_events.jsonl \
  --stations data/hazard_context/stations.csv \
  --observations data/hazard_context/six_channel_observations.csv \
  --monitoring data/hazard_context/monitoring.json \
  --config data/hazard_context/reviewed_sensor_config.json \
  --label-mode next_h_hours \
  --warning-protocol configs/himalayan_warning_v2.json \
  --targets cloudburst storm flash_flood landslide snowstorm \
  --output results/himalayan-events-v2
```

These are example paths, not acquired training data. Next, adjudicate the storm
episodes/onsets and obtain matched measured six-channel histories and monitoring.
Cloudburst still needs verified local hourly gauge evidence. The institutional
request now explicitly asks for realized thunderstorm/squall logs and gust
metadata; forecasts and nowcast warnings do not supply occurrence truth.

Until the evidence passes, event scores remain unavailable and accuracy is
undefined. The numeric Mandi API benchmark reports the same unavailable event
targets rather than learning them from modeled rain/weather proxies.
