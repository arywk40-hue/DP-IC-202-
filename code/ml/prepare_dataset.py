"""
prepare_dataset.py - Prepare training dataset for Edge AI Weather Station

Processes raw weather CSV into features/labels for XGBoost training.

Usage:
    python prepare_dataset.py --input ./data/weatherHistory.csv --output ./data/
"""

import numpy as np
import pandas as pd
import argparse
import os
from pathlib import Path

# ============================================
# FEATURE DEFINITIONS (must match train_model.py)
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

# Column mapping from typical weather CSV to our internal names
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

# ============================================
# DATA PROCESSING
# ============================================

def load_raw_data(csv_path: str) -> pd.DataFrame:
    """Load and clean raw weather data."""
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
    """Compute all derived features from base sensors."""
    out = df.copy()
    
    # Ensure required base columns exist with defaults
    for col in ['temp_current', 'humidity_current', 'pressure_current', 
                'wind_speed_current', 'pm25_current', 'co2_current', 
                'lightning_dist_current']:
        if col not in out.columns:
            defaults = {
                'temp_current': 25.0,
                'humidity_current': 50.0,
                'pressure_current': 1013.25,
                'wind_speed_current': 3.0,
                'pm25_current': 15.0,
                'co2_current': 420.0,
                'lightning_dist_current': 40.0,
            }
            out[col] = defaults.get(col, 0.0)
            print(f"Warning: {col} not in data, using default {defaults.get(col, 0.0)}")
    
    # Derived features
    out['temp_humidity_ratio'] = out['temp_current'] / out['humidity_current'].clip(lower=1)
    
    # Heat index (simplified)
    out['heat_index'] = out['temp_current'] + 0.5 * out['humidity_current']
    
    # Dew point (Magnus formula approximation)
    out['dew_point'] = out['temp_current'] - (100 - out['humidity_current']) / 5
    
    # Pressure trend (rolling linear regression slope)
    window = 6
    out['pressure_trend'] = out['pressure_current'].rolling(window).apply(
        lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) == window else 0,
        raw=True
    ).fillna(0)
    
    # Fire risk index
    fire_risk = 0.0
    fire_risk += np.where(out['temp_current'] > 30, 0.25, 0)
    fire_risk += np.where(out['humidity_current'] < 35, 0.25, 0)
    fire_risk += np.where(out['wind_speed_current'] > 5, 0.15, 0)
    fire_risk += np.where(out['pm25_current'] > 40, 0.35, 0)
    out['fire_risk_index'] = np.clip(fire_risk, 0, 1)
    
    # Flood risk index
    flood_risk = 0.0
    flood_risk += np.where(out['pressure_current'] < 1005, 0.30, 0)
    flood_risk += np.where(out['humidity_current'] > 85, 0.30, 0)
    flood_risk += np.where(out['wind_speed_current'] > 8, 0.20, 0)
    flood_risk += np.where(out['pressure_current'] < 1000, 0.20, 0)
    out['flood_risk_index'] = np.clip(flood_risk, 0, 1)
    
    # Lightning threat
    out['lightning_threat'] = np.clip((40 - out['lightning_dist_current']) / 40, 0, 1)
    
    return out


def generate_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Generate binary hazard labels from features."""
    labels = pd.DataFrame(index=df.index)
    
    # Wildfire: high temp, low humidity, wind, high PM2.5
    labels['wildfire'] = (
        (df['temp_current'] > 30) & 
        (df['humidity_current'] < 35) & 
        (df['wind_speed_current'] > 5) & 
        (df['pm25_current'] > 40)
    ).astype(int)
    
    # Flood: low pressure, high humidity, sustained wind
    labels['flood'] = (
        (df['pressure_current'] < 1000) & 
        (df['humidity_current'] > 85) & 
        (df['wind_speed_current'] > 8)
    ).astype(int)
    
    # Storm: lightning nearby + dropping pressure
    labels['storm'] = (
        (df['lightning_dist_current'] < 15) & 
        (df['pressure_current'] < 1005)
    ).astype(int)
    
    # Air quality: high PM2.5 or CO2
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
    features_path = os.path.join(output_dir, 'features.csv')
    labels_path = os.path.join(output_dir, 'labels.csv')
    X.to_csv(features_path, index=False)
    y.to_csv(labels_path, index=False)
    print(f"\nSaved features to {features_path}")
    print(f"Saved labels to {labels_path}")
    
    # Also save combined for inspection
    combined = pd.concat([X, y], axis=1)
    combined_path = os.path.join(output_dir, 'dataset.csv')
    combined.to_csv(combined_path, index=False)
    print(f"Saved combined dataset to {combined_path}")
    
    return X, y


def main():
    parser = argparse.ArgumentParser(description='Prepare dataset for hazard detection')
    parser.add_argument('--input', type=str, help='Input directory with raw CSV files')
    parser.add_argument('--output', type=str, default='./data/processed/', help='Output directory')
    parser.add_argument('--generate-synthetic', action='store_true', help='Generate synthetic data')
    parser.add_argument('--samples', type=int, default=10000, help='Number of synthetic samples')
    parser.add_argument('--test-split', type=float, default=0.2, help='Test split ratio')
    parser.add_argument('--val-split', type=float, default=0.1, help='Validation split ratio')
    
    args = parser.parse_args()
    
    if not args.generate_synthetic and not args.input:
        parser.error("--input required unless --generate-synthetic is used")
    
    # Generate data in a temp location if synthetic
    if args.generate_synthetic:
        # Use a temporary approach - just prepare the output
        import numpy as np
        import pandas as pd
        
        np.random.seed(42)
        n = args.samples
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=n, freq='1H'),
            'temp_current': np.random.uniform(15, 40, n),
            'humidity_current': np.random.uniform(20, 95, n),
            'pressure_current': np.random.uniform(995, 1025, n),
            'wind_speed_current': np.random.uniform(0, 15, n),
            'pm25_current': np.random.uniform(5, 100, n),
            'co2_current': np.random.uniform(350, 600, n),
            'lightning_dist_current': np.random.uniform(0, 50, n),
        })
        
        os.makedirs(args.output, exist_ok=True)
        
        # Compute derived features
        df = compute_derived_features(df)
        labels = generate_labels(df)
        
        X = df[FEATURE_NAMES]
        y = labels[HAZARD_CLASSES]
        
        X.to_csv(os.path.join(args.output, 'features.csv'), index=False)
        y.to_csv(os.path.join(args.output, 'labels.csv'), index=False)
        
        print(f"Generated {n} synthetic samples to {args.output}")
        print(f"  Label distribution:")
        for c in HAZARD_CLASSES:
            pos = y[c].sum()
            print(f"    {c}: {pos}/{len(y)} ({100*pos/len(y):.1f}%)")
        return
    
    prepare_dataset(args.input, args.output)


if __name__ == '__main__':
    main()