"""Rule contracts and confounders, not measured event detection accuracy."""
import copy
import json
import unittest

from ml.himachal.rules import evaluate
from ml.tests.test_himachal_features import native_records, packet


def terrain(rows, exposed=True):
    return dict(reviewed=True, exposed=exposed, source_id="reviewed_synthetic_exposure_fixture",
                available_at_utc=rows[0]["timestamp_utc"])


class HimachalRuleTests(unittest.TestCase):
    def test_exact_rain_thresholds_complete_conjunction_and_not_safety(self):
        rows = native_records(cadence=3600, hours=6)
        for r in rows:
            r["measurements"].update(temperature_c=4., relative_humidity_pct=85., pm25_ug_m3=25., pm10_ug_m3=50.)
        rows[-1]["measurements"].update(pm25_ug_m3=20., pm10_ug_m3=40.)
        rain = evaluate(packet(rows))["outputs"]["rain"]
        self.assertEqual(rain["score"], 1.)
        self.assertFalse(rain["abstain"])
        self.assertEqual(len(rain["triggered_evidence"]), 4)
        rows[-1]["measurements"]["temperature_c"] = 3.
        rain = evaluate(packet(rows))["outputs"]["rain"]
        self.assertEqual(rain["score"], 0.)
        self.assertEqual(rain["level"], "not_matched")
        self.assertIn("NOT_PROOF_OF_SAFETY", rain["non_match_means"])

    def test_clean_air_rain_confounds_proxy_and_must_abstain(self):
        rows = native_records(cadence=3600, hours=6)
        for r in rows:
            r["measurements"].update(relative_humidity_pct=99., pm25_ug_m3=1., pm10_ug_m3=2.)
        rain = evaluate(packet(rows))["outputs"]["rain"]
        self.assertTrue(rain["abstain"])
        self.assertIsNone(rain["score"])
        self.assertEqual(rain["level"], "unknown")
        self.assertFalse(rain["feature_availability"]["washout_hourly"])

    def test_snow_conjunction_boundaries_and_no_snowfall_confirmation(self):
        rows = native_records(cadence=3600, hours=6)
        for r in rows:
            r["measurements"].update(temperature_c=1., relative_humidity_pct=85., wind_speed_mps=9.)
        rows[-1]["measurements"].update(pm25_ug_m3=20., pm10_ug_m3=40.)
        snow = evaluate(packet(rows))["outputs"]["snowstorm"]
        self.assertEqual(snow["score"], 1.)
        self.assertTrue(snow["risk_only"])
        self.assertEqual(snow["display_name"], "Snowstorm risk")
        self.assertIsNone(snow["probability"])
        self.assertIsNone(snow["lead_time_h"])
        self.assertFalse(snow["warning_candidate"])
        rows[-1]["measurements"]["wind_speed_mps"] = 8.99
        self.assertEqual(evaluate(packet(rows))["outputs"]["snowstorm"]["score"], 0.)

    def test_native_cloudburst_risk_all_measurement_conditions(self):
        rows = native_records(hours=7)
        rows[-1]["measurements"].update(temperature_c=18., relative_humidity_pct=90.,
            pressure_hpa=rows[-2]["measurements"]["pressure_hpa"]-1., wind_speed_mps=8., pm25_ug_m3=20., pm10_ug_m3=40.)
        r = evaluate(packet(rows), terrain=terrain(rows))
        cloud = r["outputs"]["cloudburst_risk"]
        self.assertEqual(cloud["score"], 1.)
        self.assertEqual(cloud["dynamic_matches"], 5)
        self.assertEqual(cloud["level"], "local_warning_candidate")
        self.assertFalse(cloud["warning_candidate"])
        self.assertEqual(cloud["corroboration"], "NOT_ASSESSED")
        self.assertTrue(cloud["human_confirmation_required"])
        self.assertFalse(r["public_notifications_enabled"])
        self.assertTrue(r["synthetic_demo"])
        json.dumps(r, allow_nan=False)

    def test_missing_terrain_never_guessed_or_renormalized(self):
        rows = native_records(hours=7)
        rows[-1]["measurements"].update(temperature_c=18., relative_humidity_pct=90.,
            pressure_hpa=rows[-2]["measurements"]["pressure_hpa"]-1., wind_speed_mps=8., pm25_ug_m3=20., pm10_ug_m3=40.)
        cloud = evaluate(packet(rows))["outputs"]["cloudburst_risk"]
        self.assertEqual(cloud["score"], .95)
        self.assertEqual(cloud["coverage"], .95)
        self.assertFalse(cloud["feature_availability"]["reviewed_terrain_exposure"])
        self.assertEqual(cloud["score_interpretation"], "OBSERVED_WEIGHT_SUM_NOT_RENORMALIZED")
        rows[-1]["measurements"]["pm10_ug_m3"] = None
        cloud = evaluate(packet(rows))["outputs"]["cloudburst_risk"]
        self.assertTrue(cloud["abstain"])
        self.assertEqual(cloud["score"], .8)
        self.assertEqual(cloud["level"], "unknown")

    def test_hourly_companion_is_distinct_and_native_abstains(self):
        rows = native_records(cadence=3600, hours=6)
        rows[-1]["measurements"].update(temperature_c=18., relative_humidity_pct=95.,
            pressure_hpa=rows[-2]["measurements"]["pressure_hpa"]-1.5, wind_speed_mps=8., pm25_ug_m3=20., pm10_ug_m3=40.)
        native = evaluate(packet(rows), terrain=terrain(rows))["outputs"]["cloudburst_risk"]
        hourly = evaluate(packet(rows), profile="hourly_companion", terrain=terrain(rows))["outputs"]["cloudburst_risk"]
        self.assertTrue(native["abstain"])
        self.assertFalse(hourly["abstain"])
        self.assertEqual(hourly["score"], 1.)
        self.assertNotEqual(native["profile"], hourly["profile"])
        self.assertIn("hourly_companion", hourly["profile"])

    def test_season_terrain_and_altitude_cannot_create_warning(self):
        rows = native_records(hours=7)
        for r in rows:
            r["elevation_m"] = 4500.
        cloud = evaluate(packet(rows), terrain=terrain(rows))["outputs"]["cloudburst_risk"]
        self.assertEqual(cloud["score"], .1)
        self.assertEqual(cloud["dynamic_matches"], 0)
        self.assertEqual(cloud["level"], "not_matched")
        self.assertFalse(cloud["warning_candidate"])

    def test_pressure_model_context_never_satisfies_observed_station_rules(self):
        rows = native_records(hours=7)
        for r in rows:
            r["source_class"] = "modeled_grid"
            r["source_cell_id"] = "fixture_grid"
            r["pressure_reference"] = "grid_surface"
        result = evaluate(packet(rows))
        for event in result["outputs"].values():
            self.assertTrue(event["abstain"])
            self.assertEqual(event["assessment_state"], "SOURCE_REFERENCE_UNSUPPORTED")

    def test_storm_predrop_then_rebound_uses_disjoint_intervals(self):
        rows = native_records(hours=7)
        # P decreases by 6 hPa in the preceding six-hour window, then rebounds
        # 1.5 hPa during the final 15 min. Rebound isn't the pre-drop delta.
        rows[-1]["measurements"].update(pressure_hpa=rows[-2]["measurements"]["pressure_hpa"]+1.5,
            temperature_c=17., wind_speed_mps=10., pm25_ug_m3=20., pm10_ug_m3=40.)
        result = evaluate(packet(rows))["rainstorm_sequence"]
        self.assertTrue(result["matched"])
        self.assertTrue(result["risk_only"])
        rows[-1]["measurements"]["pressure_hpa"] -= 2.
        self.assertFalse(evaluate(packet(rows))["rainstorm_sequence"]["matched"])

    def test_unknown_profile_bad_evidence_and_future_unreviewed_terrain_refuse(self):
        rows = native_records(hours=7)
        p = packet(rows)
        for change in ("profile", "version", "label", "nonfinite", "evidence"):
            modified = copy.deepcopy(p)
            kw = {}
            if change == "profile":
                kw["profile"] = "invented"
            elif change == "version":
                modified["schema_version"] = "legacy"
            elif change == "label":
                modified["training_label_admissible"] = True
            elif change == "nonfinite":
                modified["features"]["temperature_c"]["value"] = float("nan")
            else:
                modified["features"]["temperature_c"]["evidence_id"] = "unrelated"
            with self.subTest(change=change), self.assertRaises(ValueError):
                evaluate(modified, **kw)
        for key, v in (("reviewed", False), ("available_at_utc", "2027-01-01T00:00:00Z"), ("source_id", "")):
            t = terrain(rows)
            t[key] = v
            with self.subTest(key=key), self.assertRaises(ValueError):
                evaluate(p, terrain=t)

    def test_all_public_outputs_are_risks_never_labels_or_advance_predictions(self):
        result = evaluate(packet(native_records(hours=7)))
        self.assertEqual(set(result["outputs"]), {"rain", "snowstorm", "cloudburst_risk"})
        self.assertFalse(result["training_labels_allowed"])
        for output in result["outputs"].values():
            self.assertIsNone(output["probability"])
            self.assertIsNone(output["lead_time_h"])
            self.assertFalse(output["training_label_admissible"])
            self.assertEqual(output["dispatch_state"], "DISABLED")
            self.assertEqual(output["task"], "current_condition_heuristic")
