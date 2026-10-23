"""Native feature contracts; fixtures are synthetic, not meteorological skill."""
import copy
import csv
import json
import unittest
from pathlib import Path

import pandas as pd

from ml.himachal.contracts import snapshot
from ml.himachal.features import build_packet
from ml.himachal.meteorology import heat_index, humidity
from ml.operational.contracts import UNITS
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


def native_records(cadence=900, hours=24):
    result = []
    start = pd.Timestamp("2026-07-01T00:00:00Z")
    for i in range(hours*3600//cadence+1):
        time = (start+pd.Timedelta(seconds=i*cadence)).isoformat()
        result.append(dict(node_id="fixture_node", physical_site_id="fixture_site",
            registration_id="fixture_registration", latitude=31.71, longitude=76.93,
            elevation_m=1000., elevation_datum="surveyed_orthometric", sensor_height_m=2., wind_height_m=10.,
            native_interval_seconds=cadence, source_class="synthetic_demo", source_id="software_contract_only",
            source_cell_id=None, pressure_reference="station", timestamp_utc=time, valid_time_utc=time,
            available_at_utc=time, sensor_model="synthetic_contract_not_field",
            calibration_ids={c: "synthetic_calibration_contract" for c in RAW_SENSOR_COLUMNS},
            measurements=dict(zip(RAW_SENSOR_COLUMNS, [20., 60., 900.-i*cadence/3600, 40., 80., 5.])),
            units=UNITS.copy()))
    return result


def packet(rows):
    return build_packet(rows, rows[-1]["timestamp_utc"])


def value(p, name):
    return p["features"][name]["value"]


class HimachalFeatureTests(unittest.TestCase):
    def test_native_exact_window_deltas_rates_and_history(self):
        p = packet(native_records())
        self.assertEqual(value(p, "pressure_hpa_delta_6h"), -6.)
        self.assertEqual(value(p, "pressure_hpa_delta_1h"), -1.)
        self.assertEqual(value(p, "pressure_hpa_delta_15min"), -.25)
        self.assertEqual(value(p, "pressure_hpa_rate_per_h_15min"), -1.)
        self.assertTrue(all(p["history_availability"].values()))
        json.dumps(p, allow_nan=False)
        self.assertFalse(p["training_label_admissible"])

    def test_hourly_data_never_manufactures_15min_values(self):
        p = packet(native_records(cadence=3600))
        self.assertIsNone(value(p, "pressure_hpa_delta_15min"))
        self.assertIsNone(value(p, "wind_increase_15min"))
        self.assertIsNone(value(p, "washout_15min_native"))
        self.assertEqual(value(p, "pressure_hpa_delta_1h"), -1)

    def test_storm_predrop_excludes_current_rebound_interval(self):
        rows = native_records(hours=7)
        before = packet(rows)
        rows[-1]["measurements"]["pressure_hpa"] += 5
        after = packet(rows)
        self.assertEqual(value(after, "pressure_predrop_6h_ending_15min_ago"), -6)
        self.assertEqual(value(before, "pressure_predrop_6h_ending_15min_ago"), -6)
        self.assertGreater(value(after, "pressure_hpa_delta_15min"), 0)

    def test_future_values_and_future_publications_do_not_change_prior_packet(self):
        rows = native_records()
        issue = rows[40]["timestamp_utc"]
        before = build_packet(rows[:41], issue)
        for r in rows[41:]:
            r["measurements"] = dict(zip(RAW_SENSOR_COLUMNS, [-50., 0., 350., 4999., 4000., 90.]))
        self.assertEqual(before, build_packet(rows, issue))
        rows[40]["available_at_utc"] = rows[41]["timestamp_utc"]
        late = build_packet(rows, issue)
        self.assertIsNone(value(late, "temperature_c"))
        self.assertIsNone(value(late, "pressure_hpa_delta_15min"))

    def test_gap_blocks_all_windows_that_cross_it_without_ffill(self):
        rows = native_records(hours=6)
        del rows[-3]
        p = packet(rows)
        self.assertIsNone(value(p, "pressure_hpa_delta_1h"))
        self.assertIsNone(value(p, "pressure_hpa_delta_6h"))
        self.assertEqual(value(p, "pressure_hpa_delta_15min"), -.25)
        self.assertFalse(p["history_availability"]["event_hourly_seven_snapshots"])

    def test_duplicates_reorder_offgrid_and_relocation_reject(self):
        for kind in ("duplicate", "reorder", "offgrid", "relocate", "registration", "reference", "height", "calibration"):
            with self.subTest(kind=kind):
                rows = native_records(hours=1)
                if kind == "duplicate":
                    rows.append(copy.deepcopy(rows[-1]))
                elif kind == "reorder":
                    rows[1], rows[2] = rows[2], rows[1]
                elif kind == "offgrid":
                    rows[1]["timestamp_utc"] = rows[1]["valid_time_utc"] = rows[1]["available_at_utc"] = "2026-07-01T00:16:00Z"
                elif kind == "relocate":
                    rows[-1]["longitude"] += .01
                elif kind == "registration":
                    rows[-1]["registration_id"] = "relocated"
                elif kind == "reference":
                    rows[-1]["pressure_reference"] = "grid_surface"
                elif kind == "height":
                    rows[-1]["wind_height_m"] = 2.
                else:
                    rows[-1]["calibration_ids"]["wind_speed_mps"] = "new_calibration"
                with self.assertRaises(ValueError):
                    packet(rows)

    def test_source_reference_pressure_and_missing_channel_are_explicit(self):
        rows = native_records(hours=6)
        for r in rows:
            r["pressure_reference"] = "unknown"
        self.assertIsNone(value(packet(rows), "pressure_hpa"))
        for r in rows:
            r["pressure_reference"] = "grid_surface"
            r["source_class"] = "modeled_grid"
            r["source_cell_id"] = "actual_provider_cell_fixture"
        p = packet(rows)
        self.assertEqual(p["metadata"]["pressure_reference"], "grid_surface")
        self.assertEqual(value(p, "pressure_hpa_delta_6h"), -6)
        rows[-1]["quality_flags"] = {"pm10_ug_m3": "uncertain"}
        self.assertIsNone(value(packet(rows), "pm10_ug_m3"))

    def test_conversions_preserve_values_and_explicit_ist_time(self):
        r = native_records(hours=0)[0]
        r["measurements"].update(temperature_c=293.15, pressure_hpa=90000, wind_speed_mps=18)
        r["units"].update(temperature_c="K", pressure_hpa="Pa", wind_speed_mps="km/h")
        for k in ("timestamp_utc", "valid_time_utc", "available_at_utc"):
            r[k] = "2026-07-01T05:30:00+05:30"
        s = snapshot(r)
        self.assertAlmostEqual(s["measurements"]["temperature_c"], 20)
        self.assertEqual(s["measurements"]["pressure_hpa"], 900)
        self.assertEqual(s["measurements"]["wind_speed_mps"], 5)
        self.assertEqual(s["timestamp_utc"], "2026-07-01T00:00:00+00:00")
        self.assertEqual(pd.Timestamp(s["timestamp_utc"]).tz_convert("Asia/Kolkata").hour, 5)

    def test_missing_metadata_extra_sensors_invalid_times_reject(self):
        r = native_records(hours=0)[0]
        for kind in ("extra", "missing", "naive", "availability", "bool", "datum"):
            c = copy.deepcopy(r)
            if kind == "extra":
                c["measurements"]["rainfall"] = 0
            elif kind == "missing":
                del c["available_at_utc"]
            elif kind == "naive":
                c["timestamp_utc"] = "2026-07-01T00:00:00"
            elif kind == "availability":
                c["available_at_utc"] = "2026-06-30T00:00:00Z"
            elif kind == "bool":
                c["native_interval_seconds"] = True
            else:
                c["elevation_datum"] = "GNSS_ellipsoid"
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                snapshot(c)

    def test_pm_zero_high_ratio_and_rh_percentage_point_boundary(self):
        rows = native_records(cadence=3600, hours=6)
        rows[-1]["measurements"].update(pm10_ug_m3=0, relative_humidity_pct=70)
        p = packet(rows)
        self.assertIsNone(value(p, "pm25_pm10_ratio"))
        self.assertEqual(value(p, "relative_humidity_pct_delta_1h"), 10)
        self.assertEqual(p["features"]["relative_humidity_pct_delta_1h"]["unit"], "percentage_point")
        self.assertTrue(value(p, "sharp_rh_change_1h"))
        rows[-1]["measurements"]["pm10_ug_m3"] = 20
        self.assertEqual(packet(rows)["features"]["pm25_pm10_ratio"]["quality_note"], "PM25_EXCEEDS_PM10_REVIEW")

    def test_hourly_washout_boundaries_clean_air_and_calibrated_noise(self):
        rows = native_records(cadence=3600, hours=6)
        for r in rows:
            r["measurements"].update(pm25_ug_m3=25., pm10_ug_m3=50.)
        rows[-1]["measurements"].update(pm25_ug_m3=20., pm10_ug_m3=40.)
        self.assertTrue(value(packet(rows), "washout_hourly"))
        rows[-1]["measurements"]["pm25_ug_m3"] = 20.001
        self.assertFalse(value(packet(rows), "washout_hourly"))
        rows[-1]["measurements"]["pm25_ug_m3"] = 20.
        noise = dict(calibration_id="independent_noise_fixture", available_at_utc=rows[0]["timestamp_utc"], pm25_ug_m3=2., pm10_ug_m3=4.)
        p = build_packet(rows, rows[-1]["timestamp_utc"], noise_sigma=noise)
        self.assertFalse(value(p, "washout_hourly"))
        noise["available_at_utc"] = "2027-01-01T00:00:00Z"
        with self.assertRaises(ValueError):
            build_packet(rows, rows[-1]["timestamp_utc"], noise_sigma=noise)
        for r in rows:
            r["measurements"].update(pm25_ug_m3=1., pm10_ug_m3=2.)
        self.assertIsNone(value(packet(rows), "washout_hourly"))

    def test_native_washout_previous_hour_and_wind_calibration(self):
        rows = native_records(hours=6)
        rows[-1]["measurements"].update(pm25_ug_m3=20., pm10_ug_m3=40., wind_speed_mps=8.)
        p = packet(rows)
        self.assertTrue(value(p, "washout_15min_native"))
        self.assertTrue(value(p, "wind_increase_15min"))
        for r in rows:
            r["calibration_ids"]["wind_speed_mps"] = None
        self.assertIsNone(value(packet(rows), "wind_increase_15min"))
        # One missing baseline sample cannot be treated as zero or ignored.
        rows[-4]["measurements"]["pm25_ug_m3"] = None
        self.assertIsNone(value(packet(rows), "washout_15min_native"))

    def test_committed_native_csv_is_software_fixture(self):
        path = Path(__file__).parent / "fixtures/himachal_native_observations.csv"
        with path.open() as handle:
            raw = list(csv.DictReader(handle))
        rows = native_records(hours=6)
        self.assertEqual(len(raw), len(rows))
        for fixture, row in zip(raw, rows):
            self.assertEqual(fixture["source_class"], "synthetic_demo")
            row["measurements"] = {c: float(fixture[c]) for c in RAW_SENSOR_COLUMNS}
            self.assertEqual(fixture["timestamp_utc"], row["timestamp_utc"])
        self.assertTrue(packet(rows)["history_availability"]["event_hourly_seven_snapshots"])


class MeteorologyTests(unittest.TestCase):
    def test_magnus_water_ice_domains_and_zero_rh(self):
        self.assertAlmostEqual(humidity(20, 50)["dewpoint_liquid_c"]["value"], 9.2551746, places=5)
        self.assertEqual(humidity(20, 100)["vpd_liquid_kpa"]["value"], 0.)
        self.assertAlmostEqual(humidity(-10, 100)["dewpoint_liquid_c"]["value"], -10.)
        self.assertGreater(humidity(-10, 100)["frostpoint_ice_c"]["value"], -10.)
        self.assertIsNone(humidity(20, 0)["dewpoint_liquid_c"]["value"])
        self.assertIsNotNone(humidity(20, 0)["vpd_liquid_kpa"]["value"])
        self.assertIsNone(humidity(-60, 90)["vpd_liquid_kpa"]["value"])
        self.assertIsNone(humidity(20, 50)["frostpoint_ice_c"]["value"])

    def test_nws_simple_rothfusz_and_humidity_adjustments(self):
        # Published NWS chart: 90F / 70% rounds to 106F apparent temperature.
        self.assertEqual(round(heat_index((90-32)/1.8, 70)["value"]*1.8+32), 106)
        self.assertEqual(heat_index(20, 50)["branch"], "simple_averaged")
        self.assertEqual(heat_index((95-32)/1.8, 10)["branch"], "rothfusz_low_rh")
        self.assertEqual(heat_index((85-32)/1.8, 90)["branch"], "rothfusz_high_rh")
        self.assertEqual(heat_index((90-32)/1.8, 70)["branch"], "rothfusz")
        self.assertIsNone(heat_index(-10, 90)["value"])
        self.assertIsNone(heat_index(60, 80)["value"])
        self.assertIsNotNone(heat_index(30, 0)["value"])
        self.assertIsNotNone(heat_index(30, 100)["value"])
        self.assertIsNone(heat_index(None, 80)["value"])
