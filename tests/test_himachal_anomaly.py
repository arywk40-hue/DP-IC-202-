"""Stateful diagnostics, including weather changes that must survive QC."""
import unittest

from ml.himachal.anomaly import Detector, f32, load


class AnomalyTests(unittest.TestCase):
    def test_warmup_noise_floor_and_calm_zero_are_valid(self):
        d=Detector()
        for i in range(30):
            r=d.push(1767225600+i*60,[20.,60.,900.,25.,50.,0.])
            self.assertEqual(r["valid_mask"],63)
            self.assertEqual(r["fault_mask"],0)
            self.assertEqual(r["channel_states"][5],"WARMUP" if i<8 else "WITHIN_BASELINE")
        self.assertTrue(all(s>0 for s in r["scales"]))
        self.assertTrue(all(n==16 for n in r["baseline_counts"]))

    def test_genuine_fast_weather_is_environmental_not_sensor_fault(self):
        d=Detector()
        for i in range(12):
            d.push(1767225600+i*60,[20.,60.,900.,25.,50.,0.])
        r=d.push(1767225600+12*60,[10.,95.,895.,10.,20.,12.])
        self.assertEqual(r["fault_mask"],0)
        self.assertEqual(r["valid_mask"],63)
        self.assertEqual(r["environmental_mask"],63)
        self.assertTrue(all(s=="ENVIRONMENTAL_ANOMALY" for s in r["channel_states"]))

    def test_crc_clock_replay_and_offgrid_do_not_advance_baseline(self):
        d=Detector()
        x=[20.,60.,900.,25.,50.,0.]
        d.push(1767225600,x)
        cases=[(1767225660,{"crc_ok":False},"CRC_REJECTED"),
               (1767225600,{},"TIME_REJECTED"),(1767225601,{},"TIME_REJECTED"),
               (1767225660,{"clock_uncertainty_seconds":None},"CLOCK_UNVERIFIED"),
               (1767225660,{"clock_uncertainty_seconds":31.},"CLOCK_UNVERIFIED")]
        for t,kw,status in cases:
            with self.subTest(status=status):
                r=d.push(t,x,**kw)
                self.assertEqual(r["packet_state"],status)
                self.assertEqual(r["baseline_counts"],[1]*6)

    def test_missing_infinite_range_and_self_test_fault_are_distinct(self):
        d=Detector()
        r=d.push(1767225600,[None,60.,float("inf"),25.,50.,0.],self_test_fault_mask=32)
        self.assertEqual(r["channel_states"][0],"UNAVAILABLE")
        self.assertEqual(r["channel_states"][2],"SENSOR_FAULT")
        self.assertEqual(r["channel_states"][5],"SENSOR_FAULT")
        r=d.push(1767225660,[-60.,100.,1100.,5000.,5000.,100.])
        self.assertEqual(r["fault_mask"],0)
        r=d.push(1767225720,[-60.1,100.1,1100.1,5000.1,5000.1,100.1])
        self.assertEqual(r["fault_mask"],63)

    def test_long_gap_reboot_and_slow_drift_do_not_invent_hardware_failure(self):
        d=Detector()
        for i in range(40):
            r=d.push(1767225600+i*60,[20.+i*.1,60.,900.,25.,50.,0.])
            self.assertEqual(r["fault_mask"],0)
        r=d.push(1767231600,[20.,60.,900.,25.,50.,0.])
        self.assertEqual(r["channel_states"],["WARMUP"]*6)
        d.reset()
        self.assertEqual(d.push(1767225600,[20.,60.,900.,25.,50.,0.])["baseline_counts"],[1]*6)

    def test_threshold_equality_and_adjacent_float32(self):
        for change,expected in ((1.,False),(f32(1.00001),True)):
            d=Detector()
            for i in range(10):
                d.push(1767225600+i*60,[20.,60.,900.,25.,50.,0.])
            r=d.push(1767226200,[20.+change,60.,900.,25.,50.,0.])
            self.assertEqual(bool(r["environmental_mask"]&1),expected)

    def test_bounded_config_and_inputs(self):
        cfg=load()
        self.assertFalse(cfg["hardware_validated"])
        with self.assertRaises(ValueError):
            Detector(cadence_seconds=7)
        with self.assertRaises(ValueError):
            Detector(cadence_seconds=0)
        with self.assertRaises(ValueError):
            Detector().push(1767225600,[1,2,3])
