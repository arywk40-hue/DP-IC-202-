import json
from pathlib import Path

import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from storm_risk.pipeline import run_pipeline


def test_split_isolation(config, monkeypatch):
    observed = []
    for cls in (StandardScaler, Ridge, MLPClassifier, XGBClassifier, IsotonicRegression):
        original = cls.fit
        def spy(self, x, y=None, *args, _fit=original, _name=cls.__name__, **kwargs):
            indices = x.index if isinstance(x, pd.DataFrame) else y.index
            observed.append((_name, set(indices)))
            for vx, vy in kwargs.get('eval_set', []):
                observed.append(('inner_validation', set(vy.index)))
            return _fit(self, x, y, *args, **kwargs)
        monkeypatch.setattr(cls, 'fit', spy)
    path, report = run_pipeline(config, 'isolation')
    assert report['status'] == 'COMPLETED_EXPERIMENTAL', report['warnings']
    scores = pd.read_csv(path / 'scores.csv')
    test_ids = set(scores.index[scores.split.eq('test')])
    assert observed and all(not indices & test_ids for _, indices in observed)
    assert {name for name, _ in observed} >= {'StandardScaler', 'Ridge', 'MLPClassifier', 'XGBClassifier', 'IsotonicRegression'}
    for stage in report['fit_audit']:
        assert not set(stage['row_ids']) & test_ids
        assert stage['role'] in {'train', 'calib'}
    assert len(list((path / 'heatmaps').glob('*.npz'))) > 1
    assert (path / 'heatmaps/t2m.png').is_file()
    assert list(path.glob('ensemble_*.joblib'))
    assert report['metrics']['brier_score'] is None
    assert report['calibrated'] is False
    assert all(not c.endswith('_cal_prob') for c in scores.columns)
    assert abs(sum(report['ensemble_weights'].values()) - 1) < 1e-12
    assert json.loads((path / 'report.json').read_text())['warnings']


def test_missing_inputs_still_write_complete_report(config):
    config['paths']['era5_glob'] = str(Path(config['paths']['outputs']) / 'absent*.nc')
    path, report = run_pipeline(config, 'missing')
    assert report['status'] == 'NOT_READY' and not report['calibrated']
    assert {'sample_counts', 'base_rates', 'metrics', 'confidence_intervals', 'warnings', 'gate_failures', 'calibration_method'} <= set(report)
    assert (path / 'scores.csv').is_file() and report['warnings']
