import json

import numpy as np
import pandas as pd
from sklearn.linear_model import SGDClassifier

from storm_risk.models.online import run_online


def test_online_predict_before_update(config, tmp_path, monkeypatch):
    config['online'].update(enabled=True, warmup_days=4, reference_days=1, min_positives=2, min_negatives=2, checkpoint_days=2)
    times = pd.date_range(config['time']['start'], periods=12 * 24, freq='h')
    frame = pd.DataFrame(dict(time=times, lat=31.5, lon=76.75, f=np.sin(np.arange(len(times))), label=np.arange(len(times)) % 2,
        available_at=times + pd.Timedelta(hours=24), split=np.where(np.arange(len(times)) < 7 * 24, 'train', np.where(np.arange(len(times)) < 9 * 24, 'calib', 'test'))))
    observed = []
    original = SGDClassifier.partial_fit
    def spy(self, x, y, *args, **kwargs):
        observed.append(dict(initial=kwargs.get('classes') is not None, rows=len(y), csv_exists=(tmp_path / 'online_scores.csv').exists()))
        return original(self, x, y, *args, **kwargs)
    monkeypatch.setattr(SGDClassifier, 'partial_fit', spy)
    result = run_online(frame, ['f'], tmp_path, config)
    assert result['status'] == 'COMPLETED_RETROSPECTIVE_PREQUENTIAL_REPLAY'
    assert observed[0]['initial'] and all(x['csv_exists'] for x in observed[1:])
    audit = json.loads((tmp_path / 'online_audit.json').read_text())['events']
    test_ids = set(frame.index[frame.split.eq('test')])
    seen_days = set()
    for event in audit:
        if event['action'] == 'PREDICT_RECORDED':
            seen_days.add(event['day'])
            assert pd.Timestamp(event['trained_through']) < pd.Timestamp(event['day'])
        else:
            assert not set(event['rows']) & test_ids
            if event['action'] == 'UPDATE':
                assert event['day'] in seen_days
    assert list((tmp_path / 'checkpoints').glob('*.joblib'))
    metrics = pd.read_csv(tmp_path / 'online_metrics.csv')
    assert metrics.brier_score.isna().all() and metrics.roc_auc.isna().all()
