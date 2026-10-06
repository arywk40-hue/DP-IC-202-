import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from ml.event_classifier.heatmap import HeatmapBuilder
from ml.event_classifier.predict import EventPredictor
from ml.event_classifier.features import EVENT_NAMES
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS

MODEL = Path(__file__).resolve().parents[1] / 'ml/models/uci_beijing_event_rules_6sensor'


def nodes():
    result = []
    for i, (x, y) in enumerate([(0., 0.), (1., 0.), (0., 1.)]):
        history = []
        for j, time in enumerate(pd.date_range('2026-01-01', periods=7, freq='h', tz='UTC')):
            history.append(dict(timestamp_utc=time.isoformat(), **dict(zip(RAW_SENSOR_COLUMNS,
                [20+i+j*.1, 60+i, 1010-j*.4, 40+j+i, 70+i, 2+i]))))
        result.append(dict(x=x, y=y, history=history, **history[-1]))
    return result


class SpatialReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = HeatmapBuilder(grid_shape=(3, 3), model_dir=MODEL, prefer_kriging=False)

    def test_both_strategies_and_untrained_mask(self):
        result = self.builder.run(nodes(), strategy='both')
        for key in ['event_maps', 'event_maps_b']:
            self.assertTrue(np.isnan(result[key][1:3]).all())
            self.assertTrue(np.isfinite(result[key][0, 0, 0]))
            self.assertTrue(np.isnan(result[key][:, 2, 2]).all())
        # Both algorithms reproduce a measured node when no interpolation is needed.
        np.testing.assert_allclose(result['event_maps'][:, 0, 0], result['event_maps_b'][:, 0, 0], equal_nan=True)
        self.assertIsNone(result['strategy_mean_absolute_difference'][EVENT_NAMES[1]])

    def test_missing_history_does_not_invent_events(self):
        points = nodes()
        for node in points:
            del node['history']
        result = self.builder.run(points, 'both')
        self.assertTrue(np.isnan(result['event_maps']).all())
        self.assertTrue(np.isnan(result['event_maps_b']).all())
        self.assertTrue(np.isfinite(result['feature_maps'][:, 0, 0]).all())

    def test_bad_time_position_history_and_snapshot(self):
        for mode in ['time', 'duplicate_position', 'nan_position', 'gap', 'snapshot', 'naive']:
            points = copy.deepcopy(nodes())
            if mode == 'time': points[1]['timestamp_utc'] = '2026-01-02T06:00:00Z'
            if mode == 'duplicate_position': points[1]['x'] = 0
            if mode == 'nan_position': points[1]['x'] = np.nan
            if mode == 'gap': points[1]['history'][2]['timestamp_utc'] = '2026-01-01T01:30:00Z'
            if mode == 'snapshot': points[1]['temperature_c'] += 1
            if mode == 'naive': points[1]['timestamp_utc'] = '2026-01-01T06:00:00'
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.builder.run(points, 'both')

    def test_invalid_sensors_are_unavailable(self):
        points = nodes()
        for n in points:
            n['history'][3]['relative_humidity_pct'] = 150
        result = self.builder.run(points, 'both')
        self.assertTrue(np.isnan(result['event_maps']).all())
        self.assertTrue(np.isnan(result['event_maps_b']).all())

    def test_interior_gap_blocks_predictor(self):
        frame = pd.DataFrame(nodes()[0]['history'])
        frame['location_id'] = 'node'
        predictor = EventPredictor(MODEL)
        self.assertEqual(predictor.predict(frame).iloc[-1]['status'], 'RULE_SCORES_ONLY')
        missing = frame.drop(index=3)
        self.assertEqual(predictor.predict(missing).iloc[-1]['status'], 'UNAVAILABLE')

    def test_two_nodes_support_only_line_unless_opted_in(self):
        points = nodes()[:2]
        result = self.builder.run(points)
        self.assertTrue(result['support_mask'][0].all())
        self.assertFalse(result['support_mask'][1:].any())
        self.assertTrue(np.isnan(result['feature_maps'][:, 1:]).all())

    def test_nonunit_collinear_segments_keep_both_endpoints(self):
        for length in [.5, 2., 1000.]:
            for count in [2, 3]:
                with self.subTest(length=length, nodes=count):
                    points=nodes()[:count]
                    for point,fraction in zip(points,np.linspace(0,1,count)):
                        point['x']=point['y']=length*fraction
                    builder=HeatmapBuilder((3,3),(0,length,0,length),prefer_kriging=False)
                    maps,_=builder.feature_heatmaps(points)
                    np.testing.assert_array_equal(builder._support(np.array([[p['x'],p['y']] for p in points])),np.eye(3,dtype=bool))
                    self.assertTrue(np.isfinite(maps[:,0,0]).all())
                    self.assertTrue(np.isfinite(maps[:,2,2]).all())
                    np.testing.assert_allclose(maps[:,2,2],[points[-1][c] for c in RAW_SENSOR_COLUMNS])
                    self.assertTrue(np.isnan(maps[:,0,2]).all())

    def test_tampered_model_is_rejected(self):
        report = json.loads((MODEL/'event_training_report.json').read_text())
        entry = report['models'][EVENT_NAMES[0]]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'event_training_report.json').write_text(json.dumps(report))
            target = root/entry['student_file']
            target.parent.mkdir(parents=True)
            target.write_bytes(b'corrupt model')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                EventPredictor(root)

    def test_reject_unbounded_grid(self):
        for shape in [(1, 2), (1000, 1000), (-2, 3)]:
            with self.assertRaises(ValueError):
                HeatmapBuilder(grid_shape=shape)


if __name__ == '__main__':
    unittest.main()
