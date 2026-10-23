"""Submission scoring and provenance checks; synthetic fixtures prove wiring only."""
import copy

import numpy as np
import pandas as pd
import pytest

from ml.india_mandi.submission import compare, replay_records
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from server.dashboard import assess


def inputs():
    values = np.tile([20., 65., 930., 30., 60., 3.], (30, 1))
    frame = pd.DataFrame(values, columns=RAW_SENSOR_COLUMNS)
    frame['location_id'] = 'synthetic_test_grid'
    frame['timestamp_utc'] = pd.date_range('2026-01-01', periods=30, freq='h', tz='UTC')
    manifest = dict(retrieved_at_utc='2026-01-03T00:00:00Z', requested_latitude=31.71,
        requested_longitude=76.93, source_receipts=[dict(
            weather=dict(returned_latitude=31.67, returned_longitude=76.94),
            air=dict(returned_latitude=31.7, returned_longitude=76.9))])
    return frame, manifest


def test_replay_retains_retrieval_time_and_never_claims_physical_hazards():
    frame, manifest = inputs()
    records = replay_records(frame, manifest)
    assert len(records) == 25
    for record in records:
        assert record['source_class'] == 'modeled_grid' and record['pressure_reference'] == 'grid_surface'
        assert pd.Timestamp(record['available_at_utc']) == pd.Timestamp(manifest['retrieved_at_utc'])
        assert record['elevation_m'] is None and not any(record['calibration_ids'].values())
        assert record['source_cell_id'].count('weather') == 1 and 'air' in record['source_cell_id']
    node = assess(records, now=manifest['retrieved_at_utc'])[0]
    assert node['forecastStatus'] == 'HYBRID_READY' and node['stale']
    assert not node['syntheticDemo']  # Fixture uses the modeled-source contract, not field truth.
    assert all(r['abstain'] and r['probability'] is None and r['assessment_state'] == 'SOURCE_REFERENCE_UNSUPPORTED'
               for r in node['risks'].values())


@pytest.mark.parametrize('case', ['short', 'gap', 'missing_channel', 'retrieved_too_early'])
def test_replay_rejects_incomplete_or_false_provenance(case):
    frame, manifest = inputs()
    if case == 'short': frame = frame.tail(24)
    if case == 'gap': frame = frame.drop(frame.index[-5])
    if case == 'missing_channel': frame.loc[frame.index[-1], 'pm25_ug_m3'] = np.nan
    if case == 'retrieved_too_early': manifest['retrieved_at_utc'] = '2026-01-01T00:00:00Z'
    with pytest.raises(ValueError):
        replay_records(frame, manifest)


def test_metrics_score_identical_cohorts_and_reject_silent_row_loss():
    truth = np.arange(60, dtype=float).reshape(10, 6)
    result = compare({'exact': truth.copy(), 'offset': truth+2}, truth, truth+4)
    for c in RAW_SENSOR_COLUMNS:
        assert result['exact'][c]['mae'] == 0 and result['exact'][c]['r2'] == 1
        assert result['offset'][c]['mae'] == 2 and result['offset'][c]['rows'] == 10
        assert result['offset'][c]['mae_skill_vs_persistence'] == .5
    with pytest.raises(ValueError, match='identical'):
        compare({'lost_row': truth[:-1]}, truth, truth+4)
    bad = copy.deepcopy(truth); bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        compare({'missing': bad}, truth, truth+4)
