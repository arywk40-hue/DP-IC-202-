"""
prepare_dataset.py - Prepare Real Weather Data for Training

Processes raw weatherHistory.csv into features.csv and labels.csv
for XGBoost training. NO synthetic data generation.

Usage:
    python prepare_dataset.py --input dataset/weatherHistory.csv --output data/
"""

import pandas as pd
import numpy as np
import argparse
import os
import json
from pathlib import Path


# ============================================
# FEATURE DEFINITIONS (must match firmware)
# ============================================

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


# Column mapping from raw CSV to internal names
COLUMN_MAP = {
    'temperature': 'temp_current',
    'humidity': 'humidity_current',
    'pressure': 'pressure_current',
    'wind_speed': 'wind_speed_current',
    'wind_kph': 'wind_speed_current',
    'pm25': 'pm25_current',
    'pm2_5': 'pm25_current',
    'co2': 'co2_current',
    'lightning_distance': 'lightning_dist_current',
    'lightning_dist': 'lightning_dist_current',
}


def load_raw_data(csv_path: str) -> pd.DataFrame:
    """Load and clean raw weather CSV."""
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} rows from {csv_path}")
    print(f"Columns: {list(df.columns)}")

    # Standardize column names
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    # Map known columns
    for old, new in COLUMN_MAP.items():
        if old in df.columns:
            df = df.rename(columns={old: new})

    return df


def compute_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all 14 features from base sensors."""
    out = df.copy()

    # Ensure required base columns exist
    required = ['temp_current', 'humidity_current', 'pressure_current',
                'wind_speed_current', 'pm25_current', 'co2_current',
                'lightning_dist_current']

    for col in required:
        if col not in out.columns:
            raise ValueError(f"Required column '{col}' not found in data")

    # Derived features
    out['temp_humidity_ratio'] = out['temp_current'] / out['humidity_current'].clip(lower=1)

    # Pressure trend (6-sample linear slope)
    window = 6
    out['pressure_trend'] = out['pressure_current'].rolling(window).apply(
        lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) == window else 0,
        raw=True
    ).fillna(0))

    # Heat index (simplified)
    out['heat_index'] = out['temp_current'] + 0.5 * out['humidity_current']

    # Dew point (Magnus approximation)
    out['dew_point'] = out['temp_current'] - (100 - out['humidity_current']) / 5

    # Fire risk index
    fire_risk = 0.0
    fire_risk += (out['temp_current'] > 30).astype(float) * 0.25
    fire_risk += (out['humidity_current'] < 35).astype(float) * 0.25
    fire_risk += (out['wind_speed_current'] > 5).astype(float) * 0.15
    fire_risk += (out['pm25_current'] > 40).astype(float) * 0.35
    out['fire_risk_index'] = fire_risk.clip(0, 1)

    # Flood risk index
    flood_risk = 0.0
    flood_risk += (out['pressure_current'] < 1005).astype(float) * 0.30
    flood_risk += (out['humidity_current'] > 85).astype(float) * 0.30
    flood_risk += (out['wind_speed_current'] > 8).astype(float) * 0.20
    flood_risk += (out['pressure_current'] < 1000).astype(float) * 0.20
    out['flood_risk_index'] = flood_risk.clip(0, 1)

    # Lightning threat
    out['lightning_threat'] = (40 - out['lightning_dist_current']).clip(lower=0) / 40

    return out


def generate_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Generate binary hazard labels from features."""
    labels = pd.DataFrame(index=df.index)

    labels['wildfire'] = (
        (df['temp_current'] > 30) &
        (df['humidity_current'] < 35) &
        (df['wind_speed_current'] > 5) &
        (df['pm25_current'] > 40)
    ).astype(int)

    labels['flood'] = (
        (df['pressure_current'] < 1000) &
        (df['humidity_current'] > 85) &
        (df['wind_speed_current'] > 8)
    ).astype(int)

    labels['storm'] = (
        (df['lightning_dist_current'] < 15) &
        (df['pressure_current'] < 1005)
    ).astype(int)

    labels['air_quality'] = (
        (df['pm25_current'] > 75) |
        (df['co2_current'] > 550)
    ).astype(int)

    return labels


def prepare_dataset(input_path: str, output_dir: str):
    """Full dataset preparation pipeline."""
    os.makedirs(output_dir, exist_ok=True)

    # Load raw data
    df = load_raw_data(input_path)

    # Compute derived features
    df = compute_derived_features(df)

    # Generate labels
    labels = generate_labels(df)

    # Select feature columns
    X = df[FEATURE_NAMES]
    y = labels[HAZARD_CLASSES]

    print(f"\nFeature matrix shape: {X.shape}")
    print(f"Label matrix shape: {y.shape}")
    print(f"\nLabel distribution:")
    for c in HAZARD_CLASSES:
        pos = y[c].sum()
        print(f"  {c}: {pos}/{len(y)} ({100*pos/len(y):.1f}%)")

    # Save
    X.to_csv(os.path.join(output_dir, 'features.csv'), index=False)
    y.to_csv(os.path.join(output_dir, 'labels.csv'), index=False)
    print(f"\nSaved to {output_dir}/")

    # Save metadata
    metadata = {
        'feature_names': FEATURE_NAMES,
        'label_names': HAZARD_CLASSES,
        'num_features': len(FEATURE_NAMES),
        'num_classes': len(HAZARD_CLASSES),
        'num_samples': len(X),
        'label_distribution': {c: int(y[c].sum()) for c in HAZARD_CLASSES},
    }
    with open(os.path.join(output_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)

    # Also save combined for inspection
    pd.concat([X, y], axis=1).to_csv(os.path.join(output_dir, 'dataset.csv'), index=False)

    return X, y


def main():
    parser = argparse.ArgumentParser(description='Prepare real weather data for training')
    parser.add_argument('--input', type=str, required=True, help='Input weather CSV path')
    parser.add_argument('--output', type=str, default='./data/', help='Output directory')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        return 1

    prepare_dataset(args.input, args.output)
    print("\nDataset preparation complete!")
    return 0


if __name__ == '__main__':
    exit(main())