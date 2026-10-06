# Independent Indian hazard labels + ERA5 context — 6 October 2026

**Confidential: do not publish before IP review.** [Audit/source table](../../docs/hazard_label_audit.md), [commands/schema/protocol](../../ml/hazard_context/README.md), [machine-readable receipt](results.json).

**BASELINE PRESERVED: YES.** The original `bc1d8be` passed local tests but GitHub had one GCC test-harness warning. A separate test-only repair, `1e67bd9`, passed [GitHub Actions](https://github.com/arywk40-hue/DP-IC-202-/actions/runs/37425991889). Every protected source/model/export/frozen-report hash is unchanged. New CI dependencies/lint scope serve the additive phase; no sensor-only or ESP32 behavior changed. Existing China data/artifacts remain isolated.

## What was completed

- Audited all existing measured/weak/event labels and reviewed primary IMD, MAUSAM, NASA IMERG/FIRMS, CWC, GSI, CDS and OpenAQ documentation before fitting. Registered source statuses and reasons; **no source automatically admitted**.
- Added nullable event JSON schema, source/rights/independence/QC/provenance gates, malformed-row quarantine, strict UTC and location/measurement/uncertainty checks. Unknown location/time/severity is not fabricated. Conflicting duplicate reports stop matching for adjudication.
- Added WGS84 station-event matching and conservative multi-report/multi-station event groups. Pre/post/uncertain windows stay unlabeled; monitored negatives require reviewed spatial/temporal coverage and provenance. A dry point gauge cannot certify no event within a 20 km radius.
- Added whole-event split isolation, temporal buffers, minimum event/site/year/negative support screens, future-label separation, gated research fits, validation operating curves and episode-level evaluation. Synthetic sources cannot be admitted by the real training path. Cloudburst detection/prediction remains unavailable, even though a qualified future research corpus can be analyzed separately.
- Verified the unchanged **24 CDS requests**. Added dry-run/normal authenticated downloader interface, local NetCDF normalization, coordinate/unit/time/member/duplicate checks, per-row source hashes and exact backward joins. No token was read and no authenticated download was attempted.
- Added matched Track S versus Track SB research comparison using identical rows/labels/splits, per-track precision/recall/F1/AP/Brier/ECE and paired station-bootstrap Brier differences. Track S uses the unchanged sensor builder; SB adds only named context fields afterward. Previous full-data S results are untouched.
- Ran synthetic end-to-end schema/matching/NetCDF fixtures, masked availability, leakage/safety contracts and a toy S/SB fit test. Their counts/accuracy are **not real data evidence**. CLI normalization/matching/training gates were exercised; the synthetic hazard fit remains refused.

## Source and target status

**Independent sources reviewed:** IMD station rain and event routes; MAUSAM cloudburst publication; NASA IMERG; CWC observations/occurrence records; GSI inventory; FIRMS thermal detections; official storm routes. Beijing input-generated rules remain rejected and separate.

**Admitted label sources: none.** Real normalized event records: **0**. Verified real monitored-negative windows: **0**. Candidates need rights, dated/location-resolved independent definitions, uncertainty and complete coverage—not just an accessible webpage.

| Target | Status | Reason |
|---|---|---|
| extreme_rainfall | NOT_ENOUGH_DATA | No admitted gauge corpus/monitored negatives |
| cloudburst | DISABLED | No admissible local-gauge event corpus/negative coverage |
| flash_flood | NOT_ENOUGH_DATA | No independent occurrence corpus; rain/river forecasts are not equivalent |
| landslide | NOT_ENOUGH_DATA | No dated admitted inventory/negative survey coverage |
| wildfire | NOT_ENOUGH_DATA | Thermal anomalies not automatically confirmed vegetation wildfire |
| storm | NOT_ENOUGH_DATA | No authorized independent time/location event corpus |

**Rejected/blocked:** NOAA weather thresholds remain measured-weather research, not disaster truth; Beijing rules are input-generated/non-India. NWIC wet-only rain lacks negatives/clock/rights verification. IMD needs authorized exports/rights. MAUSAM's article has conflicting CC-BY-NC/generic CC-BY notices, describes 2017 cases outside the benchmark, and its PDF fetch timed out; no event coordinates/times were invented from the abstract. CWC's policy PDF returned 401. GSI advertises public inventory downloads, but actual dated export/rights/monitored coverage was not established. FIRMS API needs MAP_KEY and coverage/attribution. See the source registry/audit for each recorded status.

## ERA5 status and comparison

**ERA5 STATUS: access blocked. ERA5 ROWS: 0 real.** No NetCDF/GRIB files or CDS credentials locally. No requests submitted or authentication bypassed. [Exact manual/API instructions](ERA5_ACCESS.md) use the existing 2023/2024 five-variable requests.

Prepared variables: temperature, dewpoint, grid-surface pressure, u/v wind, derived speed/RH/dewpoint depression, all `era5_*`. No new rain/CAPE requests. For issue H, context is the exact preceding-hour instant H−1h, not a measured station hourly average. Default mode is **retrospective_background_context**; normalized publication availability remains unknown. Online-mode fields are withheld unless provider-backed timestamps establish availability. Reanalysis forcing may indirectly include held-out observations.

**SENSOR-ONLY RESULTS:** frozen NOAA results unchanged, including zero held-out wind recall and inconsistent geography benefits. [Original results/losses](../offline_phase/RESULTS.md).

**SENSOR + ERA5 RESULTS:** not run on real data; no matched real rows. **DOES ERA5 HELP? INCONCLUSIVE.** Synthetic fitting only verifies code contracts, not a gain/loss claim. Full real ingestion, performance, availability and calibration remain unverified.

## Himalayan support and PM

Existing QC-valid geography proxy: **13 sites, elevation 550–3258 m**. It is not an official Himalayan boundary; no new licensed boundary layer was obtained. Independent admitted Himalayan events/positive hours: **0/0**. Event types, distances, quality and altitude-conditioned skill cannot be estimated without records. The five cases described by the MAUSAM abstract are not five imported/admitted training records. [Coverage receipt](himalaya_support.json).

**EVENT-LEVEL RESULTS:** unavailable for real events. The scorer implements detected-event counts, first-alert lead times, false/unknown alert episodes, event recall/precision and missed-event fraction; only synthetic contracts were exercised. Rare-event hourly support is not counted as independent disasters.

**PM TRAINING STATUS:** no new real head. CPCB remains restricted/clock-assumption limited; Delhi/Sensor.Community interpretation unresolved. OpenAQ API requires a key, but its documented public S3 archive is also lawful access; archive rows alone do not verify country, provider rights, averaging windows and complete QC. No PM export was acquired/admitted. [PM audit](pm_admission.json), [additional source distinctions](../../docs/hazard_label_audit.md).

**DISASTER OUTPUTS: DISABLED.** No field/hardware or independent disaster accuracy claim was upgraded.

## Verification and limitations

Local full suite: **140 tests plus 8 subtests passed**, including 17 new phase contracts. Ruff configured checks, stricter new-code checks, compile checks and CLI exercises passed; numerical-library deprecation/NetCDF ABI warnings were observed without failures. New-phase remote CI is checked after publication; the baseline repair's remote CI is already green.

Point matching and model procedures are software-tested, not validated against real hazard exports. Polygon boundaries use geodesic-segment approximations; ambiguous records conservatively group or refuse. Matching has explicit pair budgets and requires preserving master group IDs across partitions. The support floors are conservative research guards, not proofs of statistical adequacy; calibration/threshold selection still uses correlated hourly weather data, with episode diagnostics reported separately. Metadata review does not authenticate a provider or prove scientific truth. Real source admission, independent positives/negatives, official geography, real S/SB experiments and field validation remain necessary.

Files added: `ml/hazard_context/`, three hazard configurations, `requirements-hazard-context.txt`, phase tests, audit and phase receipts/access instructions. Existing edits: CI dependency/lint scope, ignore rules and documentation links. All frozen reports, models, China files and ESP32 claims are unchanged. The earlier GCC test fix is a separate commit.
