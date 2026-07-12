/**
 * ml.c - ML Inference Engine Implementation
 *
 * Stub implementation for Phase 1.
 * Will be replaced with a complete iterative XGBoost inference engine
 * in Phase 6/7 after the model-data pipeline is finalized.
 *
 * Current behavior:
 * - ml_init() returns ESP_OK (no model loaded yet).
 * - ml_predict() returns log-odds = 0.0 for any input.
 * - All validation and error propagation is in place.
 */

#include <string.h>
#include <math.h>
#include "esp_log.h"
#include "ml.h"

static const char *TAG = "ML";

/* Stub model metrics */
#define STUB_MODEL_RAM   4096
#define STUB_MODEL_FLASH 16384

static bool g_initialized = false;
static uint32_t g_last_inference_us = 0;

esp_err_t ml_init(void)
{
    ESP_LOGI(TAG, "ML inference engine initialized (stub — model loading pending Phase 7)");
    g_initialized = true;
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
    /* Stub — copy raw values as-is (no normalization yet) */
    for (int i = 0; i < ML_FEATURE_COUNT; i++) {
        norm[i] = raw[i];
    }
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
    /* Stub — return zero (no actual model loaded yet) */
    *output = 0.0f;
    g_last_inference_us = 1;
    return ESP_OK;
}

float ml_confidence(float raw_output)
{
    /*
     * Sigmoid: 1.0 / (1.0 + exp(-x))
     * Clamp to avoid expf overflow for large inputs.
     */
    if (raw_output > 50.0f)  return 1.0f;
    if (raw_output < -50.0f) return 0.0f;
    return 1.0f / (1.0f + expf(-raw_output));
}

size_t ml_model_ram_usage(void)
{
    return STUB_MODEL_RAM;
}

size_t ml_model_flash_usage(void)
{
    return STUB_MODEL_FLASH;
}

uint32_t ml_last_inference_us(void)
{
    return g_last_inference_us;
}
