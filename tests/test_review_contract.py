import unittest
import pandas as pd
from ml.six_sensor_forecast.features import build_features
from ml.event_classifier.features import build_features as event_features
from tests.test_six_sensor_forecast import fixture


class ReviewContractTests(unittest.TestCase):
    def test_naive_and_unbounded_time_rejected_before_reindex(self):
        for builder in [build_features, event_features]:
            frame = fixture().iloc[:2].copy()
            frame['timestamp_utc'] = frame.timestamp_utc.dt.tz_localize(None)
            with self.assertRaisesRegex(ValueError, 'timezone'):
                builder(frame)
            frame = fixture().iloc[:2].copy()
            frame.loc[0, 'timestamp_utc'] = pd.Timestamp('1900-01-01', tz='UTC')
            with self.assertRaisesRegex(ValueError, 'resource budget'):
                builder(frame)

