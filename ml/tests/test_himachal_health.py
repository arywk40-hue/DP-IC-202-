import unittest

from ml.himachal.health import Health
from ml.himachal.nodes import Registry
from ml.tests.himachal_network_fixture import EPOCH, iso, registration, rig


class HealthTests(unittest.TestCase):
    def test_stale_clock_and_three_heartbeat_intervals_are_explicit(self):
        _,h,_,_=rig()
        self.assertTrue(h.assess("fixture-0",iso(EPOCH))["eligible"])
        self.assertIn("STALE_OBSERVATION",h.assess("fixture-0",iso(EPOCH+121))["reasons"])
        self.assertIn("HEARTBEATS_MISSING",h.assess("fixture-0",iso(EPOCH+181))["reasons"])
        self.assertFalse(h.assess("fixture-0",iso(EPOCH-1))["eligible"])

    def test_channel_specific_fault_recovery_and_clock_uncertainty(self):
        _,h,_,_=rig()
        n="fixture-0"
        h.update(n,iso(EPOCH+60),iso(EPOCH+60),valid_mask=31)
        self.assertTrue(h.assess(n,iso(EPOCH+60),31)["eligible"])
        self.assertFalse(h.assess(n,iso(EPOCH+60),63)["eligible"])
        for i in range(1,4):
            h.update(n,iso(EPOCH+60+i*60),iso(EPOCH+60+i*60))
            self.assertEqual(h.assess(n,iso(EPOCH+60+i*60))["eligible"],i==3)
        h.update(n,iso(EPOCH+300),iso(EPOCH+300),clock_uncertainty=31.)
        self.assertIn("CLOCK_UNCERTAIN",h.assess(n,iso(EPOCH+300))["reasons"])

    def test_regional_shift_not_proof_of_fault_and_maintenance_hysteresis(self):
        _,h,_,_=rig()
        n="fixture-0"
        for t in (EPOCH,EPOCH+21600):
            h.residual_diagnostic(n,4,iso(t),persistent=True,independent_fault_evidence=False,evidence_id="weather-shift")
        self.assertEqual(h.records[n]["excluded_mask"],0)
        h.residual_diagnostic(n,4,iso(EPOCH+21601),persistent=True,independent_fault_evidence=True,evidence_id="reference-calibration-fault")
        self.assertEqual(h.records[n]["excluded_mask"]&4,4)
        h.clear_after_maintenance(n,4,"reviewed-sensor-replacement")
        self.assertEqual(h.records[n]["recovery"][2],0)
        self.assertEqual(h.records[n]["excluded_mask"]&4,4)

    def test_initial_warmup_missing_battery_and_duplicates(self):
        r,h,_,_=rig()
        n="fixture-0"
        h.update(n,iso(EPOCH+60),iso(EPOCH+60),battery_critical=True)
        self.assertIn("BATTERY_CRITICAL",h.assess(n,iso(EPOCH+60))["reasons"])
        with self.assertRaises(ValueError):
            h.update(n,iso(EPOCH+60),iso(EPOCH+60))
        r2=Registry()
        r2.register(registration(0),b"synthetic-fixture-key-32-bytes-long!")
        h2=Health(r2)
        for i in range(3):
            h2.update(n,iso(EPOCH+i*60),iso(EPOCH+i*60))
            self.assertEqual(h2.assess(n,iso(EPOCH+i*60))["eligible"],i==2)
