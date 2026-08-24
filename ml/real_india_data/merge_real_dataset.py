"""
merge_real_dataset.py - Merge the real India weather/air-quality export
(Location_information.xlsx, Weather_data.xlsx, Air_quality_information.xlsx,
Astronomical.xlsx) into a single clean CSV keyed on last_updated_epoch.

These 4 files come from a real per-location weather+AQ snapshot export
(543 Indian locations, Aug-Oct 2023) -- much closer to what an India-based
ESP32 weather station will actually see than the Szeged/Hungary
weatherHistory.csv that shipped in the repo.

Usage:
    python merge_real_dataset.py --input-dir . --output real_weather_india.csv
"""

import argparse
import os
import pandas as pd


def merge(input_dir: str, output_path: str):
    files = {
        'location': 'Location_information.xlsx',
        'weather': 'Weather_data.xlsx',
        'air_quality': 'Air_quality_information.xlsx',
        'astronomical': 'Astronomical.xlsx',
    }
    frames = {
        name: pd.read_excel(os.path.join(input_dir, filename))
        for name, filename in files.items()
    }

    key = 'last_updated_epoch'
    for name, frame in frames.items():
        if key not in frame.columns:
            raise ValueError(f"{name} input is missing required key {key!r}")
        if frame[key].duplicated().any():
            raise ValueError(f"{name} input contains duplicate {key} values")

    # Join by the epoch key rather than concatenating by row position. This
    # prevents a source export with a different ordering from pairing weather
    # values with the wrong location or air-quality record.
    df = frames['location'].copy()
    for name in ('weather', 'air_quality', 'astronomical'):
        frame = frames[name]
        overlap = (set(df.columns) & set(frame.columns)) - {key}
        if overlap:
            raise ValueError(f"Column name collision while merging {name}: {sorted(overlap)}")
        df = df.merge(frame, on=key, how='inner', validate='one_to_one')

    if df.empty:
        raise ValueError('No rows remain after joining India source files on last_updated_epoch')

    before = len(df)
    df = df.drop_duplicates()
    df = df.dropna(subset=['temperature_celsius', 'humidity', 'pressure_mb'])
    after = len(df)
    print(f"Rows: {before} -> {after} after dropping duplicates/NaN core columns")

    df = df.sort_values(['location_name', 'last_updated']).reset_index(drop=True)

    df.to_csv(output_path, index=False)
    print(f"Saved merged dataset: {output_path}  ({df.shape[0]} rows, {df.shape[1]} cols)")
    print(f"Locations: {df['location_name'].nunique()}  |  Date range: {df['last_updated'].min()} -> {df['last_updated'].max()}")
    return df


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input-dir', default='.')
    p.add_argument('--output', default='real_weather_india.csv')
    args = p.parse_args()
    merge(args.input_dir, args.output)


if __name__ == '__main__':
    main()
