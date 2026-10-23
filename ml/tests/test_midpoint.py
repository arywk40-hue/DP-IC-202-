import copy
import math
import unittest

from ml.six_sensor_forecast.midpoint import geographic_midpoint, prepare_midpoint


class MidpointTests(unittest.TestCase):
    def test_equator(self):
        self.assertEqual(geographic_midpoint((0, 0), (0, 20)), (0, 10))

    def test_dateline(self):
        lat, lon = geographic_midpoint((0, 179), (0, -179))
        self.assertAlmostEqual(lat, 0)
        self.assertAlmostEqual(abs(lon), 180)

    def test_identical_and_reversal(self):
        point = (31.78, 76.99)
        self.assertAlmostEqual(geographic_midpoint(point, point)[0], point[0])
        self.assertEqual(
            geographic_midpoint(point, (32, 77)), geographic_midpoint((32, 77), point)
        )

    def test_invalid_and_antipodal(self):
        for point in ((91, 0), (0, 181), (math.nan, 0), (0, 180)):
            with self.assertRaises(ValueError):
                geographic_midpoint((0, 0), point)

    def endpoints(self):
        values = dict(
            zip(
                (
                    "temperature_c",
                    "relative_humidity_pct",
                    "pressure_hpa",
                    "pm25_ug_m3",
                    "pm10_ug_m3",
                    "wind_speed_mps",
                ),
                (20, 50, 950, 35, 60, 2),
            )
        )
        left = {
            "latitude": 31.7,
            "longitude": 76.9,
            "timestamp_utc": "2026-09-14T00:00:00Z",
            "measurements": values,
        }
        right = copy.deepcopy(left)
        right["latitude"] = 31.9
        right["measurements"]["temperature_c"] = 24
        return left, right

    def test_interpolation(self):
        a, b = self.endpoints()
        self.assertEqual(
            prepare_midpoint(a, b)["estimated_inputs"]["temperature_c"], 22
        )

    def test_reject_missing_and_misaligned(self):
        for mode in ("missing", "time", "nan", "naive"):
            a, b = self.endpoints()
            if mode == "missing":
                del b["measurements"]["pm25_ug_m3"]
            if mode == "time":
                b["timestamp_utc"] = "2026-09-14T01:00:00Z"
            if mode == "nan":
                b["measurements"]["pressure_hpa"] = math.nan
            if mode == "naive":
                b["timestamp_utc"] = "2026-09-14T00:00:00"
            with self.assertRaises(ValueError):
                prepare_midpoint(a, b)


if __name__ == "__main__":
    unittest.main()
