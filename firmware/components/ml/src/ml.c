/**
 * ml.c - XGBoost Inference Engine for ESP32-S3
 *
 * Real implementation using auto-generated model_data.h from convert_to_c.py
 * Iterative (non-recursive) tree traversal for embedded inference.
 *
 * Generated headers must be present:
 *   - model_data.h (trees, inference functions)
 *   - normalization.h (z-score constants)
 *   - model_metadata.h (feature/class names)
 */

#include <string.h>
#include <math.h>
#include "esp_log.h"
#include "ml.h"
#include "common.h"

// Include auto-generated model data
#include "model_data.h"
#include "normalization.h"
#include "model_metadata.h"

static const char *TAG = "ML";

static bool g_initialized = false;
static uint32_t g_last_inference_us = 0;

// Forward declaration from model_data.h
extern void normalize_features(float *features, int num_features);
extern void xgb_model_inference(
    const float *features_raw,
    float *output_wildfire,
    float *output_flood,
    float *output_storm,
    float *output_air_quality
);

esp_err_t ml_init(void)
{
    ESP_LOGI(TAG, "Initializing ML inference engine...");
    
    // Verify model constants
    if (NUM_FEATURES != ML_FEATURE_COUNT) {
        ESP_LOGE(TAG, "Feature count mismatch: model has %d, firmware expects %d",
                 NUM_FEATURES, ML_FEATURE_COUNT);
        return ESP_ERR_INVALID_STATE;
    }
    
    if (NUM_CLASSES != ML_MAX_CLASSES) {
        ESP_LOGE(TAG, "Class count mismatch: model has %d, firmware expects %d",
                 NUM_CLASSES, ML_MAX_CLASSES);
        return ESP_ERR_INVALID_STATE;
    }
    
    // Verify model data is present
    if (WILDFIRE_NUM_TREES == 0 || FLOOD_NUM_TREES == 0 ||
        STORM_NUM_TREES == 0 || AIR_QUALITY_NUM_TREES == 0) {
        ESP_LOGE(TAG, "Model trees not loaded — check model_data.h generation");
        return ESP_ERR_INVALID_STATE;
    }
    
    g_initialized = true;
    ESP_LOGI(TAG, "ML engine ready: %d features, %d classes, trees per class: [%d, %d, %d, %d]",
             ML_FEATURE_COUNT, ML_MAX_CLASSES,
             WILDFIRE_NUM_TREES, FLOOD_NUM_TREES,
             STORM_NUM_TREES, AIR_QUALITY_NUM_TREES);
    
    return ESP_OK;
}

esp_err_t ml_normalize(const float *raw, float *norm)
{
    if (raw == NULL || norm == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    if (!g_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    
    // Copy raw features
    for (int i = 0; i < ML_FEATURE_COUNT; i++) {
        norm[i] = raw[i];
    }
    
    // Apply z-score normalization using generated constants
    normalize_features(norm, ML_FEATURE_COUNT);
    
    return ESP_OK;
}

esp_err_t ml_predict(const float *features, uint8_t class_id, float *output)
{
    if (features == NULL || output == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    if (!g_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    if (class_id >= ML_MAX_CLASSES) {
        return ESP_ERR_INVALID_ARG;
    }
    
    // Use the auto-generated model inference
    float wildfire = 0, flood = 0, storm = 0, air_quality = 0;
    
    uint32_t start = esp_timer_get_time();
    xgb_model_inference(features, &wildfire, &flood, &storm, &air_quality);
    g_last_inference_us = esp_timer_get_time() - start;
    
    // Return requested class probability
    switch (class_id) {
        case 0: *output = wildfire; break;
        case 1: *output = flood; break;
        case 2: *output = storm; break;
        case 3: *output = air_quality; break;
        default: *output = 0.0f; break;
    }
    
    return ESP_OK;
}

float ml_confidence(float raw_output)
{
    // Sigmoid: 1 / (1 + exp(-x))
    if (raw_output > 50.0f)  return 1.0f;
    if (raw_output < -50.0f) return 0.0f;
    return 1.0f / (1.0f + expf(-raw_output));
}

size_t ml_model_ram_usage(void)
{
    // Model is stored in flash (const), only stack used at runtime
    return sizeof(float) * ML_FEATURE_COUNT * 2;  // input + norm buffers
}

size_t ml_model_flash_usage(void)
{
    // Estimate: 4 classes * 16 trees * 32 nodes * sizeof(xgb_node_t)
    size_t nodes_per_tree = MAX_NODES_PER_TREE;
    size_t node_size = sizeof(int8_t) + sizeof(float) + 2*sizeof(int16_t) + sizeof(float);
    return NUM_CLASSES * MAX_TREES_PER_CLASS * nodes_per_tree * node_size;
}

uint32_t ml_last_inference_us(void)
{
    return g_last_inference_us;
}