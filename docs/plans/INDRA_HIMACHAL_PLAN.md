# INDRA Himachal implementation plan

Source: [review/build pack](../reference/indra_review_2026_10_14/README.md), verified against its SHA-256 manifest. Baseline `6bcda6b689868682cabfd95808eeb611dcb4aed3`.

Exactly six physical channels; derived history and metadata are separate. Conventional ML and deterministic rules only. Preserve all existing artifacts and applications. New UI stays in `apps/indra-himachal-ui`; teammate application will be supplied later.

| Phase | Deliverable | Status |
| --- | --- | --- |
| A | Audit, protected paths, offline committed-export checks and CI | COMPLETE |
| B | Causal native-cadence feature contract and meteorology | COMPLETE |
| C | Versioned rain/snowstorm/cloudburst risk rules | COMPLETE |
| D | Source provenance and independent observed labels | COMPLETE |
| E | Bounded anomaly engine and Python/C parity | PENDING |
| F | Dynamic registration, health, authenticated consensus and radio simulation | PENDING |
| G | Independent supervised model pipeline and registry | PENDING |
| H | Leakage-safe evaluation and evidence receipts | PENDING |
| I | Supported elevation-aware spatial estimates and uncertainty | PENDING |
| J | Isolated persistent backend and bounded jobs/SSE | PENDING |
| K | Isolated English/Hindi dashboard | PENDING |
| L | Human-confirmed pilot incident lifecycle and local fake sink | PENDING |
| M | Offline demo, Docker, CI, deployment runbooks and readiness | PENDING |
| N | Runtime-driven end-to-end simulation at 3/10/50/200 nodes | PENDING |

Each phase requires its relevant tests, existing regression suite, evidence receipt and coherent commit. Synthetic engineering results remain separate from empirical weather skill. No data download or retraining is needed for export verification.

## External evidence and field gates

- Independent synchronized Himachal six-channel histories plus observed outcomes and complete monitored negatives: NOT_READY.
- Empirical rain/snowstorm/cloudburst accuracy, calibration and pre-onset lead time: NOT_EVALUATED until the above data pass admission.
- Physical ESP32, installed sensor calibration, radio/type approval, surveyed site/elevation and winter power: NOT_TESTED.
- Public notifications: DISABLED. No configured/authorized public recipients.
- Teammate UI/shared backend: pending; do not overwrite or integrate an unknown application.

## Phase A completed

Phase A: verify the supplied package, recreate the pinned host environment, establish baseline tests, compile each committed export and test numerical parity, exact regeneration, provenance and tamper rejection. Legacy country/evidence macro differences require explicit compatibility, not numerical changes.

Validation: 209 tests and 124 subtests passed; CI-equivalent Ruff and offline six-profile committed-export verification passed. All protected artifact hashes unchanged. See `CURRENT_REPO_AUDIT.md` and `reports/deployment/phase_a_verification.json`. Next: Phase B native feature engine, then Phase C rules.

Phase B: new snapshot provenance/QC adapter, exact native features, water/ice humidity estimates and NWS branch-aware heat index; hourly/native washout and wind-calibration availability. Relevant existing/new checks and full regression suite passed. Existing models/headers unchanged. Next: versioned current-condition risk rules (Phase C).

Phase C: three risk-only current-condition rules, distinct hourly/native cloudburst profiles, explicit non-renormalized missing evidence and auxiliary disjoint storm sequence. Focused 26-test suite passed; full regression and lint passed. No independent hazard weights fitted; no probabilities, lead times or dispatch enabled. Next: source/label pipeline (Phase D).

Phase D: bounded cached context acquisition, audited manual imports, IMERG/POWER normalization, source ancestry deduplication and independent onset-label adapter reuse existing conservative gates. Full suite: 248 tests / 146 subtests passed. Offline label and manual-access CLI smoke runs returned NOT_READY as required; fixtures are never empirical training evidence. No real source download or fitted hazard head. Next: Phase E ESP32 anomaly/C contracts.
