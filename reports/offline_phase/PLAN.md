# Offline completion plan

**Confidential: do not publish before IP review.** Existing spatial/forecast models remain intact. New experiments use a separate configuration/output directory and preserve the previous measured evidence.

## Can be completed without hardware

1. Rebuild and audit all acquired Indian hourly data; retain unresolved NWIC/PM source gates and verify country/source/site isolation.
2. Extend whole-site/Himalaya holdouts with separate temporal-only and Himalayan-only experiments. Purge history/target windows and whole 72h boundary blocks. Do not mistake geographic proxies for official state boundaries.
3. Refit A–D with two predeclared class-weight candidates. Select candidate and raw-score threshold using July/August validation only; calibrate the selected fit on separate September/October data. Freeze choices before November/December evaluation. Report unsupported/rare classes, false-positive hours and losses.
4. Verify identical-seed repeated fits and metadata/provenance. Add PM training/admission utilities, but fit actual PM only if source time/units/rights and observed labels are approved. Keep every unsupported disaster head unavailable.
5. Add bounded incremental sensor-stream replay, historical live-like comparison and synthetic failures. Generate standalone C trees plus causal hourly preprocessing, fixed feature order/thresholds, test vectors and a board smoke-test harness. Verify compiled host parity and cross-compilation where the local toolchain supports it.
6. Run all tests/lint/CLI checks, audit tracked files and credentials, document explicit data-access and hardware blockers, commit verified components separately and push the current branch.

## Requires hardware

Sensor/encoder physical calibration, installed sensor accuracy, UTC synchronization/drift, measured board RAM/latency/watchdog/power, radio outage behavior, outdoor hidden-C accuracy, real alerts and long-duration reliability. Prepare collection schemas, replay/test harnesses and an acceptance checklist; record none as passed.

## Additional data/access blockers, separate from hardware

NWIC clock/pressure/rights; CPCB compilation clock verification/restricted terms; OpenAQ provider/key access; CDS product terms/token/files; authorized IMD hourly rain and independently observed event labels/monitored negatives; official regional boundaries. Synthetic labels and archive weather thresholds cannot establish disaster detection.
