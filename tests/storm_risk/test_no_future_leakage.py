import numpy as np
import pandas as pd

from storm_risk.features.lagged import build_lagged


def test_no_future_leakage(config):
    t = pd.date_range('2020-06-01', periods=55, freq='h', tz='UTC')
    frame = pd.DataFrame(dict(time=t, lat=31.5, lon=76.75, value=np.arange(len(t), dtype=float)))
    original, names, _ = build_lagged(frame, ['value'], config)
    changed = frame.copy()
    changed.loc[changed.time > t[40], 'value'] = 10000
    result, _, _ = build_lagged(changed, ['value'], config)
    np.testing.assert_array_equal(original.loc[original.time <= t[40], names], result.loc[result.time <= t[40], names])
    missing, _, _ = build_lagged(frame.drop(index=30), ['value'], config)
    assert not missing.time.between(t[30], t[54]).any()
