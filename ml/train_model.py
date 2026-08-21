"""
train_model.py - XGBoost Model Training for Edge AI Weather Station

Trains 4 binary XGBoost classifiers (one per hazard class) from real prepared data.
Exports models to JSON for convert_to_c.py.

Usage:
    python train_model.py --data ./data/ --output ./model/ --export-c --c-output ./generated/model_data.h
"""

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

# ============================================
# FEATURE DEFINITIONS (must match prepare_dataset.py)
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

NUM_BOOST_ROUND = 16             # 16 trees per class
EARLY_STOPPING_ROUNDS = 5


# ============================================
# DATA LOADING
# ============================================

def load_prepared_data(data_dir: str):
    """Load features and labels from prepared dataset."""
    features_path = os.path.join(data_dir, 'features.csv')
    labels_path = os.path.join(data_dir, 'labels.csv')

    if not os.path.exists(features_path) or not os.path.exists(labels_path):
        raise FileNotFoundError(f"Prepared data not found in {data_dir}. Run prepare_dataset.py first.")

    X = pd.read_csv(features_path).values.astype(np.float32)
    y = pd.read_csv(labels_path).values.astype(np.float32)

    print(f"Loaded data: X={X.shape}, y={y.shape}")
    return X, y


# ============================================
# MODEL TRAINING
# ============================================

def train_model(X, y, output_dir: str, max_trees: int = NUM_BOOST_ROUND):
    """Train XGBoost model for each hazard class."""

    # Split data
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.125, random_state=42  # 0.125 * 0.8 = 0.1
    )

    print(f"Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

    # Compute normalization stats from training data
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std[std == 0] = 1.0

    X_train_norm = (X_train - mean) / std
    X_val_norm = (X_val - mean) / std
    X_test_norm = (X_test - mean) / std

    # Save normalization stats
    os.makedirs(output_dir, exist_ok=True)
    norm_stats = {
        'mean': mean.tolist(),
        'std': std.tolist(),
        'feature_names': FEATURE_NAMES,
    }
    with open(os.path.join(output_dir, 'normalization.json'), 'w') as f:
        json.dump(norm_stats, f, indent=2)

    # Production alert thresholds (from architecture docs)
    ALERT_THRESHOLDS = {
        'wildfire': 0.70,
        'flood': 0.70,
        'storm': 0.75,
        'air_quality': 0.65,
    }

    # Train one model per class
    models = {}
    all_metrics = {}

    for idx, hazard in enumerate(HAZARD_CLASSES):
        print(f"\nTraining {hazard} model...")

        # Calculate class weight for imbalanced data
        pos_count = y_train[:, idx].sum()
        neg_count = len(y_train) - pos_count
        scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0
        print(f"  Class balance: {pos_count:.0f} pos, {neg_count:.0f} neg, scale_pos_weight={scale_pos_weight:.1f}")

        class_params = XGB_PARAMS.copy()
        class_params['scale_pos_weight'] = scale_pos_weight

        dtrain = xgb.DMatrix(X_train_norm, label=y_train[:, idx])
        dval = xgb.DMatrix(X_val_norm, label=y_val[:, idx])
        dtest = xgb.DMatrix(X_test_norm, label=y_test[:, idx])

        model = xgb.train(
            class_params,
            dtrain,
            num_boost_round=max_trees,
            evals=[(dtrain, 'train'), (dval, 'val')],
            early_stopping_rounds=EARLY_STOPPING_ROUNDS,
            verbose_eval=False,
        )

        # Evaluate on test set at production threshold
        y_pred_prob = model.predict(dtest)
        threshold = ALERT_THRESHOLDS[hazard]
        y_pred = (y_pred_prob > threshold).astype(int)
        report = classification_report(y_test[:, idx], y_pred, output_dict=True, zero_division=0)

        metrics = {
            'accuracy': report['accuracy'],
            'precision': report.get('1.0', {}).get('precision', report.get('1', {}).get('precision', 0)),
            'recall': report.get('1.0', {}).get('recall', report.get('1', {}).get('recall', 0)),
            'f1': report.get('1.0', {}).get('f1-score', report.get('1', {}).get('f1-score', 0)),
            'num_trees': model.best_iteration + 1 if hasattr(model, 'best_iteration') else max_trees,
            'threshold': threshold,
        }

        models[hazard] = model
        all_metrics[hazard] = metrics

        print(f"  Test Accuracy:  {metrics['accuracy']:.3f}")
        print(f"  Test Precision: {metrics['precision']:.3f}")
        print(f"  Test Recall:    {metrics['recall']:.3f}")
        print(f"  Test F1:        {metrics['f1']:.3f}")
        print(f"  Trees used:     {metrics['num_trees']}")

    # Save models
    for hazard, model in models.items():
        model_path = os.path.join(output_dir, f'xgboost_{hazard}.json')
        model.save_model(model_path)
        print(f"Saved {hazard} model to {model_path}")

    # Save metrics
    with open(os.path.join(output_dir, 'metrics.json'), 'w') as f:
        json.dump(all_metrics, f, indent=2)

    # Save feature names
    with open(os.path.join(output_dir, 'feature_names.json'), 'w') as f:
        json.dump(FEATURE_NAMES, f, indent=2)

    print(f"\nAll models saved to {output_dir}")
    return models, all_metrics, norm_stats


# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description='Train Edge AI Weather Station models')
    parser.add_argument('--data', type=str, required=True, help='Prepared data directory (features.csv, labels.csv)')
    parser.add_argument('--output', type=str, required=True, help='Output model directory')
    parser.add_argument('--export-c', action='store_true', help='Also generate C headers')
    parser.add_argument('--c-output', type=str, help='C header output path')
    parser.add_argument('--max-trees', type=int, default=NUM_BOOST_ROUND, help='Max trees per class')
    args = parser.parse_args()

    # Load data
    X, y = load_prepared_data(args.data)

    # Train
    _models, _metrics, norm_stats = train_model(X, y, args.output, args.max_trees)

    # Export to C if requested
    if args.export_c:
        if not args.c_output:
            print("Error: --c-output required when --export-c is used")
            return 1

        print("\nGenerating C headers...")
        from convert_to_c import generate_model_header, load_model_trees

        trees_by_class = load_model_trees(args.output, args.max_trees)
        generate_model_header(trees_by_class, norm_stats, args.c_output)
        print(f"Generated {args.c_output}")

    print("\nTraining complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())