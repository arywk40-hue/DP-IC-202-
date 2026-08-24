#include <Arduino.h>

#include "HazardModel.h"

namespace {

constexpr float kSmokeTestFeatures[edge_ai::kFeatureCount] = {
    25.427949905f,
    0.654353499f,
    1009.034484863f,
    9.865414619f,
    68.366226196f,
    422.665649414f,
    41.132045746f,
    44.399394989f,
    -0.009046700f,
    58.145809174f,
    18.515108109f,
    0.426380575f,
    0.253984988f,
    0.338856399f,
};

void print_prediction() {
    edge_ai::Prediction prediction{};
    if (!edge_ai::predict(kSmokeTestFeatures, edge_ai::kFeatureCount, &prediction)) {
        Serial.println("{\"status\":\"inference_error\"}");
        return;
    }

    Serial.print("{\"status\":\"ok\",\"probabilities\":{");
    for (size_t i = 0; i < edge_ai::kHazardCount; ++i) {
        const auto hazard = static_cast<edge_ai::Hazard>(i);
        if (i > 0) {
            Serial.print(',');
        }
        Serial.printf("\"%s\":%.6f", edge_ai::hazard_name(hazard), prediction.probabilities[i]);
    }
    Serial.printf("},\"alert_mask\":%u}\n", prediction.alert_mask);
}

}  // namespace

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("Edge AI ESP32-S3 model smoke test");
    print_prediction();
}

void loop() {
    delay(5000);
    print_prediction();
}

