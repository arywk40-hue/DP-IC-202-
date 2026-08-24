"""Extract a small, provenance-preserving IndiaWeatherBench HDF5 slice.

This adapter intentionally produces weather context, not hazard labels. Event
labels must be joined from an independent source before hazard training.
IndiaWeatherBench is distributed as split HDF5 files whose filenames normally
contain timestamps such as ``20010101_00.h5``.
"""

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


TIMESTAMP_RE = re.compile(r"(\d{8})[_-](\d{2})")
DEFAULT_BOUNDS = {"lat_min": 6.0, "lat_max": 36.72, "lon_min": 66.6, "lon_max": 97.25}


def parse_timestamp(path):
    match = TIMESTAMP_RE.search(path.name)
    if not match:
        raise ValueError(f"Cannot parse YYYYMMDD_HH timestamp from {path.name}")
    return datetime.strptime(
        f"{match.group(1)}_{match.group(2)}", "%Y%m%d_%H"
    ).replace(tzinfo=timezone.utc)


def dataset_items(group, prefix=""):
    """Yield (path, dataset) for every HDF5 dataset, including nested groups."""
    for name, value in group.items():
        path = f"{prefix}/{name}" if prefix else name
        if hasattr(value, "shape") and hasattr(value, "__getitem__"):
            yield path, value
        elif hasattr(value, "items"):
            yield from dataset_items(value, path)


def find_dataset(datasets, aliases):
    normalized = {key.lower().replace("/", "_"): (key, value)
                  for key, value in datasets.items()}
    for alias in aliases:
        alias = alias.lower().replace("/", "_")
        for key, value in normalized.items():
            if key == alias or key.endswith("_" + alias):
                return value
    return None


def scalar_grid(dataset, lat_index, lon_index):
    """Return a 2-D field, accepting optional leading singleton dimensions."""
    values = np.asarray(dataset)
    while values.ndim > 2 and values.shape[0] == 1:
        values = values[0]
    if values.ndim != 2:
        raise ValueError(f"Expected a 2-D spatial field, got shape {values.shape}")
    return values[lat_index, lon_index]


def nearest_indices(locations, shape, bounds):
    latitudes = np.linspace(bounds["lat_max"], bounds["lat_min"], shape[0])
    longitudes = np.linspace(bounds["lon_min"], bounds["lon_max"], shape[1])
    result = []
    for location in locations:
        lat = float(location["latitude"])
        lon = float(location["longitude"])
        if not (bounds["lat_min"] <= lat <= bounds["lat_max"] and
                bounds["lon_min"] <= lon <= bounds["lon_max"]):
            raise ValueError(f"{location['location_name']} is outside IndiaWeatherBench bounds")
        result.append((
            int(np.abs(latitudes - lat).argmin()),
            int(np.abs(longitudes - lon).argmin()),
        ))
    return result


def convert_temperature(value, units):
    units = str(units or "").lower()
    return float(value - 273.15) if units in {"k", "kelvin"} else float(value)


def convert_pressure(value, units):
    units = str(units or "").lower()
    return float(value * 100.0) if units in {"hpa", "mb", "millibar"} else float(value)


def unit_of(dataset, default="unknown"):
    if dataset is None:
        return default
    for key in ("units", "unit"):
        if key in dataset.attrs:
            raw = dataset.attrs[key]
            return raw.decode() if isinstance(raw, bytes) else str(raw)
    return default


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def extract(input_dir, locations_path, output_dir, max_files=None, bounds=None):
    try:
        import h5py
    except ImportError as exc:
        raise SystemExit("Install h5py to read IndiaWeatherBench HDF5 files") from exc

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with Path(locations_path).open(newline="") as handle:
        locations = list(csv.DictReader(handle))
    required = {"location_name", "latitude", "longitude"}
    if not locations or not required.issubset(locations[0]):
        raise ValueError(f"locations CSV must contain {sorted(required)}")
    files = sorted(input_dir.rglob("*.h5"))
    if max_files:
        files = files[:max_files]
    if not files:
        raise FileNotFoundError(f"No .h5 files found below {input_dir}")
    bounds = bounds or DEFAULT_BOUNDS

    rows = []
    selected_units = {}
    grid_shape = None
    for path in files:
        timestamp = parse_timestamp(path)
        with h5py.File(path, "r") as handle:
            datasets = dict(dataset_items(handle))
            fields = {
                "temperature_k": find_dataset(datasets, ["TMP", "temperature"]),
                "wind_u_ms": find_dataset(datasets, ["UGRD", "u_wind"]),
                "wind_v_ms": find_dataset(datasets, ["VGRD", "v_wind"]),
                "precipitation_mm": find_dataset(datasets, ["APCP", "precip"]),
                "pressure_pa": find_dataset(datasets, ["PRMSL", "mslp", "pressure"]),
                "cloud_cover": find_dataset(datasets, ["TCDCRO", "cloud"]),
                "terrain_height_m": find_dataset(datasets, ["MTERH", "terrain"]),
                "land_cover": find_dataset(datasets, ["LAND", "land"]),
            }
            missing = [name for name, field in fields.items() if field is None]
            if missing:
                raise ValueError(f"{path.name} is missing required fields: {missing}")
            shape = tuple(fields["temperature_k"].shape[-2:])
            if grid_shape is None:
                grid_shape = shape
            if shape != grid_shape:
                raise ValueError(f"Grid shape changed from {grid_shape} to {shape} in {path.name}")
            indices = nearest_indices(locations, shape, bounds)
            for name, field in fields.items():
                selected_units[name] = unit_of(field)
            for location, (lat_index, lon_index) in zip(locations, indices):
                row = {
                    "location_name": location["location_name"],
                    "latitude": float(location["latitude"]),
                    "longitude": float(location["longitude"]),
                    "last_updated": timestamp.isoformat(),
                    "last_updated_epoch": int(timestamp.timestamp()),
                    "temperature_celsius": convert_temperature(
                        scalar_grid(fields["temperature_k"], lat_index, lon_index),
                        unit_of(fields["temperature_k"], "K"),
                    ),
                    "wind_u_ms": float(scalar_grid(fields["wind_u_ms"], lat_index, lon_index)),
                    "wind_v_ms": float(scalar_grid(fields["wind_v_ms"], lat_index, lon_index)),
                    "precipitation_mm": float(scalar_grid(fields["precipitation_mm"], lat_index, lon_index)),
                    "pressure_pa": convert_pressure(
                        scalar_grid(fields["pressure_pa"], lat_index, lon_index),
                        unit_of(fields["pressure_pa"], "Pa"),
                    ),
                    "cloud_cover": float(scalar_grid(fields["cloud_cover"], lat_index, lon_index)),
                    "terrain_height_m": float(scalar_grid(fields["terrain_height_m"], lat_index, lon_index)),
                    "land_cover": float(scalar_grid(fields["land_cover"], lat_index, lon_index)),
                    "weather_source_file": path.name,
                }
                rows.append(row)

    output_csv = output_dir / "weather_context.csv"
    fieldnames = list(rows[0])
    with output_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "source_name": "IndiaWeatherBench / IMDAA",
        "source_url": "https://huggingface.co/datasets/tungnd/IndiaWeatherBench",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "coverage_start_utc": min(row["last_updated"] for row in rows),
        "coverage_end_utc": max(row["last_updated"] for row in rows),
        "spatial_extent": bounds,
        "grid_shape": grid_shape,
        "files": len(files),
        "locations": len(locations),
        "variables": fieldnames[5:-1],
        "units_seen": selected_units,
        "license": "CC BY-NC-SA 4.0",
        "processing_script": "ml/real_india_data/prepare_indiaweatherbench.py",
        "synthetic_fields": [],
        "label_provenance": "No hazard labels generated; join independent event records before hazard training.",
        "input_file_sha256": {str(path): sha256_file(path) for path in files},
    }
    with (output_dir / "manifest.json").open("w") as handle:
        json.dump(manifest, handle, indent=2)
    print(f"Wrote {len(rows):,} rows to {output_csv}")
    print(f"Wrote provenance manifest to {output_dir / 'manifest.json'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--locations", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-files", type=int, default=None)
    args = parser.parse_args()
    extract(args.input_dir, args.locations, args.output, args.max_files)


if __name__ == "__main__":
    main()
