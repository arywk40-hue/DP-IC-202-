"""Candidate imports must not manufacture event times or eligible labels."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from ml.hazard_context.coolr import candidate, run, source_descriptor


class CoolrTests(unittest.TestCase):
    def test_reported_clock_is_not_assumed_utc_or_a_training_label(self):
        source = source_descriptor('2026-10-09T00:00:00Z', 'a'*64)
        raw = dict(objectid=1, event_id=123, country_code='IN', latitude=31.71,
                   longitude=76.93, event_date=1688774400000, event_time='03:00',
                   admin_division_name='Himachal Pradesh', location_description='fixture')
        r = candidate(raw, source)
        self.assertIsNone(r['event_start_utc'])
        self.assertIsNone(r['event_end_utc'])
        self.assertIsNone(r['spatial_uncertainty_km'])
        self.assertIsNone(r['event_group_id'])
        self.assertEqual(r['reported_time_text'], '03:00')
        self.assertIn('occurrence clock unverified', r['reported_date'])
        self.assertEqual(r['admission_status'], 'candidate')
        self.assertIn('LABELS_NOT_INDEPENDENT', r['admission_reasons'])

    def test_non_indian_or_invalid_coordinate_record_is_rejected(self):
        source = source_descriptor('2026-10-09T00:00:00Z', 'a'*64)
        raw = dict(objectid=1, country_code='IN', latitude=31.71, longitude=76.93)
        for change in [dict(country_code='CN'),dict(latitude=float('nan')),
                       dict(latitude=True),dict(longitude=100),dict(objectid=True)]:
            with self.assertRaises(ValueError):
                candidate({**raw, **change}, source)

    def test_partial_download_cannot_create_a_completed_audit(self):
        for page in [dict(features=[]), dict(features=[], exceededTransferLimit=True)]:
            responses = [({'objectIdField':'objectid'},b'{}','fixture://metadata'),
                         ({'objectIdFieldName':'objectid','objectIds':[1]},b'{}','fixture://ids'),
                         (page,b'{}','fixture://page')]
            with tempfile.TemporaryDirectory() as tmp, patch(
                    'ml.hazard_context.coolr.fetch', side_effect=responses):
                output, audit = Path(tmp)/'raw', Path(tmp)/'audit.json'
                with self.assertRaises(ValueError):
                    run(output, audit)
                self.assertFalse(audit.exists())
                self.assertFalse((output/'candidates.jsonl').exists())

    def test_unknown_id_response_cannot_be_claimed_as_zero_events(self):
        responses = [({'objectIdField':'objectid'},b'{}','fixture://metadata'),
                     ({'unexpected':'schema'},b'{}','fixture://ids')]
        with tempfile.TemporaryDirectory() as tmp, patch(
                'ml.hazard_context.coolr.fetch', side_effect=responses):
            with self.assertRaises(ValueError):
                run(Path(tmp)/'raw', Path(tmp)/'audit.json')
