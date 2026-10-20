# Submission review — 21 October 2026 (Asia/Kolkata)

The active project is a six-channel numerical forecasting prototype with separate
Himalayan hazard research. The root README, feature list, model index and submission
guide now point to the active hybrid rather than older compact-only results.

## Executed checks

- Frozen Mandi source: 24,336 modeled hourly positions; 954 reused test pairs.
- Seven identical-cohort comparisons: persistence, compact/history XGBoost, ridge,
  MLP32, MLP64→32 and the fixed active hybrid. No fitting/selection on this run.
- 322 Python tests and 172 subtests passed; 8 desktop/mobile workflow tests passed.
- 2 JavaScript contract tests, production build and targeted Ruff checks passed.
- Actual historical Mandi replay checked in Chrome on desktop/mobile, through the
  development frontend and backend-served production page. Source labels, one node,
  stale status, 25/25 history, hybrid outputs and hazard abstention were checked.
- Map cleanup now cancels queued callbacks; changing imported nodes replaces an
  invalid selection. The latter has a desktop/mobile regression test.
- All 129 protected original artifact/handoff identities and 108 frozen export
  identities remain unchanged. Old reports/models/raw source were not removed.

## Deliverable and remaining work

The submission includes runnable source, saved models, a reproducible numerical
test, input/output/label examples, learned-component paths and blend coefficients,
feature/status documentation and browser evidence. Raw CSVs and local stores stay
ignored. Both services remain local; no hosting deployment was made.

This does not establish measured Mandi station accuracy, calibrated disaster
probabilities, live online learning, physical ESP32/RF operation or validated
neighbour/spatial inference. Those claims need their own independent evidence.

See [submission guide](../SUBMISSION_GUIDE.md), [features](../FEATURES.md),
[Mandi report](../../reports/submission/2026-10-21/REPORT.md) and
[verification receipt](../../reports/submission/2026-10-21/verification.json).
