#include <math.h>
#include <stdio.h>
#include <string.h>

#include "model_data_india_26_masked_distilled_edge.h"

int main(void) {
    if (strcmp(FEATURE_NAMES[0], "temp_current") != 0 ||
        strcmp(FEATURE_NAMES[NUM_FEATURES - 1], "lightning_threat") != 0) {
        fprintf(stderr, "unexpected edge feature schema\n");
        return 1;
    }

    const float features[NUM_FEATURES] = {
        25.427949905f, 0.654353499f, 1009.034484863f, 9.865414619f,
        68.366226196f, 422.665649414f, 41.132045746f, 44.399394989f,
        -0.009046700f, 58.145809174f, 18.515108109f, 0.426380575f,
        0.253984988f, 0.338856399f,
    };
    float probabilities[NUM_CLASSES] = {0};

    xgb_model_inference(
        features,
        &probabilities[0],
        &probabilities[1],
        &probabilities[2],
        &probabilities[3]);

    for (int i = 0; i < NUM_CLASSES; ++i) {
        if (!isfinite(probabilities[i]) || probabilities[i] < 0.0f || probabilities[i] > 1.0f) {
            fprintf(stderr, "invalid probability for class %d: %f\n", i, probabilities[i]);
            return 1;
        }
    }

    printf("model smoke test passed: %.6f %.6f %.6f %.6f\n",
           probabilities[0], probabilities[1], probabilities[2], probabilities[3]);
    return 0;
}
