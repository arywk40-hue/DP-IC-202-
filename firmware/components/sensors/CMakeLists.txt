idf_component_register(
    SRCS "src/bme280.c" "src/pms5003.c" "src/ds18b20.c"
    INCLUDE_DIRS "include"
    REQUIRES driver
)
