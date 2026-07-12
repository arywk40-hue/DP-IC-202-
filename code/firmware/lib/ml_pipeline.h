/**
 * ml_pipeline.h - Edge AI ML inference pipeline
 * 
 * XGBoost model training, conversion, and on-device inference
 * for ESP32-S3 weather anomaly detection
 */

#ifndef ML_PIPELINE_H
#define ML_PIPELINE_H

#include <stdint.h>
#include <stdbool.h>

/* ============================================
 * ML MODEL STRUCTURES
 * ============================================ */

// XGBoost tree node (compact for ESP32)
typedef struct {
    int8_t feature_idx;     // -1 for leaf
    float threshold;        // split threshold
    int16_t left_child;     // index of left child (-1 for leaf)
    int16_t right_child;    // index of right child
    float leaf_value;       // prediction value (if leaf)
} xgb_node_t;

// XGBoost tree
typedef struct {
    uint8_t num_nodes;
    xgb_node_t nodes[32];   // Max 32 nodes per tree
} xgb_tree_t;

// XGBoost model (ensemble of trees)
typedef struct {
    uint8_t num_trees;
    xgb_tree_t trees[16];   // Max 16 trees
    float base_score;       // Initial prediction
    float learning_rate;    // Shrinkage
} xgb_model_t;

// Inference result
typedef struct {
    uint8_t wildfire_risk;   // 0-100
    uint8_t flood_risk;      // 0-100
    uint8_t storm_risk;      // 0-100
    uint8_t air_quality;     // 0-100
    uint8_t overall_threat;  // 0-100
    uint8_t alert_code;      // bitfield
} ml_result_t;

// Model metadata
typedef struct {
    char version[16];
    uint32_t trained_samples;
    float accuracy;
    float precision;
    float recall;
    uint32_t model_size_bytes;
} ml_metadata_t;

/* ============================================
 * ML PIPELINE API
 * ============================================ */

/**
 * Initialize ML pipeline
 * Loads model from flash storage
 * @return true if model loaded successfully
 */
bool ml_pipeline_init(void);

/**
 * Run inference on feature vector
 * @param features - input features from sensor pipeline
 * @param result - output prediction
 * @return inference time in microseconds
 */
uint32_t ml_inference(const float *features, ml_result_t *result);

/**
 * Get model metadata
 */
ml_metadata_t ml_get_metadata(void);

/**
 * Update model with federated learning delta
 * @param delta - weight update from server
 * @param delta_size - size of delta in bytes
 * @return true if update applied
 */
bool ml_update_model(const uint8_t *delta, uint16_t delta_size);

/**
 * Export current model for aggregation
 * @param buffer - output buffer
 * @param max_size - buffer size
 * @return actual size written
 */
uint16_t ml_export_model(uint8_t *buffer, uint16_t max_size);

/* ============================================
 * PYTHON TRAINING PIPELINE
 * ============================================ */

/*
 * Python script to train XGBoost model and convert to C
 * 
 * Step 1: Collect training data
 *   - Record sensor readings with labeled hazard events
 *   - Minimum 1000 samples per hazard class
 *   - Save as CSV: features.csv, labels.csv
 * 
 * Step 2: Train XGBoost model
 *   - python train_model.py --data ./data/ --output model.json
 * 
 * Step 3: Convert to C header
 *   - python convert_to_c.py --model model.json --output model.h
 * 
 * Step 4: Deploy to ESP32-S3
 *   - Include model.h in firmware
 *   - Call ml_pipeline_init() to load
 */

#endif // ML_PIPELINE_H
