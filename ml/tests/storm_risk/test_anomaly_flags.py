import pandas as pd

from ml.storm_risk.anomaly.anomaly import fit_thresholds, flag_anomalies


def test_anomaly_flags(config):
    train = pd.DataFrame(dict(time=pd.date_range('2020-06-01', periods=100, freq='h', tz='UTC'), value=range(100), split='train'))
    thresholds = fit_thresholds(train, ['value'], config)
    inputs = pd.DataFrame(dict(time=pd.to_datetime(['2020-06-10T00:00Z', '2020-06-10T01:00Z', '2020-07-10T00:00Z']), value=[101, 20, 101]))
    result = flag_anomalies(inputs, thresholds, ['value'])
    assert result.anomaly_flag.tolist() == [True, False, False]
    assert result.anomaly_features.tolist() == ['value', '', '']
    assert result.anomaly_available.tolist() == [True, True, False]
