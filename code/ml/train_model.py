"""
train_model.py - XGBoost training for Edge AI Weather Station

Trains 4 binary XGBoost models (one per hazard class) and exports
to JSON format for convert_to_c.py.

Usage:
    python train_model.py --data ./data/ --output ./model/
    python train_model.py --data ./data/ --output ./model/ --export-c --c-output ../firmware/components/ml/include/model_data.h
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import argparse
import json
import os
import sys

# Add parent directory to path for prepare_dataset
sys.path.insert(0, os.path.dirname(__file__))

try:
    from prepare_dataset import (
        FEATURE_NAMES, HAZARD_CLASSES, NUM_FEATURES, NUM_CLASSES,
        load_raw_data, compute_derived_features, generate_labels
    )
except ImportError:
    # Fallback if import fails
    FEATURE_NAMES = [
        'temp_current', 'humidity_current', 'pressure_current',
        'wind_speed_current', 'pm25_current', 'co2_current',
        'lightning_dist_current', 'temp_humidity_ratio', 'pressure_trend',
        'heat_index', 'dew_point', 'fire_risk_index', 'flood_risk_index',
        'lightning_threat',
    ]
    HAZARD_CLASSES = ['wildfire', 'flood', 'storm', 'air_quality']
    NUM_FEATURES = len(FEATURE_NAMES)
    NUM_CLASSES = len(HAZARD_CLASSES)

# ============================================
# XGBOOST PARAMETERS (tuned for ESP32-S3)
# ============================================

XGB_PARAMS = {
    'objective': 'binary:logistic',
    'eval_metric': 'logloss',
    'max_depth': 4,              # Shallow trees for fast inference
    'min_child_weight': 2,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'learning_rate': 0.1,
    'gamma': 0.1,
    'reg_alpha': 0.1,
    'reg_lambda': 1.0,
    'tree_method': 'hist',       # Fast training
    'seed': 42,
}

NUM_BOOST_ROUNDS = 16            # Limit trees per class
EARLY_STOPPING_ROUNDS = 5


# ============================================
# DATA LOADING
# ============================================

def load_prepared_data(data_dir: str):
    """Load features/labels from prepared dataset."""
    features_path = os.path.join(data_dir, 'features.csv')
    labels_path = os.path.join(data_dir, 'labels.csv')
    
    if os.path.exists(features_path) and os.path.exists(labels_path):
        X = pd.read_csv(features_path).values
        y = pd.read_csv(labels_path).values
        return X, y
    
    # Try dataset.csv
    dataset_path = os.path.join(data_dir, 'dataset.csv')
    if os.path.exists(dataset_path):
        df = pd.read_csv(dataset_path)
        X = df[FEATURE_NAMES].values
        y = df[HAZARD_CLASSES].values
        return X, y
    
    return None, None


def load_raw_weather(data_dir: str):
    """Load and prepare from raw weather CSV."""
    # Find CSV files
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    if not csv_files:
        return None, None
    
    # Use first CSV (or the largest)
    csv_path = os.path.join(data_dir, sorted(csv_files)[0])
    print(f"Loading raw data from {csv_path}...")
    
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    
    # Standardize column names
    col_map = {
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
    for old, new in col_map.items():
        if old in df.columns:
            df = df.rename(columns={old: new})
    
    # Compute derived features
    df = compute_derived_features(df)
    
    # Generate labels
    labels = generate_labels(df)
    
    X = df[FEATURE_NAMES].values.astype(np.float32)
    y = labels[HAZARD_CLASSES].values.astype(np.float32)
    
    return X, y


def generate_synthetic_data(n_samples: int = 20000):
    """Generate synthetic data as fallback."""
    np.random.seed(42)
    n = n_samples
    
    df = pd.DataFrame({
        'temp_current': np.random.uniform(15, 40, n),
        'humidity_current': np.random.uniform(20, 95, n),
        'pressure_current': np.random.uniform(995, 1025, n),
        'wind_speed_current': np.random.uniform(0, 15, n),
        'pm25_current': np.random.uniform(5, 100, n),
        'co2_current': np.random.uniform(350, 600, n),
        'lightning_dist_current': np.random.uniform(0, 50, n),
    })
    
    df = compute_derived_features(df)
    labels = generate_labels(df)
    
    X = df[FEATURE_NAMES].values.astype(np.float32)
    y = labels[HAZARD_CLASSES].values.astype(np.float32)
    
    return X, y


# ============================================
# NORMALIZATION
# ============================================

def compute_normalization(X: np.ndarray):
    """Compute z-score normalization statistics."""
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0  # Avoid division by zero
    return mean, std


def normalize_data(X: np.ndarray, mean: np.ndarray, std: np.ndarray):
    """Apply z-score normalization."""
    return (X - mean) / std


# ============================================
# TRAINING
# ============================================

def train_class(X_train, y_train, X_val, y_val, class_name: str, params: dict):
    """Train single XGBoost binary classifier."""
    print(f"\nTraining {class_name} model...")
    
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    
    model = xgb.train(
        params,
        dtrain,
        num_boost_round=params.get('n_estimators', 16),
        evals=[(dtrain, 'train'), (dval, 'val')],
        early_stopping_rounds=5,
        verbose_eval=False,
    )
    
    # Evaluate
    y_pred = (model.predict(dval) > 0.5).astype(int)
    from sklearn.metrics import classification_report
    report = classification_report(y_val, y_pred, output_dict=True, zero_division=0)
    
    # Get number of trees used
    num_trees = model.best_iteration + 1 if hasattr(model, 'best_iteration') else params.get('n_estimators', 16)
    
    metrics = {
        'accuracy': report['accuracy'],
        'precision': report.get('1', {}).get('precision', 0),
        'recall': report.get('1', {}).get('recall', 0),
        'f1': report.get('1', {}).get('f1-score', 0),
        'num_trees': num_trees,
    }
    
    print(f"  Accuracy:  {metrics['accuracy']:.3f}")
    print(f"  Precision: {metrics['precision']:.3f}")
    print(f"  Recall:    {metrics['recall']:.3f}")
    print(f"  F1:        {metrics['f1']:.3f}")
    print(f"  Trees:     {metrics['num_trees']}")
    
    return model, metrics


def main():
    parser = argparse.ArgumentParser(description='Train Edge AI Weather Station models')
    parser.add_argument('--data', type=str, required=True, help='Data directory')
    parser.add_argument('--output', type=str, required=True, help='Output model directory')
    parser.add_argument('--export-c', action='store_true', help='Also generate C headers')
    parser.add_argument('--c-output', type=str, help='C header output path')
    parser.add_argument('--synthetic', action='store_true', help='Force synthetic data generation')
    parser.add_argument('--samples', type=int, default=20000, help='Synthetic samples')
    parser.add_argument('--max-trees', type=int, default=NUM_BOOST_ROUNDS, help='Max trees per class')
    args = parser.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    # Load data
    if args.synthetic:
        print("Generating synthetic data...")
        X, y = generate_synthetic_data(args.samples)
    else:
        # Try prepared dataset first
        X, y = load_prepared_data(args.data)
        if X is None:
            # Try raw weather data
            X, y = load_raw_weather(args.data)
        if X is None:
            print("No data found, generating synthetic...")
            X, y = generate_synthetic_data(args.samples)
    
    print(f"\nTraining data: X={X.shape}, y={y.shape}")
    print(f"Features: {FEATURE_NAMES}")
    print(f"Classes: {HAZARD_CLASSES}")
    print(f"Class distribution:")
    for i, cls in enumerate(HAZARD_CLASSES):
        pos = int(y[:, i].sum())
        print(f"  {cls}: {pos}/{len(y)} ({100*pos/len(y):.1f}%)")
    
    # Normalize
    mean, std = compute_normalization(X)
    X_norm = normalize_data(X, mean, std)
    
    # Save normalization stats
    norm_stats = {
        'mean': mean.tolist(),
        'std': std.tolist(),
        'feature_names': FEATURE_NAMES,
    }
    with open(os.path.join(args.output, 'normalization.json'), 'w') as f:
        json.dump(norm_stats, f, indent=2)
    
    # Train/val/test split
    X_temp, X_test, y_temp, y_test = train_test_split(
        X_norm, y, test_size=0.2, random_state=42
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.125, random_state=42  # 0.125 * 0.8 = 0.1
    )
    
    print(f"\nSplit: train={len(X_train)}, val={len(X_val)}, test={len(X_test)}")
    
    # Train one model per class
    models = {}
    all_metrics = {}
    
    params = XGB_PARAMS.copy()
    max_trees = args.max_trees
    
    for i, cls in enumerate(HAZARD_CLASSES):
        model, metrics = train_class(
            X_train, y_train[:, i],
            X_val, y_val[:, i],
            cls, params
        )
        models[cls] = model
        all_metrics[cls] = metrics
    
    # Save models
    for cls, model in models.items():
        model_path = os.path.join(args.output, f'xgboost_{cls}.json')
        model.save_model(model_path)
        print(f"Saved {cls} model to {model_path}")
    
    # Save metrics
    with open(os.path.join(args.output, 'metrics.json'), 'w') as f:
        json.dump(all_metrics, f, indent=2)
    
    # Save feature names
    with open(os.path.join(args.output, 'feature_names.json'), 'w') as f:
        json.dump(FEATURE_NAMES, f, indent=2)
    
    print(f"\nModels saved to {args.output}")
    
    # Test evaluation
    print("\nTest set evaluation:")
    dtest = xgb.DMatrix(X_test)
    for i, cls in enumerate(HAZARD_CLASSES):
        model = models[cls]
        y_pred = (model.predict(dtest) > 0.5).astype(int)
        acc = (y_pred == y_test[:, i]).mean()
        print(f"  {cls}: accuracy={acc:.3f}")
    
    # Export to C if requested
    if args.export_c:
        if not args.c_output:
            print("Error: --c-output required when --export-c is used")
            return 1
        
        print(f"\nGenerating C headers...")
        from convert_to_c import load_model_trees, generate_model_header
        
        trees_by_class = load_model_trees(args.output, max_trees)
        generate_model_header(trees_by_class, norm_stats, args.c_output)
        print(f"Generated {args.c_output}")
    
    print("\nTraining complete!")
    return 0


if __name__ == '__main__':
    exit(main())