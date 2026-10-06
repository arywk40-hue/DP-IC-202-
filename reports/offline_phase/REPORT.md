# Offline software completion — 6 October 2026

**Confidential: do not publish before IP review.** [Main overview](../../docs/PROJECT_OVERVIEW.md). All new scores are real NOAA archive observations; synthetic streams verify contracts only. No physical hardware was used.

## Completed without hardware

- Rebuilt all acquired India observations: 1,515,461 rows, 374 deduplicated physical sites; 1,497,056 current-core-valid rows at 373 sites. All 375 acquired NOAA 2024 files and 360 2023 files are represented before alias/core masks. A final 2025-01-01 hour is not another acquired year. Per-site coverage is in [station_coverage.csv](station_coverage.csv); per-variable observed counts are in [validation.json](validation.json).
- Recomputed all 374 feature matrices from original source bytes and current preprocessing, with exact equality. Rechecked source, feature, label and model hashes. India fit/evaluation has zero China rows. Original China models/data remain separate and unchanged. Missing PM is never zero.
- Preserved NWIC quarantine and restricted views. Clock, pressure, height and rights questions cannot be resolved from additional synthetic experiments; suspect Mandi/Kala Amb pressure/height remains excluded. This completes handling of acquired sources, not acquisition of every requested source or surveyed coordinates at every station.
- Ran A/B/C/D across whole-site national, whole-Himalaya-proxy, temporal-only and Himalayan-only protocols. Fit uses 2023–June 2024; selection July/August, separate calibration September/October, untouched test November/December. Geographic protocols use 20 km buffers; temporal-only intentionally shares sites across different times. Whole 72h blocks plus 24h history/6h label purges prevent cutoff overlap. Blocks are not independently adjudicated storms.
- Evaluated two predeclared weights per available head (122 candidate fits); all 61 selected fits were repeated with identical-seed model bytes. Calibration is separate from cutoff selection. Threshold optimization uses validation F2 under a maximum 0.25 false-positive hours per monitored station-day and minimum positive-site/episode support. This budget is a research policy, not field approval.
- Added optional independently masked PM regressors and rights/clock/country gates. Synthetic tests exercise a trained PM2.5 head with absent PM10. **No new real PM head was trained**: available CPCB clock assumptions/NC rights remain insufficient for clean admission.
- Added bounded arrival-order replay. Historical replay used 180 packets from a whole-site held-out November station (INI0000VABO); synthetic replay checks late/duplicate packets, a gap, invalid wind and out-of-training-range temperature. Batch/prefix feature parity was zero-error. This is no new field accuracy experiment.
- Fixed a reference-mask bug in reused pressure lags. Current source exactly reproduces all fitted archive feature matrices; the fix affects invalid-reference serving inputs, not these already-QC'd training results. Saved fit-code hashes remain historical; [validation receipt](validation.json) identifies subsequent source changes honestly.

## Measured results and losses

A=sensor/time, B=+GPS/height, C=regional calibration with B fallback, D=regional experts with B fallback. Brier is squared score error (lower better); AP is average precision (higher better). Uncalibrated scores are explicitly distinguished from probabilities. Full precision/recall/F1/AP, Brier intervals, confusion matrices, reliability/ECE, class support, per-zone/height/proxy coverage and cutoffs are in [results.json](results.json), [model_manifest.json](model_manifest.json) and [RESULTS.md](RESULTS.md).

| Protocol / target | A Brier | B Brier | C Brier | D Brier | Persistence Brier | Test positive hours |
|---|---:|---:|---:|---:|---:|---:|
| national / high_wind_measurement_at_6h | 0.00024178576131816953 | 0.000112363719381392 | 0.000112363719381392 | 0.000112363719381392 | 0.00027998656064508903 | 2 |
| national / hot_measurement_at_6h | 0.0036803388502448797 | 0.00351647543720901 | 0.00351647543720901 | 0.0031537599861621857 | 0.006522350295192578 | 61 |
| national / near_saturation_measurement_at_6h | 0.04166555032134056 | 0.04193742945790291 | 0.04193742945790291 | 0.041857052594423294 | 0.10333577093997863 | 1277 |
| himalaya_holdout / high_wind_measurement_at_6h | 1.5051155344281142e-07 | 8.035181764398658e-08 | 8.035181764398658e-08 | 8.035181764398658e-08 | 0.0 | 0 |
| himalaya_holdout / hot_measurement_at_6h | 1.3250660231278744e-06 | 1.950619889612426e-06 | 1.950619889612426e-06 | 1.950619889612426e-06 | 0.0 | 0 |
| himalaya_holdout / near_saturation_measurement_at_6h | 0.08780312538146973 | 0.08728485554456711 | 0.08728485554456711 | 0.08728485554456711 | 0.23117669315172154 | 316 |
| temporal / high_wind_measurement_at_6h | 0.000228318473091349 | 0.00023125886218622327 | 0.00023125886218622327 | 0.00023125886218622327 | 0.0003175719357143667 | 19 |
| temporal / hot_measurement_at_6h | 0.002076155971735716 | 0.0020591390784829855 | 0.0020591390784829855 | 0.0018503188621252775 | 0.003713956959112296 | 183 |
| temporal / near_saturation_measurement_at_6h | 0.03589605912566185 | 0.03582092747092247 | 0.035814378410577774 | 0.034692298620939255 | 0.08071723320338327 | 4806 |
| himalaya_only / high_wind_measurement_at_6h | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| himalaya_only / hot_measurement_at_6h | 8.949456287155044e-08 | 8.949456287155044e-08 | 8.949456287155044e-08 | 8.949456287155044e-08 | 0.0 | 0 |
| himalaya_only / near_saturation_measurement_at_6h | 0.14203619956970215 | 0.14203619956970215 | 0.14203619956970215 | 0.14203619956970215 | 0.34449093444909346 | 99 |

Geography is not a universal improvement: B worsens national RH and temporal wind Brier versus A; B improves whole-Himalaya RH but worsens its temperature diagnostic. D improves national hot-temperature Brier and temporal RH; wins are descriptive and intervals overlap. Do not compare Himalayan-only and national models as a fair model-selection contest: their held-out sites/support differ. A matched untouched Himalayan test with sufficient positive events remains necessary.

National wind misses both positive test hours; temporal wind misses all 19, including at validation-selected cutoffs. Whole-Himalaya wind/hot tests have zero positives, so detection recall is **unavailable**, not successful. Himalayan-only wind cannot be fitted; hot test has zero positives and RH calibration/cutoff support is insufficient. The stricter false-positive-budget cutoffs reduce RH recall compared with 0.5 in this test; they are not presented as an improvement. No additional tuning used test labels after seeing these losses.

National B at its raw validation cutoff: RH precision 0.8090909090909091, recall 0.2090837901331245, F1 0.33229620410703176 (1,277 positive hours); wind/hot precision/recall/F1 are zero (2/61 positives). D temporal hot recall is 0.01092896174863388 at its validation cutoff (183 positives), still very weak. A tiny Brier/ECE for rare wind is not evidence of useful detection.

Separate Platt calibration is available for national hot/RH and temporal wind/hot/RH, but national wind is withheld as uncalibrated. Temporal C has eligible RH mountain calibration; national C falls back. Whole-Himalaya D cannot train on the held-out mountain region. Station-bootstrap 95% metric intervals are not 80/90% prediction bands; shared weather episodes violate independent-station assumptions. Existing two-node weather bands remain unapproved/null; this phase does not upgrade them.

[RH comparison with confidence intervals](rh_brier_comparison.png) · [held-out reliability plot](rh_reliability.png). Figures reproduce frozen values; they do not establish field calibration.

## Prepared but requires hardware validation

The standalone national-B C99 export has 72 ordered features, 120 depth-3 trees and 1,788 total tree nodes. Exact raw-score host parity covers 5,384 archive/split-boundary/NaN cases; maximum discrepancy is below 0.00000056. Separate compiled tests verify hourly feature masks/numerics, missing history, calendar inputs and refusal gates. [Export manifest](../../esp32/india_sensor/export/export_manifest.json) records teacher/header hashes, thresholds/calibration, feature order and explicit **NOT HARDWARE VALIDATED** status.

The bounded hourly preprocessor has no heap allocation and reserves at most 848 bytes of history; telemetry is float32 with double derived intermediates. The primary contract is engineered float32 features; raw preprocessing tolerance and telemetry quantization are separate from exact tree parity. Timestamp, location and pressure-reference gates reject or mask invalid packets. This is a same-node threshold forecast export, **not the server's between-node spatial ensemble**. The six-channel spatial model remains on the server.

Cross-compiled ESP32-S3 research smoke harness: **19,612 bytes static RAM, 319,309 bytes flash**. Existing UART integration: 18,848 / 316,853 bytes; native USB: 19,080 / 314,101 bytes. These linker figures exclude runtime stack/heap and say nothing about actual latency/power/watchdogs. [Hardware procedure and interface](../../esp32/india_sensor/README.md) and the retained [A/B/hidden-C collection spec](../nwic_pipeline/NODE_COLLECTION_SPEC.md) prepare the physical tests.

## Blocked strictly by hardware

Physical offset/encoder calibration; sensor accuracy/exposure; RTC/GPS synchronization/drift; board runtime/stack/CPU/watchdog and measured energy; radio/outage behavior; outdoor hidden-C truth, real alert validation and long-duration reliability. None has been marked passed.

## Data/access and scientific blockers (not hardware)

- ERA5-Land files are absent: no `era5_*` fit/contribution. Download the 24 2023/2024 monthly NetCDF requests in `data/registry/cds_physics_requests.json`, with T/dewpoint, surface pressure and u/v wind for [38,68,6,98.5]. Use your CDS terms/token or manual download; [exact request/availability/pressure instructions](../physics_phase/ERA5_DOWNLOAD.md). No authenticated request was submitted. This sensor-only forecast excludes ERA5 by design; any joined-background spatial experiment must be separately named, causal and paired against station-only rows.
- OpenAQ requires a key and provider rights/clock units; IMD AWS/ARG/rain/event exports need authorized permission; MOSDAC needs product access. NWIC/Delhi clock/reference/rights unresolved; CPCB is a restricted legacy research view. Independent hazard negatives, official geographic boundaries and sufficient high-altitude/short-distance stations are unavailable.
- No real 1–20 km mesh validation, minute trends or gust labels. NOAA hourly mean archive is not BME280/encoder/PMS7003 sensor transfer validation. SRTM ground height is not surveyed sensor elevation. Himalaya proxy has only 13 eligible sites, excludes uncertain-height belt sites, and is not an official boundary.
- No authenticated node ingestion, end-to-end radio node or production alert system. Plausible wrong units, stuck sensors and long-term drift cannot be reliably detected by the present range/history gates alone. Local artifact hashes prevent accidental tampering but do not authenticate network messages.

## Disaster outputs: DISABLED

No independent cloudburst, extreme-rainfall, storm, flash-flood, landslide or wildfire targets are trained/released. T/RH/pressure/wind are nonspecific precursors; high-RH is not rainfall/fog, optical PM is not an identified wildfire. [Source/capability research](../../docs/INDIA_SENSOR_RISK_PLAN.md) covers IMD rain and storm records, GPM IMERG, FIRMS, CWC/GSI and authorized access. These are candidates, not accepted labels. [IMD MAUSAM](https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/5084) describes extreme local rain for cloudbursts; no rain gauge exists in the specified sensors. Satellite modeled rain/thermal detections require uncertainty/attribution and cannot establish cloudburst/flash-flood/field-alert truth by themselves. Admission requires observed evidence, monitored negatives, provider rights, uncertainty, event IDs and whole-event separation. Missing labels stay null.

Legacy Beijing rule-matching event scores are retained only as explicitly unvalidated sensor-rule diagnostics in their original interfaces; they are neither India models nor enabled disaster predictions.

## Reproduction, tests and version control

[Exact commands](../../ml/india_sensor/README.md). Versioned national-B UBJ weights/metadata permit raw-free checkout inference, plus C headers/manifest, compact fixtures, tests and reports. Large observations, matrices, caches, build products and other working model fits are ignored; hashed provenance is retained. No keys/tokens are committed. CI's older Python/package environment is separate from the measured Python 3.13.11 pinned runtime; remote CI has not yet been observed.

The October 5 report/patch snapshots remain historical evidence, not current-source patch instructions. No old evidence, China artifact or original documentation was deleted. The measured fit's `esp32` text predates the export; use the later export manifest for deployment preparation. The old claim that all C heads fall back is superseded only for temporal RH. Spatial results are unchanged.

Final software checks: **123 tests plus 8 subtests passed**; CI-equivalent Ruff, stricter new-code unused-import checks and Python compile checks passed. Eight CLI help commands, bundled prediction/replay and the retained A/B demo were executed. Four firmware configurations cross-compiled. [Final receipt](verification.json) records hashes and software checks; Git history records the separate commits/push. Dependency deprecations and sandbox Arrow/font-cache warnings were observed without failures. No deployment approval follows from any result.
