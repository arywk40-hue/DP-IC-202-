# INDRA Himachal implementation plan

Source: [review/build pack](../reference/indra_review_2026_10_14/README.md), verified against its SHA-256 manifest. Baseline `6bcda6b689868682cabfd95808eeb611dcb4aed3`.

Exactly six physical channels; derived history and metadata are separate. Conventional ML and deterministic rules only. Preserve all existing artifacts and applications. The supplied teammate dashboard is preserved under `docs/reference/dp_mesh_dashboard_handoff`; its working adaptation stays in `apps/indra-himachal-ui`.

| Phase | Deliverable | Status |
| --- | --- | --- |
| A | Audit, protected paths, offline committed-export checks and CI | COMPLETE |
| B | Causal native-cadence feature contract and meteorology | COMPLETE |
| C | Versioned rain/snowstorm/cloudburst risk rules | COMPLETE |
| D | Source provenance and independent observed labels | COMPLETE |
| E | Bounded anomaly engine and Python/C parity | COMPLETE |
| F | Dynamic registration, health, authenticated consensus and radio simulation | IN_PROGRESS |
| G | Independent supervised model pipeline and registry | PENDING |
| H | Leakage-safe evaluation and evidence receipts | PENDING |
| I | Supported elevation-aware spatial estimates and uncertainty | PENDING |
| J | Isolated persistent backend and bounded jobs/SSE | PARTIAL — read-only SQLite dashboard adapter; jobs/SSE pending |
| K | Isolated English/Hindi dashboard | PARTIAL — teammate UI connected; Hindi and full spatial/incident workflows pending |
| L | Human-confirmed pilot incident lifecycle and local fake sink | PENDING |
| M | Offline demo, Docker, CI, deployment runbooks and readiness | PENDING |
| N | Runtime-driven end-to-end simulation at 3/10/50/200 nodes | PENDING |

Each phase requires its relevant tests, existing regression suite, evidence receipt and coherent commit. Synthetic engineering results remain separate from empirical weather skill. No data download or retraining is needed for export verification.

## External evidence and field gates

- Independent synchronized Himachal six-channel histories plus observed outcomes and complete monitored negatives: NOT_READY.
- Empirical rain/snowstorm/cloudburst accuracy, calibration and pre-onset lead time: NOT_EVALUATED until the above data pass admission.
- Physical ESP32, installed sensor calibration, radio/type approval, surveyed site/elevation and winter power: NOT_TESTED.
- Public notifications: DISABLED. No configured/authorized public recipients.
- Teammate UI supplied and preserved byte-for-byte; working six-channel integration tested. Master firmware transport is not connected.

## Phase A completed

Phase A: verify the supplied package, recreate the pinned host environment, establish baseline tests, compile each committed export and test numerical parity, exact regeneration, provenance and tamper rejection. Legacy country/evidence macro differences require explicit compatibility, not numerical changes.

Validation: 209 tests and 124 subtests passed; CI-equivalent Ruff and offline six-profile committed-export verification passed. All protected artifact hashes unchanged. See `CURRENT_REPO_AUDIT.md` and `reports/deployment/phase_a_verification.json`. Next: Phase B native feature engine, then Phase C rules.

Phase B: new snapshot provenance/QC adapter, exact native features, water/ice humidity estimates and NWS branch-aware heat index; hourly/native washout and wind-calibration availability. Relevant existing/new checks and full regression suite passed. Existing models/headers unchanged. Next: versioned current-condition risk rules (Phase C).

Phase C: three risk-only current-condition rules, distinct hourly/native cloudburst profiles, explicit non-renormalized missing evidence and auxiliary disjoint storm sequence. Focused 26-test suite passed; full regression and lint passed. No independent hazard weights fitted; no probabilities, lead times or dispatch enabled. Next: source/label pipeline (Phase D).

Phase D: bounded cached context acquisition, audited manual imports, IMERG/POWER normalization, source ancestry deduplication and independent onset-label adapter reuse existing conservative gates. Full suite: 248 tests / 146 subtests passed. Offline label and manual-access CLI smoke runs returned NOT_READY as required; fixtures are never empirical training evidence. No real source download or fitted hazard head. Next: Phase E ESP32 anomaly/C contracts.

Phase E: bounded diagnostics, generated Python/C stateful parity and capability-limited local risk indicator; isolated physical-default-disabled firmware. Full suite 258 tests / 153 subtests; four firmware cross-builds pass. Anomaly state 424 bytes; Xtensa object/static stack and full firmware sizes recorded. Native minute collector spans 75 min and cannot establish local rain/snow six-hour pressure history; hourly mode and server histories are separate supported paths. Board/RF/latency/peak stack remain NOT_TESTED. Next: Phase F dynamic nodes/health/authenticated consensus and radio scheduling.

Phase F in progress: dynamic registry and bounded spatial candidate index, per-channel health/recovery, locked authenticated consensus, exact 82-byte codec and conditional Indian RF profile. Focused tests passed before subsequent reboot/expiry hardening; radio scheduling, C codec/policy parity and 30-seed scale receipts remain to finish before committing this phase. A–E pushed to origin/main at ec76184.

## Teammate dashboard integration steering (2026-10-15)

User supplied DP Mesh Dashboard and requested connection before the remaining phases. Working UI now consumes the saved Mandi student and current experimental risk rules through a separate read-only SQLite/FastAPI adapter. Original handoff is hashed and retained unchanged. Six channels, model/source evidence, missing-history abstention, stale/cache labels and disabled hardware commands replace the old browser mocks and extra sensors. This is a focused J/K subset, not completion of the wider G–N plan. See `docs/HIMACHAL_DASHBOARD_INTEGRATION.md` and `reports/himachal/dashboard/verification.json`.

## Numerical architecture improvement (2026-10-15)

User requested an architecture beyond XGBoost. Two six-channel, 66-history-feature residual neural networks were trained and compared on the existing Mandi modeled cohort. Validation chooses neural temperature/wind, ridge pressure and XGBoost teacher humidity/PM heads. The research candidates are saved separately; no existing weight/export or active UI profile is replaced. This numerical experiment does not complete the independent hazard training/evaluation phases. Online learning remains NOT_IMPLEMENTED; see `docs/FORECAST_MODEL_IMPROVEMENT.md`.
