from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

from ml.six_sensor_forecast.audit_india import SAMPLES, audit, read_table


class IndiaSourceAuditTest(unittest.TestCase):
    def test_zip_response_and_unverified_six_input_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "raw").mkdir()
            (root / "source_metadata.json").write_text(
                json.dumps({"licenseName": "test-only"})
            )
            stations = []
            for station in SAMPLES:
                stations.append(
                    {
                        "file_name": station,
                        "city": "Baddi",
                        "state": "Himachal Pradesh",
                        "station_location": "fixture",
                    }
                )
                frame = pd.DataFrame(
                    {
                        "From Date": ["2020-01-01 00:00:00"],
                        "To Date": ["2020-01-01 01:00:00"],
                        "AT (degree C)": [20],
                        "RH (%)": [50],
                        "BP (mmHg)": [1000],
                        "PM2.5 (ug/m3)": [10],
                        "PM10 (ug/m3)": [20],
                        "WS (m/s)": [2],
                    }
                )
                if station == "HP001":
                    frame = frame.drop(columns="BP (mmHg)")
                with zipfile.ZipFile(root / "raw" / (station + ".csv"), "w") as archive:
                    archive.writestr(station + ".csv", frame.to_csv(index=False))
            pd.DataFrame(stations).to_csv(root / "raw/stations_info.csv", index=False)
            self.assertEqual(len(read_table(root / "raw/HP001.csv")), 1)
            report = audit(root)
            self.assertEqual(report["downloaded_station_rows"], 7)
            self.assertFalse(report["current_model_retrained"])
            self.assertEqual(report["station_inventory"]["mandi_himachal_stations"], [])
            self.assertEqual(
                report["downloaded_samples"][0]["rows_with_all_six_finite_raw_values"],
                0,
            )
            other = report["downloaded_samples"][1]
            self.assertEqual(other["rows_with_all_six_finite_raw_values"], 1)
            self.assertFalse(other["approved_for_model_evaluation"])
            self.assertEqual(
                other["sensor_audit"]["pressure_hpa"][
                    "outside_300_1100_hpa_if_declared_mmHg_used"
                ],
                1,
            )


if __name__ == "__main__":
    unittest.main()
