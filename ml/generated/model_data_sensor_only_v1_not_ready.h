#pragma once

/* Schema export only: no predictor is present until a real model is validated. */
#define SENSOR_ONLY_V1_SCHEMA_VERSION "sensor_only_v1"
#define SENSOR_ONLY_V1_SCHEMA_CHECKSUM "a85fd11ea784026b6b27a0157a4498567102e71c82b9e689ddcbbb5698c2c441"
#define SENSOR_ONLY_V1_MODEL_STATUS "NOT_READY"
#define SENSOR_ONLY_V1_MODEL_CHECKSUM "NOT_READY-no-trained-model"
#define SENSOR_ONLY_V1_NUM_FEATURES 14

static const char* const sensor_only_v1_feature_names[SENSOR_ONLY_V1_NUM_FEATURES] = {
    "temperature_c", "relative_humidity_pct", "pressure_hpa", "wind_speed_mps",
    "pm25_ug_m3", "pressure_trend_hpa_per_hour", "dew_point_c", "heat_index_c",
    "hour_sin", "hour_cos", "day_of_year_sin", "day_of_year_cos",
    "latitude_deg", "longitude_deg",
};
