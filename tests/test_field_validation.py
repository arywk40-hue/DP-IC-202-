import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from ml.deployment.field_validation import calibrate_and_evaluate, utc_times, forecast_metrics
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


class FieldValidationTests(unittest.TestCase):
    def test_calibration_cannot_see_test_labels(self):
        times = pd.date_range('2026-01-01', periods=120, freq='h', tz='UTC')
        scores = np.tile([.15, .8], 60)
        labels = np.tile([0, 1], 60).astype(float)
        cutoff = times[80]
        a = calibrate_and_evaluate(scores, labels, times, cutoff)
        labels[80:] = 1 - labels[80:]
        b = calibrate_and_evaluate(scores, labels, times, cutoff)
        self.assertEqual(a['calibration'], b['calibration'])
        self.assertNotEqual(a['calibrated_test']['brier'], b['calibrated_test']['brier'])
        self.assertEqual(a['status'], 'EVALUATED_REQUIRES_REVIEW')

    def test_unknown_and_sparse_labels_do_not_become_confidence(self):
        times = pd.date_range('2026-01-01', periods=10, freq='h', tz='UTC')
        labels = np.array([np.nan]*5 + [0]*5)
        result = calibrate_and_evaluate(np.full(10, .1), labels, times, times[5])
        self.assertIsNone(result['calibration'])
        self.assertEqual(result['counts']['calibration_rows'], 0)
        self.assertEqual(result['status'], 'INSUFFICIENT_INDEPENDENT_LABELS')
        with self.assertRaises(ValueError):
            calibrate_and_evaluate([.1], [2], times[:1], times[0])

    def test_end_to_end_evidence_never_auto_approves_deployment(self):
        from ml.deployment.field_validation import evaluate
        from ml.event_classifier.features import EVENT_NAMES
        root = Path(__file__).resolve().parents[1]
        times = pd.date_range('2026-01-01', periods=100, freq='h', tz='UTC')
        frame = pd.DataFrame(np.tile([20., 50., 1013., 35., 60., 2.], (100, 1)), columns=RAW_SENSOR_COLUMNS)
        frame['timestamp_utc'] = times
        frame['location_id'] = 'synthetic_unit_test'
        labels = frame[['timestamp_utc', 'location_id']].copy()
        for name in EVENT_NAMES:
            labels[name] = np.tile([0, 1], 50)
        provenance = dict(independent_event_labels=True, timezone_verified=True,
                          units_verified=True, pressure_reference='station',
                          observation_source='synthetic unit-test fixture',
                          label_source='synthetic unit-test fixture')
        report = evaluate(frame, labels, provenance, times[60],
                          root/'ml/models/uci_beijing_6h',
                          root/'ml/models/uci_beijing_event_rules_6sensor')
        self.assertFalse(report['field_deployment_approved'])
        self.assertEqual(report['events']['snowstorm_blizzard']['status'], 'UNTRAINED')
        self.assertEqual(report['forecasts']['ALL']['temperature_c']['pairs'], 34)
        provenance['independent_event_labels'] = False
        with self.assertRaises(ValueError):
            evaluate(frame, labels, provenance, times[60], None, None)

    def test_timezone_must_be_explicit(self):
        with self.assertRaises(ValueError):
            utc_times(['2026-01-01'])
        self.assertEqual(str(utc_times(['2026-01-01T05:30:00+05:30'])[0]), '2026-01-01 00:00:00+00:00')

    def test_exact_future_matching_not_next_row(self):
        times = pd.to_datetime(['2026-01-01T00:00Z', '2026-01-01T06:00Z', '2026-01-01T13:00Z'])
        observations = pd.DataFrame({c: [10., 20., 30.] for c in RAW_SENSOR_COLUMNS})
        observations['timestamp_utc'] = times
        observations['location_id'] = 'test'
        forecasts = observations[['timestamp_utc', 'location_id']].copy()
        forecasts['forecast_timestamp_utc'] = times + pd.Timedelta(hours=6)
        forecasts['status'] = 'test'
        for c in RAW_SENSOR_COLUMNS:
            forecasts['forecast_' + c] = [20., 30., 40.]
        report = forecast_metrics(observations, forecasts, times[0])
        for name in RAW_SENSOR_COLUMNS:
            self.assertEqual(report['ALL'][name]['pairs'], 1)
            self.assertEqual(report['ALL'][name]['mae'], 0)
            self.assertEqual(report['ALL'][name]['persistence_mae'], 10)


if __name__ == '__main__':
    unittest.main()
