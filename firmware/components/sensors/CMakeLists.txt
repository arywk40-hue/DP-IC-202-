idf_component_register(
    SRCS "src/bme280.c" "src/pms5003.c" "src/ds18b20.c"
         "src/anemometer.c" "src/sen0575.c" "src/ltr390.c"
         "src/scd41.c" "src/sgp41.c" "src/mics6814.c"
         "src/as3935.c" "src/battery.c"
    INCLUDE_DIRS "include"
    REQUIRES driver esp_adc
)
