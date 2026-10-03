import unittest
import numpy as np
import pandas as pd
from ml.spatial_ensemble.model import SpatialEnsemble, snapshot_features
from ml.spatial_ensemble.evaluate import examples


def nodes():
    values = [20, 60, 1000, 30, 50, 2]
    from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
    return [dict(latitude=0., longitude=lon, timestamp_utc='2025-01-01T00:00:00Z',
                 **dict(zip(RAW_SENSOR_COLUMNS, values))) for lon in [-1., 1.]]


class ReviewRobustnessTests(unittest.TestCase):
    def test_invalid_empty_missing_stale_and_colocated_nodes(self):
        model = SpatialEnsemble()
        for query in [(91, 0), (0, 181), (np.nan, 0), (0, np.inf)]:
            with self.assertRaises(ValueError):
                model.predict(nodes(), *query, '2025-01-01T00:00:00Z')
        for payload in [[], [{}], [dict(nodes()[0], timestamp_utc='2024-01-01T00:00:00Z')]]:
            result = model.predict(payload, 0, 0, '2025-01-01T00:00:00Z')
            self.assertIsNone(result['targets']['temperature_c']['prediction'])
        duplicate = [dict(n, longitude=0.) for n in nodes()]
        duplicate[0]['temperature_c'] = 10.
        self.assertEqual(model.predict(duplicate, 0, 0, '2025-01-01T00:00:00Z')['targets']['temperature_c']['prediction'], 15.)
        partial = nodes()
        partial[0]['temperature_c'] = np.inf
        partial[1]['pressure_hpa'] = 100000  # Pa instead of hPa rejected.
        result = model.predict(partial, 0, 0, '2025-01-01T00:00:00Z')
        self.assertEqual(result['targets']['temperature_c']['prediction'], 20.)
        self.assertEqual(result['targets']['pressure_hpa']['prediction'], 1000.)

    def test_model_failures_and_nonfinite_predictions_fall_back(self):
        class Broken:
            def predict(self, x):
                raise RuntimeError('offline')
        class Nonfinite:
            def predict(self, x):
                return np.array([np.nan])
        model = SpatialEnsemble()
        model.heads['temperature_c'] = dict(models={'boosting': Broken(), 'neural_net': Nonfinite()},
            scale=1., weights={'idw': .2, 'boosting': .4, 'neural_net': .4},
            lower=np.full(25, -np.inf), upper=np.full(25, np.inf), p90=1.)
        result = model.predict(nodes(), 0, 0, '2025-01-01T00:00:00Z')['targets']['temperature_c']
        self.assertEqual(result['prediction'], 20.)
        self.assertEqual(len(result['failed_models']), 2)
        self.assertIsNone(result['absolute_error_p90'])
        model.heads['temperature_c']['upper'] = np.zeros(25)
        self.assertTrue(model.predict(nodes(), 0, 0, '2025-01-01T00:00:00Z')['targets']['temperature_c']['out_of_distribution'])

    def test_query_truth_never_enters_features(self):
        from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
        frame = pd.DataFrame(nodes())
        frame['location_id'] = ['a', 'b']
        _, x, y, _ = examples(frame, {'a'}, {'a', 'b'})
        frame.loc[0, RAW_SENSOR_COLUMNS] = 42
        _, changed_x, changed_y, _ = examples(frame, {'a'}, {'a', 'b'})
        np.testing.assert_equal(x, changed_x)
        self.assertFalse(np.array_equal(y, changed_y))

    def test_small_ensemble_fit(self):
        x, base, _ = snapshot_features(nodes(), 0, 0, '2025-01-01T00:00:00Z')
        x = np.tile(x, (40, 1))
        y = np.tile(base, (40, 1))
        model = SpatialEnsemble().fit(x, y, x, y)
        result = model.predict(nodes(), 0, 0, '2025-01-01T00:00:00Z')
        self.assertEqual(len(model.heads), 6)
        self.assertEqual(len(result['targets']['temperature_c']['models']), 3)
        self.assertIsNotNone(result['targets']['temperature_c']['absolute_error_p90'])


if __name__ == '__main__':
    unittest.main()
