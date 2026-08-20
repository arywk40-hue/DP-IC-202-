idf_component_register(
    SRCS "src/crypto.c" "src/key_provisioning.c"
    INCLUDE_DIRS "include"
    REQUIRES mbedtls nvs_flash
)