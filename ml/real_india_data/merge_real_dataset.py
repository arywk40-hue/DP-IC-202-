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
    loc = pd.read_excel(os.path.join(input_dir, 'Location_information.xlsx'))
    wd = pd.read_excel(os.path.join(input_dir, 'Weather_data.xlsx'))
    aq = pd.read_excel(os.path.join(input_dir, 'Air_quality_information.xlsx'))
    astro = pd.read_excel(os.path.join(input_dir, 'Astronomical.xlsx'))

    # Sanity check: all 4 files must be row-aligned on the same epoch key
    assert (loc['last_updated_epoch'] == wd['last_updated_epoch']).all(), "Weather_data epoch mismatch"
    assert (loc['last_updated_epoch'] == aq['last_updated_epoch']).all(), "Air_quality epoch mismatch"
    assert (loc['last_updated_epoch'] == astro['last_updated_epoch']).all(), "Astronomical epoch mismatch"

    # Drop the duplicate epoch columns before concatenating
    wd = wd.drop(columns=['last_updated_epoch'])
    aq = aq.drop(columns=['last_updated_epoch'])
    astro = astro.drop(columns=['last_updated_epoch'])

    df = pd.concat([loc, wd, aq, astro], axis=1)

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
