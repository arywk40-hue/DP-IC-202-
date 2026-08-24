#include "HazardModel.h"

#include <math.h>

#include "model_data_india_26_masked_distilled_edge.h"

namespace edge_ai {
namespace {

constexpr float kAlertThresholds[kHazardCount] = {
    0.70f,
    0.70f,
    0.75f,
    0.65f,
};

constexpr const char* kHazardNames[kHazardCount] = {
    "wildfire",
    "flood",
    "storm",
    "air_quality",
};

size_t hazard_index(Hazard hazard) {
    return static_cast<size_t>(hazard);
}

}  // namespace

static_assert(NUM_FEATURES == kFeatureCount, "Firmware and model feature counts differ");
static_assert(NUM_CLASSES == kHazardCount, "Firmware and model class counts differ");

bool predict(const float* features, size_t feature_count, Prediction* output) {
    if (features == nullptr || output == nullptr || feature_count != kFeatureCount) {
        return false;
    }

    for (size_t i = 0; i < feature_count; ++i) {
        if (!isfinite(features[i])) {
            return false;
        }
    }

    xgb_model_inference(
        features,
        &output->probabilities[0],
        &output->probabilities[1],
        &output->probabilities[2],
        &output->probabilities[3]);

    output->alert_mask = 0;
    for (size_t i = 0; i < kHazardCount; ++i) {
        const float probability = output->probabilities[i];
        if (!isfinite(probability) || probability < 0.0f || probability > 1.0f) {
            return false;
        }
        if (probability >= kAlertThresholds[i]) {
            output->alert_mask |= static_cast<uint8_t>(1U << i);
        }
    }
    return true;
}

bool is_alert(Hazard hazard, const Prediction& prediction) {
    const size_t index = hazard_index(hazard);
    return index < kHazardCount && (prediction.alert_mask & (1U << index)) != 0;
}

const char* hazard_name(Hazard hazard) {
    const size_t index = hazard_index(hazard);
    return index < kHazardCount ? kHazardNames[index] : "unknown";
}

float alert_threshold(Hazard hazard) {
    const size_t index = hazard_index(hazard);
    return index < kHazardCount ? kAlertThresholds[index] : 1.0f;
}

}  // namespace edge_ai

