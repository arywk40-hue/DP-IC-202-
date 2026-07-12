"""
train_model.py - XGBoost model training for Edge AI Weather Station

Trains hazard detection model and converts to C header for ESP32-S3

Usage:
    python train_model.py --data ./data/ --output ./model/
    python convert_to_c.py --model ./model/xgboost.json --output ./firmware/lib/model_data.h
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import argparse
import json
import os

# ============================================
# FEATURE DEFINITIONS
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

# Hazard classes
HAZARD_CLASSES = ['wildfire', 'flood', 'storm', 'air_quality']

# ============================================
# DATA LOADING
# ============================================

def load_data(data_dir):
    """Load training data from CSV files"""
    features_path = os.path.join(data_dir, 'features.csv')
    labels_path = os.path.join(data_dir, 'labels.csv')
    
    if os.path.exists(features_path) and os.path.exists(labels_path):
        X = pd.read_csv(features_path)
        y = pd.read_csv(labels_path)
        return X.values, y.values
    
    # Generate synthetic data for demo
    print("Generating synthetic training data...")
    return generate_synthetic_data()

def generate_synthetic_data(n_samples=5000):
    """Generate synthetic training data for demonstration"""
    np.random.seed(42)
    
    X = np.zeros((n_samples, len(FEATURE_NAMES)))
    y = np.zeros((n_samples, len(HAZARD_CLASSES)))
    
    for i in range(n_samples):
        # Random base weather
        temp = np.random.uniform(15, 40)
        humidity = np.random.uniform(20, 95)
        pressure = np.random.uniform(995, 1025)
        wind_speed = np.random.uniform(0, 15)
        pm25 = np.random.uniform(5, 100)
        co2 = np.random.uniform(350, 600)
        lightning_dist = np.random.uniform(0, 50)
        
        # Derived features
        temp_humidity_ratio = temp / max(humidity, 1)
        heat_index = temp + 0.5 * humidity  # Simplified
        dew_point = temp - (100 - humidity) / 5
        fire_risk = 0.0
        flood_risk = 0.0
        lightning_threat = max(0, (40 - lightning_dist) / 40)
        
        # Determine hazard labels
        wildfire = 0
        flood = 0
        storm = 0
        air_quality = 0
        
        # Wildfire conditions
        if temp > 30 and humidity < 35 and wind_speed > 5 and pm25 > 40:
            wildfire = 1
            fire_risk = 0.8
        
        # Flood conditions
        if pressure < 1000 and humidity > 85 and wind_speed > 8:
            flood = 1
            flood_risk = 0.7
        
        # Storm conditions
        if lightning_dist < 15 and pressure < 1005:
            storm = 1
        
        # Air quality conditions
        if pm25 > 75 or co2 > 550:
            air_quality = 1
        
        X[i] = [temp, humidity, pressure, wind_speed, pm25, co2, lightning_dist,
                temp_humidity_ratio, heat_index, dew_point, fire_risk, flood_risk,
                lightning_threat, 0]  # pressure_trend placeholder
        
        y[i] = [wildfire, flood, storm, air_quality]
    
    return X, y

# ============================================
# MODEL TRAINING
# ============================================

def train_model(X, y, output_dir):
    """Train XGBoost multi-output model"""
    print(f"Training data shape: X={X.shape}, y={y.shape}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    models = {}
    metrics = {}
    
    # Train one model per hazard class
    for idx, hazard in enumerate(HAZARD_CLASSES):
        print(f"\nTraining {hazard} model...")
        
        # Create DMatrix
        dtrain = xgb.DMatrix(X_train, label=y_train[:, idx])
        dtest = xgb.DMatrix(X_test, label=y_test[:, idx])
        
        # XGBoost parameters (tuned for ESP32-S3)
        params = {
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            'max_depth': 4,           # Shallow trees for ESP32
            'min_child_weight': 2,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'learning_rate': 0.1,
            'gamma': 0.1,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'tree_method': 'hist',    # Fast training
            'seed': 42,
        }
        
        # Train
        model = xgb.train(
            params,
            dtrain,
            num_boost_round=16,       # Limit trees for ESP32
            evals=[(dtrain, 'train'), (dtest, 'test')],
            early_stopping_rounds=5,
            verbose_eval=False,
        )
        
        models[hazard] = model
        
        # Evaluate
        y_pred = (model.predict(dtest) > 0.5).astype(int)
        report = classification_report(y_test[:, idx], y_pred, output_dict=True)
        metrics[hazard] = {
            'accuracy': report['accuracy'],
            'precision': report['1']['precision'] if '1' in report else 0,
            'recall': report['1']['recall'] if '1' in report else 0,
            'f1': report['1']['f1-score'] if '1' in report else 0,
        }
        
        print(f"  Accuracy: {metrics[hazard]['accuracy']:.3f}")
        print(f"  Precision: {metrics[hazard]['precision']:.3f}")
        print(f"  Recall: {metrics[hazard]['recall']:.3f}")
        print(f"  Trees: {model.best_ntree_limit}")
    
    # Save models
    os.makedirs(output_dir, exist_ok=True)
    
    for hazard, model in models.items():
        model_path = os.path.join(output_dir, f'xgboost_{hazard}.json')
        model.save_model(model_path)
        print(f"Saved {hazard} model to {model_path}")
    
    # Save metrics
    metrics_path = os.path.join(output_dir, 'metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    # Save feature normalization stats
    norm_stats = {
        'mean': X.mean(axis=0).tolist(),
        'std': X.std(axis=0).tolist(),
    }
    norm_path = os.path.join(output_dir, 'normalization.json')
    with open(norm_path, 'w') as f:
        json.dump(norm_stats, f, indent=2)
    
    print(f"\nModels saved to {output_dir}")
    return models, metrics

# ============================================
# MODEL EXPORT TO C
# ============================================

def export_to_c(models, output_path):
    """Convert XGBoost model to C header for ESP32-S3"""
    
    print(f"\nExporting model to C header: {output_path}")
    
    with open(output_path, 'w') as f:
        f.write("/**\n")
        f.write(" * model_data.h - Auto-generated XGBoost model for ESP32-S3\n")
        f.write(" * \n")
        f.write(" * Generated by train_model.py\n")
        f.write(" */\n\n")
        f.write("#ifndef MODEL_DATA_H\n")
        f.write("#define MODEL_DATA_H\n\n")
        f.write("#include <stdint.h>\n\n")
        
        # Feature normalization
        f.write("// Feature normalization (from training data)\n")
        f.write("static const float FEATURE_MEAN[14] = {\n")
        for i, name in enumerate(FEATURE_NAMES):
            f.write(f"    0.0f,  // {name} (update from normalization.json)\n")
        f.write("};\n\n")
        
        f.write("static const float FEATURE_STD[14] = {\n")
        for i, name in enumerate(FEATURE_NAMES):
            f.write(f"    1.0f,  // {name} (update from normalization.json)\n")
        f.write("};\n\n")
        
        # Model parameters
        f.write("// Model configuration\n")
        f.write("#define NUM_TREES_PER_CLASS 16\n")
        f.write("#define NUM_CLASSES 4\n")
        f.write("#define MAX_NODES_PER_TREE 32\n\n")
        
        # Tree structure (simplified for ESP32)
        f.write("// XGBoost tree node structure\n")
        f.write("typedef struct {\n")
        f.write("    int8_t feature_idx;     // -1 for leaf\n")
        f.write("    float threshold;        // split threshold\n")
        f.write("    int16_t left_child;     // index of left child\n")
        f.write("    int16_t right_child;    // index of right child\n")
        f.write("    float leaf_value;       // prediction value\n")
        f.write("} xgb_node_t;\n\n")
        
        f.write("// XGBoost tree\n")
        f.write("typedef struct {\n")
        f.write("    uint8_t num_nodes;\n")
        f.write("    xgb_node_t nodes[MAX_NODES_PER_TREE];\n")
        f.write("} xgb_tree_t;\n\n")
        
        # Export each model
        for hazard in HAZARD_CLASSES:
            if hazard in models:
                model = models[hazard]
                trees = model.get_dump(with_stats=True)
                
                f.write(f"// {hazard.upper()} model trees\n")
                f.write(f"static const xgb_tree_t {hazard.upper()}_TREES[{len(trees)}] = {{\n")
                
                for i, tree_str in enumerate(trees):
                    f.write(f"    {{  // Tree {i}\n")
                    f.write(f"        .num_nodes = 0,  // Parse from JSON\n")
                    f.write(f"        .nodes = {{0}}\n")
                    f.write(f"    }},\n")
                
                f.write(f"}};\n\n")
        
        f.write("#endif // MODEL_DATA_H\n")
    
    print(f"C header written to {output_path}")

# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description='Train Edge AI Weather Station model')
    parser.add_argument('--data', type=str, default='./data/', help='Data directory')
    parser.add_argument('--output', type=str, default='./model/', help='Output directory')
    parser.add_argument('--export-c', action='store_true', help='Export to C header')
    args = parser.parse_args()
    
    # Load data
    X, y = load_data(args.data)
    
    # Train model
    models, metrics = train_model(X, y, args.output)
    
    # Export to C if requested
    if args.export_c:
        c_output = os.path.join(args.output, 'model_data.h')
        export_to_c(models, c_output)
    
    print("\nTraining complete!")
    print("Next steps:")
    print("1. Review metrics in model/metrics.json")
    print("2. Run: python convert_to_c.py --model model/ --output firmware/lib/model_data.h")
    print("3. Build and flash firmware to ESP32-S3")

if __name__ == '__main__':
    main()
