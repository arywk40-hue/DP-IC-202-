"""Exercise the exact portable runtime compiled into the ESP32-S3 firmware."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from ml.event_classifier.features import ALL_EVENT_FEATURE_COLS, build_features
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.predict import predict

ROOT = Path(__file__).resolve().parents[1]


class Esp32IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('c++')
        if not compiler:
            raise RuntimeError('C++ compiler required for ESP32 runtime tests')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        source = Path(cls.tmp.name) / 'runner.cpp'
        cls.binary = Path(cls.tmp.name) / 'runner'
        source.write_text(r'''
#include <cstdio>
#include "indra_ml_runtime.h"
int main() {
  indra::Runtime runtime;
  unsigned timestamp;
  float x[6];
  while (scanf("%u %f %f %f %f %f %f", &timestamp, x, x+1, x+2, x+3, x+4, x+5) == 7) {
    auto r = runtime.push(timestamp, x);
    printf("%d %u %u", static_cast<int>(r.status), r.history_rows, r.event_valid_mask);
    for (float v : r.forecast) printf(" %.9g", v);
    for (float v : r.features) printf(" %.9g", v);
    for (float v : r.events) printf(" %.9g", v);
    puts("");
  }
}
''')
        subprocess.run([compiler, '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-I' + str(ROOT / 'esp32/ml_integration/include'),
                        '-I' + str(ROOT / 'ml/models/uci_beijing_6h/esp32_student/export'),
                        '-I' + str(ROOT / 'ml/models/uci_beijing_event_rules_6sensor/esp32_student/export'),
                        str(source), '-o', str(cls.binary)], check=True, capture_output=True)

    def run_rows(self, raw, times=None):
        if times is None:
            times = 1767225600 + np.arange(len(raw)) * 3600
        data = ''.join(str(int(t)) + ' ' + ' '.join(str(float(x)) for x in row) + '\n'
                       for t, row in zip(times, raw))
        result = subprocess.run([str(self.binary)], input=data, capture_output=True,
                                text=True, check=True)
        return np.array([[float(x) for x in line.split()] for line in result.stdout.splitlines()])

    def test_python_feature_and_model_parity(self):
        rng = np.random.default_rng(42)
        raw = rng.uniform([-20, 5, 800, 1, 5, 0], [42, 100, 1040, 350, 450, 15], (80, 6)).astype(np.float32)
        # Cover monotonic history, RH=0, PM10=0, and heat index branch boundaries.
        raw[:8, 3] = np.arange(8) + 20
        raw[12, 1] = 0
        raw[25, 4] = 0
        raw[40:43, 0] = [26.666664, 26.666666, 26.66667]
        frame = pd.DataFrame(raw, columns=RAW_SENSOR_COLUMNS)
        frame['timestamp_utc'] = pd.date_range('2026-01-01', periods=80, freq='h', tz='UTC')
        frame['location_id'] = 'test'
        _, features = build_features(frame)
        expected_features = features[ALL_EVENT_FEATURE_COLS].to_numpy(dtype=np.float32)
        result = self.run_rows(raw)
        ready = result[:, 0] == 3
        self.assertTrue((result[:6, 0] == 2).all())
        self.assertFalse(ready[25])
        self.assertTrue(ready[26])
        self.assertTrue((result[ready, 2] == 0xff9).all())
        np.testing.assert_allclose(result[ready, 9:26], expected_features[ready], atol=5e-5, rtol=2e-6)
        forecast = predict(frame, ROOT / 'ml/models/uci_beijing_6h', 'student')
        expected_forecast = forecast[['forecast_' + k for k in RAW_SENSOR_COLUMNS]].to_numpy()
        np.testing.assert_allclose(result[:, 3:9], expected_forecast, atol=5e-4, rtol=0)
        model_dir = ROOT / 'ml/models/uci_beijing_event_rules_6sensor'
        report = json.loads((model_dir / 'event_training_report.json').read_text())
        dm = xgb.DMatrix(expected_features[ready], feature_names=ALL_EVENT_FEATURE_COLS)
        for i, name in enumerate(report['event_names']):
            entry = report['models'][name]
            if entry.get('skipped'):
                self.assertTrue(np.isnan(result[:, 26+i]).all())
            else:
                model = xgb.Booster(params={'nthread': 1})
                model.load_model(model_dir / entry['student_file'])
                np.testing.assert_allclose(result[ready, 26+i], model.predict(dm), atol=5e-4, rtol=0)

    def test_gap_duplicate_and_out_of_order(self):
        raw = np.tile([20, 50, 1013, 35, 60, 2], (11, 1))
        times = 1767225600 + np.array([0, 1, 2, 3, 4, 5, 6, 6, 5, 8, 9]) * 3600
        result = self.run_rows(raw, times)
        np.testing.assert_array_equal(result[:, 0], [2]*6 + [3, 1, 1, 2, 2])
        np.testing.assert_array_equal(result[-2:, 1], [1, 2])
        self.assertTrue(np.isnan(result[7:9, 3:]).all())

    def test_invalid_inputs_and_missing_hour(self):
        raw = np.tile([20, 50, 1013, 35, 60, 2], (10, 1)).astype(float)
        raw[2, 0] = np.nan
        raw[4, 2] = np.inf
        raw[6, 1] = 101
        raw[8, 5] = -1
        result = self.run_rows(raw)
        for i in [2, 4, 6, 8]:
            self.assertEqual(result[i, 0], 0)
            self.assertTrue(np.isnan(result[i, 3:]).all())
            self.assertEqual(result[i+1, 1], 1)
        self.assertTrue((result[:, 2] == 0).all())
        self.assertEqual(self.run_rows(raw[:1], [0])[0, 0], 0)

    def test_board_fixture_matches_runtime(self):
        import re
        text = (ROOT / 'esp32/ml_integration/include/self_test_fixture.h').read_text()
        def floats(s):
            return [float(x.strip().removesuffix('f').replace('NAN', 'nan')) for x in s.split(',') if x.strip()]
        rows_text = text.split('kTestRows[7][6] = {')[1].split('};')[0]
        rows = [floats(s) for s in re.findall(r'\{([^}]+)\}', rows_text)]
        result = self.run_rows(rows)[-1]
        for name, actual in [('kExpectedForecast[6]', result[3:9]), ('kExpectedEvents[12]', result[26:])]:
            expected = floats(text.split(name + ' = {')[1].split('}')[0])
            np.testing.assert_allclose(actual, expected, atol=5e-4, rtol=0, equal_nan=True)


if __name__ == '__main__':
    unittest.main()
