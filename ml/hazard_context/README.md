# Independent Indian labels and ERA5 context research

**Confidential: do not publish before IP review.** [Audit](../../docs/hazard_label_audit.md) · [executed phase report](../../reports/hazard_context_phase/REPORT.md).

This additive package preserves the sensor-only baseline and China isolation. Direct sensor measurements, future sensor measurements, environmental-risk estimates, independently observed disaster records and retrospective reanalysis are different evidence. No new disaster output is deployed. No admitted real hazard corpus or real ERA5 files currently exists.

## Setup and verified fixture commands

Use Python 3.13 and a separate environment; preserve the original pinned environments.

```sh
python3 -m venv /tmp/indra-context-venv
/tmp/indra-context-venv/bin/python -m pip install -r requirements-india-sensor.txt -r requirements-hazard-context.txt
/tmp/indra-context-venv/bin/python -m pytest -q
/tmp/indra-context-venv/bin/python -m ml.hazard_context.cli audit-era5
/tmp/indra-context-venv/bin/python -m ml.hazard_context.cli download-era5  # dry-run, no authentication
/tmp/indra-context-venv/bin/python -m ml.hazard_context.demo --output /tmp/indra-hazard-demo-v1
```

Demo output is synthetic contract evidence only, with `real_events=0`, `real_era5_rows=0` and `hazard_models_fitted=0`. Choose a fresh directory for each run. Normal admission rejects its synthetic sources; an explicit unit-only override is used internally to test positive association mechanics. Synthetic counts/scores never establish hazard or ERA5 accuracy.

```sh
# Exercise normalization/matching/gates using the generated fixture.
python -m ml.hazard_context.cli normalize-events --events /tmp/indra-hazard-demo-v1/events.jsonl --sources /tmp/indra-hazard-demo-v1/sources.json --output /tmp/indra-hazard-vetted.jsonl
python -m ml.hazard_context.cli match --events /tmp/indra-hazard-vetted.jsonl --sources /tmp/indra-hazard-demo-v1/sources.json --stations /tmp/indra-hazard-demo-v1/stations.csv --observations /tmp/indra-hazard-demo-v1/sensor_fixture.csv --monitoring /tmp/indra-hazard-demo-v1/monitoring.json --output /tmp/indra-hazard-matched.csv
python -m ml.hazard_context.cli train-hazards --events /tmp/indra-hazard-vetted.jsonl --sources /tmp/indra-hazard-demo-v1/sources.json --stations /tmp/indra-hazard-demo-v1/stations.csv --observations /tmp/indra-hazard-demo-v1/sensor_fixture.csv --monitoring /tmp/indra-hazard-demo-v1/monitoring.json --output /tmp/indra-hazard-gates-v1
```

Here `python` means the isolated environment interpreter. Hazard fitting must remain blocked for this synthetic example. The commands are real interfaces, not claims of acquired data. Invalid event rows are retained in `.quarantine.jsonl` with input hashes; uncertain valid rows retain null fields and computed candidate/research status. Provider exports need an explicit mapping into the canonical JSONL schema; no column/clock/coordinate guessing or fabricated event adapter is provided.

## Formal schema and admission

For the explicit next-six-hour onset experiment, use `warning-labels` or
`train-hazards --label-mode next_h_hours` with
`configs/himalayan_warning_v1.json`. The [warning protocol](../../docs/HIMALAYAN_WARNING_PROTOCOL.md)
documents complete six-channel history, full monitoring windows, uncertainty,
episode metrics and the validation alert budget. `exact_future_window` remains
the historical default; neither mode currently has admitted real hazard data.

### Public landslide candidate acquisition

```sh
python3 -m ml.hazard_context.coolr \
  --output results/field_sources/coolr-north-new-snapshot \
  --audit-output reports/hazard_context_phase/coolr-north-new-audit.json
```

Use fresh paths. This requests Indian reports within 29–36°N and 72–81°E,
checks the complete returned object-ID inventory and preserves originals in
the ignored local output. `candidates.jsonl` is compatible with event
normalization but remains candidate-only. Serialized dates/approximate clocks
are not assumed to be UTC occurrence times. No monitored negatives, fitted
weights or validation labels are produced. The committed summary contains
counts and provenance rather than raw report text.

The [9 October acquisition review](../../docs/reference/HIMALAYAN_EVIDENCE_PROGRESS.md)
records the current six-channel gaps and the response to the supplied scope audit.

`train-hazards --targets cloudburst flash_flood landslide snowstorm` selects
the requested Himalayan research heads. The default target list also includes
snowstorm. All targets still require independent admission and held-out support;
snowstorm specifically requires confirmed occurrence, not a cold/humidity or
rainfall proxy. See [integration scope](../../docs/HIMALAYAN_EVENT_SCOPE.md).

`configs/hazard_event_schema.json` and `events.FIELDS` define nullable factual attributes: stable report/event/group IDs and original reported event IDs, provider/dataset/version/record/hash/retrieval provenance, UTC interval, coordinates or GeoJSON Point/Polygon/MultiPolygon, location/time uncertainty, original date/location/time text, definition/measurement/unit, country/state/district, quality/confidence and rights. Unknown location/time/severity stays null. Country/type and source identity must be explicitly known for an Indian record; unsupported or malformed raw rows quarantine. Dates without verified UTC interpretation remain original text, never guessed midnight. No centroid or severity is invented.

Statuses: `candidate` means source discovery, `research_only` means incomplete or qualified evidence, `admitted_for_training` means independent definition/time/location/uncertainty/QC/provenance and reviewed rights pass; `rejected` means incompatible source/label. Source review must additionally confirm physical event identity (`event_identity_reviewed=true`) and supply a nonempty adjudicated group ID. Proximity clustering alone cannot admit an event. These are evidence reviews, not automatic proof of truth. Source-level review is in `configs/hazard_sources.json`. Cloudburst additionally requires specifically verified local gauge evidence and its intensity/definition; RH, pressure, ERA5 or satellite rain cannot satisfy that check. Satellite thermal detections can only be qualified thermal-anomaly targets, never automatically wildfire. Restricted records require `--restricted`, and fitted artifacts go to a separate `restricted/` view; clean fits use `clean/`.

Minimum research screen: 50 conservative independent episode groups, 10 positive sites, two years, five known districts and 30 verified negative site-days. Actual splits additionally require train/selection/calibration/test positive episodes ≥20/10/10/10 and at least 10 negative episodes each. These floors are predeclared conservative guards, **not sufficient statistical evidence or deployment approval**. Missing administrative fields remain unknown and can block the screen.

## Matching, monitoring and leakage

Matching CLI accepts `--matching-config` containing a subset of `matching.DEFAULTS`; unknown parameters refuse. Matching inputs are reviewed events, unique physical-site registry, observed explicit-UTC windows and a separate monitoring JSON list. Parameters in `matching.DEFAULTS` configure radius, pre/event-context/post windows, negative exclusion/separation and uncertainty limits. Event-context expansion never fabricates observed event duration. Point distances use WGS84 geodesics; regional polygons retain their footprint and uncertainty. Polygon boundary distances approximate geodesic segments; dateline-crossing geometry is rejected. No state/district join is used as a substitute for location.

A positive is an observed **nearby-event association**, not proof of disaster at a weather station. Pre/post/uncertain/candidate associations stay unlabeled. A negative needs a reviewed monitoring ID, physical site/target, explicit UTC coverage, independent/complete-coverage flags, definition, provider/version/license/rights evidence/reviewer/retrieval/hash and category `confirmed_negative` or `monitored_no_event`. `spatial_coverage_radius_km` must cover the experiment's radius: a dry point gauge cannot establish no cloudburst anywhere within 20 km. Unknown events conservatively exclude potential negative windows.

Exact duplicate reports collapse; conflicting duplicates stop matching for adjudication. A deterministic temporal sweep groups supplied physical IDs and close co-occurring reports across hazard types. This is conservative leakage grouping, not a claim they are identical events. Whole multi-station/multi-day groups stay in one role; crossing and temporally buffered groups drop wholly. Global 72h background blocks prevent correlated negative windows being randomly split. Pair budgets refuse oversized ambiguous batches; use a frozen complete event master and preserve its group IDs when partitioning station/date matching.

Hazard targets join exact future observed windows at +6h; event/time/label fields are never predictors. Selection uses the frozen validation-only weight/threshold policy; calibration and final testing are later/disjoint. Operating curves are validation diagnostics, not test retuning. Episode scoring reports detection, first-alert lead time, missed-event fraction and true/false/unknown alert episodes. Unknown monitoring periods never count as false alerts. Hourly F2 selection may still favor long events; no new empirical effectiveness claim exists.

## ERA5 preparation and matched research

The unchanged 24 monthly requests in `data/registry/cds_physics_requests.json` cover 2023/2024, all valid days/UTC hours, `[38,68,6,98.5]`, T/dewpoint, surface pressure and u/v wind. [Manual access instructions](../../reports/hazard_context_phase/ERA5_ACCESS.md). `download-era5` is dry-run by default; executing requires normal personal authentication and explicit manual terms acceptance. Existing files/partials are not overwritten; ZIP/non-NetCDF responses remain partial for inspection. The downloader is mocked in tests, **not authenticated against CDS**.

Authorized raw files can be normalized with:

```sh
python -m ml.hazard_context.cli prepare-era5 --input data/backgrounds/raw/era5_land/era5_land_2023_01.nc --stations data/india_sensor/offline/processed/stations.csv --metadata /path/to/reviewed-era5-metadata.json --output data/hazard_context/v1/background.parquet
python -m ml.hazard_context.cli compare --observations /path/to/canonical-noaa-sensor-view.csv --background data/hazard_context/v1/background.parquet --manifest data/hazard_context/v1/background.manifest.json --scope national --output data/hazard_context/v1/comparison-national
python -m ml.hazard_context.cli episodes --input /path/to/research-episode-predictions.csv --threshold VALIDATION_SELECTED_RAW_CUTOFF --output /tmp/episode-diagnostics.json
```

Repeat comparison with `temporal`, `himalaya_holdout` and `himalaya_only` on the **same frozen data/splits**. Real commands above remain data-blocked; fixture/unit tests verify their underlying functions. Metadata must identify provider=`ECMWF/Copernicus`, dataset=`era5_land`, country=`IN`, version, retrieval UTC, license/rights and review URI. Real normalized-file hash must match the manifest. All files retain raw SHA256 and per-row ancestors. Time is CF-decoded UTC under the verified ERA5 product contract; reversed coordinates, 0–360 longitude, duplicate times, missing pixels/units and ambiguous members are checked. Partial variable files require exact shared coordinates; conflicting overlapping exports refuse. Extraction crops four pixels before loading.

Named features: `era5_temperature_c`, `era5_dewpoint_c`, `era5_surface_pressure_hpa`, `era5_u10_mps`, `era5_v10_mps`, derived wind speed, RH and dewpoint depression. Grid-surface pressure is not station or sea-level pressure. No precipitation, CAPE or invented hazard input is added to these requests.

For completed station hour ending H, context uses exactly the provider instant H−1h; this is **preceding-hour instantaneous context, not a measured hourly mean**. No nearest time, extrapolation or future fill. Default mode is `retrospective_background_context`, because reanalysis publication/forcing can include later/held-out observations. `availability_verified_context` masks values unless explicitly verified publication time is between sample and issue; normalized files have unknown availability by default. No real-time deployment claim follows.

Track S uses the unchanged causal sensor builder; Track SB adds only named background features afterward. Fit/calibration/test rows and labels are exactly matched on the common complete-background subset, with SHA256 of selected keys. S is refitted on those same rows, so differences are not caused by sample coverage. Paired station-bootstrap Brier differences, per-track metrics/calibration and validation cutoffs are separate from the old full-data S scores. Synthetic comparisons require explicit unit-only opt-in. Nothing updates old weights/results or the ESP32 interface.

## Remaining real-data work

IMD permission/complete rain and event exports, resolved source rights, full event IDs/uncertainty/monitored negatives, CDS files/publication receipts, and verified PM clock/provider metadata remain necessary. OpenAQ's API needs a key; its documented public S3 archive is another lawful access route, but does not by itself establish country/provider license/QC or averaging intervals. No new PM head is admitted. No official Himalayan boundary was obtained: keep the existing geography proxy caveat.
