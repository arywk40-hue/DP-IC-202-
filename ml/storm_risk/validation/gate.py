"""A failed gate changes naming, never triggers test-driven refitting."""
from __future__ import annotations


def evaluate_gate(result: dict | None, bootstrap: dict | None, positive_events: int, method: str, cfg: dict) -> dict:
    """Evaluate every declared requirement without changing frozen models."""
    gate = cfg['gate']
    failures = []
    if cfg['evidence_kind'] != 'confirmed_event_records':
        failures.append('SYNTHETIC_EVIDENCE_ONLY')
    if method == 'none':
        failures.append('NO_FITTED_CALIBRATOR')
    if positive_events < gate['min_positives_test']:
        failures.append('INSUFFICIENT_INDEPENDENT_POSITIVE_TEST_EVENTS')
    if result is None or bootstrap is None:
        failures.append('HELD_OUT_DIAGNOSTICS_UNAVAILABLE')
    else:
        interval = bootstrap['intervals']['brier_skill_score']
        if interval['lower'] is None or interval['lower'] <= gate['bss_min']:
            failures.append('BRIER_SKILL_LOWER_BOUND_NOT_ABOVE_MINIMUM')
        if result['reliability'] >= gate['reliability_max']:
            failures.append('RELIABILITY_COMPONENT_ABOVE_LIMIT')
        if any(b['unreliable'] for b in result['reliability_diagram']['bins']):
            failures.append('POPULATED_RELIABILITY_BINS_UNDERSAMPLED')
        if bootstrap['days'] < gate['min_test_days']:
            failures.append('INSUFFICIENT_TEST_DAY_BLOCKS')
    return dict(calibrated=not failures, failed_conditions=failures, thresholds=gate)
