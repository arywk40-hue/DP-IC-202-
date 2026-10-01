"""Fetch a bounded Indian station sample and audit six-sensor suitability.

This is source inspection, not preparation of approved model inputs. No missing
measurements are invented and no ambiguous pressure units are silently changed.
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

import numpy as np
import pandas as pd

from ml.six_sensor_forecast.data import sha256

SOURCE_REF = "abhisheksjha/time-series-air-quality-data-of-india-2010-2023"
API = "https://www.kaggle.com/api/v1/datasets/"
SAMPLES = ("HP001", "UK001", "JK001", "DL001", "RJ001", "KA001", "AS001")
COLUMNS = {
    "temperature_c": ("AT (degree C)", "Temp (degree C)", "AT (degree)"),
    "relative_humidity_pct": ("RH (%)",),
    "pressure_hpa": ("BP (mmHg)",),
    "pm25_ug_m3": ("PM2.5 (ug/m3)",),
    "pm10_ug_m3": ("PM10 (ug/m3)",),
    "wind_speed_mps": ("WS (m/s)",),
}


def fetch(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    subprocess.run(
        ["curl", "-L", "--fail", "--max-time", "120", "-sS", url, "-o", str(partial)],
        check=True,
    )
    partial.replace(path)


def download(root: Path) -> None:
    fetch(API + "view/" + SOURCE_REF, root / "source_metadata.json")
    metadata = json.loads((root / "source_metadata.json").read_text())
    if metadata.get("currentVersionNumber") != 2:
        raise ValueError(
            "Publisher version changed; review the inventory before refreshing this version-2 audit"
        )
    files, token = [], None
    for _ in range(20):
        query = {"pageSize": 200}
        if token:
            query["pageToken"] = token
        page = root / "listing_page.json"
        fetch(API + "list/" + SOURCE_REF + "?" + urlencode(query), page)
        payload = json.loads(page.read_text())
        files.extend(payload["datasetFiles"])
        token = payload.get("nextPageToken")
        if not payload.get("hasNextPageToken") or not token:
            break
    else:
        raise RuntimeError("Station inventory pagination did not finish")
    (root / "file_inventory.json").write_text(
        json.dumps(
            [{"name": f["name"], "bytes": f["totalBytes"]} for f in files], indent=2
        )
        + "\n"
    )
    page.unlink()
    for name in ["stations_info.csv", *(station + ".csv" for station in SAMPLES)]:
        fetch(
            API
            + "download/"
            + SOURCE_REF
            + "/"
            + quote(name)
            + "?datasetVersionNumber=2",
            root / "raw" / name,
        )


def read_table(path: Path) -> pd.DataFrame:
    # Kaggle returns some per-file downloads as ZIPs even with a .csv URL.
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.endswith(".csv")]
            if len(names) != 1:
                raise ValueError(f"Expected one CSV inside {path.name}")
            return pd.read_csv(io.BytesIO(archive.read(names[0])))
    return pd.read_csv(path)


def audit(root: Path) -> dict:
    stations = read_table(root / "raw/stations_info.csv")
    source = json.loads((root / "source_metadata.json").read_text())
    report = {
        "source_url": "https://www.kaggle.com/datasets/" + SOURCE_REF,
        "source_role": "Secondary compilation attributed by publisher to CPCB; not a direct CPCB export",
        "source_version_downloaded": 2,
        "publisher_license": source.get("licenseName"),
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "station_inventory": {
            "stations": len(stations),
            "cities": int(stations.city.nunique()),
            "states_and_uts": int(stations.state.nunique()),
            "mandi_himachal_stations": stations[
                stations.state.str.strip().eq("Himachal Pradesh")
                & stations.city.str.strip().str.casefold().eq("mandi")
            ].file_name.tolist(),
            "himachal_stations": stations[
                stations.state.str.strip().eq("Himachal Pradesh")
            ].to_dict(orient="records"),
        },
        "downloaded_samples": [],
        "current_model_retrained": False,
        "evaluation_status": "NOT_RUN_PENDING_UNIT_TIME_AND_LOCATION_VERIFICATION",
    }
    for station in SAMPLES:
        path = root / "raw" / (station + ".csv")
        frame = read_table(path)
        location = stations.loc[stations.file_name.eq(station)].iloc[0]
        entry = {
            "station_id": station,
            "state": location.state.strip(),
            "city": location.city.strip(),
            "station_location": location.station_location.strip(),
            "downloaded_file": str(path.relative_to(root)),
            "sha256": sha256(path),
            "transport": "ZIP containing CSV" if zipfile.is_zipfile(path) else "CSV",
            "rows": len(frame),
            "columns": frame.columns.tolist(),
            "sensor_audit": {},
        }
        start = pd.to_datetime(frame["From Date"], errors="coerce")
        end = pd.to_datetime(frame["To Date"], errors="coerce")
        entry.update(
            {
                "first_source_timestamp": str(start.min()),
                "last_source_timestamp": str(start.max()),
                "invalid_timestamp_rows": int((start.isna() | end.isna()).sum()),
                "duplicate_interval_rows": int(
                    frame.duplicated(["From Date", "To Date"]).sum()
                ),
                "one_hour_interval_rows": int(
                    (end - start).eq(pd.Timedelta(hours=1)).sum()
                ),
            }
        )
        complete = np.ones(len(frame), dtype=bool)
        blockers = [
            "Verify source timezone and interval-end availability before causal six-hour alignment",
            "Verify station coordinates/elevation and measurement metadata with primary provider",
        ]
        for target, options in COLUMNS.items():
            present = [name for name in options if name in frame]
            if not present:
                complete[:] = False
                entry["sensor_audit"][target] = {
                    "source_column": None,
                    "finite_rows": 0,
                }
                blockers.append("Missing " + target)
                continue
            name = present[0]
            numeric = pd.to_numeric(frame[name], errors="coerce")
            finite = np.isfinite(numeric)
            complete &= finite.to_numpy()
            stat = {
                "source_column": name,
                "finite_rows": int(finite.sum()),
                "median_raw": float(numeric[finite].median()) if finite.any() else None,
            }
            if target == "pressure_hpa":
                converted = numeric * 1.33322387415
                stat["outside_300_1100_hpa_if_declared_mmHg_used"] = int(
                    (finite & ~converted.between(300, 1100)).sum()
                )
                blockers.append(
                    "Confirm BP units and station-vs-sea-level pressure; mmHg header not sufficient evidence"
                )
            if name == "AT (degree)":
                blockers.append(
                    "Temperature unit 'degree' is ambiguous; obtain Celsius confirmation"
                )
            entry["sensor_audit"][target] = stat
        entry["rows_with_all_six_finite_raw_values"] = int(complete.sum())
        entry["blockers"] = blockers
        entry["approved_for_model_evaluation"] = False
        report["downloaded_samples"].append(entry)
    report["downloaded_station_rows"] = sum(
        s["rows"] for s in report["downloaded_samples"]
    )
    (root / "coverage_report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/india_station_audit"))
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if args.download:
        download(args.output)
    report = audit(args.output)
    print(
        f"Audited {report['downloaded_station_rows']:,} rows in {len(SAMPLES)} stations; "
        "coverage_report.json records missing inputs and unresolved metadata."
    )


if __name__ == "__main__":
    main()
