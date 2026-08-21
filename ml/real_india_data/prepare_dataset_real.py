"""
prepare_dataset_real.py - Prepare REAL India weather+AQ data for training

Drop-in replacement for prepare_dataset.py that consumes the merged
real_weather_india.csv (built by merge_real_dataset.py from the 4 uploaded
xlsx exports) instead of the Szeged/Hungary weatherHistory.csv.

Output feature schema is IDENTICAL to the original prepare_dataset.py
(same 14 FEATURE_NAMES, same 4 HAZARD_CLASSES) so it stays a drop-in
replacement for train_model.py / convert_to_c.py / the firmware inference
code -- no firmware or feature-count changes needed.

What's REAL vs SYNTHETIC in this version:
  - temp_current, humidity_current, pressure_current, wind_speed_current,
    pm25_current  -> REAL (from Weather_data.xlsx / Air_quality_information.xlsx)
  - co2_current, lightning_dist_current -> STILL SYNTHETIC
    (no CO2 sensor or lightning-strike data exists in the uploaded export;
    only CO, O3, NO2, SO2, PM2.5, PM10 are present as air-quality columns).
    These two are generated the same correlated way as the original script,
    clearly flagged below so it's obvious what to replace once you have
    real SCD41/AS3935 sensor logs.

Usage:
    python prepare_dataset_real.py --input real_weather_india.csv --output data/
"""

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

FEATURE_NAMES = [
    'temp_current',
    'humidity_current',
    'pressure_current',
    'wind_speed_current',
    'pm25_current',
    'co2_current',
    'lightning_dist_current',
    'temp_humidity_ratio',
    'pressure_trend',
    'heat_index',
    'dew_point',
    'fire_risk_index',
    'flood_risk_index',
    'lightning_threat',
]

HAZARD_CLASSES = ['wildfire', 'flood', 'storm', 'air_quality']


def load_raw_data(csv_path: str) -> pd.DataFrame:
    """Load the merged real India CSV and map it onto the internal schema."""
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} rows from {csv_path}")

    out = pd.DataFrame(index=df.index)
    out['location_name'] = df['location_name']
    out['last_updated'] = pd.to_datetime(df['last_updated'])

    # Real sensor-equivalent columns
    out['temp_current'] = df['temperature_celsius']
    out['humidity_current'] = df['humidity'] / 100.0          # match 0-1 scale used elsewhere
    out['pressure_current'] = df['pressure_mb']
    out['wind_speed_current'] = df['wind_kph']
    out['pm25_current'] = df['air_quality_PM2.5']

    # Extra real AQ columns kept around for reference / future feature work
    out['pm10_real'] = df['air_quality_PM10']
    out['co_real'] = df['air_quality_Carbon_Monoxide']
    out['ozone_real'] = df['air_quality_Ozone']
    out['no2_real'] = df['air_quality_Nitrogen_dioxide']
    out['so2_real'] = df['air_quality_Sulphur_dioxide']

    # Clean bad pressure values (0 / unrealistic == invalid), same rule as original script
    out.loc[out['pressure_current'] <= 900, 'pressure_current'] = np.nan
    out['pressure_current'] = (
        out.groupby('location_name')['pressure_current']
        .transform(lambda s: s.interpolate().bfill().ffill())
    )

    # Drop any rows still missing core fields after cleaning
    before = len(out)
    out = out.dropna(subset=['temp_current', 'humidity_current', 'pressure_current', 'wind_speed_current', 'pm25_current'])
    print(f"Dropped {before - len(out)} rows with unrecoverable missing values")

    return out.reset_index(drop=True)


def add_synthetic_sensors(df: pd.DataFrame) -> pd.DataFrame:
    """Fill in the two sensors this export has no real data for: CO2 and lightning.

    Kept correlated with real weather the same way the original script did,
    so the label logic downstream still behaves sensibly. Replace this with
    real SCD41 / AS3935 logs as soon as you have field data.
    """
    out = df.copy()
    n = len(out)
    rng = np.random.default_rng(42)

    base_co2 = 400 + 50 * (out['temp_current'] / 30)
    wind_effect_co2 = -out['wind_speed_current'] * 2
    noise_co2 = rng.normal(0, 20, n)
    out['co2_current'] = (base_co2 + wind_effect_co2 + noise_co2).clip(350, 800)

    storm_prob = ((out['pressure_current'] < 1005) & (out['humidity_current'] > 0.70)).astype(float)
    is_storm = rng.random(n) < (0.05 + 0.15 * storm_prob)
    lightning_dist = rng.exponential(scale=50, size=n)
    lightning_dist = np.where(is_storm, rng.exponential(scale=10, size=n), lightning_dist)
    out['lightning_dist_current'] = lightning_dist.clip(0, 100)

    return out


def compute_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the 14 features. Pressure trend is now computed PER LOCATION
    (grouped + sorted by time) since this dataset covers 543 different places --
    without grouping, a naive rolling slope would blend readings from
    unrelated cities and produce garbage trend values."""
    out = df.copy()

    humidity_pct = out['humidity_current'] * 100

    out['temp_humidity_ratio'] = out['temp_current'] / out['humidity_current'].clip(lower=0.01)

    window = 6
    out = out.sort_values(['location_name', 'last_updated'])
    out['pressure_trend'] = (
        out.groupby('location_name')['pressure_current']
        .transform(lambda s: s.rolling(window).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) == window else 0,
            raw=True
        ).fillna(0))
    )

    out['heat_index'] = out['temp_current'] + 0.5 * humidity_pct
    out['dew_point'] = out['temp_current'] - (100 - humidity_pct) / 5

    fire_risk = 0.0
    fire_risk += (out['temp_current'] > 30).astype(float) * 0.25
    fire_risk += (humidity_pct < 35).astype(float) * 0.25
    fire_risk += (out['wind_speed_current'] > 5).astype(float) * 0.15
    fire_risk += (out['pm25_current'] > 40).astype(float) * 0.35
    out['fire_risk_index'] = fire_risk.clip(0, 1)

    flood_risk = 0.0
    flood_risk += (out['pressure_current'] < 1005).astype(float) * 0.30
    flood_risk += (humidity_pct > 85).astype(float) * 0.30
    flood_risk += (out['wind_speed_current'] > 8).astype(float) * 0.20
    flood_risk += (out['pressure_current'] < 1000).astype(float) * 0.20
    out['flood_risk_index'] = flood_risk.clip(0, 1)

    out['lightning_threat'] = (40 - out['lightning_dist_current']).clip(lower=0) / 40

    return out.reset_index(drop=True)


def generate_labels(df: pd.DataFrame) -> pd.DataFrame:
    labels = pd.DataFrame(index=df.index)

    labels['wildfire'] = (
        (df['temp_current'] > 28) &
        (df['humidity_current'] < 0.55) &
        (df['wind_speed_current'] > 6) &
        (df['pm25_current'] > 35)
    ).astype(int)

    labels['flood'] = (
        (df['pressure_current'] < 1005) &
        (df['humidity_current'] > 0.80) &
        (df['wind_speed_current'] > 10)
    ).astype(int)

    labels['storm'] = (
        (df['lightning_dist_current'] < 40) &
        (df['pressure_current'] < 1008)
    ).astype(int)

    labels['air_quality'] = (
        (df['pm25_current'] > 60) |
        (df['pm10_real'] > 100) |
        (df['co2_current'] > 480)
    ).astype(int)

    return labels


def prepare_dataset(input_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    df = load_raw_data(input_path)
    df = add_synthetic_sensors(df)
    df = compute_derived_features(df)
    labels = generate_labels(df)

    X = df[FEATURE_NAMES]
    y = labels[HAZARD_CLASSES]

    print(f"\nFeature matrix shape: {X.shape}")
    print(f"Label matrix shape: {y.shape}")
    print("\nLabel distribution:")
    for c in HAZARD_CLASSES:
        pos = y[c].sum()
        print(f"  {c}: {pos}/{len(y)} ({100*pos/len(y):.1f}%)")

    X.to_csv(os.path.join(output_dir, 'features.csv'), index=False)
    y.to_csv(os.path.join(output_dir, 'labels.csv'), index=False)
    print(f"\nSaved to {output_dir}/")

    metadata = {
        'source': 'real_weather_india.csv (543 India locations, Aug-Oct 2023)',
        'feature_names': FEATURE_NAMES,
        'label_names': HAZARD_CLASSES,
        'num_features': len(FEATURE_NAMES),
        'num_classes': len(HAZARD_CLASSES),
        'num_samples': len(X),
        'label_distribution': {c: int(y[c].sum()) for c in HAZARD_CLASSES},
        'synthetic_fields': ['co2_current', 'lightning_dist_current'],
        'real_fields': ['temp_current', 'humidity_current', 'pressure_current', 'wind_speed_current', 'pm25_current'],
    }
    with open(os.path.join(output_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)

    pd.concat([X, y], axis=1).to_csv(os.path.join(output_dir, 'dataset.csv'), index=False)
    return X, y


def main():
    parser = argparse.ArgumentParser(description='Prepare real India weather data for training')
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, default='./data/')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        return 1

    prepare_dataset(args.input, args.output)
    print("\nDataset preparation complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
