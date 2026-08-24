"""
train_model_v2.py - Improved XGBoost Training: Temporal CV + SHAP Pruning

Key improvements over v1:
  1. Chronological hold-out: last 20% of data by time is the true test set,
     never touched during hyper-parameter search.
  2. TimeSeriesSplit(n_splits=5) + GridSearchCV scored on F1-macro —
     each fold trains on the past and evaluates on the immediate future.
  3. GridSearch over: max_depth, learning_rate, n_estimators, min_child_weight.
  4. SHAP feature importance after tuning: reports per-feature mean |SHAP|
     and flags low-importance features as candidates for pruning.
  5. Per-class metrics (precision, recall, F1, support) — not just accuracy.
  6. --prune-features: re-train with SHAP-selected features for lean ESP32 export.
  7. --fast: reduced grid for quick iteration (~3 min vs ~15 min full grid).

Usage:
    python train_model_v2.py --data data_v2/ --output model_v2/
    python train_model_v2.py --data data_v2/ --output model_v2/ --fast
    python train_model_v2.py --data data_v2/ --output model_v2/ --prune-features
"""

import numpy as np
import pandas as pd
import xgboost as xgb
import shap
import json
import os
import argparse
import warnings
from datetime import datetime

from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import (
    classification_report, f1_score, precision_recall_fscore_support
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore', category=UserWarning)

# ============================================
# CONSTANTS
# ============================================

HAZARD_CLASSES = ['wildfire', 'flood', 'storm', 'air_quality']

# Production alert thresholds (from architecture docs — unchanged)
ALERT_THRESHOLDS = {
    'wildfire':    0.70,
    'flood':       0.70,
    'storm':       0.75,
    'air_quality': 0.65,
}

# Full hyper-parameter grid (~10-15 min on M-series Mac)
FULL_PARAM_GRID = {
    'max_depth':        [3, 4, 5],
    'learning_rate':    [0.05, 0.1],
    'n_estimators':     [50, 100, 200],
    'min_child_weight': [1, 3, 5],
}

# Fast grid for quick iteration (~2-4 min)
FAST_PARAM_GRID = {
    'max_depth':        [3, 4],
    'learning_rate':    [0.1],
    'n_estimators':     [50, 100],
    'min_child_weight': [1, 3],
}

# XGBoost base params (not searched)
BASE_XGB_PARAMS = {
    'objective':       'binary:logistic',
    'eval_metric':     'logloss',
    'subsample':       0.8,
    'colsample_bytree': 0.8,
    'gamma':           0.1,
    'reg_alpha':       0.1,
    'reg_lambda':      1.0,
    'tree_method':     'hist',
    'seed':            42,
    'verbosity':       0,
}

# SHAP pruning threshold: drop features whose mean |SHAP| < this fraction of max
SHAP_PRUNE_THRESHOLD = 0.01


# ============================================
# DATA LOADING
# ============================================

def load_prepared_data(data_dir: str):
    """Load features and labels; return as numpy arrays (already chronological)."""
    features_path = os.path.join(data_dir, 'features.csv')
    labels_path   = os.path.join(data_dir, 'labels.csv')
    meta_path     = os.path.join(data_dir, 'metadata.json')

    if not os.path.exists(features_path) or not os.path.exists(labels_path):
        raise FileNotFoundError(
            f"Prepared data not found in {data_dir}. "
            "Run prepare_dataset_v2.py first."
        )

    X_df = pd.read_csv(features_path)
    y_df = pd.read_csv(labels_path)

    feature_names = X_df.columns.tolist()

    # Load metadata to verify feature list
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        print(f"Dataset: {meta['num_samples']:,} samples, {meta['num_features']} features")
        print(f"Date range: {meta.get('date_range', {}).get('start', '?')} -> "
              f"{meta.get('date_range', {}).get('end', '?')}")
    else:
        print(f"Loaded data: X={X_df.shape}, y={y_df.shape}")

    X = X_df.values.astype(np.float32)
    y = y_df.values.astype(np.float32)

    return X, y, feature_names


# ============================================
# CHRONOLOGICAL TRAIN / TEST SPLIT
# ============================================

def temporal_train_test_split(X, y, test_fraction=0.20):
    """
    Split data into training and test sets by chronological position.

    The last `test_fraction` of the data (by row index, which is
    chronological after prepare_dataset_v2.py) becomes the held-out
    test set. This means the model is evaluated on future data it
    has never seen — the only valid estimate of operational performance.

    Random shuffling would let the model 'see' patterns from 2016 while
    being trained on 2006-2009, inflating test scores by 5-15 pp.
    """
    n = len(X)
    split_idx = int(n * (1 - test_fraction))
    print(f"\nTemporal split: train rows 0-{split_idx-1} ({split_idx:,}), "
          f"test rows {split_idx}-{n-1} ({n - split_idx:,})")
    print(f"  Train = {100*(1-test_fraction):.0f}% of data (earlier), "
          f"Test = {100*test_fraction:.0f}% (later)")
    return X[:split_idx], X[split_idx:], y[:split_idx], y[split_idx:]


# ============================================
# NORMALISATION (fit on train, apply to test)
# ============================================

def fit_normalizer(X_train):
    """Compute mean/std from training data only."""
    mean = X_train.mean(axis=0)
    std  = X_train.std(axis=0)
    std[std == 0] = 1.0
    return mean, std

def apply_norm(X, mean, std):
    return (X - mean) / std


# ============================================
# GRID SEARCH WITH TIMESERIES SPLIT
# ============================================

def search_best_params(X_train_norm, y_class, param_grid, n_splits=5, n_jobs=1):
    """
    Run GridSearchCV with TimeSeriesSplit for one binary hazard class.

    TimeSeriesSplit creates n_splits folds where each fold's test window
    is strictly after its training window — no future data leaks into
    any training fold. Scored on F1-macro to penalise class imbalance.
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)

    # scale_pos_weight from full training set
    pos = y_class.sum()
    neg = len(y_class) - pos
    spw = neg / pos if pos > 0 else 1.0

    clf = xgb.XGBClassifier(
        **BASE_XGB_PARAMS,
        scale_pos_weight=spw,
        use_label_encoder=False,
    )

    gs = GridSearchCV(
        clf,
        param_grid,
        cv=tscv,
        scoring='f1_macro',
        n_jobs=n_jobs,
        refit=True,
        verbose=0,
    )
    gs.fit(X_train_norm, y_class)

    print(f"    Best params: {gs.best_params_}")
    print(f"    CV F1-macro: {gs.best_score_:.4f}")
    return gs.best_estimator_, gs.best_params_, gs.best_score_


# ============================================
# SHAP ANALYSIS
# ============================================

def compute_shap_importance(model, X_test_norm, feature_names):
    """
    Compute SHAP values (TreeExplainer - exact, not sampling-based).
    Returns a dict of {feature_name: mean_abs_shap}.
    """
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test_norm)

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    importance = dict(zip(feature_names, mean_abs_shap.tolist()))
    return importance, shap_values


def get_pruned_features(shap_importances_all, feature_names, threshold=SHAP_PRUNE_THRESHOLD):
    """
    Aggregate SHAP importance across all hazard classes and identify
    features to drop (mean |SHAP| < threshold * max across all classes).
    """
    # Average importance across hazard classes
    combined = {}
    for hazard, imp in shap_importances_all.items():
        for feat, val in imp.items():
            combined[feat] = combined.get(feat, 0) + val
    for feat in combined:
        combined[feat] /= len(shap_importances_all)

    max_imp = max(combined.values()) if combined else 1.0
    keep = [f for f in feature_names if combined.get(f, 0) >= threshold * max_imp]
    drop = [f for f in feature_names if combined.get(f, 0) < threshold * max_imp]

    return keep, drop, combined


# ============================================
# FULL TRAINING PIPELINE
# ============================================

def train_models(
    X, y, feature_names, output_dir,
    param_grid=FULL_PARAM_GRID,
    n_splits=5,
    prune_features=False,
    n_jobs=1,
):
    """Train one XGBoost model per hazard class with temporal CV + SHAP."""

    os.makedirs(output_dir, exist_ok=True)

    # 1. Chronological train/test split
    X_train, X_test, y_train, y_test = temporal_train_test_split(X, y)

    # 2. Normalize (fit on train ONLY)
    mean, std = fit_normalizer(X_train)
    X_train_norm = apply_norm(X_train, mean, std)
    X_test_norm  = apply_norm(X_test,  mean, std)

    # 3. Save normalisation stats
    norm_stats = {
        'mean':          mean.tolist(),
        'std':           std.tolist(),
        'feature_names': feature_names,
    }
    with open(os.path.join(output_dir, 'normalization.json'), 'w') as f:
        json.dump(norm_stats, f, indent=2)

    # 4. Train + evaluate per class
    models = {}
    all_metrics = {}
    shap_importances = {}

    n_total = len(param_grid.get('max_depth', [1])) * \
              len(param_grid.get('learning_rate', [1])) * \
              len(param_grid.get('n_estimators', [1])) * \
              len(param_grid.get('min_child_weight', [1]))
    print(f"\nGrid size: {n_total} combinations x {n_splits} folds x {len(HAZARD_CLASSES)} classes "
          f"= {n_total * n_splits * len(HAZARD_CLASSES)} fits")

    for idx, hazard in enumerate(HAZARD_CLASSES):
        print(f"\n{'='*60}")
        print(f"  [{idx+1}/{len(HAZARD_CLASSES)}] {hazard.upper()}")
        print(f"{'='*60}")

        y_tr = y_train[:, idx]
        y_te = y_test[:,  idx]

        pos_tr = y_tr.sum()
        pos_te = y_te.sum()
        print(f"  Train: {int(pos_tr):,} pos / {len(y_tr):,} total ({100*pos_tr/len(y_tr):.1f}%)")
        print(f"  Test:  {int(pos_te):,} pos / {len(y_te):,} total ({100*pos_te/len(y_te):.1f}%)")

        # Grid search with TimeSeriesSplit
        print(f"  Running GridSearchCV ({n_splits} folds)...")
        best_model, best_params, cv_score = search_best_params(
            X_train_norm, y_tr, param_grid, n_splits, n_jobs
        )

        # SHAP analysis on test set
        print(f"  Computing SHAP values...")
        imp, shap_vals = compute_shap_importance(best_model, X_test_norm, feature_names)
        shap_importances[hazard] = imp

        # Evaluate at production threshold
        threshold = ALERT_THRESHOLDS[hazard]
        y_pred_prob = best_model.predict_proba(X_test_norm)[:, 1]
        y_pred = (y_pred_prob >= threshold).astype(int)

        report = classification_report(y_te, y_pred, output_dict=True, zero_division=0)
        prec, rec, f1, sup = precision_recall_fscore_support(
            y_te, y_pred, labels=[0, 1], zero_division=0
        )

        print(f"\n  --- Per-class metrics at threshold={threshold} ---")
        print(f"  {'Class':<15} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
        print(f"  {'-'*55}")
        class_labels = ['No hazard (0)', f'{hazard} (1)']
        for i, lbl in enumerate(class_labels):
            print(f"  {lbl:<15} {prec[i]:>10.3f} {rec[i]:>10.3f} {f1[i]:>10.3f} {int(sup[i]):>10,}")
        f1_macro = f1_score(y_te, y_pred, average='macro', zero_division=0)
        print(f"  {'Macro avg':<15} {'-':>10} {'-':>10} {f1_macro:>10.3f}")

        metrics = {
            'cv_f1_macro':   cv_score,
            'accuracy':      report.get('accuracy', 0.0),
            'precision_pos': float(prec[1]),
            'recall_pos':    float(rec[1]),
            'f1_pos':        float(f1[1]),
            'f1_macro':      f1_macro,
            'support_pos':   int(sup[1]),
            'threshold':     threshold,
            'best_params':   best_params,
            'n_trees':       best_model.n_estimators,
        }

        models[hazard]     = best_model
        all_metrics[hazard] = metrics

        # Show top SHAP features for this class
        sorted_imp = sorted(imp.items(), key=lambda x: x[1], reverse=True)
        print(f"\n  Top-10 SHAP features for {hazard}:")
        for feat, val in sorted_imp[:10]:
            bar = '#' * int(val / max(imp.values()) * 20) if max(imp.values()) > 0 else ''
            print(f"    {feat:<25} {val:8.4f}  {bar}")

    # 5. SHAP-based feature pruning report
    print(f"\n{'='*60}")
    print("  SHAP-BASED FEATURE IMPORTANCE (across all hazards)")
    print(f"{'='*60}")
    keep_feats, drop_feats, combined_imp = get_pruned_features(shap_importances, feature_names)
    sorted_combined = sorted(combined_imp.items(), key=lambda x: x[1], reverse=True)
    max_imp_val = sorted_combined[0][1] if sorted_combined else 1.0
    for feat, val in sorted_combined:
        pct = 100 * val / max_imp_val
        flag = '  *** LOW IMPORTANCE - prune candidate ***' if feat in drop_feats else ''
        print(f"  {feat:<25} {val:8.4f}  ({pct:5.1f}%){flag}")

    print(f"\n  Features to KEEP ({len(keep_feats)}): {keep_feats}")
    print(f"  Features to DROP ({len(drop_feats)}): {drop_feats}")

    # 6. Optionally retrain with pruned features
    pruned_models = {}
    if prune_features and drop_feats:
        print(f"\n{'='*60}")
        print("  RETRAINING WITH PRUNED FEATURES")
        print(f"{'='*60}")
        keep_idx = [feature_names.index(f) for f in keep_feats]
        X_train_pruned = X_train_norm[:, keep_idx]
        X_test_pruned  = X_test_norm[:,  keep_idx]

        for idx, hazard in enumerate(HAZARD_CLASSES):
            y_tr = y_train[:, idx]
            y_te = y_test[:,  idx]

            best_params = all_metrics[hazard]['best_params']
            pos = y_tr.sum()
            neg = len(y_tr) - pos
            spw = neg / pos if pos > 0 else 1.0

            pruned_clf = xgb.XGBClassifier(
                **BASE_XGB_PARAMS,
                **best_params,
                scale_pos_weight=spw,
                use_label_encoder=False,
            )
            pruned_clf.fit(X_train_pruned, y_tr)

            threshold = ALERT_THRESHOLDS[hazard]
            y_pred = (pruned_clf.predict_proba(X_test_pruned)[:, 1] >= threshold).astype(int)
            f1_pruned = f1_score(y_te, y_pred, average='macro', zero_division=0)
            f1_full   = all_metrics[hazard]['f1_macro']

            print(f"  {hazard}: F1-macro {f1_full:.4f} -> {f1_pruned:.4f} "
                  f"({'improved' if f1_pruned > f1_full else 'unchanged/worse'})")
            all_metrics[hazard]['f1_macro_pruned'] = f1_pruned
            pruned_models[hazard] = pruned_clf

        # Save pruned norm stats
        mean_pruned = mean[keep_idx]
        std_pruned  = std[keep_idx]
        norm_pruned = {
            'mean':          mean_pruned.tolist(),
            'std':           std_pruned.tolist(),
            'feature_names': keep_feats,
        }
        with open(os.path.join(output_dir, 'normalization_pruned.json'), 'w') as f:
            json.dump(norm_pruned, f, indent=2)

    # 7. Save everything
    export_models = pruned_models if (prune_features and pruned_models) else models
    for hazard, model in export_models.items():
        path = os.path.join(output_dir, f'xgboost_{hazard}.json')
        model.save_model(path)
        print(f"Saved {hazard} model -> {path}")

    with open(os.path.join(output_dir, 'metrics.json'), 'w') as f:
        json.dump(all_metrics, f, indent=2)

    shap_report = {
        'per_hazard': shap_importances,
        'combined':   combined_imp,
        'keep_features': keep_feats,
        'drop_features': drop_feats,
        'prune_threshold': SHAP_PRUNE_THRESHOLD,
    }
    with open(os.path.join(output_dir, 'shap_importance.json'), 'w') as f:
        json.dump(shap_report, f, indent=2)

    final_feat_names = keep_feats if (prune_features and drop_feats) else feature_names
    with open(os.path.join(output_dir, 'feature_names.json'), 'w') as f:
        json.dump(final_feat_names, f, indent=2)

    # 8. Final summary table
    print(f"\n{'='*60}")
    print("  FINAL RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"  {'Hazard':<15} {'CV F1-mac':>10} {'Test F1-mac':>12} {'Prec':>8} {'Recall':>8} {'F1-pos':>8}")
    print(f"  {'-'*65}")
    for hazard in HAZARD_CLASSES:
        m = all_metrics[hazard]
        pruned_marker = '*' if 'f1_macro_pruned' in m else ' '
        print(f"  {hazard:<15} {m['cv_f1_macro']:>10.4f} {m['f1_macro']:>12.4f} "
              f"{m['precision_pos']:>8.3f} {m['recall_pos']:>8.3f} {m['f1_pos']:>8.3f}{pruned_marker}")
    print(f"  (* = metrics before pruning; pruned F1 logged in metrics.json)")

    print(f"\n  All outputs saved to: {output_dir}/")
    return models, all_metrics, norm_stats


# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description='Train Edge AI Weather Station models v2 (temporal CV + SHAP)'
    )
    parser.add_argument('--data',           type=str, required=True,
                        help='Prepared data directory (from prepare_dataset_v2.py)')
    parser.add_argument('--output',         type=str, required=True,
                        help='Output model directory')
    parser.add_argument('--fast',           action='store_true',
                        help='Use reduced param grid for quick iteration (~3 min)')
    parser.add_argument('--prune-features', action='store_true',
                        help='Re-train with SHAP-pruned features for lean ESP32 export')
    parser.add_argument('--n-splits',       type=int, default=5,
                        help='Number of TimeSeriesSplit folds (default: 5)')
    parser.add_argument('--n-jobs',         type=int, default=1,
                        help='Grid-search workers (default: 1; use more only when supported)')
    parser.add_argument('--export-c',       action='store_true',
                        help='Also generate C headers (calls convert_to_c.py)')
    parser.add_argument('--c-output',       type=str,
                        help='C header output path (required with --export-c)')
    parser.add_argument('--max-trees',      type=int, default=16,
                        help='Max trees per class for C export (default: 16)')
    args = parser.parse_args()

    print(f"\nEdge AI Weather Station — Model Training v2")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'FAST' if args.fast else 'FULL'} grid, "
          f"{'pruned' if args.prune_features else 'full'} features, "
          f"{args.n_splits} CV folds")

    # Load data
    X, y, feature_names = load_prepared_data(args.data)

    # Select grid
    param_grid = FAST_PARAM_GRID if args.fast else FULL_PARAM_GRID
    combos = (len(param_grid['max_depth']) * len(param_grid['learning_rate']) *
              len(param_grid['n_estimators']) * len(param_grid['min_child_weight']))
    print(f"Param grid: {combos} combinations")

    # Train
    models, metrics, norm_stats = train_models(
        X, y, feature_names, args.output,
        param_grid=param_grid,
        n_splits=args.n_splits,
        prune_features=args.prune_features,
        n_jobs=args.n_jobs,
    )

    # Export to C if requested
    if args.export_c:
        if not args.c_output:
            print("Error: --c-output required when --export-c is used")
            return 1
        print(f"\nGenerating C headers...")
        from convert_to_c import load_model_trees, load_model_base_scores, generate_model_header
        trees_by_class = load_model_trees(args.output, args.max_trees)
        base_scores = load_model_base_scores(args.output)
        generate_model_header(trees_by_class, norm_stats, args.c_output, base_scores)
        print(f"Generated {args.c_output}")

    print(f"\nDone! {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return 0


if __name__ == '__main__':
    exit(main())
