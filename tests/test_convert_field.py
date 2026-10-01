import json
from pathlib import Path
import tempfile
import unittest

from ml.deployment.convert_field import convert
from ml.deployment.evaluate_forecast import evaluate
from tests.test_field_recorder import BUILD, info, observation


class ConvertFieldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def journal(self, name, records, tail=''):
        rows = [dict(kind='SESSION_START', expected_build=BUILD),
                dict(kind='INFO', payload=info()), *records]
        path = self.root / name
        path.write_text(''.join(json.dumps(dict(station='synthetic', **r)) + '\n'
                                for r in rows) + tail)
        return path

    def row(self, hour=0, kind='OBSERVATION', **changes):
        payload = observation()
        payload.update(sequence=hour+1, timestamp_utc=1767225600 + hour*3600,
                       forecast_timestamp_utc=1767247200 + hour*3600)
        payload.update(changes)
        return dict(kind=kind, payload=payload)

    def test_export_measured_inputs_and_run_saved_model(self):
        path = self.journal('session.jsonl', [self.row(i) for i in range(7)])
        frame, report = convert([path])
        self.assertEqual(report['exported_observations'], 7)
        self.assertEqual(frame.temperature_c.tolist(), [20]*7)  # Forecasts are 21.
        self.assertFalse(report['provenance_verified'])
        provenance = dict(observation_source='synthetic test', timezone_verified=True,
                          units_verified=True, pressure_reference='station')
        result = evaluate(frame, provenance, '2026-01-01T00:00Z',
                          Path(__file__).resolve().parents[1]/'ml/models/uci_beijing_6h')
        self.assertEqual(result['six_hour_test_pairs'], 1)

    def test_stale_rejected_invalid_and_truncated_records_are_excluded(self):
        path = self.journal('session.jsonl', [self.row(),
            self.row(1, 'STALE_OBSERVATION'), self.row(2, 'REJECTED'),
            self.row(3, status='INVALID_INPUT', forecast_6h=[None]*6),
            self.row(4, measurements=[20, 150, 1013, 35, 60, 2])], tail='{"kind":')
        frame, report = convert([path])
        self.assertEqual(len(frame), 1)
        self.assertEqual(report['counts']['truncated_final_line'], 1)
        self.assertEqual(report['counts']['out_of_range'], 1)
        self.assertEqual(report['counts']['rejected_on_revalidation'], 1)

    def test_duplicate_and_conflicting_station_hours(self):
        a = self.journal('a.jsonl', [self.row()])
        b = self.journal('b.jsonl', [self.row()])
        frame, report = convert([a, b])
        self.assertEqual(len(frame), 1)
        self.assertEqual(report['counts']['duplicate_observation'], 1)
        c = self.journal('c.jsonl', [self.row(measurements=[22,50,1013,35,60,2])])
        with self.assertRaisesRegex(ValueError, 'conflicting measurements'):
            convert([a, c])

    def test_forged_identity_and_malformed_lines_fail_closed(self):
        path = self.journal('bad.jsonl', [self.row(build_sha256='b'*64)])
        with self.assertRaisesRegex(ValueError, 'No accepted'):
            convert([path])
        path = self.journal('broken.jsonl', [self.row()], tail='bad json\n')
        with self.assertRaisesRegex(ValueError, 'malformed journal record'):
            convert([path])


if __name__ == '__main__':
    unittest.main()
