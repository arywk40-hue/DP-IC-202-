import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from storm_risk.calibration.calibrate import fit_calibrator
from storm_risk.pipeline import SCORE_COLUMNS, run_pipeline


def test_calibrator_skip(config, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Insufficient positives reached calibrator.fit')
    monkeypatch.setattr(IsotonicRegression, 'fit', forbidden)
    frame = pd.DataFrame(dict(label=[0, 0, 1], split='calib'))
    model, method, warnings = fit_calibrator(np.array([.1, .2, .5]), frame, config, [])
    assert model is None and method == 'none' and warnings
    assert all(c.endswith('_risk_uncal') for c in SCORE_COLUMNS)
    config['calibration']['min_positives_calib'] = 100000
    directory, report = run_pipeline(config, 'skip_mapping')
    assert report['status'] == 'COMPLETED_EXPERIMENTAL' and report['calibration_method'] == 'none'
    assert not report['calibrated']
    scores = pd.read_csv(directory / 'scores.csv')
    assert all(not c.endswith('_cal_prob') for c in scores)
