import copy
import json
import tempfile
import unittest
from pathlib import Path

from esp32.ml_integration.tools.record_field import Validator, append_record

BUILD = 'a' * 64


def info(boot=1):
    return dict(info=True, protocol_version=1, node_id='abc', boot_id=boot,
                self_test_passed=True, research_only=True, build_sha256=BUILD)


def observation():
    return dict(protocol_version=1, boot_id=1, sequence=1, build_sha256=BUILD,
                research_only=True, timestamp_utc=1767225600,
                forecast_timestamp_utc=1767247200, status='WARMING_UP',
                measurements=[20, 50, 1013, 35, 60, 2], forecast_6h=[21, 51, 1012, 36, 61, 3],
                event_scores=[None]*12, event_valid_mask=0)


class FieldRecorderTests(unittest.TestCase):
    def test_requires_identity_and_self_test(self):
        v = Validator(BUILD)
        self.assertEqual(v.classify(observation())[0], 'REJECTED')
        self.assertEqual(v.classify(dict(info(), self_test_passed=False))[0], 'REJECTED')
        self.assertEqual(v.classify(info())[0], 'INFO')
        self.assertEqual(v.classify(observation())[0], 'OBSERVATION')

    def test_dedup_reboot_and_failed_self_test(self):
        v = Validator(BUILD); v.classify(info())
        self.assertEqual(v.classify(observation())[0], 'OBSERVATION')
        self.assertEqual(v.classify(observation())[0], 'REJECTED')
        self.assertEqual(v.classify(info(2))[0], 'INFO')
        self.assertEqual(v.classify(dict(observation(), boot_id=2))[0], 'OBSERVATION')
        v.classify({'self_test': 'FAIL'})
        self.assertEqual(v.classify(dict(observation(), boot_id=2, sequence=2))[0], 'REJECTED')

    def test_malformed_and_invented_scores_are_rejected(self):
        for key, value in [('forecast_timestamp_utc', 0), ('measurements', [1]),
                           ('sequence', True), ('build_sha256', 'b'*64),
                           ('forecast_6h', [float('nan')]*6), ('event_scores', [0]*12),
                           ('event_valid_mask', 0xfff)]:
            v = Validator(BUILD); v.classify(info())
            data = copy.deepcopy(observation()); data[key] = value
            self.assertEqual(v.classify(data)[0], 'REJECTED', key)

    def test_session_never_switches_devices(self):
        v = Validator(BUILD); v.classify(info())
        for _ in range(2):
            self.assertEqual(v.classify(dict(info(), node_id='different'))[0], 'REJECTED')

    def test_ready_scores_have_exact_availability(self):
        v = Validator(BUILD); v.classify(info())
        data = observation(); data.update(status='READY', event_valid_mask=0xff9)
        data['event_scores'] = [.5, None, None]+[.5]*9
        self.assertEqual(v.classify(data)[0], 'OBSERVATION')

    def test_journal_preserves_records_and_rejects_non_json_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'journal.jsonl'
            with path.open('x') as handle:
                append_record(handle, {'kind': 'TEST', 'payload': observation()})
                with self.assertRaises(ValueError):
                    append_record(handle, {'bad': float('nan')})
            records = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(len(records), 1)
            with self.assertRaises(FileExistsError):
                path.open('x')


if __name__ == '__main__':
    unittest.main()
