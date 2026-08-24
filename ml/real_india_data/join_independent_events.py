"""Join independently sourced interval events to canonical weather rows.

The input event table must describe the coverage of each source. Rows outside
that coverage remain unknown rather than being silently labeled as negatives.
This prevents the common mistake of treating an event database's missing
records as proof that no hazard occurred.
"""

import argparse
import json
from pathlib import Path

import pandas as pd


EVENT_TYPES = {
    "wildfire": {"wildfire", "fire"},
    "flood": {"flood", "heavy_rain"},
    "storm": {"storm", "cyclone", "severe_weather"},
    "air_quality": {"air_quality", "pm25_exceedance"},
}


def join(weather_path, events_path, output_dir):
    weather = pd.read_csv(weather_path)
    events = pd.read_csv(events_path)
    if "last_updated" not in weather.columns and "date_utc" in weather.columns:
        weather = weather.copy()
        weather["last_updated"] = weather["date_utc"]
    weather_required = {"location_name", "last_updated"}
    event_required = {
        "event_id", "event_type", "location_name", "start_utc", "end_utc",
        "source_name", "source_url", "verified",
        "coverage_start_utc", "coverage_end_utc",
    }
    if missing := weather_required - set(weather.columns):
        raise ValueError(f"Weather input missing columns: {sorted(missing)}")
    if missing := event_required - set(events.columns):
        raise ValueError(f"Event input missing columns: {sorted(missing)}")
    if events["event_id"].duplicated().any():
        raise ValueError("event_id must be unique")
    verified = events["verified"].astype(str).str.strip().str.lower().isin({"1", "true", "yes"})
    if not verified.all():
        raise ValueError("Unverified event rows cannot be used for hazard labels")

    weather = weather.copy()
    weather["timestamp_utc"] = pd.to_datetime(weather["last_updated"], utc=True, errors="raise")
    events = events.copy()
    events["start_utc"] = pd.to_datetime(events["start_utc"], utc=True, errors="raise")
    events["end_utc"] = pd.to_datetime(events["end_utc"], utc=True, errors="raise")
    events["coverage_start_utc"] = pd.to_datetime(
        events["coverage_start_utc"], utc=True, errors="raise"
    )
    events["coverage_end_utc"] = pd.to_datetime(
        events["coverage_end_utc"], utc=True, errors="raise"
    )
    if (events["end_utc"] < events["start_utc"]).any():
        raise ValueError("Event end_utc cannot precede start_utc")
    if (events["coverage_end_utc"] < events["coverage_start_utc"]).any():
        raise ValueError("coverage_end_utc cannot precede coverage_start_utc")
    if ((events["start_utc"] < events["coverage_start_utc"]) |
            (events["end_utc"] > events["coverage_end_utc"])).any():
        raise ValueError("Events must fall within their source coverage interval")
    if events[["source_name", "source_url"]].isna().any().any():
        raise ValueError("Every event requires source_name and source_url")
    unknown_types = set(events["event_type"]) - set().union(*EVENT_TYPES.values())
    if unknown_types:
        raise ValueError(f"Unsupported event_type values: {sorted(unknown_types)}")

    output = weather.copy()
    for hazard in EVENT_TYPES:
        output[hazard] = pd.Series(pd.NA, index=output.index, dtype="Int8")
        output[f"{hazard}_label_source"] = pd.NA
        output[f"{hazard}_label_event_id"] = pd.NA

    # Build per-hazard interval joins. The number of weather rows is typically
    # much larger than the event table, so this avoids a full Cartesian join.
    for hazard, accepted_types in EVENT_TYPES.items():
        selected = events[events["event_type"].isin(accepted_types)]
        for location, indices in output.groupby("location_name").groups.items():
            local_events = selected[selected["location_name"] == location]
            if local_events.empty:
                continue
            local_times = output.loc[indices, "timestamp_utc"]
            covered = pd.Series(False, index=local_times.index)
            for coverage in local_events.itertuples(index=False):
                covered |= local_times.between(
                    coverage.coverage_start_utc,
                    coverage.coverage_end_utc,
                    inclusive="both",
                )
            output.loc[covered.index[covered], hazard] = 0
            for event in local_events.itertuples(index=False):
                matched = local_times.between(event.start_utc, event.end_utc, inclusive="both")
                matched_indices = local_times.index[matched]
                if len(matched_indices):
                    existing = output.loc[matched_indices, hazard] == 1
                    if existing.any():
                        raise ValueError(
                            f"Overlapping {hazard} events at {location}; resolve before training"
                        )
                    output.loc[matched_indices, hazard] = 1
                    output.loc[matched_indices, f"{hazard}_label_source"] = event.source_name
                    output.loc[matched_indices, f"{hazard}_label_event_id"] = event.event_id

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_dir / "weather_with_independent_labels.csv", index=False)
    summary = {
        "weather_rows": int(len(output)),
        "event_rows": int(len(events)),
        "hazards": {
            hazard: {
                "positive_rows": int((output[hazard] == 1).sum()),
                "labeled_rows": int(output[hazard].notna().sum()),
                "unknown_rows": int(output[hazard].isna().sum()),
            }
            for hazard in EVENT_TYPES
        },
        "negative_labels_not_inferred": True,
        "event_sources": sorted(events["source_name"].unique().tolist()),
    }
    with (output_dir / "label_join_summary.json").open("w") as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weather", required=True)
    parser.add_argument("--events", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    join(args.weather, args.events, args.output)


if __name__ == "__main__":
    main()
