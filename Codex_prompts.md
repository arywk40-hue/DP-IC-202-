# INDRA — copy-paste Codex prompt set
Prepared 14 October 2026; corrected to conventional ML after user clarification. Use with INDRA_review.md, planning_simulation.py,
planning_results.json and export_probe.json in the accompanying package.
Paste the master prompt first. Paste one numbered phase prompt at a time.
Paths labelled “create” are proposed new paths, not claims that they already exist.

## 0. Master goal prompt

```text
Complete INDRA in https://github.com/arywk40-hue/DP-IC-202- using the supplied
INDRA_review.md and phases A-N in this file. Codex is the coding tool; the
INDRA application uses conventional machine learning and deterministic rules.
Do not add a runtime LLM, generative API client, chat interface or token billing.

First inspect current HEAD, working tree and AGENTS.md. The review inspected
6bcda6b689868682cabfd95808eeb611dcb4aed3; re-audit any later changes.
Current main already includes six-channel forecasts, Mandi modeled-data work,
India feature pipelines, independent-event evidence gates, operational ingestion
and spatial experiments. Extend useful modules and preserve existing work.

Goal: finish a separate Himachal research system for rain, snowstorm risk and
cloudburst_risk using temperature C, RH %, station pressure hPa, PM2.5/PM10
ug/m3 and wind m/s. Derived values, coordinates/elevation/time and health are
metadata/computations. Independent rain/snow outcomes may be offline labels;
they must not quietly become additional runtime sensor inputs.

Architecture:
1. ESP32-S3: calibrated sensor acquisition/QC, lightweight per-sample anomaly
   detection, compact local event model or rule fallback, buffered records and
   local operation during connectivity loss.
2. Dynamic N-node network: registration-only join, distance/elevation discovery,
   health and authentication, bounded peer queries, freshness, consensus and
   internet-independent local coordinator. No hard-coded peer IDs.
3. Server: conventional supervised event models, versioned model loading,
   calibration where independent evidence supports it, deterministic fallback,
   neighbour consensus, evidence summaries, alerts and FastAPI.
4. Spatial: elevation-aware regression kriging with returned variance/support,
   source-aware virtual backgrounds, sparse fallback, bounded local tiles.
5. NEW isolated React/Vite/Tailwind UI: all six charts, three risk cards, map
   layers/variance, source trust, node health, alert history and model/rule evidence;
   English/Hindi, mobile-first, low-bandwidth and offline/stale states.

Targets are explicit: current conditions versus onset in the next six hours.
The existing +6h numerical forecast does not itself establish event detection.
Cloudburst output is risk only; these channels do not measure rainfall intensity.
Snowstorm output does not establish measured snowfall, visibility or blizzard.
Use independently observed labels and complete monitored negatives.
Never train empirical hazard heads on rule-generated or synthetic labels.

Begin with rules and gradient-boosted trees; compare a small temporal model only
when independent local data supports that experiment. Distil/export an eligible
compact student separately. Preserve original model/feature/source versions.
When independent data is absent, finish the pipeline, tests and offline demo,
but report NOT_READY for empirical fitting/accuracy rather than inventing it.

Compute every feature deterministically: exact-window pressure/temperature/RH/PM
trends, dew point, VPD, NWS heat index and quality-aware PM-decline proxies.
Keep true native 15-minute data separate from hourly history. Never invent
finer samples, gusts, station pressure, availability times or event onset times.
Current Mandi/Beijing numerical teachers use history through 24h; the compact
student uses current values; seven-hour event snapshots are a separate contract.
Track sensor faults separately from environmental anomalies.

Design for arbitrary registered N; prototype 2-3, valley pilot 8-12 and regional
20+ across valleys/elevation bands. Bound work per incident/tile, not global N.
Three agreeing healthy physical nodes including origin are the proposed quorum;
record freshness, response coverage, distance/elevation weights and failure groups.
No quorum remains local-only/unknown, never safe.
Virtual IMD/ERA5/Open-Meteo nodes are source-tagged, lower/explicit trust and
excluded from consensus by default; correlated model cells cannot manufacture
physical votes or observed station coverage.
Kriging needs adequate spatial/elevation/pair-distance support, not just a count.

Run protocol/spatial/end-to-end simulation at 3,10,50,200 nodes with dropout,
packet loss, clock drift, duplicate/replayed records and common sensor faults.
Report latency including timeouts, frame/airtime load, synthetic false alarms,
missed episodes, CPU/memory and all denominators. Use actual scheduling/type-
approval-compatible Indian radio settings and verified airtime budgets.
Simulation does not establish field accuracy, range or board performance.

Reuse ml/six_sensor_forecast, ml/india_sensor, ml/india_mandi, ml/hazard_context,
ml/operational, ml/spatial_ensemble and existing ESP32 abstractions where useful.
master/kriging is absent; current heatmap code is ml/event_classifier/heatmap.py.
Create additive ml/himachal, server, simulator, esp32/himachal_node and
apps/indra-himachal-ui modules. Locate/hash protected teammate UI/shared paths;
the review found no frontend at inspected branch heads, so ask for its exact
location while working only in the isolated new application directory.

Requirements:
- Freeze strict request/response schemas, finite values, exact sensor order,
  source/pressure/cadence/time provenance and model/calibrator identities.
- Use null/abstain for unavailable probabilities/lead times. Raw scores are not
  calibrated probabilities. Unknown/stale data must never display as green zero.
- Explanation comes from actual rules/features/model contributions; no generated
  rationale or invented causal claims.
- No secrets in code/logs/browser. Weather-source credentials stay server-side.
- No fabricated accuracy/cost/latency or undocumented links/API capabilities.
- Preserve existing data/models/UI and user edits. Ask before destructive changes.
- Commit small coherent phases; run existing and relevant new tests each phase.
- Actual external notifications/public deployment need configured recipients and
  evidence readiness; tests use local fake sinks.

Complete the software with a documented one-command offline demo, committed
export verification, Python/C parity, dynamic registration/health/consensus,
three-target ML/rule interfaces, supported maps/uncertainty, API/UI, alerts,
Docker/CI/configuration/runbooks and 3/10/50/200 reproducible simulation receipts.
Maintain docs/plans/INDRA_HIMACHAL_PLAN.md and readiness.json.
Scientific completion additionally requires independent Himachal data, untouched
chronological/whole-event/station/season evaluation, measured false alarms,
calibration and real pre-onset lead time, plus physical ESP32/radio/power tests.
List these separately as blocked/untested when evidence is unavailable.
At each phase report files changed, commands/results, blockers and next steps.
```

## 1. Phase A — repo audit and CI/export-gap fix

```text
Objective: establish current truth, preserve teammate work and make committed
shipping model exports reproducible and directly tested.

Read: README.md, docs/ARCHITECTURE.md, docs/PROJECT_OVERVIEW.md,
configs/model_catalog.json, all requirements*.txt, .github/workflows/ci.yml,
ml/six_sensor_forecast/{contract,features,predict,c_codegen,export}.py,
tests/test_six_sensor_forecast.py, tests/test_esp32_ml_integration.py,
tests/test_india_mandi.py, all catalogued model reports and shipping headers.
Inspect firmware's actual included model paths. Search UI paths and AGENTS.md.

Create:
- docs/plans/INDRA_HIMACHAL_PLAN.md
- docs/plans/PROTECTED_PATHS.json
- docs/plans/CURRENT_REPO_AUDIT.md
- ml/deployment/verify_exports.py
- tests/test_committed_exports.py
- tests/fixtures/forecast_export_inputs.csv
- requirements-himachal.txt initially containing only the agreed common runtime
  dependencies for conventional ML and no generative API packages.

Change:
- .github/workflows/ci.yml to run the verifier explicitly.
- ml/six_sensor_forecast/export.py only as needed for a versioned deterministic
  export manifest and parity-fixture identity.
- Existing export reports/headers only for an explicitly documented provenance
  migration. Preserve model weights, numeric behavior and original evidence roles.

The review found legacy headers missing new country/evidence macros; today’s
active Mandi header reproduces. Do not mistake metadata differences for
demonstrated wrong predictions. Give exports an exporter/schema identity;
regenerate under its pinned version and compare committed bytes. If legacy
compatibility is retained, make it explicit and test it. Verify report/model
hashes, target order, model constraints, shipping header checksum and runtime
predictions for every firmware profile and the active Mandi export.

Compile the committed header, not only a new temporary header. Compare against
the exact committed model weights with physical bounds, every tree's threshold
and adjacent float32 values, missing/NaN/Inf/out-of-range rows and input/output
aliasing/null-pointer behavior as applicable. Put generated files in temporary
directories and fail if committed artifacts drift. No source dataset download
or retraining should be needed for CI.

CLI to implement:
python -m ml.deployment.verify_exports --catalog configs/model_catalog.json \
  --output reports/deployment/committed_export_verification.json --offline

Run:
python -m pip install -r requirements-physics.txt \
  -r requirements-hazard-context.txt -r requirements-operational.txt \
  xgboost==3.1.1 ruff==0.16.10
python -m pytest -q
ruff check ml tests esp32/ml_integration/tools --select E9,F63,F7,F82
python -m ml.deployment.verify_exports --catalog configs/model_catalog.json \
  --output reports/deployment/committed_export_verification.json --offline
git diff --check

Tests/acceptance:
- Header, weight and report tampering each fail verification.
- Active Mandi committed header is compiled and numerically checked in CI.
- No network/dataset/ESP32 board required for host tests.
- Existing source-country/research statuses remain correct.
- Protected-path hashes are unchanged. State explicitly if UI location is still
  unknown; do not invent an existing frontend.
- Summarize contradictory active docs versus clearly marked archived material.
- Commit only this phase after checks pass.
```

## 2. Phase B — deterministic native-cadence feature engine

```text
Objective: one versioned causal feature engine with explicit units, timing,
source reference and missing-state semantics, compatible with existing research.

Read ml/india_sensor/features.py, ml/operational/{contracts,aggregate,rules}.py,
ml/event_classifier/features.py and the forecast feature contract.

Create:
- ml/himachal/__init__.py
- ml/himachal/contracts.py
- ml/himachal/features.py
- ml/himachal/meteorology.py
- configs/himachal_features_v1.json
- tests/test_himachal_features.py
- tests/fixtures/himachal_native_observations.csv
- docs/HIMACHAL_FEATURE_CONTRACT.md

Reuse the existing canonical sensor order, unit conversions and timestamp/QC
rules through adapters. Do not rename or change frozen legacy feature meanings.
Include physical_site_id, registration ID, site elevation/datum, sensor/wind
height, native interval, source class/native cell identity, pressure reference,
observation/valid time and actual available_at. A relocated node starts a new
history. Extra measured sensor channels do not quietly enter model input.

Compute:
exact ΔP6h, ΔP1h and native ΔP15min; elapsed-time-normalized dP/dt/dT/dt;
temperature/PM/RH/wind trends; liquid-water dew point, documented ice-domain
behavior, VPD kPa, complete NWS heat index with its domain/status, PM2.5/PM10 ratio,
quality-aware six-hour summaries and explicit PM-decline proxies.

Initial washout setting is the median of the preceding three complete hourly PM
values, with PM2.5 decline >=max(5 ug/m3,20% baseline) and PM10 decline
>=max(10 ug/m3,20% baseline). Baselines <10/<20 respectively make evidence
unavailable. Calibration-derived noise criteria can add a required 3-sigma
decline when calibration exists. Native 15-minute washout uses a separately
versioned preceding-hour baseline; no implicit interpolation.
Initial sharp RH change is |ΔRH1h|>=10 percentage points. Wind-increase proxy
uses genuine ΔW15min>=3 m/s and current W>=8, never an inferred true gust.
All of these are research configuration choices, not validated meteorology.

Station, model-grid-surface and sea-level pressure remain separate source types.
Do not invent station pressure from grid inputs. Use same-site tendencies and
appropriate model-layer context. RH=0 dew point and PM10=0 ratio are unavailable.
Never silently replace missing values with zero, forward-fill gaps or use future
samples/publication times. Require true contiguous cadence per window.

Freeze a stable JSON feature packet. Event-model input can include seven complete hourly
snapshots plus native summaries; optional 24h teacher input availability must
be stated separately. Generate all numerical evidence IDs/units in code.

Run:
python -m pytest -q tests/test_himachal_features.py tests/test_india_sensor.py \
  tests/test_operational.py tests/test_six_sensor_forecast.py
python -m pytest -q
git diff --check

Tests/acceptance:
- Future perturbation cannot change earlier features.
- Missing, duplicate, reordered/off-grid, delayed, relocated and mixed-reference
  records produce the declared errors/missing states.
- Real 15-minute data passes; hourly-only data cannot produce Δ15min.
- Valid conversions include Pa/hPa, km/h/m/s, K/C and UTC/IST display conversion.
- NWS reference branches, 0/100% RH, subfreezing domain, PM denominator zero,
  washout/percentage-point boundaries and clean-air unavailable cases are tested.
- No old model/header fixtures change unless a separately justified migration
  is needed. All legacy tests continue to pass.
```

## 3. Phase C — rule baseline for the three requested targets

```text
Objective: offline research baseline using the new feature packet, with
deterministic evidence, availability and risk-only naming.

Create:
- ml/himachal/rules.py
- configs/himachal_rules_v1.json
- tests/test_himachal_rules.py
- docs/HIMACHAL_RULE_BASELINE.md

Use public keys rain, snowstorm and cloudburst_risk. Label snowstorm output
as snowstorm risk; do not claim confirmed snowfall/blizzard.
Implement the supplied rain and snow conjunctions as explicitly named current-
condition heuristic baselines, using complete same-site pressure history and
the versioned PM-decline proxy. A rule false is a non-match, not proof of safety.
An unavailable required feature yields abstention/unknown, not a negative label.

Provide a separate experimental cloudburst score, never a probability or
confirmation. Initial weighting proposal:
RH>=90: .20
real ΔP15min<=-1 hPa: .20
real ΔT15min<=-2 C: .20
wind-increase proxy: .15
quality-aware native washout: .15
calendar June-September proxy: .05
reviewed terrain-exposure prior: .05.
Terrain missing is missing, not a guessed elevation threshold. Do not renormalize
a partially observed score into artificial high confidence.
An hourly-only companion profile uses explicitly hourly/6h features and a
different profile name; never claim it is the 15-minute profile.

Proposed display thresholds watch>=.4 and warning-candidate>=.7 are configurable
research defaults. A warning candidate also needs at least three dynamic
measurement criteria, sufficient feature coverage, consensus policy and
human-confirm mode; month/elevation alone cannot trigger it. The supervised event model supplies the learned assessment when independently
fitted and available. Preserve raw rule and model results separately.

Output includes level, score, probability=null until an independently evaluated
calibration exists, feature availability, confidence kind, lead_time_h=null for
current conditions, triggered_evidence IDs/values/units, abstain, profile/version
and risk_only. Retain the required strict event fields; unknown status is
additional explicit metadata rather than a misleading green none.

Run:
python -m pytest -q tests/test_himachal_rules.py tests/test_himachal_features.py
python -m pytest -q

Tests/acceptance:
- Threshold equalities and missing/dirty PM baselines are covered.
- True rain in a synthetic clean-air scenario is not certified absent.
- Cloudburst text/API keys always retain risk meaning.
- Rules never produce independent training labels or measured detection metrics.
- No current-condition rule claims a measured six-hour advance warning.
- Storm pre-drop/rebound intervals cannot be confused with one same-time delta.
```

## 4. Phase D — downloads and independent labelling

```text
Objective: reproducible source acquisition, source-aware virtual-node material,
and independently admitted observed outcomes with monitored negatives.

Read the verified-source table in INDRA_review.md, docs/DATA_LICENSES.md,
ml/datasets, ml/hazard_context/{events,acquire,matching,warning,policy,cli}.py,
configs/hazard_sources.json, configs/himalayan_warning_v2.json and
docs/reference/IMD_HIMACHAL_DATA_REQUEST_PACKAGE.md. Reuse those gates.

Create:
- ml/himachal/data/__init__.py
- ml/himachal/data/sources.py
- ml/himachal/data/download.py
- ml/himachal/data/observations.py
- ml/himachal/data/labels.py
- ml/himachal/data/virtual_nodes.py
- configs/himachal_sources_v1.json
- configs/himachal_labels_v1.json
- tests/test_himachal_data.py
- tests/fixtures/himachal_reviewed_events.jsonl
- tests/fixtures/himachal_monitoring.json
- docs/HIMACHAL_DATA_PIPELINE.md

Change only as necessary:
ml/hazard_context/events.py and configs/hazard_event_schema.json to add an
independently defined rain target without breaking existing event schemas.
Use a new protocol profile rather than overwriting existing v1/v2 experiments.
Cloudburst observed labels remain separate from public cloudburst_risk output.

Verified entry links:
ERA5: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels
IMERG: https://gpm.nasa.gov/data/imerg
       https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGHH_07/summary
Open-Meteo: https://open-meteo.com/en/docs/historical-weather-api
            https://open-meteo.com/en/docs/air-quality-api
NASA POWER: https://power.larc.nasa.gov/docs/services/api/temporal/hourly/
IMD: https://dsp.imdpune.gov.in/
     https://mausam.imd.gov.in/shimla/
CPCB: https://cpcb.gov.in/air-quality-management-portals/
OpenAQ: https://docs.openaq.org/resources/measurements
        https://docs.openaq.org/resources/licenses
HPSDMA: https://hpsdma.hp.gov.in/
Candidate PDF: https://mausam.imd.gov.in/shimla/mcdata/disasterous_event.pdf

Use provider documentation and current portal-generated request formats.
Do not invent dataset IDs, file URLs or API paths. IMD/CPCB bulk permissions,
historical AWS access and source rights remain source-specific; provide an
audited manual-import adapter where an approved feed is unavailable.
Read credentials from environment/user-managed files. Mock network in CI.

Cache immutable raw downloads with request, provider/collection version,
retrieval time, checksum, licence/rights evidence, returned grid/station ID,
native cadence/resolution, units and provenance. Bound retries/resources.
Handle provider missing sentinels, rate limits, resumable chunks and partial
downloads. Use UTC explicitly; NASA POWER defaults to LST unless changed.

IMERG mm/h rates become half-hour accumulation before hourly summing. Missing
intervals stay missing. Daily IMD rainfall is not hourly cloudburst truth.
ERA5/Open-Meteo/POWER are background/reanalysis/model data, not an independent
local gauge. Weather/PM from different grid cells are not six co-located
measurements. Deduplicate OpenAQ/CPCB copies and model cell identities.

Use observed rain gauge/snow reports with source-defined measurement windows,
event definitions, original local time, coordinate/time uncertainty, QC and
reviewed physical event group IDs. Store accumulations, duration/statistic and
units structurally. Cloudburst admission needs reviewed local rainfall evidence
consistent with the one-hour definition; a media incident or 0.1-degree satellite
cell cannot satisfy it. Define rain onset/amount/duration with the user or a
documented gauge-sensitive research profile, not an undocumented universal rule.

Negative windows need complete compatible monitoring and no possible/candidate
event overlap. Unknown outcomes stay null. Whole events and sites remain grouped;
a date-only incident cannot become a guessed midnight UTC label.
Synthetic fixtures remain SYNTHETIC_CONTRACT_ONLY and cannot enter empirical
training. The existing admission engine must not be weakened to make training run.

CLI to implement:
python -m ml.himachal.data.download --config configs/himachal_sources_v1.json \
  --source SOURCE --start YYYY-MM-DD --end YYYY-MM-DD --output LOCAL_PATH
python -m ml.himachal.data.labels --events EVENTS --observations OBSERVATIONS \
  --monitoring MONITORING --config configs/himachal_labels_v1.json \
  --output LOCAL_PATH --offline

Run mocked fixture commands and:
python -m pytest -q tests/test_himachal_data.py tests/test_hazard_context.py \
  tests/test_warning_windows.py tests/test_dataset_pipeline.py
python -m pytest -q

Acceptance:
- Repeated offline processing reproduces manifests/labels.
- No fabricated co-location, pressure, time, coordinates, negatives or rights.
- Observed/virtual/reanalysis/synthetic roles survive to output.
- Unsupported or insufficient datasets yield NOT_READY with detailed counts.
- Public candidate events remain candidates until reviewed evidence passes.
```

## 5. Phase E — ESP32-sized anomaly inference and C parity

```text
Objective: per-sample local anomaly/QC and a compact rule indicator, independent
of server connectivity. No fake fitted hazard model.

Create:
- ml/himachal/anomaly.py
- ml/himachal/anomaly_codegen.py
- configs/himachal_anomaly_v1.json
- esp32/himachal_node/platformio.ini
- esp32/himachal_node/include/indra_anomaly.h
- esp32/himachal_node/include/indra_local_rules.h
- esp32/himachal_node/include/device_config.example.h
- esp32/himachal_node/src/main.cpp
- tests/test_himachal_anomaly.py
- tests/test_himachal_anomaly_c.py
- docs/HIMACHAL_EDGE_VALIDATION.md

Reuse/adapt esp32/operational_node sensor abstractions and canonical order;
preserve its compile-only/default-disabled boundary.
Implement finite/range/CRC/time/missing checks and robust EWMA/median-MAD residual
inference. Distinguish sensor_fault, environmental_anomaly, warmup and unavailable.
Train/select any thresholds on appropriate development data only. Maintain
explicit minimum scale/noise floors so MAD=0 cannot divide by zero.
An abrupt valid meteorological change is not automatically rejected as sensor
failure. Encoder-zero during calm weather is not a sufficient fault diagnosis.

Initial proposed module budgets: anomaly flash<=32 KiB, working RAM<=4 KiB.
Use fixed-size ring buffers/state and bounded operations; no heap in inference.
Derive actual board flash/PSRAM/pins/cadence from supplied configuration.
Implement the current-condition/risk-only rule indicator where supported.
If an independently fitted edge event model is unavailable, return unavailable
for its model probability; never relabel a rule imitator as a real event model.

C and Python must share constants/version/state semantics and a generated
parity manifest. Test reading boundaries, warmup, time gaps/reboot, slow drift,
stuck/CRC-fault scenarios and fast genuine weather changes. Keep skipped heads
unavailable rather than constant zero.

CLI to implement:
python -m ml.himachal.anomaly_codegen --config configs/himachal_anomaly_v1.json \
  --output esp32/himachal_node/include/indra_anomaly.h --verify

Run:
python -m pytest -q tests/test_himachal_anomaly.py tests/test_himachal_anomaly_c.py
python -m pytest -q
pio run -d esp32/himachal_node
pio run -d esp32/operational_node
pio run -d esp32/ml_integration -e esp32-s3-ml -e esp32-s3-ml-usb

Acceptance:
- Host-compiled C matches Python on the declared corpus/tolerance and status flags.
- Actual compile/object/firmware sizes are recorded, not guessed.
- Hardware execution/latency remains NOT_TESTED without a connected board.
- Physical mode requires real pin/calibration/clock configuration.
- Local indication works without server/API; no external alert is sent in tests.
```

## 6. Phase F — N-node registration, health, neighbours, radio protocol

```text
Objective: dynamic bounded consensus with internet-independent local operation,
a source-aware node-health layer and a real scheduling stress simulator.

Create:
- ml/himachal/nodes.py
- ml/himachal/health.py
- ml/himachal/neighbours.py
- ml/himachal/radio.py
- ml/himachal/consensus.py
- configs/himachal_network_v1.json
- configs/india_radio_profile_v1.json
- simulator/network.py
- simulator/radio.py
- simulator/run_network.py
- esp32/himachal_node/include/indra_peer_protocol.h
- esp32/himachal_node/include/indra_consensus_policy.h
- tests/test_himachal_registration.py
- tests/test_himachal_health.py
- tests/test_himachal_consensus.py
- tests/test_himachal_radio.py
- docs/HIMACHAL_NETWORK_PROTOCOL.md

Registration/config supplies coordinates/elevation/datum, native cadence,
capabilities, source/trust, per-node auth and failure-domain metadata.
New nodes join without editing source. Use a spatial index and dynamic updates,
not an all-N hard-coded ID list or an unbounded all-pairs query.
Default nearest eligible radius<=5 km and elevation difference<=750 m; weight
quality*exp(-d/3km-|dz|/500m). Query at most six peers; global N is unrestricted.
Validate observed freshness<=120 s and clock uncertainty<=30 s for the
minute-sampling initial profile; longer-cadence sources need an explicit profile.

Require origin+at least two distinct agreeing healthy authenticated physical
peers, weighted agreement>=2/3 and at least two known failure domains.
Expose eligible/queried/responding/agreeing counts and response coverage.
Known or hidden common faults need explicit tests; multiple IDs are not
independent physical evidence. Never compare altitude-mismatched absolute P.
Virtual/model nodes default to no vote. Configured external observed stations
may supply qualified supplemental evidence; model-only votes cannot meet the
physical corroboration minimum.

Health handles heartbeat gaps, clock drift, persistent calibrated residuals,
self-tests, CRC/missing/range issues, battery and source validity.
Automatic exclusions are per affected channel/map/event where appropriate.
Do not remove a true regional weather shift as common sensor drift without
independent fault evidence. Recovery/warmup must be explicit and hysteretic.

Specify unique query/boot IDs, sequence, observation epoch, snapshot membership,
deadline, versions, bounded TTL, vote authentication, duplicate cache, timeout,
idempotent result, response slots/jitter, capped retries and local coalescing.
Queries must not recursively trigger a broadcast storm. Same policy runs on
server and an offline gateway/edge coordinator; key verification/provisioning
must actually support that offline path. Do not rely on the internet to verify
a local vote. A degraded node can display local evidence without clearing risk.

The package's 62-byte frame/airtime and Monte Carlo reference are planning input.
Define and sizeof-test actual binary frames and quantization/missing sentinels.
Per-node auth tags, LoRaWAN or routing overhead may change airtime. Verify actual
regional MAC payload limits; a raw-LoRa 62-byte frame is not automatically an
allowed LoRaWAN app payload at all data rates.

Implement airtime budgets and channel scheduling using the approved Indian
equipment profile. Reference GSR 853(E) Table II meteorology/pollution category:
500mW ERP, APC, <=200kHz, 2.5% device / 10% access-point duty cycle, subject to
actual applicable type approval. Verify current primary rules and count antenna
gain/cable loss. Do not import EU1%, old no-duty-cycle IN865 assumptions or RFID
2W rules. Reject an incompatible radio config and fail RF enablement clearly.
Duty accounting includes heartbeats, queries, replies, ACKs, retries and relays.

CLI to implement:
python -m simulator.run_network --config configs/himachal_network_v1.json \
  --nodes 3 10 50 200 --scenarios nominal dropouts clock_drift common_faults \
  packet_loss combined --seeds 30 --output reports/himachal/network_scale.json

Run the CLI, host C parity/codec tests and:
python -m pytest -q tests/test_himachal_registration.py \
  tests/test_himachal_health.py tests/test_himachal_consensus.py \
  tests/test_himachal_radio.py
python -m pytest -q
pio run -d esp32/himachal_node

Acceptance:
- 2-node no-quorum and 3-node degraded modes are explicit.
- Registration/removal/reboot/clock changes work without code edits.
- No duplicate, stale, replayed or incompatible vote increments agreement.
- Offline coordinator/server outage does not block local behavior.
- Actual airtime/scheduler receipts report p50/p95 latency including timeouts,
  frames/bytes/channel load, per-device TX budgets, timeout rate, false warning
  episodes and missed synthetic episodes by N/scenario/seed.
- Saturation thresholds are conditional on topology/SF/traffic, not universal N.
- Do not optimize thresholds on final stress seeds and call them evaluated.
```

## 7. Phase G — conventional event-model training, registry and inference

```text
Objective: conventional supervised rain/snowstorm/cloudburst-risk inference,
with evidence-gated fitting, versioned artifacts and deterministic fallback.

Create:
- ml/himachal/models/__init__.py
- ml/himachal/models/train.py
- ml/himachal/models/registry.py
- ml/himachal/models/predict.py
- ml/himachal/models/calibrate.py
- ml/himachal/models/explain.py
- ml/himachal/models/export_student.py
- configs/himachal_models_v1.json
- schemas/himachal_detection_request_v1.json
- schemas/himachal_detection_response_v1.json
- tests/test_himachal_model_training.py
- tests/test_himachal_model_inference.py
- tests/test_himachal_model_export.py
- docs/HIMACHAL_EVENT_MODEL_CONTRACT.md

Read the D independent-label pipeline, B feature contract, existing
ml/hazard_context training/warning/episode support and six-sensor C exporter.
Use three public target keys: rain, snowstorm and cloudburst_risk.
Observed cloudburst outcomes are labels only, never a runtime confirmation.

Start with separate gradient-boosted binary heads on the same causal feature
cohort as the rule baseline; preserve multilabel outputs.
Train/development/calibration/test partitions are chronological and isolate
whole events/sites/valleys/seasons with horizon purges. Fit preprocessing,
class weighting, early stopping, thresholds and calibration in their respective
development partitions only. Reserve final tests for H.
Select temporal-model experiments only after baseline/support gates pass.

Reject circular rule labels, synthetic empirical corpora, country/source
misclassification, fabricated full-six-channel coverage, future information,
post-onset positives and absent-monitoring negatives.
If real independent data is missing, produce a readiness receipt and runnable
rule fallback; do not emit an invented trained hazard artifact.
Synthetic models may exist only as explicitly separate contract-test fixtures.

Registry records task/window, feature order/versions, source roles, training
commit/input hashes, target counts, splits, fitted parameters, model checksum,
calibrator/threshold versions, evidence class and deployment readiness.
Atomic load/warm-up must verify artifacts and prevent incompatible substitution.
Distinguish active Mandi numerical forecast, legacy rule imitation and newly
admitted event heads. Beijing transfer is a separate evaluated comparison.

Response per event: level none|watch|warning, model_score when available,
probability [0,1] or null, calibration_status, lead_time_h or null, availability,
abstain, grounded feature/rule evidence, model/version and risk_only.
Only use probability when independent calibration applies. Never claim a
measured lead time from a configured six-hour horizon. Missing/current-data
failures return unavailable, not zero risk. Failed model load falls back to
versioned rules with explicit reason/source.

Explain exact rule conditions and verified model feature contributions using a
tested attribution method supported by the model, with deterministic wording.
Attributions explain model behavior, not physical causation.
Optional numerical-forecast inputs are causal predictions generated at issue time,
with the necessary history/profile; never substitute observed future values.

Prepare compact depth/tree-bounded students only from eligible teacher outputs
on training partitions. Record their independent evaluation separately.
Export model plus preprocessing and any calibrator exactly; verify host C parity,
status, thresholds, missing states and resource limits. Board validation remains
untested without real hardware. Do not force a large temporal model onto ESP32.

CLI to create:
python -m ml.himachal.models.train --config configs/himachal_models_v1.json --dataset LOCAL_DATA --output LOCAL_MODELS --offline
python -m ml.himachal.models.predict --input OBSERVATIONS --model LOCAL_MODELS --output PREDICTIONS --offline
python -m ml.himachal.models.export_student --model LOCAL_MODELS --output LOCAL_EXPORT --verify

Run:
python -m pytest -q tests/test_himachal_model_training.py tests/test_himachal_model_inference.py tests/test_himachal_model_export.py
python -m pytest -q

Acceptance:
- Leakage, circular-label, insufficient-class and tamper tests fail safely.
- Missing real labels yield NOT_READY and a functional rule-only path.
- Model/calibrator/feature/schema incompatibility cannot silently load.
- Inference is deterministic for fixed inputs/artifacts; no generative API/client.
- Compact C parity and measured host size/latency are recorded honestly.
```

## 8. Phase H — independent ML evaluation and calibration

```text
Objective: compare rules and conventional ML fairly without claiming synthetic
or rule-imitation metrics as weather skill.

Create:
- ml/himachal/evaluation/__init__.py
- ml/himachal/evaluation/splits.py
- ml/himachal/evaluation/baselines.py
- ml/himachal/evaluation/metrics.py
- ml/himachal/evaluation/calibration.py
- ml/himachal/evaluation/drift.py
- ml/himachal/evaluation/run.py
- configs/himachal_evaluation_v1.json
- tests/test_himachal_evaluation.py
- docs/HIMACHAL_EVALUATION_PROTOCOL.md

Reuse independent monitoring/whole-event/site gates from ml/hazard_context.
Separate current conditions, exact +6h sensor values, and onset in (issue,issue+6h].
Use chronological training/development/calibration/final test, held-out stations/
valleys/seasons, whole physical episodes and horizon purges.
Training-only preprocessing/weights and development-selected hyperparameters,
feature selections and thresholds must never access final labels.

Compare matched data/information: deterministic rules, persistence/climatology
where appropriate, gradient boosting, and an optional small temporal model if
independent data supports it. Include teacher/student accuracy/resource tradeoffs
and with/without causal numerical-forecast outputs as separate ablations.
Do not use true future readings as forecasts.
Keep modeled grids, real sensor observations, Beijing transfers, rule imitation
and synthetic interface tests in explicitly separate evidence tables.

Report PR-AUC, event-level recall at a pre-registered false-alerts-per-monitored-
station-day budget, precision, false alarm episodes, missed events, Brier/log loss,
calibration/reliability, abstention coverage, and real pre-onset lead-time
distributions. Show class counts, independent episode counts and monitored
negative exposure. Cluster bootstrap by event/site instead of pretending every
positive time window is an independent disaster.
No-class/insufficient-support branches yield NOT_EVALUATED with reasons.

Measure repeated deterministic inference, sensitivity to realistic calibrated
sensor noise, feature missingness, elevation/season/source domain shift and model
version regressions on frozen canaries. Record model fit/inference/queue/map
p50/p95/p99 CPU latency, memory, flash and actual board results when available.
Measure complete training-to-calibration-to-test pipeline with frozen seeds,
commits, dataset/split hashes and model identities.
Empirical calibration and event thresholds require independent development
outcomes; otherwise probability remains unavailable.

CLI:
python -m ml.himachal.evaluation.run --config configs/himachal_evaluation_v1.json --dataset LOCAL_DATA --output reports/himachal/evaluation --offline

Run the offline contract fixtures and:
python -m pytest -q tests/test_himachal_evaluation.py tests/test_warning_windows.py tests/test_hazard_context.py
python -m pytest -q

Acceptance:
- Future/source/label/split leakage tests reject contaminated datasets.
- Synthetic and rule-derived labels cannot enter empirical skill reports.
- Sparse support is explicit; missing labels do not become a fabricated accuracy.
- All compared models use the intended causal cohort and untouched final test.
- Calibration/abstention/lead-time claims match actual evaluated evidence.
```

## 9. Phase I — elevation-aware spatial maps and uncertainty

```text
Objective: server-side feature/risk mapping with source trust, elevation drift,
conditional variance, support masks and bounded N-node work.

Read ml/event_classifier/heatmap.py, ml/spatial_ensemble,
ml/operational/{terrain,map_data,map_view}.py and available source/DEM metadata.
master/kriging is absent. Historical ml/kriging/kriging.py may be inspected
read-only at the verified legacy branch commit; do not reinstate its unmeasured
ESP32 timing claims or fixed-variogram matrix inverse as production evidence.

Create:
- ml/himachal/spatial/__init__.py
- ml/himachal/spatial/coordinates.py
- ml/himachal/spatial/variogram.py
- ml/himachal/spatial/kriging.py
- ml/himachal/spatial/virtual_background.py
- ml/himachal/spatial/service.py
- configs/himachal_spatial_v1.json
- tests/test_himachal_spatial.py
- tests/test_himachal_spatial_scale.py
- docs/HIMACHAL_SPATIAL_METHODS.md

Preserve the legacy heatmap API; use an additive adapter/new API.
Use a documented metre-based local projection/geodesic treatment and surveyed
elevation covariates. Fit drift plus residual variogram per appropriate
feature/region/season on development observations. Use stable factorization/
linear solves, duplicate-site handling, nugget/measurement error, condition
checks and explicit fitting failures. Return the PyKrige/custom solver variance;
never discard it or invent IDW variance.

Initial fit screen: >=8 healthy observed training stations, >=5 occupied pair
distance bins, noncollinear useful spread and sufficient elevation support.
Those screens are not statistical certification. Use withheld-node validation
and fitted-parameter stability. Sparse/clustered/collinear modes are station
points or support-limited IDW with uncertainty_available=false.
For <3 healthy physical nodes no fitted hazard surface should imply coverage.

Virtual IMD station data retains actual capabilities/source trust. ERA5/IFS/CAMS
provide separate model/background fields with native cell identity, coarse
resolution and source covariance. Do not count repeated API queries as stations.
Fit observed residuals against a model background instead of pseudo-replicating
virtual values. Pressure is adjusted/interpreted according to explicitly
documented reference/elevation, not silently relabelled measured station P.

N registration is dynamic. Tile maps, cap local solves at a configurable 64
nearest eligible observed stations, bound distance-pair sampling/grid size,
reuse factors and cache by station/source/time/health/model identity.
Map event scores only after local assessment, using bounded cached model inference.
Keep raw score surfaces distinct from independently calibrated probabilities.
A logit transform is allowed only with documented bounds/variance propagation.

Return mean, variance with units, support mask, age, method, conditional
uncertainty kind, sample/source count, physical/virtual composition and versions.
Do not fill an unsupported statewide polygon just because two nodes exist.
Use a licensed verified Himachal boundary; if absent, state missing geometry.

CLI to implement:
python -m ml.himachal.spatial.service --fixture SYNTHETIC_FIXTURE \
  --config configs/himachal_spatial_v1.json --output LOCAL_MAP --offline

Run:
python -m pytest -q tests/test_himachal_spatial.py \
  tests/test_himachal_spatial_scale.py tests/test_spatial_readiness.py
python -m pytest -q

Acceptance:
- Zero/one/two nodes, colocated/collinear sites, stale/faulty nodes, altitude
  offsets, correlated virtual cells and nonfinite data degrade explicitly.
- Controlled synthetic spatial fixtures cover 3/10/50/200 nodes with dropout,
  drift, common faults and simulated loss; measure CPU/latency and support.
- Validate finite nonnegative variance and its stated conditional meaning.
- Held-out physical nodes never influence drift/variogram/calibration fitting.
- No synthetic RMSE/interval coverage becomes real-Himachal map accuracy.
```

## 10. Phase J — versioned FastAPI backend and streaming

```text
Objective: one new API coordinates validated readings, health, dynamic nodes,
consensus, ML/rule fallback, map layers and stored incident results.

Create:
- server/__init__.py
- server/app.py
- server/settings.py
- server/schemas.py
- server/store.py
- server/jobs.py
- server/routes/__init__.py
- server/routes/detect.py
- server/routes/neighbours.py
- server/routes/heatmap.py
- server/routes/health.py
- server/routes/nodes.py
- server/routes/stream.py
- server/routes/alerts.py
- tests/test_himachal_api.py
- docs/HIMACHAL_API.md

Expose POST /detect, /neighbours, /heatmap; GET /health and /stream (SSE), with
documented /api/v1 equivalents if namespaced. Add registered-node listing,
history/pagination, registration, health exclusions and operator acknowledgement.
Keep ml.operational.server's current behavior and any protected shared backend
unchanged; adapt its validated ingestion where useful.

Server-side source/identity/availability checks cannot be supplied by a client
boolean. Preserve per-node auth, replay protection and actual receipt clocks.
Provide a distinct authenticated backfill path for buffered old observations;
it stores original time plus receipt time and never promotes old evidence into
a fresh live warning. Index site/time/event queries and implement observation,
nonce, message and job retention.

Use a persistent store/outbox, bounded async worker queue, request coalescing,
deadline/fallback and idempotent incident IDs. Do not block the request/event
loop on model fitting or repeated global kriging inversion. SSE supports Last-Event-ID,
bounded retention/backpressure and reconnect. A slow viewer cannot grow memory
without bounds. Expose measured queue/age/service state in health.

Return feature/schema/model/consensus/calibration/source versions,
valid-time vs issue-time, research availability and clear risk-only flags.
Use null for unavailable values/variance/probability. No default zero risk.
Secrets stay in backend env; validate CORS/origin/auth/request sizes and
registration roles. Use sanitized logs.

Run:
uvicorn server.app:app --host 127.0.0.1 --port 8000
python -m pytest -q tests/test_himachal_api.py
python -m pytest -q

Acceptance:
- Offline detect works through rules; eligible model inference returns grounded evidence.
- Invalid/oversized/incompatible/stale/unauthenticated requests are rejected.
- 3/10/50/200 registered nodes work with bounded requests and pagination.
- Virtual nodes and unhealthy exclusion state are visible, not silently counted.
- Concurrent duplicate requests/SSE reconnect/backfill/reboot/outbox behavior
  is idempotent and tested; existing backend/interface tests still pass.
```

## 11. Phase K — NEW React/Vite/Tailwind UI

```text
Objective: a usable mobile-first live research dashboard for the new API,
separate from the teammate's application.

Only create/change apps/indra-himachal-ui and its own tests/configuration.
Do not edit protected UI files, shared package.json or teammate backend routes.
Verify docs/plans/PROTECTED_PATHS.json before and after. Use current official
framework documentation and pin a compatible React/Vite/Tailwind version set;
commit the lockfile. Do not assume an obsolete Tailwind setup command.

Create:
- apps/indra-himachal-ui/package.json and package-lock.json
- apps/indra-himachal-ui/index.html
- apps/indra-himachal-ui/vite.config.ts
- apps/indra-himachal-ui/tsconfig.json
- apps/indra-himachal-ui/src/main.tsx
- apps/indra-himachal-ui/src/App.tsx
- apps/indra-himachal-ui/src/styles.css
- apps/indra-himachal-ui/src/api/client.ts
- apps/indra-himachal-ui/src/api/types.ts
- apps/indra-himachal-ui/src/components/SensorCharts.tsx
- apps/indra-himachal-ui/src/components/EventCards.tsx
- apps/indra-himachal-ui/src/components/RiskGauge.tsx
- apps/indra-himachal-ui/src/components/HimachalMap.tsx
- apps/indra-himachal-ui/src/components/NodeStatus.tsx
- apps/indra-himachal-ui/src/components/AlertHistory.tsx
- apps/indra-himachal-ui/src/components/EvidencePanel.tsx
- apps/indra-himachal-ui/src/i18n/en.json and hi.json
- apps/indra-himachal-ui/src/hooks/useStream.ts
- apps/indra-himachal-ui/tests/dashboard.spec.ts
- apps/indra-himachal-ui/README.md

Show all six sensor charts with units/window/source/age; three event cards for
rain risk, snowstorm risk and cloudburst risk; level/abstain/offline status;
source-labelled risk score gauge; Himachal feature/risk layers; variance/support
toggle; physical versus observed-external versus model-grid styling; node health,
quorum/timeout state and alert history; brief input-grounded evidence panel.

Unknown/stale/missing data is grey/unavailable and never rendered as zero or safe.
Uncalibrated score is not a percent event probability. Conditional kriging
variance is not an event-model confidence meter. Snowfall/blizzard and cloudburst
confirmation must not be inferred from card titles/icons. Make research status
and source/coverage gaps visible where they affect a user's decision.

English/Hindi toggle uses static reviewed strings, keeps numerical units stable,
and includes risk-only meaning in both languages. Use accessible contrast,
keyboard labels, responsive layouts and text/severity cues beyond color.
Low-bandwidth mode reduces chart updates/data points and fetches supported map
tiles only; SSE reconnect falls back to capped polling. Never require a huge
statewide raster on mobile. Cached data clearly retains its timestamp.

Implement realistic offline demo fixtures with SYNTHETIC_DEMO identity; no fake
live source attribution. VITE variables contain backend/public configuration
only; weather-source and node secrets never enter the browser bundle.

Run from the new directory:
npm ci
npm run typecheck
npm run build
npm run test
npm run test:e2e

Acceptance:
- Inspect desktop and mobile renders for all six channels, risk cards, maps,
  explanations and English/Hindi.
- Test registration appearance, node failure, sparse map, missing data,
  consensus timeout, model/rule fallback, SSE reconnect and alert acknowledgement.
- Clean browser build has no secrets or unsupported probability/confirmation
  claims. Protected path hashes remain unchanged.
```

## 12. Phase L — alerting, debounce, consensus gating and human confirm

```text
Objective: deterministic incident lifecycle and safe, idempotent research
notifications with explicit local/offline behavior.

Create:
- ml/himachal/alerts.py
- configs/himachal_alerts_v1.json
- server/notifications.py
- tests/test_himachal_alerts.py
- docs/HIMACHAL_ALERT_POLICY.md

Change only the new backend alert routes/store and new UI AlertHistory.

Model lifecycle: local indication -> watch candidate -> corroborated warning
candidate -> operator confirmed (pilot) -> resolved. Store separate event
assessment and dispatch status; the operator cannot rewrite raw sensor evidence.
Use stable incident IDs, event-window/spatial identity, versioned thresholds,
debounce, hysteresis, cooldown, expiry and an idempotent outbox. Escalation,
update and resolution are distinct events. Do not emit one alert per hourly
positive window or every retry.

Three-node consensus can strengthen confidence/dispatch eligibility, but an
uncorroborated localized cloudburst indicator must not become "safe."
Maintain local-only watch/evidence during gateway/server outages. A severe
local observation can request operator attention without pretending to have
quorum or calibrated probability. Cloudburst always remains risk-only.

Pilot warning candidates require human confirmation; public disaster
notification remains disabled until field/evaluation gates and recipients/
channels are explicitly configured. Rule fallback and degraded-source modes
retain their identities. Confidence/probability remains unavailable unless
independently evaluated calibration applies.

Implement local/in-app notification sink and a mock external adapter.
Do not actually contact people or public channels during implementation/tests.
No recipient or credential may be guessed.

Run:
python -m pytest -q tests/test_himachal_alerts.py tests/test_himachal_api.py
python -m pytest -q
Run the new UI alert/reconnect E2E cases.

Acceptance:
- Duplicate/replayed/concurrent retries create one incident/dispatch.
- Threshold chatter, clock rollback, recovery, node dropouts and common faults
  are covered. Confirmation/expiry/resolution survive service restart.
- Offline local indication remains functional.
- Human-confirm/public-disabled states are enforced by the backend, not only UI.
```

## 13. Phase M — Docker, CI, configuration and small-VM runbook

```text
Objective: reproducible local deployment, restrained operation and reviewable
VM packaging without claiming unavailable field readiness.

Create:
- Dockerfile
- compose.himachal.yml
- .env.example
- scripts/run_himachal_demo.py
- scripts/check_protected_paths.py
- scripts/check_himachal_readiness.py
- docs/HIMACHAL_DEPLOYMENT.md
- docs/HIMACHAL_FIELD_CHECKLIST.md
- docs/HIMACHAL_NODE_PLACEMENT.md
- requirements-himachal.lock or a compatible documented lock mechanism.

Change:
- .github/workflows/ci.yml with isolated backend/edge/UI jobs and offline
  simulation smoke tests; fuller scale receipts can be a separate scheduled/
  explicit job that does not use paid APIs.
- requirements-himachal.txt with only verified compatible dependency versions.
- docs/README.md and README.md with additive setup/navigation, preserving honest
  evidence status and existing experiments.

Environment example includes actual variable names for database, public UI/API
origins, node-key management, weather-source credentials, local model directory,
inference/queue/retention budgets, model/calibrator profiles, radio profile,
human-confirm, public-alert disabled, demo/offline modes. Values are empty or
safe synthetic examples, never real secrets. Document incompatible legacy/root/
research environments rather than forcing conflicting pins into one resolver.

Use persistent volumes, bounded retention/queues, backups and migration policy,
least-privilege container execution, health checks, TLS/auth proxy and proper
viewer/operator separation. Keep field positions/raw private data out of public
debug logs and source credentials outside the browser.

Provide a resource budget and measured load procedure for an initial small VM,
with CPU/RAM/storage/API limits, not invented host prices or throughput.
Measure 200-node synthetic ingestion/map/queue behavior and choose tile/cache/
worker settings from the results. An arbitrary N-cap is not the scaling design.
Document gateways/valley grouping/relay limits, battery/solar/snow installation,
surveyed elevation bands/spacing and total-cost categories from the review.

Commands:
docker compose -f compose.himachal.yml build
docker compose -f compose.himachal.yml up -d
python scripts/check_protected_paths.py
python scripts/check_himachal_readiness.py --output reports/himachal/readiness.json
python -m pytest -q
pio run -d esp32/himachal_node
Run npm ci, typecheck, build and tests in the new UI directory.

Acceptance:
- Fresh checkout starts a useful offline demo without production secrets.
- Missing real data/API/board/radio evidence yields explicit NOT_READY gates.
- Existing CI plus new jobs pass with locked environments.
- Backup/restore, restart, stale-source and offline fallback behavior is tested.
- Do not publish/enable public warnings or deploy to an external account
  incidentally. Deliver concrete deployment artifacts and explain outstanding
  configuration/evidence requirements.
```

## 14. Phase N — synthetic multi-node end-to-end replay and final verification

```text
Objective: reproducible replay of all three target scenarios and engineering
failures through edge-equivalent features, consensus, local ML/rule inference, API, maps and UI.

Create:
- simulator/__init__.py
- simulator/scenarios.py
- simulator/replay.py
- simulator/run_end_to_end.py
- configs/himachal_simulation_v1.json
- tests/test_himachal_replay.py
- tests/test_himachal_end_to_end.py
- reports/himachal/SIMULATION_REPORT.md generated from actual receipts.

Keep network/radio modules from F and spatial tests from I.
Use actual physical-channel-like synthetic histories at true native cadence,
with current-condition and next-window semantics explicit.
Create rain, cold/windy snow-risk, and localized convective cloudburst-risk
episodes, plus fog/high-RH nuisance, clean-air rain, dry windy dust, cold without
snow, sensor saturation/PM humidity artifact, battery/clock/CRC failures,
relocation, weather-source outage, virtual-data staleness and common-mode drift.
Known synthetic scenario labels are separate oracle fields never included in
runtime requests or empirical training. No synthetic rainfall channel is added
to the six-sensor runtime interface.

Run 3/10/50/200 registered nodes for every target and required failure condition:
dropout, LoRa loss, duplicate/reordered/replayed packets, clock drift, faulty/
common-mode sensors, gateway/server outage and recovery.
Include dense single-domain and multiple-valley collision-domain topologies.
A sparse isolated event must remain local-only/unknown when corroboration fails;
do not call it absent. Add dynamic join/remove without source edits.

Use the actual airtime/duty scheduler from F, not only the supplied simplified
Monte Carlo planning reference. Persist seeds/config/commit/model/
feature/source versions, frames/bytes/airtime per node/channel/relay,
ingestion/consensus/model/fallback/map end-to-end p50/p95/p99 with timeouts,
false warning episodes per monitored synthetic-negative interval,
missed synthetic events, invalid/abstain/timeout rates and CPU/memory.
Show denominators and sample counts. Run-to-run timings may differ; seeded
semantic results should reproduce.

CLI:
python -m simulator.run_end_to_end --config configs/himachal_simulation_v1.json \
  --nodes 3 10 50 200 --targets rain snowstorm cloudburst_risk \
  --seeds 30 --offline --output reports/himachal/end_to_end
python scripts/run_himachal_demo.py --offline

Run:
python -m pytest -q
python -m ml.deployment.verify_exports --catalog configs/model_catalog.json \
  --output reports/deployment/committed_export_verification.json --offline
pio run -d esp32/himachal_node
Run new UI typecheck/build/unit/E2E tests.
python scripts/check_protected_paths.py
python scripts/check_himachal_readiness.py --output reports/himachal/readiness.json
git diff --check

Acceptance/definition of finish:
- Offline end-to-end demo is runnable and visually verified.
- Dynamic registration, three-event displays, virtual-node separation, health
  exclusions, sparse spatial uncertainty and outages behave as documented.
- Simulation receipts and actual radio scheduling limits exist at all four scales.
- No test fabricated real event accuracy, calibrated probability, physical
  board/RF measurements or six-hour weather lead time.
- List software completed, empirical evaluation blocked, hardware untested,
  data/access and hardware questions and protected-UI location as separate actual facts.
- Small commits, clean required checks, no secrets and no unrelated changes.
- Scientific/operational readiness remains NOT_READY until independent evidence
  and physical validation pass. Give the user exact remaining inputs and
  procedures, not a misleading "production-ready" declaration.
```

## Practical order

Use A → B → C first. D develops independent source acquisition/admission; E → F
prepares edge/network work. G implements the conventional model pipeline and
fallback; fitting waits for D's admitted real data. H provides the independent
comparison. I/J work in sparse/offline mode, followed by K → L → M → N.

Start coding now from the reviewed repository; do not ask for an LLM provider,
model API, context limit, token price or fine-tuning capability.
Resolve only genuinely blocking sensor/data/UI/radio questions while continuing
independent implementation.
