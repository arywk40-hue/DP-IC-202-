# Himalayan weather-event forecasting scope — 8 October 2026

Cloudburst and Himalayan weather-event forecasting remain project objectives.
The three currently fitted India measurement-threshold heads do not complete
this objective. Adding an event name or testing a rainfall proxy does not fit
an independent cloudburst detector.

The physical weather inputs remain temperature, relative humidity, station
pressure, PM2.5, PM10 and calibrated wind. Site coordinates, elevation and
timestamps describe the node. Rain/event records may provide offline targets
and validation without becoming additional deployed sensor channels.

| Requested research output | Current implementation/evidence | Next missing evidence |
| --- | --- | --- |
| Localized extreme-rainfall / cloudburst risk | Cloudburst event schema, admission, matching and training pipeline exist; no fitted head | Verified local rain-rate/event timing, locations, rainfall definition and monitored non-event periods |
| Heavy-rainfall risk | Hazard pipeline prepared; prior rain/flood scores imitate input rules | Independent rainfall targets and causal matched sensor histories |
| Storm / strong-wind risk | +6h high-wind measurement head fitted; independent storm head absent | Observed storm/gust labels; evaluate missed events and false alarms |
| Snowstorm / snowfall and freezing conditions | Legacy snowstorm head is untrained; frost/freezing rules are diagnostics | Independent snowfall/frost/freezing observations and target definitions |
| Fog, heat and cold episodes | Future near-saturation/hot measurement heads and current rule diagnostics exist | Visibility observations; local temperature normals, event duration and independent episode labels |
| Wildfire-conducive weather | Surface feature/rule diagnostics and hazard pipeline prepared | Independent fire attribution, event chronology and monitored negatives |
| Flash-flood or landslide weather contribution | Independent-event pipeline prepared; no fitted disaster head | Occurrence records and relevant rainfall/catchment/slope context; weather-only predictors do not establish total physical risk |

Future measured thresholds at exactly +6h differ from the occurrence of an
event at any time in the next six hours. The existing hazard matcher targets
exact future observed windows. A different warning window needs an explicit
target-definition change and fresh evaluation; no six-hour cloudburst lead-time
claim is currently established.

The subsequent [warning protocol v1](HIMALAYAN_WARNING_PROTOCOL.md) now implements
an explicit `next_h_hours` experiment alongside this preserved exact-window
benchmark. It still needs admitted real data and fresh model/evaluation results.

## Sources found for the cloudburst work

- [IMD Shimla July 2024 incident report](https://mausam.imd.gov.in/shimla/mcdata/disasterous_event.pdf)
  includes Padhar, Mandi in a 31 July multi-location incident entry. The
  underlying information is media-sourced, and rainfall intensity is blank.
  Preserve it as a reported incident candidate, not verified rain-rate truth.
- [HPSDMA major-event narrative](https://hpsdma.nic.in/admnis/admin/showimg.aspx?ID=3664)
  has a Rajvan/Rajban, Padhar, Mandi case in the primary site's search index.
  The direct fetch timed out. Its date/time must be reconciled against the IMD
  report before any hourly label is assigned. No UTC time or coordinates were
  guessed.
- [IMD MAUSAM 2022 Himalayan study](https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/7150),
  published 1 October 2026, reports 66 cases. The abstract is a discovery lead,
  not 66 admitted labels; original records, rain-rate evidence and negative
  coverage remain unverified. The current archive also needs 2022 coverage for
  a matched experiment using those cases.

These sources are registered as **candidates** in
`configs/hazard_sources.json`. None was used for fitting or scored as ground
truth. Original source rights, event identity and spatial/time uncertainty still
need review. The [IMD cloudburst study](https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/5084)
describes localized rainfall of at least 100 mm in an hour; the existing six
channels do not directly measure that quantity. They can be tested as predictors
of independently verified events, without claiming rainfall measurement.

## Work required to fit and test the event heads

1. Obtain the dated event records plus verified rain-rate evidence where the
   cloudburst definition requires it, and independently monitored negatives.
2. Match causal six-channel histories from the same area to the event windows.
   Keep unknown times, locations and outcomes unavailable.
3. Fit separate multilabel heads using the existing hazard pipeline; keep entire
   episodes and sites out of training for selection, calibration and final tests.
4. Report event recall, false alarms and measured lead time. Artificial data may
   exercise interfaces and failure cases; it cannot establish field event accuracy.

No cloudburst probability or fitted Himalayan disaster model is claimed by
this scope update. The blocking issue is missing independent target evidence,
not the absence of a named output in the software.

## Integration update — 9 October 2026

The independent-event pipeline now accepts `snowstorm`, alongside `cloudburst`,
`flash_flood` and `landslide`. Snowstorm admission requires a reviewed source
with independently confirmed occurrence, a documented event definition, time,
location and the existing provenance checks. A cold/humid reading or rain gauge
measurement alone cannot admit a snowstorm. This adds a research target; it
does not train the legacy untrained snowstorm head or enable an ESP32 warning.

Once canonical event JSONL, station metadata, synchronized observations and
verified monitoring coverage are available, select the four targets explicitly:

```sh
python3 -m ml.hazard_context.cli train-hazards \
  --events /path/to/reviewed-events.jsonl \
  --stations /path/to/stations.csv \
  --observations /path/to/observations.csv \
  --monitoring /path/to/monitoring.json \
  --targets cloudburst flash_flood landslide snowstorm \
  --output /tmp/indra-himalayan-research-v1
```

These are placeholder input paths, not an acquired dataset. Use a fresh output
directory. The command writes per-target admission/support results and fits
only targets whose evidence and independent split checks pass. The existing
research trainer uses the India feature builder and XGBoost; this update does
not introduce a neural model or certify six-complete-channel training data.

The implementation sequence is:

1. Define each outcome and its time window, then obtain matched observations
   and both confirmed events and monitored non-event intervals. Rainfall can
   supply offline cloudburst evidence without becoming a seventh runtime input.
2. Establish a baseline separately for each target. Hold out entire events and
   sites. Evaluate recall, false alarms, calibration and actual warning lead time.
3. Compare a small temporal neural model using causal histories of the same six
   channels only after there is enough independent data. Its architecture is
   an experiment, not a substitute for labels or a guaranteed improvement.
4. Export an eligible model, verify host/ESP32 prediction parity and measure
   board latency. Until then these disaster outputs remain unavailable.

The current evidence cannot establish whether six local atmospheric channels
alone provide sufficient skill for flash floods or landslides. Additional
catchment/terrain context is a separate research option that must be evaluated
explicitly, without silently changing the six-channel deployment contract.
