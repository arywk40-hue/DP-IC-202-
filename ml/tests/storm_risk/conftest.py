from pathlib import Path

import pytest

from ml.storm_risk.demo import create_fixture
from ml.storm_risk.settings import load_config


@pytest.fixture
def config(tmp_path):
    root = Path(__file__).resolve().parents[3]
    cfg = load_config(root / 'ml/storm_risk/config/default.yaml', base=root)
    cfg['paths']['outputs'] = str(tmp_path / 'outputs')
    cfg['fixture'].update(days=12, train_fraction=.6, calib_fraction=.2)
    cfg['models']['mlp'].update(hidden_layers=[8], epochs=2)
    cfg['models']['xgb'].update(n_estimators=6, early_stopping_rounds=2)
    cfg['calibration'].update(min_positives_calib=2, min_negatives_calib=2)
    cfg['heatmaps']['features'] = ['t2m']
    cfg['heatmaps']['time_stride_hours'] = 24
    return create_fixture(cfg, tmp_path / 'inputs')
