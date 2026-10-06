"""Labels stay outside features. Missing evidence never means a negative event."""
import pandas as pd

from ml.india_sensor.features import utc
from ml.six_sensor_forecast.features import future_targets
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


def measured_future(frame, cfg):
    """Exact t+6h completed hourly measurement, NOT occurrence during next 6h."""
    ordered = frame.sort_values(['location_id', 'timestamp_utc']).reset_index(drop=True)
    future = future_targets(ordered[['location_id', 'timestamp_utc', *RAW_SENSOR_COLUMNS]], cfg['forecast_hours'])
    labels = ordered[['physical_site_id', 'timestamp_utc', 'source_id']].copy()
    labels['target_timestamp_utc'] = labels.timestamp_utc + pd.Timedelta(hours=cfg['forecast_hours'])
    for name, target in cfg['threshold_targets'].items():
        v = future[target['variable']]
        labels[name] = (v >= target['threshold']).astype(float).where(v.notna())
    return labels


EVENT_FIELDS = {'physical_site_id', 'interval_start_utc', 'interval_end_utc', 'target', 'label',
                'source_id', 'source_version', 'raw_sha256', 'evidence_kind', 'negative_coverage_verified',
                'event_group_id', 'available_at_utc', 'definition_version', 'country_code',
                'location_uncertainty_m', 'time_uncertainty_seconds'}


def validate_independent(frame, allowed_targets, allowed_sources):
    """Admission contract for independently acquired, adjudicated event exports.

    Weak rules, modeled rain and alert polygons cannot pass as observed events.
    This validator does not establish a provider's rights or scientific truth.
    """
    if set(frame) != EVENT_FIELDS or frame.empty:
        raise ValueError('Independent label schema/empty data')
    out = frame.copy()
    for c in ['interval_start_utc', 'interval_end_utc', 'available_at_utc']:
        out[c] = utc(out[c])
    if (out.interval_start_utc >= out.interval_end_utc).any() or (out.available_at_utc < out.interval_end_utc).any():
        raise ValueError('Invalid event interval or availability')
    if not out.target.isin(allowed_targets).all() or not out.source_id.isin(allowed_sources).all():
        raise ValueError('Unapproved target/source')
    if not out.country_code.eq('IN').all():
        raise ValueError('Indian event labels only')
    for name in ['location_uncertainty_m', 'time_uncertainty_seconds']:
        values = pd.to_numeric(out[name], errors='raise')
        if values.isna().any() or not values.between(0, 1e6).all():
            raise ValueError('Explicit finite location/time uncertainty required')
    if not out.evidence_kind.eq('independent_observed').all():
        raise ValueError('Weak/modeled labels cannot become historical event truth')
    if not out.label.isin([0, 1]).all():
        raise ValueError('Unknown labels must be omitted, never filled with zero')
    if ((out.label == 0) & ~out.negative_coverage_verified.eq(True)).any():
        raise ValueError('Negative labels need explicit monitored non-event coverage')
    for c in ['physical_site_id', 'source_id', 'source_version', 'event_group_id', 'definition_version']:
        if out[c].isna().any() or out[c].astype(str).str.strip().eq('').any():
            raise ValueError('Missing label provenance/group')
    if out.raw_sha256.isna().any() or not out.raw_sha256.astype(str).str.fullmatch('[0-9a-f]{64}').all():
        raise ValueError('Raw label SHA256 required')
    if out.duplicated(['physical_site_id', 'target', 'interval_start_utc', 'interval_end_utc']).any():
        raise ValueError('Duplicate label intervals')
    return out


def require_disjoint_events(groups_by_role):
    seen = set()
    for groups in groups_by_role.values():
        present = set(groups) - {None, ''}
        if present & seen:
            raise ValueError('Shared event episode across folds')
        seen |= present
