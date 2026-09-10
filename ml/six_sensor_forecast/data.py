"""Download and adapt the complete UCI 501 archive without inventing events."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS

SOURCE_URL = "https://archive.ics.uci.edu/static/public/501/beijing+multi+site+air+quality+data.zip"
SOURCE_SHA256 = "b04da438b2f331ac0ffd45aebdfec0d20d2367feb5f6948c4b1f7ce1191e33c4"
SCHEMA = "indra_hourly_forecast_v1"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def adapt_archive(archive: Path) -> pd.DataFrame:
    """Read only the 12 original station tables, never ZIP paths on disk."""
    with zipfile.ZipFile(archive) as outer:
        payload = outer.read("PRSA2017_Data_20130301-20170228.zip")
    with zipfile.ZipFile(io.BytesIO(payload)) as inner:
        names = sorted(n for n in inner.namelist() if n.endswith(".csv"))
        if len(names) != 12:
            raise ValueError("Expected exactly 12 UCI station tables")
        raw = pd.concat([pd.read_csv(inner.open(n)) for n in names], ignore_index=True)
    # Original hours are local Beijing time, with no DST during this period.
    timestamps = pd.to_datetime(raw[["year", "month", "day", "hour"]])
    timestamps = timestamps.dt.tz_localize("Asia/Shanghai").dt.tz_convert("UTC")
    humidity = 100 * np.exp(
        17.625 * raw.DEWP / (243.04 + raw.DEWP)
        - 17.625 * raw.TEMP / (243.04 + raw.TEMP)
    )
    result = pd.DataFrame(
        {
            "timestamp_utc": timestamps,
            "location_id": raw.station,
            "temperature_c": raw.TEMP,
            "relative_humidity_pct": humidity,
            "pressure_hpa": raw.PRES,
            "pm25_ug_m3": raw["PM2.5"],
            "pm10_ug_m3": raw.PM10,
            "wind_speed_mps": raw.WSPM,
        }
    )
    for column, (lower, upper) in PHYSICAL_RANGES.items():
        result[column] = result[column].where(result[column].between(lower, upper))
    if result.duplicated(["location_id", "timestamp_utc"]).any():
        raise ValueError("Duplicate station-hour in source archive")
    return result.sort_values(["location_id", "timestamp_utc"]).reset_index(drop=True)


def prepare(output: Path, archive: Path | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "source.zip"
    if archive is not None and archive.resolve() != destination.resolve():
        shutil.copyfile(archive, destination)
    elif not destination.exists():
        partial = destination.with_suffix(".partial")
        with (
            urllib.request.urlopen(SOURCE_URL, timeout=60) as response,
            partial.open("wb") as stream,
        ):
            shutil.copyfileobj(response, stream)
        partial.replace(destination)
    digest = sha256(destination)
    if digest != SOURCE_SHA256:
        raise ValueError(
            "UCI archive checksum changed; inspect the source before accepting it"
        )
    frame = adapt_archive(destination)
    if len(frame) != 420768 or frame.location_id.nunique() != 12:
        raise ValueError("Incomplete UCI dataset")
    observations = output / "observations.csv"
    frame.to_csv(observations, index=False)
    manifest = {
        "schema_version": SCHEMA,
        "source_name": "UCI Beijing Multi-Site Air Quality (501)",
        "source_url": SOURCE_URL,
        "doi": "https://doi.org/10.24432/C5RK5G",
        "attribution": "Chen, S. (2017). Beijing Multi-Site Air Quality. UCI Machine Learning Repository.",
        "license": "CC BY 4.0",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive_sha256": digest,
        "observations_sha256": sha256(observations),
        "rows": len(frame),
        "locations": sorted(frame.location_id.unique().tolist()),
        "coverage_start_utc": frame.timestamp_utc.min().isoformat(),
        "coverage_end_utc": frame.timestamp_utc.max().isoformat(),
        "sensor_columns": RAW_SENSOR_COLUMNS,
        "missing_measurements": frame[RAW_SENSOR_COLUMNS].isna().sum().to_dict(),
        "relative_humidity": "Magnus approximation derived from observed temperature and dew point; not directly measured RH",
        "weather_alignment": "UCI source matches air-quality sites to nearest meteorological station",
        "timestamp_policy": "Source local hours interpreted as Asia/Shanghai and converted to UTC",
        "label_provenance": "Exact future station measurements; no hazard labels or synthetic sensor values",
        "geographic_limit": "Beijing, China; external pretraining/benchmark only, not India field validation",
    }
    (output / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("data/uci_beijing_air_quality")
    )
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output, args.archive), indent=2))


if __name__ == "__main__":
    main()
