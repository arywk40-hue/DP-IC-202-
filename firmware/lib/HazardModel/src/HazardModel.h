#pragma once

#include <stddef.h>
#include <stdint.h>

namespace edge_ai {

constexpr size_t kFeatureCount = 14;
constexpr size_t kHazardCount = 4;

enum class Hazard : uint8_t {
    Wildfire = 0,
    Flood = 1,
    Storm = 2,
    AirQuality = 3,
};

struct Prediction {
    float probabilities[kHazardCount];
    uint8_t alert_mask;
};

bool predict(const float* features, size_t feature_count, Prediction* output);
bool is_alert(Hazard hazard, const Prediction& prediction);
const char* hazard_name(Hazard hazard);
float alert_threshold(Hazard hazard);

}  // namespace edge_ai

