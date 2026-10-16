"""Actual hybrid inference, chronology, warm-up and persisted-cache migration."""
import copy
import json
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
import numpy as np
import pandas as pd
import pytest

from ml.india_mandi.hybrid import DEFAULT_MODEL, PROFILE_ID, Hybrid, select_blend
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.predict import predict as compact_predict
from server.dashboard import MODEL, Store, assess, create_app, demo_observations

NOW = '2026-10-16T06:00:00Z'
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def engine():
    return Hybrid()


def hourly(rows):
    data = [dict(location_id=r['node_id'], timestamp_utc=r['timestamp_utc'], **r['measurements']) for r in rows]
    end = pd.Timestamp(data[-1]['timestamp_utc'])
    return pd.DataFrame([r for r in data if (end - pd.Timestamp(r['timestamp_utc'])).total_seconds() % 3600 == 0])


def test_active_api_runs_actual_neural_blend_and_differs_from_compact(engine):
    raw = [r for r in demo_observations(NOW) if r['node_id'] == 'demo-01']
    assert len(raw) == 97
    frame = hourly(raw)
    direct = engine.predict(frame).iloc[-1]
    node = assess(raw, now=NOW)[0]
    assert MODEL == DEFAULT_MODEL and node['forecastModel']['id'] == PROFILE_ID
    assert node['forecastStatus'] == 'HYBRID_READY' and node['forecastHistoryRows'] == 25
    assert all(head['weights']['neural'] > 0 for head in node['forecastModel']['blendWeights'].values())
    np.testing.assert_allclose(list(node['forecast6h'].values()), [direct['forecast_'+c] for c in RAW_SENSOR_COLUMNS], rtol=0, atol=1e-6)
    old = compact_predict(frame, ROOT/'ml/models/india_mandi_modeled_6h_v1', 'student').iloc[-1]
    assert not np.allclose(list(node['forecast6h'].values()), [old['forecast_'+c] for c in RAW_SENSOR_COLUMNS])


def test_gaps_and_missing_current_never_become_fabricated_history(engine):
    rows = [r for r in demo_observations(NOW) if r['node_id'] == 'demo-01']
    frame = hourly(rows)
    missing_hour = frame.drop(index=frame.index[-3])
    result = engine.predict(missing_hour).iloc[-1]
    assert result.status == 'WARMING_UP_PERSISTENCE'
    np.testing.assert_allclose([result['forecast_'+c] for c in RAW_SENSOR_COLUMNS], frame.iloc[-1][RAW_SENSOR_COLUMNS].to_numpy(float))
    incomplete = frame.copy()
    incomplete.loc[incomplete.index[-1], 'pm25_ug_m3'] = np.nan
    result = engine.predict(incomplete).iloc[-1]
    assert result.status == 'MISSING_CURRENT_SENSOR'
    assert all(pd.isna(result['forecast_'+c]) for c in RAW_SENSOR_COLUMNS)
    # No future observation may change an earlier issue's forecast.
    longer = pd.concat([frame, frame.tail(1).assign(timestamp_utc=pd.Timestamp(NOW)+pd.Timedelta(hours=1), temperature_c=80)], ignore_index=True)
    earlier = engine.predict(longer).iloc[-2]
    expected = engine.predict(frame).iloc[-1]
    # BLAS may regroup the same dot product for different batch dimensions.
    np.testing.assert_allclose([earlier['forecast_'+c] for c in RAW_SENSOR_COLUMNS], [expected['forecast_'+c] for c in RAW_SENSOR_COLUMNS], rtol=0, atol=1e-12)


def test_off_top_of_hour_native_snapshots_use_exact_hourly_phase():
    rows = [r for r in demo_observations('2026-10-16T06:15:00Z') if r['node_id'] == 'demo-01']
    node = assess(rows, now='2026-10-16T06:15:01Z')[0]
    assert node['forecastStatus'] == 'HYBRID_READY'
    assert node['forecastTimestamp'] == '2026-10-16T12:15:00+00:00'
    assert all(pd.Timestamp(r['timestamp']).minute == 15 for r in node['forecastHistory'])


def test_cache_migration_recomputes_values_instead_of_relabelling(tmp_path):
    nodes = assess(demo_observations(NOW), now=NOW)
    expected = copy.deepcopy(nodes[0]['forecast6h'])
    for n in nodes:
        n['forecastModel'] = dict(id='india_mandi_modeled_6h_v1')
        n['forecast6h'] = dict.fromkeys(RAW_SENSOR_COLUMNS, -999)
        n.pop('forecastHistory', None)
    path = tmp_path/'cache.sqlite'
    Store(path).replace(nodes)
    with TestClient(create_app(path, clock=lambda: pd.Timestamp(NOW).timestamp())) as client:
        result = client.get('/api/nodes/demo-01/telemetry').json()
        assert result['forecastModel']['id'] == PROFILE_ID
        assert result['forecast6h'] == expected
        assert client.get('/api/status').json()['forecastArchitecture'] == 'NEURAL_XGB_RIDGE_HISTORY_ENSEMBLE'
    # A legacy seven-hour cache cannot be presented as a warmed-up hybrid.
    for n in nodes:
        n['history'] = n['history'][-29:]
    Store(path).replace(nodes)
    with TestClient(create_app(path)) as client:
        result = client.get('/api/nodes/demo-01/telemetry').json()
        assert result['forecastStatus'] == 'WARMING_UP_PERSISTENCE'
        assert result['forecast6h'] == result['sensors']


def test_blend_selection_is_convex_and_has_single_family_vertices():
    truth = np.tile(np.arange(8, dtype=float)[:, None], (1, 6))
    candidates = dict(residual_mlp_small=truth.copy(), residual_mlp_large=truth+5, xgb_history=truth+2, ridge_history=truth-3)
    state = select_blend(candidates, truth, .05)
    for head in state['heads'].values():
        assert head['neural'] == 'residual_mlp_small'
        assert head['weights']['neural'] == 1 and head['validation_mae'] == 0
        assert sum(head['weights'].values()) == 1
    with pytest.raises(ValueError, match='step'):
        select_blend(candidates, truth, .13)


def test_profile_tampering_and_missing_component_hash_fail_closed(tmp_path):
    target = tmp_path/'profile'
    shutil.copytree(DEFAULT_MODEL, target)
    with (target/'ensemble_weights.json').open('ab') as stream:
        stream.write(b' ')
    with pytest.raises(ValueError, match='checksum'):
        Hybrid(target)
    shutil.copy2(DEFAULT_MODEL/'ensemble_weights.json', target/'ensemble_weights.json')
    profile = json.loads((target/'profile.json').read_text())
    removed = next(p for p in profile['component_hashes'] if p.endswith('.ubj'))
    del profile['component_hashes'][removed]
    (target/'profile.json').write_text(json.dumps(profile))
    with pytest.raises(ValueError, match='checksum manifest'):
        Hybrid(target)


def test_validation_selector_never_receives_poisoned_test_targets(tmp_path, monkeypatch):
    from scripts import promote_mandi_hybrid as script
    from ml.six_sensor_forecast.features import build_features, future_targets
    # Synthetic inputs test routing/partition isolation, never predictive skill.
    # CI requires only committed model artifacts, not the ignored source CSV.
    values = np.tile([20., 60., 900., 30., 60., 3.], (200, 1)) + np.sin(np.arange(200)[:, None]/10)
    observations = pd.DataFrame(values, columns=RAW_SENSOR_COLUMNS)
    observations['location_id'] = 'synthetic-unit-cell'
    observations['timestamp_utc'] = pd.date_range('2024-01-01', periods=200, freq='h', tz='UTC')
    frame, features = build_features(observations)
    truth = future_targets(frame, 6)
    source = json.loads((ROOT/'ml/models/india_mandi_modeled_6h_v1/training_report.json').read_text())
    manifest = dict(observations_sha256=source['source']['observations_sha256'])
    ix = np.arange(200)
    masks = dict(train=(ix>=24)&(ix<100), validation=(ix>=100)&(ix<140), future_test=ix>=140)
    truth.loc[masks['future_test']] = 1e8
    monkeypatch.setattr(script, 'arrays', lambda _: (frame, features, truth, masks, manifest))
    selector = script.select_blend
    called = []
    def spy(candidates, y, step):
        called.append(y.copy())
        assert len(y) == 40 and np.max(y) < 1e8
        return selector(candidates, y, step)
    monkeypatch.setattr(script, 'select_blend', spy)
    config = json.loads((ROOT/'configs/mandi_hybrid_forecast_v1.json').read_text())
    config.update(models_output=str(tmp_path/'model'), reports_output=str(tmp_path/'report'))
    path = tmp_path/'config.json'; path.write_text(json.dumps(config))
    report = script.build(path)
    assert len(called) == 1 and report['shipping_parity_max_absolute_error'] == 0
    # Replacing the source must not silently reuse models fitted on other rows.
    manifest['observations_sha256'] = '0'*64
    config['models_output'] = str(tmp_path/'wrong-source-model')
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match='matching frozen source'):
        script.build(path)
    assert not Path(config['models_output']).exists() and len(called) == 1
