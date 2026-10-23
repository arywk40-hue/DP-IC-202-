"""Mocked acquisition and independent-label gates; no provider credentials."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

from ml.himachal.data.download import acquire, cached_download, request_for, windows
from ml.himachal.data.labels import build_labels, outcome, write_outputs
from ml.himachal.data.observations import imerg_hourly, power_hourly
from ml.himachal.data.sources import load
from ml.himachal.data.virtual_nodes import virtual_nodes
from ml.tests.test_himachal_features import native_records

ROOT = Path(__file__).resolve().parents[2]


class Response(io.BytesIO):
    def __init__(self, data, url, status=200, headers=None):
        super().__init__(data)
        self.url, self.status, self.headers = url, status, headers or {"ETag": '"fixture-v1"'}

    def geturl(self):
        return self.url


class AcquisitionTests(unittest.TestCase):
    def test_requests_bound_months_and_pin_utc_model_units(self):
        self.assertEqual(list(windows("2024-02-28", "2024-03-01")), [("2024-02-28", "2024-02-29"), ("2024-03-01", "2024-03-01")])
        with self.assertRaises(ValueError):
            list(windows("2025-01-01", "2024-01-01"))
        c = load()
        weather = request_for(c, "open_meteo_weather", "2024-01-01", "2024-01-31")
        self.assertIn("timezone=UTC", weather)
        self.assertIn("models=era5", weather)
        self.assertIn("wind_speed_unit=ms", weather)
        power = request_for(c, "nasa_power", "2024-01-01", "2024-01-31")
        self.assertIn("time-standard=UTC", power)
        with self.assertRaises(ValueError):
            request_for(c, "imd", "2024-01-01", "2024-01-31")

    def test_mocked_download_cache_offline_reproducible_and_tamper_fails(self):
        c = load()
        calls = []
        def opener(request, timeout):
            calls.append(request.full_url)
            return Response(b'{"latitude":31.75,"longitude":77,"hourly_units":{"surface_pressure":"hPa"}}', request.full_url)
        with tempfile.TemporaryDirectory() as tmp:
            first = acquire(c, "open_meteo_weather", "2024-01-01", "2024-01-02", tmp, opener=opener, sleep=lambda _: None)
            second = acquire(c, "open_meteo_weather", "2024-01-01", "2024-01-02", tmp, offline=True, opener=lambda *a, **k: self.fail("Network during offline test"))
            self.assertEqual(first, second)
            self.assertEqual(len(calls), 1)
            self.assertFalse(first["empirical_training_ready"])
            raw = next(Path(tmp).glob("*/response.json"))
            raw.write_text("changed")
            with self.assertRaisesRegex(ValueError, "checksum"):
                acquire(c, "open_meteo_weather", "2024-01-01", "2024-01-02", tmp, offline=True)

    def test_rate_limit_retry_size_bound_and_partial_resume(self):
        url = "https://archive-api.open-meteo.com/test"
        calls, sleeps = [], []
        data = b'{"ok":true}'
        def opener(request, timeout):
            calls.append(request)
            if len(calls) == 1:
                raise HTTPError(url, 429, "busy", {"Retry-After": "2"}, None)
            return Response(data, url)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"response.json"
            self.assertEqual(cached_download(url, path, max_bytes=64, attempts=3, opener=opener, sleep=sleeps.append), {"ok": True})
            self.assertEqual(sleeps, [2.])
            with self.assertRaisesRegex(ValueError, "byte budget"):
                cached_download(url, Path(tmp)/"too_big.json", max_bytes=3, attempts=1,
                    opener=lambda *a, **k: Response(data, url))
            path.unlink()
            path.with_suffix(".partial").write_bytes(data[:5])
            path.with_suffix(".partial.identity.json").write_text(json.dumps({"etag": '"fixture-v1"'}))
            def resume(req, timeout):
                self.assertEqual(req.get_header("Range"), "bytes=5-")
                return Response(data[5:], url, 206, {"ETag": '"fixture-v1"', "Content-Range": f"bytes 5-{len(data)-1}/{len(data)}"})
            self.assertEqual(cached_download(url, path, max_bytes=64, attempts=1, opener=resume), {"ok": True})

    def test_manual_access_is_explicit_and_import_is_immutable(self):
        c = load()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(acquire(c, "imd", "2024-01-01", "2024-01-31", tmp)["status"], "NOT_READY")
            path = Path(tmp)/"approved.csv"
            path.write_text("temperature_c\n20\n")
            m = dict(provider_version="source_export_v1", source_station_or_cell_id="station_fixture",
                native_cadence_seconds=3600, units={"temperature": "C"}, rights_evidence_uri="fixture:terms",
                reviewed_by="fixture_only", original_request={"export": "fixture"}, retrieved_at_utc="2024-02-01T00:00:00Z")
            result = acquire(c, "imd", "2024-01-01", "2024-01-31", Path(tmp)/"cache", input_path=path, metadata=m)
            self.assertFalse(result["empirical_training_ready"])
            with self.assertRaises(ValueError):
                acquire(c, "imd", "2024-01-01", "2024-01-31", Path(tmp)/"cache", input_path=path, metadata={**m,"reviewed_by":"changed"})
            with self.assertRaisesRegex(ValueError, "Credentials"):
                acquire(c, "imd", "2024-01-01", "2024-01-31", Path(tmp)/"cache", input_path=path,
                        metadata={**m,"original_request":{"api_key":"test-secret-not-a-real-key"}})


class NormalizationTests(unittest.TestCase):
    def test_imerg_rate_to_accumulation_qc_and_missing_half_hour(self):
        a = dict(source_cell_id="satellite_fixture_cell", interval_start_utc="2024-07-01T00:00:00Z", interval_end_utc="2024-07-01T00:30:00Z",
                 rate=100., unit="mm/h", quality="valid", random_error=20., fill_value=-9999.)
        b = {**a,"interval_start_utc":"2024-07-01T00:30:00Z","interval_end_utc":"2024-07-01T01:00:00Z","rate":20.}
        result = imerg_hourly([a,b])[0]
        self.assertEqual(result["precipitation_mm"], 60.)
        self.assertFalse(result["cloudburst_label_admissible"])
        self.assertEqual(len(result["original_quality_error"]), 2)
        self.assertIsNone(imerg_hourly([a])[0]["precipitation_mm"])
        self.assertIsNone(imerg_hourly([a,{**b,"quality":"rejected"}])[0]["precipitation_mm"])
        self.assertIsNone(imerg_hourly([{**a,"rate":0.,"fill_value":0.},b])[0]["precipitation_mm"])
        with self.assertRaises(ValueError):
            imerg_hourly([a,a])
        with self.assertRaises(ValueError):
            imerg_hourly([{**a,"unit":"mm/day"}])

    def test_power_utc_units_fill_and_absent_pm(self):
        response = dict(header={"time_standard":"UTC","fill_value":-999},
            parameters={"T2M":{"units":"C"},"RH2M":{"units":"%"},"PS":{"units":"kPa"},"WS10M":{"units":"m/s"}},
            properties={"parameter":{k:{"2024070100":v} for k,v in {"T2M":20.,"RH2M":80.,"PS":90.,"WS10M":-999}.items()}})
        row = power_hourly(response)[0]
        self.assertEqual(row["measurements"]["pressure_hpa"], 900.)
        self.assertIsNone(row["measurements"]["pm25_ug_m3"])
        self.assertIsNone(row["measurements"]["wind_speed_mps"])
        for change in ("LST", None):
            response["header"]["time_standard"] = change
            with self.assertRaises(ValueError):
                power_hourly(response)

    def test_duplicate_upstream_sources_cannot_manufacture_physical_votes(self):
        r = dict(provider="CPCB", upstream_provider="CPCB", upstream_station_or_cell_id="same_station",
            source_class="observed_external_station", variables=["pm25_ug_m3"], native_cadence_seconds=3600, native_resolution="station",
            valid_time_utc="2024-07-01T00:00:00Z", available_at_utc="2024-07-01T00:10:00Z", rights_status="UNVERIFIED",
            units={"pm25_ug_m3":"ug/m3"}, elevation_m=None, elevation_datum="unknown", pressure_reference="unknown",
            source_version="fixture_v1", provider_license="UNVERIFIED", measurement_uncertainty=None, source_ancestry=["fixture_upstream_record"])
        nodes = virtual_nodes([r,{**r,"provider":"OpenAQ"}])
        self.assertEqual(len(nodes), 1)
        self.assertFalse(nodes[0]["physical_vote_eligible"])
        with self.assertRaises(ValueError):
            virtual_nodes([r,{**r,"provider":"OpenAQ","variables":["pm10"]}])


def label_fixtures():
    events = [json.loads(line) for line in (ROOT/"ml/tests/fixtures/himachal_reviewed_events.jsonl").read_text().splitlines()]
    monitors = json.loads((ROOT/"ml/tests/fixtures/himachal_monitoring.json").read_text())
    config = json.loads((ROOT/"ml/configs/himachal_labels_v1.json").read_text())
    rows = native_records(cadence=3600, hours=48)
    site = "fixture_site:fixture_registration"
    config["approved_sites"] = {site:dict(co_location_verified=True, country_code="IN", state="Himachal Pradesh",
        reviewed_by="SOFTWARE_FIXTURE_ONLY", source_id=rows[0]["source_id"], latitude=31.71, longitude=76.93)}
    config["approved_sources"] = {"software_gauge_fixture":dict(status="admitted_for_training", evidence="SYNTHETIC_CONTRACT_ONLY",
        independent_observed=True, rights_status="approved_open", rights_evidence_uri="fixture:not_real_rights", reviewed_by="SOFTWARE_FIXTURE_ONLY",
        source_dataset="software_gauge_fixture", source_provider="software_fixture", event_identity_reviewed=True,
        country="IN", targets=["rain","snowstorm","cloudburst"], provider_license="SYNTHETIC_CONTRACT_ONLY")}
    return events, rows, monitors, config


class LabelAdmissionTests(unittest.TestCase):
    def test_synthetic_fixtures_never_approve_empirical_training(self):
        events, rows, monitors, config = label_fixtures()
        labels, receipt = build_labels(events, rows, monitors, config)
        self.assertEqual(receipt["status"], "NOT_READY")
        self.assertFalse(receipt["empirical_training_approved"])
        self.assertEqual(receipt["evidence_kind"], "SYNTHETIC_CONTRACT_ONLY")
        self.assertTrue(labels.label.isna().all())
        self.assertFalse(labels.empirical_training_admissible.any())
        self.assertGreater(receipt["rejected_reasons"]["SYNTHETIC_NOT_INDEPENDENT"], 0)

    def test_contract_mode_exercises_onset_and_complete_negative_monitoring(self):
        events, rows, monitors, config = label_fixtures()
        labels, receipt = build_labels(events, rows, monitors, config, contract_mode=True)
        rain = labels[labels.public_target.eq("rain")]
        self.assertTrue(rain.label.eq(1).any())
        self.assertTrue(rain.label.eq(0).any())
        self.assertFalse(labels.empirical_training_admissible.any())
        self.assertEqual(receipt["status"], "NOT_READY")
        # No monitoring means no fabricated dry/negative windows.
        unknown, _ = build_labels([], rows, [], config, contract_mode=True)
        self.assertTrue(unknown.label.isna().all())

    def test_daily_satellite_and_unstructured_cloudburst_evidence_stay_unadmitted(self):
        events, _, _, config = label_fixtures()
        rain = events[0]
        bad = copy.deepcopy(rain)
        bad["measurement"]["interval_end_utc"] = "2026-07-03T00:00:00Z"
        self.assertNotEqual(outcome(bad, config, contract_mode=True)["admission_status"], "admitted_for_training")
        bad = copy.deepcopy(rain)
        bad["record"]["event_type"] = "cloudburst"
        bad["record"]["evidence_kind"] = "satellite_detection"
        self.assertNotEqual(outcome(bad, config, contract_mode=True)["admission_status"], "admitted_for_training")

    def test_reprocessing_is_identical_and_changed_output_refuses_overwrite(self):
        events, rows, monitors, config = label_fixtures()
        first, receipt = build_labels(events, rows, monitors, config)
        second, receipt2 = build_labels(events, rows, monitors, config)
        self.assertEqual(receipt, receipt2)
        with tempfile.TemporaryDirectory() as tmp:
            a = write_outputs(tmp, first, receipt)
            b = write_outputs(tmp, second, receipt2)
            self.assertEqual(a, b)
            with self.assertRaises(ValueError):
                write_outputs(tmp, second, {**receipt2,"status":"CHANGED"})

    def test_unknown_country_colocation_and_pressure_cannot_be_guessed(self):
        events, rows, monitors, config = label_fixtures()
        config["approved_sites"] = {}
        labels, receipt = build_labels(events, rows, monitors, config, contract_mode=True)
        self.assertTrue(labels.empty)
        self.assertEqual(receipt["unreviewed_or_ineligible_observation_rows"], len(rows))

    def test_cloudburst_candidate_blocks_rain_negative_without_becoming_truth(self):
        events, rows, monitors, config = label_fixtures()
        candidate = copy.deepcopy(events[0])
        candidate["record"].update(event_type="cloudburst", cloudburst_evidence_verified=False,
            measurement_value=0.2, measurement_unit="mm/h", threshold_definition=config["definitions"]["cloudburst"])
        labels, _ = build_labels([candidate], rows, monitors, config, contract_mode=True)
        rain = labels[labels.public_target.eq("rain")]
        issue = rain[rain.timestamp_utc.eq("2026-07-02T00:00:00+00:00")]
        self.assertEqual(len(issue),1)
        self.assertTrue(issue.label.isna().all())
        self.assertFalse(rain.label.eq(1).any())
