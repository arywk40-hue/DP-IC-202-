idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES 
        lora
        sensors
        ml
        mesh
        crypto
        driver
        esp_timer
        nvs_flash
        freertos
)
