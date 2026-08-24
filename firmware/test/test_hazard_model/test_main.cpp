#include <math.h>
#include <string.h>

#include <unity.h>

#include "HazardModel.h"

#ifdef ARDUINO
#include <Arduino.h>
#endif

namespace {

const float kNominalFeatures[edge_ai::kFeatureCount] = {
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

void test_nominal_prediction_is_valid() {
    edge_ai::Prediction prediction{};
    TEST_ASSERT_TRUE(edge_ai::predict(kNominalFeatures, edge_ai::kFeatureCount, &prediction));
    for (size_t i = 0; i < edge_ai::kHazardCount; ++i) {
        TEST_ASSERT_TRUE(isfinite(prediction.probabilities[i]));
        TEST_ASSERT_GREATER_OR_EQUAL_FLOAT(0.0f, prediction.probabilities[i]);
        TEST_ASSERT_LESS_OR_EQUAL_FLOAT(1.0f, prediction.probabilities[i]);
    }
}

void test_prediction_is_deterministic() {
    edge_ai::Prediction first{};
    edge_ai::Prediction second{};
    TEST_ASSERT_TRUE(edge_ai::predict(kNominalFeatures, edge_ai::kFeatureCount, &first));
    TEST_ASSERT_TRUE(edge_ai::predict(kNominalFeatures, edge_ai::kFeatureCount, &second));
    TEST_ASSERT_EQUAL_UINT8(first.alert_mask, second.alert_mask);
    for (size_t i = 0; i < edge_ai::kHazardCount; ++i) {
        TEST_ASSERT_EQUAL_FLOAT(first.probabilities[i], second.probabilities[i]);
    }
}

void test_invalid_input_is_rejected() {
    edge_ai::Prediction prediction{};
    float invalid[edge_ai::kFeatureCount];
    memcpy(invalid, kNominalFeatures, sizeof(invalid));
    invalid[3] = NAN;

    TEST_ASSERT_FALSE(edge_ai::predict(nullptr, edge_ai::kFeatureCount, &prediction));
    TEST_ASSERT_FALSE(edge_ai::predict(invalid, edge_ai::kFeatureCount, &prediction));
    TEST_ASSERT_FALSE(edge_ai::predict(kNominalFeatures, edge_ai::kFeatureCount - 1, &prediction));
    TEST_ASSERT_FALSE(edge_ai::predict(kNominalFeatures, edge_ai::kFeatureCount, nullptr));
}

void test_alert_mask_matches_thresholds() {
    edge_ai::Prediction prediction{};
    TEST_ASSERT_TRUE(edge_ai::predict(kNominalFeatures, edge_ai::kFeatureCount, &prediction));
    for (size_t i = 0; i < edge_ai::kHazardCount; ++i) {
        const auto hazard = static_cast<edge_ai::Hazard>(i);
        const bool expected = prediction.probabilities[i] >= edge_ai::alert_threshold(hazard);
        TEST_ASSERT_EQUAL(expected, edge_ai::is_alert(hazard, prediction));
    }
}

void run_tests() {
    UNITY_BEGIN();
    RUN_TEST(test_nominal_prediction_is_valid);
    RUN_TEST(test_prediction_is_deterministic);
    RUN_TEST(test_invalid_input_is_rejected);
    RUN_TEST(test_alert_mask_matches_thresholds);
    UNITY_END();
}

}  // namespace

#ifdef ARDUINO
void setup() {
    delay(2000);
    run_tests();
}

void loop() {}
#else
int main() {
    run_tests();
    return 0;
}
#endif

