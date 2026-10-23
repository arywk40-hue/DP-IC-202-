import numpy as np
import pandas as pd

from ml.storm_risk.validation.bootstrap import day_bootstrap
from ml.storm_risk.validation.gate import evaluate_gate
from ml.storm_risk.validation.metrics import metrics


def test_reliability_bins(config):
    y = np.array([0, 1, 0, 1, 0, 1])
    values = np.array([0, 1, .1, .9, .2, .8])
    result = metrics(y, values, config)
    assert sum(b['count'] for b in result['reliability_diagram']['bins']) == len(y)
    assert np.isclose(result['brier_score'], result['reliability'] - result['resolution'] + result['uncertainty'] + result['binning_remainder'])
    frame = pd.DataFrame(dict(time=pd.date_range('2020-06-01', periods=6, freq='D', tz='UTC'), label=y))
    a, b = day_bootstrap(frame, values, config), day_bootstrap(frame, values, config)
    assert a == b and a['days'] == 6 and a['resamples'] >= 1000
    gate = evaluate_gate(result, a, 6, 'isotonic', config)
    assert not gate['calibrated'] and 'SYNTHETIC_EVIDENCE_ONLY' in gate['failed_conditions']
