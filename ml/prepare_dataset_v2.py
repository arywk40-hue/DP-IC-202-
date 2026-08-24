"""
prepare_dataset_v2.py - Improved Dataset Preparation for Edge AI Weather Station

Key improvements over v1:
  1. Chronological ordering - data sorted by timestamp before any split,
     eliminating seasonal leakage that random shuffle causes.
  2. Cyclical time features - hour_sin/cos (24-h) and doy_sin/cos (365-day)
     encode diurnal and seasonal cycles continuously.
  3. Physical interaction features:
       pressure_drop_rate  - 6-h rolling pressure slope; sharp negative = storm onset
       smoke_transport     - PM2.5 x wind_speed; high both = transported fire smoke
       heat_stress         - temp - apparent_temp; proxy for evaporative/wind load
       visibility_rain     - visibility x precip_binary (rain intensity proxy)
  4. 22 features total (was 14).

Usage:
    python prepare_dataset_v2.py --input dataset/weatherHistory.csv --output data_v2/
"""

import pandas as pd
import numpy as np
import argparse
import os
import json
from pathlib import Path


# ============================================
# FEATURE DEFINITIONS (must match train_model_v2.py)
# ============================================

FEATURE_NAMES = [
    # Raw sensors (7)
    'temp_current',
    'humidity_current',
    'pressure_current',
    'wind_speed_current',
    'pm25_current',
    'co2_current',
    'lightning_dist_current',
    # Classic derived features (7)
    'temp_humidity_ratio',
    'pressure_trend',
    'heat_index',
    'dew_point',
    'fire_risk_index',
    'flood_risk_index',
    'lightning_threat',
    # Cyclical time features (4)
    'hour_sin',
    'hour_cos',
    'doy_sin',
    'doy_cos',
    # Physical interaction features (4)
    'pressure_drop_rate',
    'smoke_transport',
    'heat_stress',
    'visibility_rain',
]

HAZARD_CLASSES = ['wildfire', 'flood', 'storm', 'air_quality']

COLUMN_MAP = {
    'temperature_(c)':          'temp_current',
    'apparent_temperature_(c)': 'apparent_temp',
    'humidity':                 'humidity_current',
    'pressure_(millibars)':     'pressure_current',
    'wind_speed_(km/h)':        'wind_speed_current',
    'wind_kph':                 'wind_speed_current',
    'visibility_(km)':          'visibility_km',
    'precip_type':              'precip_type_raw',
    'pm25':                     'pm25_current',
    'pm2_5':                    'pm25_current',
    'co2':                      'co2_current',
    'lightning_distance':       'lightning_dist_current',
    'lightning_dist':           'lightning_dist_current',
}


# ============================================
# LOADING & CLEANING
# ============================================

def load_raw_data(csv_path: str) -> pd.DataFrame:
    """Load, clean, and chronologically sort the raw weather CSV."""
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} rows from {csv_path}")
    print(f"Columns: {list(df.columns)}")

    # Standardize column names
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    # Parse timestamp - critical for anti-leakage chronological ordering
    date_col = 'formatted_date'
    if date_col not in df.columns:
        raise ValueError(f"Expected column '{date_col}' not found. Available: {df.columns.tolist()}")

    df['timestamp'] = pd.to_datetime(df[date_col], utc=True, errors='coerce')
    bad = df['timestamp'].isna().sum()
    if bad:
        print(f"  WARNING: {bad} rows with unparseable dates dropped.")
        df = df.dropna(subset=['timestamp'])

    # CRITICAL: sort chronologically before anything else
    df = df.sort_values('timestamp').reset_index(drop=True)
    print(f"Date range: {df['timestamp'].min()} -> {df['timestamp'].max()}")

    # Map known columns
    for old, new in COLUMN_MAP.items():
        if old in df.columns:
            df = df.rename(columns={old: new})

    # Clean bad pressure values
    if 'pressure_current' in df.columns:
        df.loc[df['pressure_current'] <= 900, 'pressure_current'] = np.nan
        df['pressure_current'] = df['pressure_current'].interpolate(method='linear').bfill().ffill()

    # Visibility: fill with median
    if 'visibility_km' in df.columns:
        df['visibility_km'] = df['visibility_km'].fillna(df['visibility_km'].median())
    else:
        df['visibility_km'] = 15.0

    # Apparent temperature: fall back to temp if missing
    if 'apparent_temp' not in df.columns:
        df['apparent_temp'] = df.get('temp_current', 0.0)

    # Precip type binary flag
    if 'precip_type_raw' in df.columns:
        df['precip_binary'] = (df['precip_type_raw'].str.lower() == 'rain').astype(float)
    else:
        df['precip_binary'] = 0.0

    return df


# ============================================
# SYNTHETIC SENSORS (for missing hardware)
# ============================================

def add_synthetic_sensors(df: pd.DataFrame) -> pd.DataFrame:
    """Add synthetic PM2.5, CO2, and lightning - correlated with weather."""
    out = df.copy()
    n = len(out)
    rng = np.random.default_rng(42)

    base_pm25 = 15 + 20 * out['humidity_current']
    pressure_effect = (out['pressure_current'] - 1013) * 0.5
    wind_effect = -out['wind_speed_current'] * 0.5
    noise = rng.normal(0, 5, n)
    out['pm25_current'] = (base_pm25 + pressure_effect + wind_effect + noise).clip(0, 200)

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


# ============================================
# CYCLICAL TIME FEATURES
# ============================================

def add_cyclical_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Encode hour-of-day and day-of-year as sin/cos pairs.

    Sin/cos projection onto a unit circle ensures hour=23 and hour=0 are
    treated as adjacent (distance ~0) rather than maximally distant (23 units),
    which is critical for learning diurnal and seasonal patterns.
    """
    out = df.copy()
    ts = df['timestamp']
    # Strip tz for dt accessor
    ts_naive = ts.dt.tz_convert('UTC').dt.tz_localize(None)

    hour = ts_naive.dt.hour + ts_naive.dt.minute / 60.0
    doy  = ts_naive.dt.dayofyear

    out['hour_sin'] = np.sin(2 * np.pi * hour / 24.0)
    out['hour_cos'] = np.cos(2 * np.pi * hour / 24.0)
    out['doy_sin']  = np.sin(2 * np.pi * doy  / 365.25)
    out['doy_cos']  = np.cos(2 * np.pi * doy  / 365.25)

    return out


# ============================================
# PHYSICAL INTERACTION FEATURES
# ============================================

def add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute physically-motivated interaction terms.

    pressure_drop_rate (mb/h):
        Rolling 6-sample linear slope of pressure. Sharp negative slope is
        the textbook precursor to cyclonic storms and flash floods.

    smoke_transport (normalised):
        PM2.5 x wind_speed. Distinguishes trapped (high PM25, low wind) from
        transported wildfire smoke (high PM25, high wind).

    heat_stress (deg C delta):
        temp - apparent_temp. Positive = humidity traps heat; negative = wind
        cooling. Relevant to wildfire ignition and heat-emergency thresholds.

    visibility_rain (km, rain-suppressed):
        visibility_km x precip_binary. Visibility drops sharply in heavy rain;
        acts as a rain-intensity proxy in the absence of a rain gauge.
    """
    out = df.copy()

    # pressure_drop_rate: 6-h rolling linear slope
    window = 6
    def _slope(x):
        # A one-point window has no slope. Guarding here also keeps the
        # pipeline stable when an upstream source contains a bad value.
        x = np.asarray(x, dtype=float)
        valid = np.isfinite(x)
        if valid.sum() < 2:
            return 0.0
        t = np.arange(len(x), dtype=float)[valid]
        return float(np.polyfit(t, x[valid], 1)[0])

    out['pressure_drop_rate'] = (
        out['pressure_current']
        .rolling(window, min_periods=1)
        .apply(_slope, raw=True)
        .fillna(0.0)
    )

    # smoke_transport (normalised to [0,1])
    raw_smoke = out['pm25_current'] * out['wind_speed_current']
    out['smoke_transport'] = raw_smoke / (raw_smoke.max() + 1e-6)

    # heat_stress
    out['heat_stress'] = out['temp_current'] - out['apparent_temp']

    # visibility_rain
    out['visibility_rain'] = out['visibility_km'] * out['precip_binary']

    return out


# ============================================
# CLASSIC DERIVED FEATURES (unchanged from v1 for comparability)
# ============================================

def compute_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the original 7 derived features."""
    out = df.copy()

    required = ['temp_current', 'humidity_current', 'pressure_current',
                'wind_speed_current', 'pm25_current', 'co2_current',
                'lightning_dist_current']
    for col in required:
        if col not in out.columns:
            raise ValueError(f"Required column '{col}' not found")

    humidity_pct = out['humidity_current'] * 100

    out['temp_humidity_ratio'] = out['temp_current'] / out['humidity_current'].clip(lower=0.01)

    window = 6
    def _slope(x):
        x = np.asarray(x, dtype=float)
        valid = np.isfinite(x)
        if valid.sum() < 2:
            return 0.0
        t = np.arange(len(x), dtype=float)[valid]
        return float(np.polyfit(t, x[valid], 1)[0])

    out['pressure_trend'] = (
        out['pressure_current']
        .rolling(window, min_periods=1)
        .apply(_slope, raw=True)
        .fillna(0.0)
    )

    out['heat_index'] = out['temp_current'] + 0.5 * humidity_pct
    out['dew_point']  = out['temp_current'] - (100 - humidity_pct) / 5

    fire_risk  = (out['temp_current'] > 30).astype(float) * 0.25
    fire_risk += (humidity_pct < 35).astype(float) * 0.25
    fire_risk += (out['wind_speed_current'] > 5).astype(float) * 0.15
    fire_risk += (out['pm25_current'] > 40).astype(float) * 0.35
    out['fire_risk_index'] = fire_risk.clip(0, 1)

    flood_risk  = (out['pressure_current'] < 1005).astype(float) * 0.30
    flood_risk += (humidity_pct > 85).astype(float) * 0.30
    flood_risk += (out['wind_speed_current'] > 8).astype(float) * 0.20
    flood_risk += (out['pressure_current'] < 1000).astype(float) * 0.20
    out['flood_risk_index'] = flood_risk.clip(0, 1)

    out['lightning_threat'] = (40 - out['lightning_dist_current']).clip(lower=0) / 40

    return out


# ============================================
# HAZARD LABELS (same thresholds as v1 for apples-to-apples comparison)
# ============================================

def generate_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Generate binary hazard labels from features."""
    labels = pd.DataFrame(index=df.index)

    labels['wildfire'] = (
        (df['temp_current'] > 15) &
        (df['humidity_current'] < 0.60) &
        (df['wind_speed_current'] > 8) &
        (df['pm25_current'] > 20)
    ).astype(int)

    labels['flood'] = (
        (df['pressure_current'] < 1010) &
        (df['humidity_current'] > 0.70) &
        (df['wind_speed_current'] > 10)
    ).astype(int)

    labels['storm'] = (
        (df['lightning_dist_current'] < 40) &
        (df['pressure_current'] < 1012)
    ).astype(int)

    labels['air_quality'] = (
        (df['pm25_current'] > 25) |
        (df['co2_current'] > 480)
    ).astype(int)

    return labels


# ============================================
# MAIN PIPELINE
# ============================================

def prepare_dataset(input_path: str, output_dir: str):
    """Full dataset preparation pipeline - v2."""
    os.makedirs(output_dir, exist_ok=True)

    df = load_raw_data(input_path)
    df = add_synthetic_sensors(df)
    df = compute_derived_features(df)
    df = add_cyclical_time_features(df)
    df = add_interaction_features(df)
    labels = generate_labels(df)

    missing = [f for f in FEATURE_NAMES if f not in df.columns]
    if missing:
        raise ValueError(f"Missing expected features after pipeline: {missing}")

    X = df[FEATURE_NAMES].copy()
    y = labels[HAZARD_CLASSES].copy()

    nan_counts = X.isna().sum()
    if nan_counts.any():
        print("WARNING: NaN in features, forward-filling:")
        print(nan_counts[nan_counts > 0])
        X = X.ffill().bfill()

    print(f"\nFeature matrix: {X.shape}")
    print(f"Label matrix:   {y.shape}")
    print(f"\nLabel distribution:")
    for c in HAZARD_CLASSES:
        pos = y[c].sum()
        print(f"  {c:15s}: {pos:6,}/{len(y):,} ({100*pos/len(y):.1f}%)")

    X.to_csv(os.path.join(output_dir, 'features.csv'), index=False)
    y.to_csv(os.path.join(output_dir, 'labels.csv'), index=False)

    combined = pd.concat([df[['timestamp']].reset_index(drop=True), X, y], axis=1)
    combined.to_csv(os.path.join(output_dir, 'dataset.csv'), index=False)

    metadata = {
        'feature_names':   FEATURE_NAMES,
        'label_names':     HAZARD_CLASSES,
        'num_features':    len(FEATURE_NAMES),
        'num_classes':     len(HAZARD_CLASSES),
        'num_samples':     len(X),
        'date_range': {
            'start': str(df['timestamp'].min()),
            'end':   str(df['timestamp'].max()),
        },
        'label_distribution': {c: int(y[c].sum()) for c in HAZARD_CLASSES},
        'new_features_v2': [
            'hour_sin', 'hour_cos', 'doy_sin', 'doy_cos',
            'pressure_drop_rate', 'smoke_transport', 'heat_stress', 'visibility_rain',
        ],
    }
    with open(os.path.join(output_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved to {output_dir}/")
    return X, y


def main():
    parser = argparse.ArgumentParser(
        description='Prepare real weather data for training (v2)'
    )
    parser.add_argument('--input',  type=str, required=True,        help='Input weatherHistory.csv')
    parser.add_argument('--output', type=str, default='./data_v2/', help='Output directory')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        return 1

    prepare_dataset(args.input, args.output)
    print("\nDataset preparation complete!")
    return 0


if __name__ == '__main__':
    exit(main())
