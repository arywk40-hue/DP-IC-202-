/**
 * normalization.h - Feature normalization for Edge AI Weather Station
 * Auto-generated from training data
 */

#ifndef NORMALIZATION_H
#define NORMALIZATION_H

#include <stdint.h>

// Z-score normalization: (x - mean) / std
static const float NORM_MEAN[14] = {
    27.483618f,  // temp_current
    57.453642f,  // humidity_current
    1010.000126f,  // pressure_current
    7.507594f,  // wind_speed_current
    52.329394f,  // pm25_current
    475.266674f,  // co2_current
    24.960097f,  // lightning_dist_current
    0.572071f,  // temp_humidity_ratio
    0.000453f,  // pressure_trend
    56.210439f,  // heat_index
    18.974346f,  // dew_point
    0.468330f,  // fire_risk_index
    0.266900f,  // flood_risk_index
    0.401061f,  // lightning_threat
};

static const float NORM_STD[14] = {
    7.212393f,  // temp_current
    21.590452f,  // humidity_current
    8.664473f,  // pressure_current
    4.302041f,  // wind_speed_current
    27.521482f,  // pm25_current
    72.339095f,  // co2_current
    14.432792f,  // lightning_dist_current
    0.316789f,  // temp_humidity_ratio
    2.082049f,  // pressure_trend
    12.890250f,  // heat_index
    8.348996f,  // dew_point
    0.243275f,  // fire_risk_index
    0.243892f,  // flood_risk_index
    0.326382f,  // lightning_threat
};

// Normalize a feature vector in-place
static inline void normalize_features(float *features, int num_features) {
    int n = num_features < NUM_FEATURES ? num_features : NUM_FEATURES;
    for (int i = 0; i < n; i++) {
        features[i] = (features[i] - NORM_MEAN[i]) / NORM_STD[i];
    }
}

#endif // NORMALIZATION_H
