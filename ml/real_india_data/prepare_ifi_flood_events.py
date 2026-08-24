"""Convert explicit city/district matches from the IFI flood inventory to events.

State-only inventory rows are intentionally excluded.  A match is retained
only when a city (or documented district alias) appears as a token in the
inventory's Location or Districts field. Overlapping matches for one city are
merged so the independent-event joiner can apply them without ambiguity.
"""

import argparse
import json
import re
from pathlib import Path

import pandas as pd


SOURCE_NAME = "India Flood Inventory-Impacts / IMD"
SOURCE_URL = "https://zenodo.org/records/11275211"

# Only aliases that are common in the inventory or are unambiguous historical
# names.  Cities without an exact district token remain unlabeled.
ALIASES = {
    "Allahabad": ["allahabad", "prayagraj"],
    "Bengaluru": ["bengaluru", "bangalore"],
    "Gurugram": ["gurugram", "gurgaon"],
    "Kozhikode": ["kozhikode", "calicut"],
    "Mangalore": ["mangalore", "dakshina kannada"],
    "Mysuru": ["mysuru", "mysore"],
    "Thiruvananthapuram": ["thiruvananthapuram", "trivandrum"],
    "Vadodara": ["vadodara", "baroda"],
    "Visakhapatnam": ["visakhapatnam", "vishakhapatnam"],
}


def normalize(value):
    value = str(value).lower().replace("(", ",").replace(")", ",")
    return re.sub(r"\s+", " ", value).strip()


def tokens(value):
    return {normalize(part) for part in str(value).split(",") if normalize(part)}


def prepare(input_path, locations_path, output_path):
    inventory = pd.read_csv(input_path, encoding="utf-8-sig")
    locations = pd.read_csv(locations_path)
    required = {"UEI", "Start Date", "End Date", "Location", "Districts"}
    if missing := required - set(inventory.columns):
        raise ValueError(f"Inventory missing columns: {sorted(missing)}")
    if "location_name" not in locations:
        raise ValueError("Locations file must contain location_name")

    inventory["start"] = pd.to_datetime(inventory["Start Date"], dayfirst=True, errors="coerce")
    inventory["end"] = pd.to_datetime(inventory["End Date"], dayfirst=True, errors="coerce")
    inventory = inventory.dropna(subset=["start", "end"])
    invalid_intervals = inventory["end"] < inventory["start"]
    inventory = inventory.loc[~invalid_intervals].copy()
    rows = []
    for city in locations["location_name"].dropna().unique():
        aliases = set(ALIASES.get(city, [city]))
        aliases = {normalize(alias) for alias in aliases}
        for event in inventory.itertuples(index=False):
            available = tokens(getattr(event, "Location")) | tokens(getattr(event, "Districts"))
            matched = sorted(aliases & available)
            if not matched:
                continue
            rows.append({
                "location_name": city,
                "start_utc": event.start.strftime("%Y-%m-%dT00:00:00Z"),
                "end_utc": event.end.strftime("%Y-%m-%dT23:59:59Z"),
                "source_event_id": event.UEI,
                "matched_token": matched[0],
            })

    matched = pd.DataFrame(rows)
    if matched.empty:
        raise ValueError("No explicit city/district matches found")
    matched["start"] = pd.to_datetime(matched["start_utc"], utc=True)
    matched["end"] = pd.to_datetime(matched["end_utc"], utc=True)
    merged_rows = []
    for city, group in matched.sort_values(["location_name", "start"]).groupby("location_name"):
        current_start = current_end = None
        source_ids = []
        for event in group.itertuples(index=False):
            if current_start is None or event.start > current_end + pd.Timedelta(days=1):
                if current_start is not None:
                    merged_rows.append((city, current_start, current_end, source_ids))
                current_start, current_end, source_ids = event.start, event.end, [event.source_event_id]
            else:
                current_end = max(current_end, event.end)
                source_ids.append(event.source_event_id)
        if current_start is not None:
            merged_rows.append((city, current_start, current_end, source_ids))

    output = pd.DataFrame([
        {
            "event_id": f"ifi_{city}_{index:04d}",
            "event_type": "flood",
            "location_name": city,
            "start_utc": start.isoformat(),
            "end_utc": end.isoformat(),
            "coverage_start_utc": "1967-01-01T00:00:00Z",
            "coverage_end_utc": "2023-12-31T23:59:59Z",
            "source_name": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "verified": True,
            "inventory_event_ids": ";".join(ids),
            "spatial_match_policy": "explicit_location_or_district_token",
        }
        for index, (city, start, end, ids) in enumerate(merged_rows, start=1)
    ])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    summary = {
        "source_name": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "inventory_rows": int(len(inventory)),
        "invalid_intervals_excluded": int(invalid_intervals.sum()),
        "matched_raw_city_events": int(len(matched)),
        "merged_city_intervals": int(len(output)),
        "cities": sorted(output.location_name.unique().tolist()),
        "state_only_rows_excluded": True,
        "spatial_match_policy": "explicit_location_or_district_token",
    }
    with output_path.with_suffix(".manifest.json").open("w") as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--locations", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    prepare(args.input, args.locations, args.output)


if __name__ == "__main__":
    main()
