/**
 * normalization.h - Feature normalization for Edge AI Weather Station
 * Auto-generated from training data
 */

#ifndef NORMALIZATION_H
#define NORMALIZATION_H

#include <stdint.h>

static const float NORM_MEAN[14] = {
    25.427949905f,  // temp_current
    0.654353499f,  // humidity_current
    1009.034484863f,  // pressure_current
    9.865414619f,  // wind_speed_current
    68.366226196f,  // pm25_current
    422.665649414f,  // co2_current
    41.132045746f,  // lightning_dist_current
    44.399394989f,  // temp_humidity_ratio
    -0.009046700f,  // pressure_trend
    58.145809174f,  // heat_index
    18.515108109f,  // dew_point
    0.426380575f,  // fire_risk_index
    0.253984988f,  // flood_risk_index
    0.338856399f,  // lightning_threat
};

static const float NORM_STD[14] = {
    5.491669178f,  // temp_current
    0.172620937f,  // humidity_current
    5.863323212f,  // pressure_current
    3.907968998f,  // wind_speed_current
    61.931686401f,  // pm25_current
    22.882358551f,  // co2_current
    33.145591736f,  // lightning_dist_current
    26.102348328f,  // temp_humidity_ratio
    0.572993636f,  // pressure_trend
    8.749422073f,  // heat_index
    5.553127289f,  // dew_point
    0.228003964f,  // fire_risk_index
    0.230335698f,  // flood_risk_index
    0.362432837f,  // lightning_threat
};

// Normalize feature vector in-place
static inline void normalize_features(float *features, int num_features) {
    int n = num_features < 14 ? num_features : 14;
    for (int i = 0; i < n; i++) {
        features[i] = (features[i] - NORM_MEAN[i]) / NORM_STD[i];
    }
}

#endif // NORMALIZATION_H
