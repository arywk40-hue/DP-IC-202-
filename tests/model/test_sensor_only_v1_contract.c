#include <stdio.h>
#include <string.h>

#include "model_data_sensor_only_v1_not_ready.h"

int main(void) {
    if (SENSOR_ONLY_V1_NUM_FEATURES != 14) return 1;
    if (strcmp(SENSOR_ONLY_V1_SCHEMA_VERSION, "sensor_only_v1") != 0) return 2;
    if (strcmp(SENSOR_ONLY_V1_MODEL_STATUS, "NOT_READY") != 0) return 3;
    if (strcmp(sensor_only_v1_feature_names[0], "temperature_c") != 0) return 4;
    if (strcmp(sensor_only_v1_feature_names[13], "longitude_deg") != 0) return 5;
    puts("sensor_only_v1 C contract: PASS (model NOT_READY)");
    return 0;
}
