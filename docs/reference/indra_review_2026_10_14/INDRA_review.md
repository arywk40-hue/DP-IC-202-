# INDRA: current-code review, verified sources, and N-node design
Prepared 14 October 2026 for Ariyan Bhakat / IIT Mandi. Corrected: Codex is the implementation tool; INDRA uses conventional ML and deterministic rules, with no runtime LLM integration.
Repository: https://github.com/arywk40-hue/DP-IC-202-
Reviewed main commit: **6bcda6b689868682cabfd95808eeb611dcb4aed3**.
This package implements the requested review and build-prompt deliverables. It does not modify or publish the repository.

## Part 1 — Review first

### What is actually present

Your attachment describes the September PR #4 snapshot. Current main is substantially newer. PR #4 merged on 14 September 2026; current main contains later India/Mandi, hazard-evidence, spatial, and operational work.

| Attachment assumption | Current verified state |
| --- | --- |
| Only a Beijing model exists | Beijing artifacts remain, but the active numerical benchmark is `ml/models/india_mandi_modeled_6h_v1/`, fitted on Indian-location Open-Meteo IFS/CAMS grids. Indian CPCB comparisons also exist. |
| Earlier India/hazard code was deleted | It was removed in the cleanup snapshot; current main now contains `ml/india_sensor`, `ml/india_mandi`, `ml/hazard_context`, `ml/operational`, and `ml/spatial_ensemble`. |
| Seven snapshots are the forecasting model's entire context | The legacy event wrapper uses seven hourly snapshots. The history forecast teacher uses 66 features with lags through 24 hours. The compact student uses only the current six values. The current independent-warning protocol also requires at least 24-hour history. |
| Codex should finish the project after research | User clarified that Codex is the coding tool, not a runtime component. The committed numerical models are XGBoost/ridge; the new event pipeline uses conventional supervised ML and a rule fallback. |
| `master/kriging` exists | That path is absent. Current spatial heatmap code is `ml/event_classifier/heatmap.py`; `ml/spatial_ensemble/` contains other spatial experiments. Two older branches retain `ml/kriging/kriging.py`. |
| A teammate's web UI exists here | No HTML, JSX, TSX, package.json, or identified frontend directory was found in current main or any of the four listed branch heads. An external/uncommitted UI remains possible. Obtain its exact location; create the new UI only in an isolated new directory. |
| CI never checks committed headers | Legacy header/report hashes and the exact committed C++ runtime have tests. The residual gap is export regeneration, wider boundary coverage, and direct checks of the active Mandi committed export. |

The root README explicitly calls the Mandi result a **modeled-grid retrospective benchmark**, rather than measured field accuracy. It says disaster heads remain unfitted and physical ESP32 warning validation is absent. Keep those qualifications. The older twelve-sensor and five-class material is under `docs/archive/`; archival descriptions are not the current runtime contract.

The six physical channels are temperature °C, relative humidity %, station pressure hPa, PM2.5 and PM10 µg/m³, and wind m/s. Site elevation, coordinates, timestamps, health, and derived features are metadata or computations, not extra physical sensors.

### Executed verification

- Read-only checkout of the exact main commit; working tree remained clean.
- The CI lint command passed.
- Full test suite: **206 passed, 14 subtests passed**, in 17.07 seconds, on Python 3.12.14 with the dependency versions from CI. CI itself selects Python 3.11 for model tests. This run does not establish 3.11 or board execution.
- Two warnings appeared: a pandas future deprecation and a NumPy/netCDF binary-size warning. There was no test failure. Track compatible clean-install environments; do not describe the warning as a demonstrated prediction bug.
- Regenerated four forecast exports in temporary directories using synthetic contract fixtures. All new exports passed Python/compiled-C parity at the exporter’s existing tolerance.
- The active Mandi header reproduced byte-for-byte. The three older checked headers did not reproduce byte-for-byte; they lack the new country/evidence macros emitted by today's exporter. This is a provenance/versioning difference, not evidence that their numerical predictions are wrong.
- The checks did not retrain production artifacts, acquire an Indian field corpus, exercise a physical ESP32, or run an actual LoRa link. Results are in `export_probe.json`.

### Ranked findings and exact evidence

| Rank | Finding | Code evidence and consequence | Fix |
| --- | --- | --- | --- |
| 1 | Independent local outcomes and monitored negatives are still missing | `ml/hazard_context/events.py:95–145` already screens source rights, identity, times, and independent outcomes. `warning.py` keeps unknown outcomes unavailable. Existing numerical and rule-imitation metrics cannot certify weather detection. | Preserve these admission gates. Acquire co-located histories and independently observed rain/snow outcomes. Do not train on your rule flags. |
| 2 | Three distinct tasks are being conflated | `six_sensor_forecast/predict.py` predicts exact +6h numerical values; `event_classifier/features.py:181–215` defines current-time rules; `hazard_context/warning.py` defines future onset windows. The target, information window and evidence type must remain explicit. | Version contracts for current conditions, next-six-hour onset risk, and +6h numeric forecast. Fit independent supervised event heads as a separate task. |
| 3 | Current hourly inputs cannot resolve rapid storm precursors | `esp32/ml_integration/include/indra_ml_runtime.h:54–65` accepts exact one-hour steps and retains seven rows. Legacy squall logic omits the 15-minute pressure rebound and uses hourly temperature change. The operational rules already refuse unsupported finer cadence. | Keep legacy hourly semantics frozen; add a native-cadence feature engine with real 15-minute windows. Do not interpolate hourly data into invented 15-minute observations. |
| 4 | Current heatmaps omit kriging variance and elevation drift | `heatmap.py:71` discards the variance returned by PyKrige. Ordinary kriging is attempted with three nodes if installed; no elevation covariate is passed. PyKrige is not in current CI's installed requirements, so the real kriging branch is not assured by those tests. | Add a tested server spatial adapter with elevation-aware regression kriging, returned variance, source correlation, a support mask, and explicit sparse fallback. |
| 5 | CI/export provenance remains incomplete | `tests/test_six_sensor_forecast.py:46–61` checks the Beijing report/header hashes. `test_esp32_ml_integration.py` compiles and compares the committed legacy runtime. `tests/test_india_mandi.py` tests synthetic workflow contracts but does not directly verify the shipped active Mandi header. | Check every shipping profile's report, model hashes, feature order, export identity, and compiled committed-header outputs. Pin or version exporter behavior. |
| 6 | “NOAA heat index” is a simplified approximation | `event_classifier/features.py:68–82` selects the Rothfusz polynomial by temperature alone and omits the NWS humidity adjustments and preliminary simple-index branch. India and operational code reuse this helper. Python/C parity can reproduce the same meteorological error. | Implement a new version following the verified NWS calculation. Do not change the feature meaning of frozen legacy classifiers without a version transition and regeneration/retraining as applicable. |
| 7 | Pressure provenance is enforced inconsistently across layers | The generic forecast frame contains no pressure-reference/elevation metadata. Legacy inversion logic uses fixed station `P>=1010`. The newer India and operational contracts correctly reject unknown/sea-level pressure and track elevation. Mandi data correctly admits that grid-surface pressure is not measured station pressure. | Make the server canonical contract authoritative. Forecast profiles may stay frozen, but every field/virtual record must retain pressure reference, source elevation, sensor height, and availability time. |
| 8 | There is no implemented neighbour consensus or per-sample anomaly service | Searches of current modules and firmware found no operational LoRa discovery/consensus protocol or completed independent event-inference service. `esp32/operational_node/src/main.cpp` is a driver preparation harness; physical mode and live radio are disabled. | Implement bounded local inference, dynamic registration/discovery, node health, and an offline coordinator before connecting public alerting. |
| 9 | Offline replay/backfill needs a separate ingestion path | `ml/operational/ingestion.py:34,59,74` defaults to a 120-second send-clock gate and rejects observations older than 300 seconds. This intentionally protects live ingestion but will reject buffered Himachal packets after a long outage. | Keep live freshness gates; add authenticated idempotent backfill with original observation times and actual receipt times, excluded from live warnings. Add retention for observations/nonces; the current raw-message table alone has a pruning bound. |
| 10 | Research reproducibility and deployment gates need consolidation | Root training pins differ from the CI experiment pins. The Mandi benchmark has only one modeled location and uses weather/PM on different native grids; CAMS's native cadence is coarser than its hourly API output. Existing firmware has not switched to Mandi weights. | Provide separate pinned environments and a model/profile catalog consumed by the backend. Preserve explicit source, deployment, geography, calibration, and hardware statuses. |

Legacy weaknesses are already documented and partly addressed by newer modules. For example, `ml/operational/rules.py` explicitly distinguishes strict PM decline from the legacy `<=0` condition, requires native 15-minute support, takes an explicit local pressure baseline, and rejects undefined parameters. Extend those parts instead of recreating a second contradictory system.

The older branch's `ml/kriging/kriging.py` explicitly inverts a full kriging system, uses fixed default variogram parameters, and includes an unsupported ESP32 timing estimate in its docstring. It should be treated as historical prototype code. Server-side sparse/local linear solves and measured compute receipts are the appropriate new route.

### Units, physical consistency, and proposed numeric definitions

These are **proposed initial research settings**, not IMD-validated detection thresholds. Freeze them in a versioned configuration and select final thresholds on development data only.

1. **Pressure:** retain actual station pressure for each fixed site. Compute tendencies at that same sensor: ΔP6h=P(t)−P(t−6h), and rates as ΔP divided by the exact elapsed hours. Compare neighbour tendencies or station-normalized residuals, rather than different stations' absolute pressures. Grid-surface pressure, mean-sea-level pressure, and station pressure remain different evidence types. Moving a node resets its historical baseline. Do not convert a grid value into a claimed station measurement.
2. **Cadence:** maintain separate native samples, completed 15-minute summaries, completed hourly summaries, and legacy forecast snapshots. A 15-minute delta has units hPa/15 min or °C/15 min; a rate is hPa/h or °C/h. ΔP=1.5 hPa in 15 minutes equals 6 hPa/h, but an hourly delta cannot establish that the change occurred in one quarter hour.
3. **Washout proxy:** use the median of the three preceding complete hourly PM readings as each channel's baseline B. Require both PM2.5 drop ≥max(5 µg/m³,0.20B25) and PM10 drop ≥max(10 µg/m³,0.20B10). Baselines below 10 and 20 µg/m³ respectively yield unavailable washout evidence, not “no rain.” Once co-location calibration exists, also require decline beyond three estimated measurement-noise standard deviations. Native-cadence storm washout uses a separately named previous-hour baseline and genuine 15-minute data. This measures a PM-decline pattern; it does not identify scavenging as a physical cause.
4. **Sharp humidity change:** initial |ΔRH1h|≥10 percentage points. Name it `rh_change_1h_pp`. A percentage-point change is different from a relative percent change. The legacy classifier uses a 5-point hourly cutoff; do not quietly replace its meaning.
5. **Wind increase:** initial ΔW15min≥3 m/s with current W≥8 m/s, only when native sampling and wind calibration support it. Call it a wind-increase proxy. Hourly mean wind does not measure a true short gust.
6. **Dew point:** Magnus-based liquid-water dew point may be computed in its documented domain, with RH=0 unavailable. Use a separate ice/frost-point definition when needed below freezing. The legacy helper's RH clamp yields a finite artificial dew point at zero humidity; newer India/operational paths already mask that situation.
7. **VPD:** return kPa; document whether saturation is over liquid water or ice. Atmospheric humidity estimates are not observations of precipitation.
8. **Heat index:** implement the NWS preliminary calculation, Rothfusz branch, humidity adjustments, Fahrenheit intermediates and Celsius conversion. Mark outputs outside the supported domain. This is ancillary to the three target events.
9. **PM quality:** optical PM can respond to high humidity, condensation, aerosol composition, and inlet contamination. Do not make washout mandatory ground truth. A primary Indian PMS7003 co-location study is listed in the sources. Treat PM2.5>PM10 as a QC signal to investigate, rather than silently clipping the ratio.
10. **Season and terrain:** month and elevation are weak contextual priors. June–September is a versioned calendar proxy, not a proof of monsoon conditions; elevation alone does not establish orographic lift or cloudburst occurrence. Terrain/windward exposure requires a reviewed source and an explicit missing state.

The snow rule combines cold, humid, windy conditions with a PM decline. It cannot observe falling snow, visibility, whiteout, or storm duration. For the supplied severe-rain rule, define the pre-drop interval separately from the subsequent pressure rebound; do not require an unspecified simultaneous ΔP fall and rise in the same window.

### Feasibility and domain shift

| Requested event | Six-channel capability | Verdict |
| --- | --- | --- |
| Rain | Can test atmospheric-condition and onset-risk inference; there is no rain gauge in the runtime contract. Rain in clean air may have no detectable PM washout. | **Partial.** Suitable as a research risk/condition indicator. Direct confirmation of rainfall is not available. |
| Snowstorm | Cold/humidity/wind patterns can support a research risk estimate. Snowfall, visibility, and duration are not measured. | **Partial.** A confirmed blizzard detector is **not feasible** with these six measurements alone. |
| Cloudburst risk | Correlated surface changes can be tested as weak predictors against independent local high-intensity rainfall outcomes. Sudden changes may occur during or after onset. | **Partial and exploratory** as risk indication. Confirming a cloudburst or its ≥100 mm/h intensity is **not feasible** from these six channels. |

“Feasible software interface” is different from “demonstrated predictive skill.” The Chinese models cannot be assumed to transfer to a Mandi sensor station. The active Indian modeled-grid benchmark also leaves a model-grid-to-instrument domain shift.

Evaluate separately: elevation/station pressure; winter western disturbances versus monsoon; valley/ridge exposure and wind measurement height; winter inversion versus other aerosol mixtures; optical versus reference PM instruments; sensor installation/calibration; and reconstructed versus actually available historical inputs. A learned model cannot recover unmeasured rainfall or establish sensor validity without independent evaluation.

### Four tasks, now designed for N nodes

**Task 1 — anomaly inference.** Start with range/CRC/timeout checks, stuck-sensor diagnostics with context, and robust EWMA or median/MAD residuals per channel. These fit a small deterministic C implementation and work locally without server connectivity. Keep `sensor_fault` separate from `environmental_anomaly`; a genuine rapid cooling event must not be discarded as a faulty sensor. A proposed anomaly-module budget is 32 KiB flash and 4 KiB working RAM, subject to the actual board build. Measure object/firmware size, execution latency, and peak stack on the board. Do not repurpose a +6h forecast error as a current anomaly unless the forecast timestamp has actually matured.

**Task 2 — neighbours and consensus.** Registration stores node identity, coordinates, surveyed elevation/datum, capability/cadence, authentication material, trust/source class, failure-domain metadata, health, and last-seen time. Use a spatial index for radius/elevation searches, with a dynamic index update on registration. No source-code edit or hard-coded peer IDs is needed for a new node. Query at most six eligible peers per incident, independently of global N.

Proposed initial eligibility: healthy authenticated physical node, within 5 km, elevation difference ≤750 m, observation age ≤120 seconds, reported clock uncertainty ≤30 seconds, compatible event window and model/feature version. Weight w=q×exp(−distance/3000m−|Δelevation|/500m); q is a versioned quality weight, not a learned probability. Geographical thresholds are starting research settings.

Require origin plus at least two distinct agreeing physical peers, weighted agreement ≥2/3 among valid responses, and at least two known failure domains. Record the number of eligible, queried, responding, and agreeing nodes. Missing votes remain unknown. Known common faults cannot become independent evidence simply by being broadcast through multiple node IDs.

Every request has an origin, boot/session identifier, unique query ID, sequence, event mask, observation epoch, deadline, bounded TTL, model/feature identity, and authenticated votes. Cache query IDs, reject stale/duplicate votes, lock snapshot membership at query creation, and make the final result idempotent. Responses do not recursively initiate new queries. Coalesce only compatible local incidents; a distant incident must retain its own identity.

Use a 30-second initial deadline for the proposed SF9 direct-local profile, with a deadline derived from slot/airtime/route configuration when the radio changes. Schedule replies to avoid synchronized broadcasts; bound retries and obey the airtime bucket. A server can reproduce the decision, while an internet-independent valley gateway/coordinator runs the same policy locally. Nodes retain a provisional local indication if the coordinator/server is unavailable.

**Task 3 — conventional ML event prediction.** Fit separate rain, snowstorm-risk and cloudburst-risk heads with gradient boosting as the first learned baseline. Consider a compact temporal model only if independently labeled histories support it. Keep training/development/calibration/final test isolated. Run inference locally on the server; export an eligible compact student for ESP32 where useful. A deterministic rule indicator handles absent/failed model artifacts. Unknown outcomes remain unavailable; calibrated probabilities require independent evaluation.

**Task 4 — heatmaps.** Interpolate individual measured features and per-node event-risk scores through a server adapter. Fit elevation drift and residual variograms from appropriate observed training data, using local metric coordinates, measurement error, and source provenance. Return mean, variance, support, sample count, source composition, model/version and staleness. Kriging variance is conditional on the covariance/drift model; it is not total weather/event/model uncertainty.

Use cached bounded model inference for maps. Map a bounded local neighbourhood, tile/cache grids, limit variogram-fitting pairs, and factor covariance matrices once per tile/snapshot. A practical initial solver cap is 64 nearest eligible stations per tile; this caps computation per tile rather than the network size. Fit variograms only with adequate pair-distance support and cross-validation. Distinct grid queries into one model cell do not create independent stations.

### Stage behavior and graceful degradation

| Stage | What works | Conditions and degradation |
| --- | --- | --- |
| Prototype: 2–3 physical nodes | Acquisition/QC, local anomaly checks, deterministic features, local provisional alerts, basic server/UI, rule/ML contract demonstrations | Two nodes cannot meet a three-node quorum. Three nodes work only when all required peers are healthy, reachable, and exposed to a compatible event. Show points/support-limited IDW, with uncertainty unavailable; no fitted variogram claim. |
| Valley pilot: 8–12 nodes | Dynamic discovery, bounded consensus, node-health exclusion, map cross-validation, ML shadow evaluation | A count of eight is not sufficient by itself. Start attempted regression kriging only with ≥8 healthy observed stations, at least five occupied distance bins, useful two-dimensional spread and elevation support; validate fit stability. Fall back when stations are collinear, clustered, stale, or missing. |
| Regional: 20+ across valleys/bands | Valley gateways and bounded local groups, tile-specific spatial models, source-aware regional maps, pooled held-out-valley evaluation | Global N stays dynamic. Coverage, local density, and radio collision domains govern capability. Separate valley/basin/season evaluation; do not fill unsupported Himachal areas with a confident smooth surface. |
| 50–200 simulated or deployed nodes | Same interfaces and registration; queued model/map work, bounded peer sets, local tiles, retention and monitoring | One crowded collision domain can saturate well before a global 200-node network does. Add gateways, channel capacity, telemetry scheduling and rate control based on measured load. |

For no quorum, return `consensus_unavailable` or `local_only`, retain the local evidence, and expose the offline/timeout reason. A dry neighbour does not clear a highly localized cloudburst indicator. Consensus may strengthen corroboration, but it must not convert “no corroboration” into “safe.” Cloudburst remains **risk only** at every level.

### Node placement for Himachal

Use a valley transect with low, middle, and upper sites plus paired valley-floor and ridge/exposed locations. Illustrative planning bands are <1200 m, 1200–2200 m, 2200–3200 m and >3200 m; they are not official hazard classifications. Use surveyed elevations, locally relevant terrain bands, and a consistent vertical datum.

- For the prototype, cluster three nodes around one monitored test area with overlapping local event exposure, approximately 0.5–1 km separation as an initial survey target. Add a reference rain/snow observation source for evaluation only.
- For a valley pilot, balance those close pairs with longer along-valley transects. An initial 0.5–2 km spacing target improves local event sampling, but no LoRa range guarantee follows. Verify each link's terrain obstruction, signal quality and packet loss.
- Put a gateway or relay at a tested visible site with power/access. At 865 MHz, wavelength is about 0.347 m. For a 1 km symmetric link, first Fresnel radius at the midpoint is about 9.3 m; a 60% clearance planning target is about 5.6 m. Derive clearance from the actual link geometry and terrain, not a nominal radio-distance advertisement.
- Keep temperature/RH radiation-shielded and away from enclosure heating; document anemometer height/exposure; protect PM intakes against water without silently changing the sampling response. Survey cold and condensation behavior of the actual PMS module before treating high-altitude snow sites as six-channel-complete.
- Mount PV and intakes above locally surveyed snow accumulation, consider shading and safe winter maintenance, and size power from measured Wh/day, winter solar availability and battery usable fraction. Specify BMS/cold charging constraints from the chosen battery's datasheet.
- Coverage cost is nodes + gateways/relays + poles/enclosures/power + calibration visits + permissions + winter access + maintenance + server/API. Increasing point count on one accessible road can be cheaper while contributing little new terrain coverage. A surveyed gateway and independent validation may be more useful than many uncalibrated copies.

No component prices or total Himachal deployment cost were measured for this review.

### Virtual nodes and trust

Maintain separate source classes: `physical_indra`, `observed_external_station`, `modeled_grid`, and `synthetic_demo`. Preserve native spatial/temporal resolution, true provider cell/station ID, variables available, grid/sensor elevation, observation/valid time, issue/publication/receipt time, QC, measurement uncertainty, source ancestry and licence.

IMD AWS values can support weather interpolation only if a permitted feed/archive and station metadata are actually available. Most external stations will not provide your complete six-channel event context. ERA5/Open-Meteo points can provide a **coarse background/model layer**; multiple nearby requests may be the same model cell. Use one source-cell identity and correlated errors rather than independent pseudo-observations.

Default all virtual nodes to ineligible for neighbour consensus, with lower/explicit trust and visible source styling. A reviewed configuration can allow a qualified external station to contribute supplemental evidence. Model-grid-only agreement must not satisfy the minimum physical corroboration count for a warning. It cannot manufacture the missing independent observed evidence.

Fit observed residuals against the virtual background and propagate source/model uncertainty; do not feed a large number of virtual points into a variogram as if they were measured stations. During sparse operation show a separate model-background layer, real station markers, and an unsupported-area mask.

### Node health

Use heartbeats whose period follows the link's airtime budget, timestamp/clock uncertainty, missing-channel flags, CRC failures, sensor self-tests, calibrated-range checks, battery/power status and health history. Mark missing after three expected heartbeat intervals; track observation freshness separately.

Detect slow drift using a training-only local seasonal baseline plus robust elevation-aware neighbour residuals over persistent windows. A six-hour persistent residual and independently healthy comparator stations are an initial diagnostic setting, not an automatic truth label. Wind that is constantly zero in calm weather is not proof of a stuck encoder.

Exclude hard-invalid, stale, unsynchronized, and confirmed-drifting channels/nodes automatically from the affected consensus/map layer. Keep raw records and reasons. Recovery requires a versioned health-clear rule or reviewed maintenance event, followed by warm-up; one good sample does not immediately restore voting. Shared batch/firmware/installation failures and weather-driven regional changes require a common-mode diagnostic, rather than majority voting.

### LoRa payload, airtime, legal category, and saturation

A proposed binary local frame is **62 bytes**:

| Field group | Bytes |
| --- | ---: |
| Version/type/flags/TTL | 4 |
| Registered node ID | 4 |
| Query/session ID | 8 |
| Sequence | 2 |
| UTC epoch | 4 |
| Deadline/window field | 2 |
| Event and channel-quality masks | 2 |
| Clock-uncertainty field | 2 |
| Six quantized sensor channels | 12 |
| Anomaly and rule-score fields | 4 |
| Authentication tag | 16 |
| Application checksum | 2 |
| Total | 62 |

Specify each quantization/range and a missing sentinel. This fits one proposed peer frame; seven histories and model feature packets belong on the server, not inside this radio packet. Real LoRaWAN headers, routing envelopes, retransmissions, or signatures add bytes. This is a raw-LoRa planning frame: current LoRaWAN RP002-1.0.5 IN865 permits only 51 application bytes at DR0–DR2 (SF12–SF10/125 kHz), with 115 at DR3 (SF9), before optional FOpts reduce that limit. A LoRaWAN implementation needs its own compact envelope/profile and recalculated airtime. Key distribution and peer authentication must be defined: per-node keys can be verified by an offline gateway; arbitrary peers must not trust claimed identities.

Calculated LoRa PHY airtime: explicit header, radio CRC on, coding rate 4/5, 125 kHz BW, eight preamble symbols, low-data-rate optimization where required.

| SF | One 62-byte frame | Query + six replies + one result, 8 frames |
| --- | ---: | ---: |
| 7 | 0.118016 s | 0.944128 s |
| 9 | 0.369664 s | 2.957312 s |
| 10 | 0.698368 s | 5.586944 s |
| 11 | 1.478656 s | 11.829248 s |
| 12 | 2.793472 s | 22.347776 s |

These are sums of channel airtime, not measured end-to-end delivery times. Guard slots, half duplex, retries, relays and duty-cycle waiting increase latency.

**Verified regulation:** G.S.R. 853(E), 10 December 2021, Table II explicitly lists meteorology/pollution sensors within tracking/tracing/data acquisition. It states 500 mW ERP, adaptive power control, bandwidth ≤200 kHz, and transmit duty cycle ≤2.5% for devices and ≤10% for network access points. Table I instead has different bandwidth/FHSS and 1% conditions; do not select it solely because 1% sounds conservative. Type approval and the equipment's applicable category matter. The current NFAP 2025 listing still points to these 2021 rules. Do not apply the RFID 2 W provision to this network. Sources are linked in Part 2.

A 62-byte SF12 frame once per minute consumes **4.66%** transmit duty cycle before any votes or retries. That schedule fails the above 2.5% device-budget assumption. At SF9 the same heartbeat consumes about 0.616%; at SF11 about 2.464%, leaving almost no room for incident responses. Configure heartbeat batching/adaptive periods and a radio airtime scheduler. Virtual map cells consume no LoRa airtime.

There is no universal node-count saturation point. For a homogeneous single collision domain and pure ALOHA, G=frame_rate×airtime/channels and packet success is approximated by exp(−2G). Ignoring incident traffic, 62-byte SF9 heartbeats every 60 s reach G=0.5 at about **81 nodes on one channel or 243 on three evenly used channels**. The model's maximum successful channel occupancy is then about 18.4%, not perfect reliability. For an illustrative ≤10% collision-loss target, the corresponding heartbeat-only counts are about **8 per channel or 25 across three**. Queries, telemetry, relay duplication and retries lower the limits; coding/spreading-factor diversity, scheduling and capture change them. These calculations are engineering approximations, not a site capacity certification.

### Executed planning simulation — scales 3, 10, 50, 200

The runnable `planning_simulation.py` executes 32 consensus cases and 16 spatial cases: four node counts, four scenarios, one/three channels, ten seeds, 200 rounds per seed. Scenarios are nominal, dropout/loss/clock drift, correlated faults, and all combined. It is a standalone reference of the proposed design, not a test of an existing repository protocol.

Assumptions: one dense 4×4 km collision domain; SF9 62-byte frames; one heartbeat and one domain query per minute; up to six peers; 30-second deadline; minimum three agreeing nodes; a localized synthetic event footprint; 15% node dropout, 10% additional packet loss and 80-second clock-drift standard deviation in stress cases; common-mode faults with an explicitly assumed 75% health-screen detection chance. Cryptography, radio capture, real terrain, per-node duty scheduling, LoRaWAN receive windows, routing and real learned weather inference are omitted. Consequently this reference is useful for failure discovery; implementation-grade radio scheduling and measurements remain required. Successful-warning latency here means the local consensus decision plus one scheduled result transmission; result reception/acknowledgement is not simulated. The three-channel case assumes an appropriately capable coordinated/multichannel receiving setup; it is not a free capability of one single-channel radio.

The tables below are filled from the executed JSON receipt in the package. Failed/unresolved rounds include the full 30-second timeout; successful-round latency must be read together with success fraction. Zero false alerts under saturation is not a successful system.

**Nominal transport, 1 channel(s).** False-warning fraction is conditional on synthetic negative query rounds, not real weather false alarms.

| Nodes | Frames/hour | p95 successful warning (s) | p95 all rounds (s) | False warning / negative query | Positive synthetic queries warned |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3 | 355.3 | 1.679 | 30.0 | 0.000% | 56.79% |
| 10 | 956.4 | 3.557 | 30.0 | 0.118% | 66.45% |
| 50 | 3236.6 | 3.557 | 30.0 | 0.059% | 36.09% |
| 200 | 12085.7 | Unavailable | 30.0 | 0.000% | 0.00% |

**Nominal transport, 3 channel(s).** False-warning fraction is conditional on synthetic negative query rounds, not real weather false alarms.

| Nodes | Frames/hour | p95 successful warning (s) | p95 all rounds (s) | False warning / negative query | Positive synthetic queries warned |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3 | 363.8 | 1.679 | 30.0 | 0.059% | 73.31% |
| 10 | 1001.9 | 3.557 | 30.0 | 0.000% | 75.58% |
| 50 | 3353.8 | 3.557 | 30.0 | 0.118% | 88.89% |
| 200 | 12216.8 | 3.557 | 30.0 | 0.000% | 24.04% |

**Combined faults, 3 channels.** These include dropped nodes, clock uncertainty, packet loss and imperfect common-fault screening.

| Nodes | Frames/hour | p95 successful warning (s) | p95 all rounds (s) | False warning / negative query | Positive synthetic queries warned |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3 | 187.0 | 1.679 | 30.0 | 0.000% | 1.34% |
| 10 | 608.9 | 2.618 | 30.0 | 0.138% | 8.30% |
| 50 | 2873.7 | 3.557 | 30.0 | 0.830% | 48.88% |
| 200 | 10421.3 | 3.557 | 30.0 | 0.290% | 17.03% |

**Nominal synthetic temperature regression kriging.** Ten replicas; fit needs at least eight valid training stations. Only supported withheld nodes are scored.

| Nodes | Supported held-out predictions | Synthetic RMSE (C) | Conditional 95% interval coverage | p95 fit + held-out prediction CPU (ms) |
| --- | ---: | ---: | ---: | ---: |
| 3 | 0 | Unavailable | Unavailable | Unavailable |
| 10 | 6 | 1.246 | 83.3% | 4.325 |
| 50 | 72 | 0.730 | 95.8% | 5.576 |
| 200 | 360 | 0.545 | 93.3% | 10.807 |


At three nodes, dropout or clock exclusion destroys quorum. At 200 nodes, the nominal single-channel configuration produces no successful warnings in this reference. More global nodes do not overcome one overloaded local radio domain. Correlated failures survive imperfect health screening, so voting cannot certify sensor independence.

Sparse spatial cases return no variance and no score. The spatial CPU measurements are fit plus held-out query predictions, not full-Himachal raster-render or network latency. The synthetic withheld-node results do not establish calibrated real-weather uncertainty.

### Conventional ML design and measurements

Use deterministic causal feature packets and validated local model artifacts.
The new supervised heads are separate from the numerical +6h forecast and
legacy rule-imitation models. Start with rules and gradient boosting; compare a
small temporal model only when independent event support justifies it.

Raw model scores are not calibrated event probabilities. Fit a calibrator on
independent development/calibration outcomes and test it on untouched events/sites.
Return null/abstain when data, labels or model support is missing. Missing values
must not display as a reassuring zero-risk result.

Ground explanations in triggered rule conditions and a verified feature-
attribution method for the fitted model. These explain model behavior, not
physical causation. Retain exact feature values/units and artifact identities.

| Risk | Measurement |
| --- | --- |
| Circular labels | Reject input-rule-derived and synthetic labels from empirical training; retain original independently observed source and monitoring evidence. |
| Time/source leakage | Perturb future observations; audit availability clocks, whole-event/site splits and feature/calibration fitting partitions. |
| Domain shift | Report errors and abstention by valley, elevation, season, sensor type and modeled-versus-measured source role. |
| Calibration failure | Independent Brier/log loss, reliability plots, coverage and thresholds at a pre-registered false-alert budget. |
| Model/version drift | Re-run frozen canaries and independent tests after artifact/feature/calibrator changes; verify hashes and target windows. |
| Runtime cost | Measure fit/inference/queue/map CPU latency and memory; measure flash/stack/board latency for compact exports. No generative API/token billing is required. |
| Added forecast value | Compare matched causal models with/without issue-time numerical forecasts; never substitute true future readings. |
| Sparse evidence | Publish class/episode counts, monitored negatives, missing histories and NOT_READY/NOT_EVALUATED branches. |

Use model checksums, feature order/version and calibrator identity as cache/load
keys. Avoid fitting in request handlers; atomically activate verified model
artifacts. Preserve bounded queues, rate-limited map work and rule fallback.
Model training cannot be completed empirically merely by passing synthetic
software tests. Software/demo completion and scientific/field readiness remain
separate.

### Evaluation plan

Define each target before training: current rain observation versus onset in (issue,issue+6h], independently defined snowstorm occurrence, and externally verified cloudburst-related high-intensity rainfall risk. Preserve existing broader hazard targets as separate experiments.

1. Acquire independent positive outcomes and complete monitored non-event intervals. Missing reports are unknown outcomes. Daily rainfall may support daily rain labels but cannot establish hourly cloudburst intensity.
2. Match source clocks, locations, elevation and timing uncertainty. Store original reports and reviewed event-group IDs. Never set midnight UTC or precise coordinates from an approximate news date/place.
3. Hold out whole physical events, whole stations/valleys and seasons. Use chronological development, calibration and final test periods, horizon purging and feature-history support. Fit preprocessing, anomaly thresholds, variograms, examples, calibrators and decision thresholds on the correct development partition.
4. Keep Beijing, CPCB reduced-channel, Mandi modeled, genuine field and virtual-background experiments separate. Simulations test interfaces, protocol behavior and failure recovery; they do not enter field-skill tables.
5. Compare rules, persistence/climatology where appropriate, gradient boosting, and a compact temporal model if independently labeled data supports it. Compare teacher/student exports and with/without causal numerical forecasts on matched cohorts.
6. Report PR-AUC, event-level recall at a pre-registered false-alerts-per-monitored-station-day budget, false alarm episodes, precision, ROC-AUC where appropriate, calibration, abstention coverage and lead-time distributions. Use episode-level matching and cluster bootstrap by event/station, rather than counting every positive window as a new independent disaster.
7. Report only genuine pre-onset lead times. Current storm cooling/washout or post-onset windows must not become six-hour warnings.
8. When a split lacks both classes, support, or appropriate monitoring, report `NOT_EVALUATED` with the reason. Choose operational alert limits and recall requirements with the mentor/local responsible team; no empirical values are invented here.

## Part 2 — Verified data sources and links

Checked 14 October 2026. “Verified” means the primary source/documentation was retrieved or, where stated, indexed by the primary provider. It does not mean a private account download succeeded. Rights and coverage stay dataset-specific.

| Source | Verified links | Coverage / native resolution | Licence / access / use |
| --- | --- | --- | --- |
| ERA5, Copernicus CDS | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview ; https://cds.climate.copernicus.eu/ | Global; 1940–present; hourly; 0.25° atmospheric grid. | Catalog lists CC-BY. Record the exact accepted licence version. Create a CDS account, accept dataset terms, copy the current portal-generated API request, and download a bounded area/month. Use temperature, dew point, surface pressure, u/v wind and precipitation/snow context. ERA5 is retrospective/model-assimilated context, not independent local rain-gauge truth. It lacks observed PM. |
| NASA IMERG / GES DISC | https://gpm.nasa.gov/data/imerg ; https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGHH_07/summary ; https://gpm.nasa.gov/data/policy | V07 precipitation at 0.1°/half-hour; TRMM/GPM era. Verify the selected collection's exact start/end from its download metadata; this session did not resolve that precise collection boundary. | NASA GPM policy makes processed data freely available and asks for attribution. Use Earthdata authentication and GES DISC subset/download tools; Final for retrospective research, Early/Late for lower-latency use. The GES DISC collection is provider-indexed; its detailed JS page was not retrieved. Cell-average estimates and their phase estimates cannot confirm a point cloudburst or local snowstorm. |
| Open-Meteo historical weather | https://open-meteo.com/en/docs/historical-weather-api ; https://open-meteo.com/en/terms | Global; ERA5 hourly 1940+, ERA5-Land 1950+, IFS 2017+; native grids differ. | Data CC BY 4.0; free hosted API is for non-commercial use, with stated limits. Commercial API access is a separate service condition. Request exact model, UTC, units and elevation behavior; cache original responses and returned cell coordinates. This is a convenient virtual/background provider, not an IMD observation archive. |
| Open-Meteo/CAMS PM background | https://open-meteo.com/en/docs/air-quality-api | Global CAMS forecast archive listed from August 2022; 0.4° (~45 km), 3-hourly native product. API may return hourly positions. | CC BY 4.0 plus Open-Meteo/CAMS attribution and hosted-service terms. Select global domain for India; save true native cadence/resolution. PM grid points must not be described as hourly co-located PMS7003 measurements. |
| NASA POWER | https://power.larc.nasa.gov/docs/services/api/temporal/hourly/ ; https://power.larc.nasa.gov/docs/tutorials/service-data-request/api/ ; https://power.larc.nasa.gov/ | Global; hourly UTC/LST 2001–near-real-time; meteorology 0.5×0.625°. Daily archives have a different period. | Official documentation describes free global data; a specific standardized redistribution licence for the chosen product is **UNVERIFIED** here. Keep provider citation and rights review. Use the point API, `time-standard=UTC`, bounded dates and parameter metadata. PS units must be inspected, not guessed. No PM and no local cloudburst truth. |
| IMD measured station/AWS archive | https://dsp.imdpune.gov.in/ ; https://mausam.imd.gov.in/shimla/docs/data-procedure.pdf ; https://mausam.imd.gov.in/shimla/ | Indian stations; variables, cadence and dates are station/request specific. Co-located six-channel coverage was not verified. | Dataset agreement/fees/research category apply; no blanket open licence was verified. DSP is primary-indexed, but its direct page timed out. The procedure PDF is an older published process, so confirm current terms in the portal. Request station metadata, native rain accumulation and interval, measured T/RH/station pressure/wind, snowfall/present weather, QC and publication clocks. A stable public bulk IMD AWS API for this task is **UNVERIFIED**. |
| IMD station bulletins and historical incident candidates | https://mausam.imd.gov.in/shimla/ ; https://mausam.imd.gov.in/shimla/mcdata/Weather_Forecast_Bulletin.pdf ; https://mausam.imd.gov.in/shimla/mcdata/disasterous_event.pdf | Himachal bulletins; current forecast URL is mutable. Retrieved incident PDF covers July 2024. | Public official documents; machine-learning redistribution rights **UNVERIFIED**. Download and hash each dated document; distinguish observed weather, forecasts and media-based incidents. Forecast alerts are not observed event outcomes. |
| CPCB measured pollution data | https://cpcb.gov.in/air-quality-management-portals/ ; https://app.cpcbccr.com/AQIIndia | Indian stations; dates/cadence/variables vary. PM2.5/PM10 and some station meteorology; station pressure/full six-channel completeness not assured. | No universal open reuse/bulk-download licence was verified. Use permitted dashboard export or an approved request; retain station IDs/QC/units/clock metadata. Do not promise an undocumented unauthenticated scraping API. PM data provides features, not independent rain/snow/cloudburst labels. |
| OpenAQ | https://docs.openaq.org/resources/measurements ; https://docs.openaq.org/resources/licenses ; https://docs.openaq.org/using-the-api/api-key | Global with Indian locations; dateFirst/dateLast, parameters and measurement cadence are per sensor. | API v3 uses a key. Source/provider licences vary; retrieve licence records and restrictions for every selected sensor. Discover Indian locations and sensor IDs, then paginate bounded `/v3/sensors/<id>/hours` or measurement requests. Preserve upstream IDs; CPCB and OpenAQ copies of one sensor are not independent nodes. |
| Himachal SDMA | https://hpsdma.hp.gov.in/ | Himachal disaster records and reports; narrative coverage is report-specific and incomplete as negative monitoring. | Public records; dataset/redistribution licence and bulk API **UNVERIFIED**. Discover downloadable dated reports from the official portal and preserve source/page/hash. The older registered narrative https://hpsdma.nic.in/admnis/admin/showimg.aspx?ID=3664 is **UNVERIFIED in this session**; do not infer its exact event timing. |
| MAUSAM cloudburst studies | https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/5084 ; https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/7150 | First paper discusses observed cloudburst events; second reports 66 IHR cases during 2022, published 1 October 2026. A reviewed Himachal-only timestamped list is not acquired here. | The pages show conflicting CC BY-NC and generic CC BY text. Treat commercial redistribution/training rights as **UNVERIFIED** until resolved. Download the paper, inspect event tables and original sources, preserve date/location uncertainty, and admit only independently verified compatible labels. A paper's case count is not automatically a training corpus. |
| Primary snowfall-event sources | https://www.pib.gov.in/PressReleasePage.aspx?PRID=1547289 ; https://hpkullu.nic.in/about-disaster-managment/rescue-work-details-from-25-09-2018-onward-during-unexpected-snowfall-in-kullu-and-lahaul-spiti/ | Official September 2018 snowfall/rescue reports for Lahaul-Spiti/Kullu. | Public official reporting; dataset reuse licence **UNVERIFIED**. These establish severe/unexpected snowfall and response dates, not a fully timed meteorologically defined blizzard catalog. Avoid personal data in rescue lists; use only event-level evidence. |

### Independently sourced event candidates with dates

| Reported date/window | Location and reported event | Source | Label status |
| --- | --- | --- | --- |
| 24 July 2024 | Sarehi Nala / Palchan, Kullu; reported cloudburst/flash flood | IMD Shimla July 2024 DWE PDF, entry 2 | **Candidate.** Information source is Media; rainfall intensity is blank. Unknown precise onset and local hourly gauge evidence. |
| 28 July 2024 | Rispa Nala, Kinnaur; heavy rain/flood | Same PDF, entry 1 | **Candidate rainfall/flood incident**, not cloudburst-confirmed. |
| 31 July 2024 | Jhakadi/Rampur, Samej, Singhgad, Padhar/Mandi; cloudburst/flood/heavy-rain incident group | Same PDF, entry 3 | **Candidate group.** Reconcile separate places and midnight/date conventions against original records. Do not assign one fabricated UTC instant to all locations. |
| September 2018; official report 26 September; rescue-list window starts 25 September | Rohtang/Lahaul-Spiti/Kullu unexpected severe snowfall | PIB/BRO report and District Kullu event page | **Snowfall candidate.** Do not equate the report/rescue date to storm onset or invent visibility/wind duration. |
| Third week of September 1962 | Lahaul and Spiti severe early snowfall | https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/5706 | Primary paper abstract is provider-indexed; detailed event times/data and rights remain **UNVERIFIED**. Discovery lead only. |
| 2022, exact per-event dates pending extraction/review | Indian Himalayan region; paper reports 66 cloudburst cases | MAUSAM article 7150 | **Discovery list**, not 66 automatically admitted labels; restrict to reviewed Himachal records. |

For precipitation, a half-hourly rate in mm/h must be converted to accumulation by multiplying by 0.5 h before summing to an hour. Missing half-hours do not become zero rainfall. ERA5 accumulated-variable semantics must follow that product's metadata. A daily rain total cannot prove the one-hour cloudburst threshold.

### Technical references used

- Indian rules and applicable categories: https://thc.nic.in/Central%20Governmental%20Rules/use%20of%20low%20power%20Equipment%20in%20the%20frequency%20band%20865%20to%20868%20MHz%20for%20Short%20Range%20Devices%20Exemption%20from%20Licence%20Rules%2C2021.pdf
- NFAP 2025, current rule listing: https://www.dot.gov.in/static/uploads/2026/02/b110cdc386d3a4e41c8483d7ffd7c410.pdf
- LoRa Alliance current Regional Parameters page: https://resources.lora-alliance.org/technical-specifications/rp002-1-0-5-lorawan-regional-parameters
- Semtech calculator, primary indexed page; direct retrieval was blocked: https://www.semtech.com/design-support/lora-calculator
- Semtech-authored LoRa Design Guide hosted by Meshtastic, document URL discovered but full document not read in this session: https://meshtastic.org/assets/files/LoRa_Design_Guide-b3f1bb6c4d86b62a065c50d5961bc6b2.pdf
- Primary scalability analysis: https://arxiv.org/abs/1610.04793 . The simple ALOHA calculation used here is not a replacement for terrain/packet simulation.
- NWS complete heat-index calculation: https://www.weather.gov/tbw/heatindex
- Primary Indian PMS7003/high-humidity instrument study: https://arxiv.org/abs/2504.06615 . Use the paper's own domain and instruments; its reported instrument correlation is not INDRA's event accuracy.

## Part 3 — Complete Codex prompts

See **Codex_prompts.md** in this package: one master prompt and 14 separate phase prompts A–N. They use verified current paths, additive new modules, commands/tests, measurable software criteria, and explicit research-versus-field completion gates. The prompts incorporate dynamic N, health/trust, virtual nodes, 3/10/50/200 simulations, radio airtime and independent labels. Paste the master first, then one phase at a time.

### Every current code group Codex must inspect

- `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/ARCHITECTURE.md`, `docs/README.md`, `configs/model_catalog.json`.
- `ml/six_sensor_forecast/{contract,features,data,train,predict,c_codegen,export}.py`; `tests/test_six_sensor_forecast.py`, `tests/test_sensor_profiles.py`.
- `ml/india_mandi/{data,benchmark}.py`; `configs/mandi_modeled_forecast_v1.json`; `tests/test_india_mandi.py`.
- `ml/models/uci_beijing_6h/`, `ml/models/india_mandi_modeled_6h_v1/`, `ml/generated/india_mandi_modeled_6h_v1/`, and catalogued reduced-channel models; preserve their source roles.
- `ml/event_classifier/{features,predict,train,export,heatmap}.py`, reliability docs and committed rule-imitation artifacts; `tests/test_event_classifier.py`.
- `ml/india_sensor/{features,labels,config,preprocess_c}.py` and its remaining support modules; `tests/test_india_sensor.py`.
- `ml/hazard_context/{events,matching,warning,policy,train,episodes,diagnostics,acquire,era5,cli,output}.py`; event/warning/source configs; matching tests.
- `ml/operational/{contracts,aggregate,rules,ingestion,server,drivers,terrain,map_data,map_view}.py`; `tests/test_operational.py`.
- `ml/spatial_ensemble/`, `ml/deployment/readiness.py`; spatial/readiness tests.
- `esp32/model_test/`, `esp32/ml_integration/`, `esp32/operational_node/`; include sensor/config/packet files and integration/serial tests.
- `.github/workflows/ci.yml`, all `requirements*.txt`, `scripts/README.md`, `scripts/test_india_mandi.py`.
- `docs/DATA_LICENSES.md`, `docs/HIMALAYAN_EVENT_SCOPE.md`, `docs/HIMALAYAN_WARNING_PROTOCOL.md`, `docs/hazard_label_audit.md`, `docs/reference/IMD_HIMACHAL_DATA_REQUEST_PACKAGE.md`, data provenance/readiness receipts.
- Existing reference entry `master/kriging` is absent; Codex must not invent its contents. Historical `ml/kriging/kriging.py` exists at branch commit `bb03c20107a2557071131882bd6afdea7119584b` and should be read only as a prototype reference.
- The exact teammate-UI path/repo remains unknown. Record protected paths once supplied; never silently overwrite another application.

### Risks and assumptions to keep visible

Codex is the coding tool, not a runtime dependency. The event pipeline uses
conventional ML and rules. Independent co-located data and event/negative
monitoring remain gating inputs. Current research does not establish calibrated
Himachal event probability, operational warning accuracy, board/RF performance
or deployment cost. Virtual nodes do not manufacture observations or physical
votes. The planning simulation omits radio mechanisms and per-device scheduling;
read missed synthetic events together with false warnings. Existing UI location,
radio profile/type approval, surveyed installation/wiring/calibration, winter
power, deployment access and independent validation remain unresolved.

### Remaining practical questions

1. Where is the teammate UI: exact repository, branch and directory/local path?
2. Which ESP32-S3, LoRa radio/antenna and approved operating profile are installed?
3. What are the true sampling cadence, wind calibration, clock setup, elevations/
   datum, sensor installation heights and environmental operating envelopes?
4. Which co-located Himachal measurements, rain/snow observations, local hourly
   gauge records and verified non-event monitoring are actually accessible?
5. Is the target current-condition detection, next-six-hour onset prediction,
   or both? Which independent snowstorm definition will be evaluated?
6. What false-alert budget, missed-event tolerance, human-confirm policy and
   notification audience have been agreed for the pilot?
7. What valley/sites, node/gateway/power budget and VM/data-use constraints apply?

Begin A-C and pipeline/edge/network implementation immediately. Fit and score
real hazard heads when independent data is admitted. Physical radio operation
and public warnings remain gated by measured validation and configuration.
