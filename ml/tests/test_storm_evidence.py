"""Observed-code semantics and independent storm admission, not field performance."""
import unittest

from ml.hazard_context.events import admit
from ml.hazard_context.storm_audit import classification
from ml.hazard_context.warning import load_protocol
from ml.tests.test_hazard_context import event,source


class StormEvidenceTests(unittest.TestCase):
    def test_code_families_and_previous_hour_reports_are_distinct(self):
        self.assertEqual(classification('pres_wx_MW1','TS:95'),'thunderstorm_at_observation')
        self.assertEqual(classification('pres_wx_MW2','17'),'thunderstorm_at_observation')
        self.assertEqual(classification('pres_wx_MW1','29'),'thunderstorm_previous_hour')
        self.assertEqual(classification('pres_wx_AW1','TS:90'),'thunderstorm_at_observation')
        self.assertEqual(classification('pres_wx_AW1','26'),'thunderstorm_previous_hour')
        self.assertIsNone(classification('pres_wx_MW1','90'))
        self.assertIsNone(classification('pres_wx_AW1','99'))
        self.assertIsNone(classification('pres_wx_AU1','TS:95'))

    def test_lightning_alone_and_missing_codes_are_not_storm_or_negative_labels(self):
        for value in ['13','00',None,'','SQ:95','TS:foo']:
            self.assertIsNone(classification('pres_wx_MW1',value))

    def test_storm_requires_confirmed_occurrence_and_normal_synthetic_admission_fails(self):
        s={**source(),'targets':['storm']};r={**event(),'event_type':'storm'}
        self.assertIn('STORM_CONFIRMED_OCCURRENCE_REQUIRED',admit(r,s,allow_fixture=True)['admission_reasons'])
        r.update(evidence_kind='confirmed_occurrence',measurement_value=None,measurement_unit=None,
                 threshold_definition='Synthetic independently confirmed thunderstorm fixture')
        self.assertEqual(admit(r,s,allow_fixture=True)['admission_status'],'admitted_for_training')
        self.assertNotEqual(admit(r,s)['admission_status'],'admitted_for_training')

    def test_expanded_protocol_keeps_frozen_v1_available(self):
        self.assertNotIn('storm',load_protocol('ml/configs/himalayan_warning_v1.json')['targets'])
        self.assertIn('storm',load_protocol()['targets'])
        self.assertEqual(load_protocol()['horizon_hours'],6)
