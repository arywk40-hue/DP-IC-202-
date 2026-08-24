"""Convert official IMD best-track points into city-level storm events.

The output follows ``events.template.csv`` and is suitable for
``join_independent_events.py``. A city is labeled only when a verified IMD
track point for a named system is within the configured radius; basin-wide
cyclone existence is not treated as a city event.
"""

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd


def find_column(columns, patterns):
    normalized = {column: re.sub(r"[^a-z0-9]", "", str(column).lower()) for column in columns}
    for pattern in patterns:
        pattern = re.sub(r"[^a-z0-9]", "", pattern.lower())
        for column, value in normalized.items():
            if pattern in value:
                return column
    return None


def parse_time(value):
    if pd.isna(value):
        return pd.Timedelta(0)
    if isinstance(value, pd.Timestamp):
        return pd.Timedelta(hours=value.hour, minutes=value.minute)
    text = str(value).strip().replace(":", "")
    try:
        number = int(float(text))
    except ValueError:
        return pd.Timedelta(0)
    return pd.Timedelta(hours=number // 100, minutes=number % 100)


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0088
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
    return radius * 2 * np.arcsin(np.sqrt(a))


def read_tracks(workbook, years):
    sheets = pd.ExcelFile(workbook).sheet_names
    frames = []
    for year in years:
        if str(year) not in sheets:
            continue
        raw = pd.read_excel(workbook, sheet_name=str(year))
        if find_column(raw.columns, ["date"]) is None:
            raw_unheaded = pd.read_excel(workbook, sheet_name=str(year), header=None)
            header_row = None
            for index, values in raw_unheaded.iterrows():
                text = " ".join(str(value) for value in values.tolist()).lower()
                if "date" in text and ("latitude" in text or "lat" in text):
                    header_row = index
                    break
            if header_row is None:
                raise ValueError(f"Cannot locate header row in IMD sheet {year}")
            raw_unheaded.columns = raw_unheaded.iloc[header_row]
            raw = raw_unheaded.iloc[header_row + 1:].reset_index(drop=True)
        date_col = find_column(raw.columns, ["date"])
        time_col = find_column(raw.columns, ["time"])
        lat_col = find_column(raw.columns, ["latitude", "lat"])
        lon_col = find_column(raw.columns, ["longitude", "long", "lon"])
        grade_col = find_column(raw.columns, ["grade"])
        wind_col = find_column(raw.columns, ["maximumsustainedsurfacewind"])
        name_col = find_column(raw.columns, ["name"])
        serial_col = find_column(raw.columns, ["serialnumber"])
        required = [date_col, time_col, lat_col, lon_col, grade_col, wind_col, name_col, serial_col]
        if any(column is None for column in required):
            raise ValueError(f"Cannot identify required columns in IMD sheet {year}: {list(raw.columns)}")
        frame = pd.DataFrame({
            "year": int(year),
            "serial": raw[serial_col].ffill(),
            "system_name": raw[name_col].ffill().replace("-", pd.NA).ffill(),
            "date": raw[date_col].ffill(),
            "time": raw[time_col],
            "latitude": pd.to_numeric(raw[lat_col], errors="coerce"),
            "longitude": pd.to_numeric(raw[lon_col], errors="coerce"),
            "grade": raw[grade_col].astype(str).str.strip().str.upper(),
            "wind_kt": pd.to_numeric(raw[wind_col], errors="coerce"),
        })
        parsed_dates = pd.to_datetime(frame["date"], errors="coerce", format="mixed")
        parsed_dates = parsed_dates.where(parsed_dates.dt.year == int(year))
        frame["timestamp_utc"] = parsed_dates + frame["time"].map(parse_time)
        frame = frame.dropna(subset=["timestamp_utc", "latitude", "longitude", "serial"])
        frames.append(frame)
    if not frames:
        raise ValueError("No requested IMD year sheets were found")
    return pd.concat(frames, ignore_index=True)


def prepare(workbook, locations_path, output, years, radius_km, min_wind_kt):
    tracks = read_tracks(workbook, years)
    locations = pd.read_csv(locations_path)
    required = {"location_name", "latitude", "longitude"}
    if missing := required - set(locations.columns):
        raise ValueError(f"Locations CSV missing columns: {sorted(missing)}")
    # Tropical-storm strength or stronger; retain named systems even when wind
    # is absent if IMD's grade explicitly identifies a cyclonic storm class.
    storm_grade = tracks["grade"].str.contains("CS|SCS|VSCS|ESCS|SUCS", regex=True, na=False)
    tracks = tracks[storm_grade | (tracks["wind_kt"] >= min_wind_kt)].copy()
    rows = []
    coverage_start = pd.Timestamp(min(years), 1, 1, tz="UTC")
    coverage_end = pd.Timestamp(max(years), 12, 31, 23, 59, 59, tz="UTC")
    for location in locations.itertuples(index=False):
        distance = haversine_km(
            tracks["latitude"].to_numpy(), tracks["longitude"].to_numpy(),
            float(location.latitude), float(location.longitude),
        )
        nearby = tracks.loc[distance <= radius_km].copy()
        for (year, serial), event in nearby.groupby(["year", "serial"], dropna=False):
            start = event["timestamp_utc"].min()
            end = event["timestamp_utc"].max()
            name = str(event["system_name"].dropna().iloc[0]) if event["system_name"].notna().any() else "unnamed"
            event_id = f"imd_{int(year)}_{serial}_{location.location_name}"
            rows.append({
                "event_id": event_id,
                "event_type": "storm",
                "location_name": location.location_name,
                "start_utc": pd.Timestamp(start, tz="UTC").isoformat(),
                "end_utc": pd.Timestamp(end, tz="UTC").isoformat(),
                "coverage_start_utc": coverage_start.isoformat(),
                "coverage_end_utc": coverage_end.isoformat(),
                "source_name": "IMD/RSMC New Delhi Best Track",
                "source_url": "https://rsmcnewdelhi.imd.gov.in/report.php?internal_menu=MzM",
                "verified": True,
                "system_name": name,
                "radius_km": radius_km,
            })
    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError("No city-level storm events matched the radius/intensity filters")
    result.to_csv(output, index=False)
    print(f"Wrote {len(result)} city-level IMD storm events to {output}")
    print(f"Cities: {result['location_name'].nunique()} systems: {result['event_id'].nunique()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--locations", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--years", nargs="+", type=int, default=[2015, 2016, 2017, 2018, 2019, 2020])
    parser.add_argument("--radius-km", type=float, default=250.0)
    parser.add_argument("--min-wind-kt", type=float, default=34.0)
    args = parser.parse_args()
    prepare(args.workbook, args.locations, args.output, args.years, args.radius_km, args.min_wind_kt)


if __name__ == "__main__":
    main()
