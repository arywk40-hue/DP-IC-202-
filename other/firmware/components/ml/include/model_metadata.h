/**
 * model_metadata.h - Model metadata for debugging
 * Auto-generated
 */

#ifndef MODEL_METADATA_H
#define MODEL_METADATA_H

static const char *FEATURE_NAMES[14] = {
    "temp_current",
    "humidity_current",
    "pressure_current",
    "wind_speed_current",
    "pm25_current",
    "co2_current",
    "lightning_dist_current",
    "temp_humidity_ratio",
    "pressure_trend",
    "heat_index",
    "dew_point",
    "fire_risk_index",
    "flood_risk_index",
    "lightning_threat",
};

static const char *HAZARD_CLASS_NAMES[4] = {
    "wildfire",
    "flood",
    "storm",
    "air_quality",
};

static const float ALERT_THRESHOLDS[4] = {
    0.70f,  // wildfire
    0.70f,  // flood
    0.75f,  // storm
    0.65f,  // air_quality
};

#endif // MODEL_METADATA_H
