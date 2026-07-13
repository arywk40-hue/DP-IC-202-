/**
 * key_provisioning.c - Network Key Provisioning Implementation
 * 
 * Handles secure storage and retrieval of the 16-byte network encryption key
 * using ESP-IDF NVS (Non-Volatile Storage). Supports first-boot key generation
 * with hardware RNG, manual key provisioning, and bootstrap detection.
 */

#include <string.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_random.h"
#include "key_provisioning.h"
#include "crypto.h"

static const char *TAG = "KEY_PROV";

#define KP_NVS_NAMESPACE      "mesh_sec"
#define KP_NVS_KEY_NETKEY     "netkey"
#define KP_NVS_KEY_BOOTSTRAP  "bootstrap"

/* Bootstrap marker value indicating auto-generated key */
#define KP_BOOTSTRAP_MARKER   0xA5A5A5A5

/**
 * @brief Initialize the key provisioning system.
 */
esp_err_t key_provisioning_init(void)
{
    /* NVS is already initialized in app_main via nvs_flash_init() */
    ESP_LOGI(TAG, "Key provisioning initialized");
    return ESP_OK;
}

/**
 * @brief Load the network key from NVS, generating one if missing.
 */
esp_err_t key_provisioning_load_network_key(uint8_t out_key[CRYPTO_KEY_SIZE], bool generate_if_missing)
{
    if (out_key == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(KP_NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS namespace: %s", esp_err_to_name(err));
        return err;
    }

    size_t required_size = CRYPTO_KEY_SIZE;
    err = nvs_get_blob(nvs_handle, KP_NVS_KEY_NETKEY, out_key, &required_size);
    
    if (err == ESP_OK) {
        /* Key found in NVS */
        ESP_LOGI(TAG, "Loaded network key from NVS");
        nvs_close(nvs_handle);
        return ESP_OK;
    }

    if (err == ESP_ERR_NVS_NOT_FOUND) {
        if (!generate_if_missing) {
            nvs_close(nvs_handle);
            ESP_LOGW(TAG, "Network key not found in NVS");
            return ESP_ERR_NOT_FOUND;
        }

        /* Generate new key using hardware RNG */
        ESP_LOGW(TAG, "No network key found — generating new key (BOOTSTRAP MODE)");
        esp_fill_random(out_key, CRYPTO_KEY_SIZE);

        /* Store the generated key */
        err = nvs_set_blob(nvs_handle, KP_NVS_KEY_NETKEY, out_key, CRYPTO_KEY_SIZE);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "Failed to store generated key: %s", esp_err_to_name(err));
            nvs_close(nvs_handle);
            return err;
        }

        /* Mark as bootstrap-generated */
        uint32_t bootstrap_marker = KP_BOOTSTRAP_MARKER;
        err = nvs_set_u32(nvs_handle, KP_NVS_KEY_BOOTSTRAP, bootstrap_marker);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "Failed to store bootstrap marker: %s", esp_err_to_name(err));
            nvs_close(nvs_handle);
            return err;
        }

        err = nvs_commit(nvs_handle);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "Failed to commit NVS: %s", esp_err_to_name(err));
            nvs_close(nvs_handle);
            return err;
        }

        nvs_close(nvs_handle);

        ESP_LOGW(TAG, "=================================================");
        ESP_LOGW(TAG, "  BOOTSTRAP KEY GENERATED - NOT FOR PRODUCTION!");
        ESP_LOGW(TAG, "  This key was auto-generated on first boot.");
        ESP_LOGW(TAG, "  For production, provision a manual key via");
        ESP_LOGW(TAG, "  Kconfig or key_provisioning_store_network_key().");
        ESP_LOGW(TAG, "=================================================");
        return ESP_OK;
    }

    /* Other error */
    nvs_close(nvs_handle);
    ESP_LOGE(TAG, "Failed to read network key: %s", esp_err_to_name(err));
    return err;
}

/**
 * @brief Store a network key to NVS (for manual provisioning).
 */
esp_err_t key_provisioning_store_network_key(const uint8_t key[CRYPTO_KEY_SIZE])
{
    if (key == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(KP_NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS namespace: %s", esp_err_to_name(err));
        return err;
    }

    /* Store the key */
    err = nvs_set_blob(nvs_handle, KP_NVS_KEY_NETKEY, key, CRYPTO_KEY_SIZE);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to store network key: %s", esp_err_to_name(err));
        nvs_close(nvs_handle);
        return err;
    }

    /* Clear bootstrap marker (manual provisioning) */
    err = nvs_erase_key(nvs_handle, KP_NVS_KEY_BOOTSTRAP);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGW(TAG, "Failed to clear bootstrap marker: %s", esp_err_to_name(err));
    }

    err = nvs_commit(nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to commit NVS: %s", esp_err_to_name(err));
        nvs_close(nvs_handle);
        return err;
    }

    nvs_close(nvs_handle);
    ESP_LOGI(TAG, "Network key stored to NVS (manual provisioning)");
    return ESP_OK;
}

/**
 * @brief Check if a network key exists in NVS.
 */
bool key_provisioning_has_network_key(void)
{
    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(KP_NVS_NAMESPACE, NVS_READONLY, &nvs_handle);
    if (err != ESP_OK) {
        return false;
    }

    size_t required_size = 0;
    err = nvs_get_blob(nvs_handle, KP_NVS_KEY_NETKEY, NULL, &required_size);
    nvs_close(nvs_handle);

    return (err == ESP_OK && required_size == CRYPTO_KEY_SIZE);
}

/**
 * @brief Delete the network key from NVS.
 */
esp_err_t key_provisioning_delete_network_key(void)
{
    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(KP_NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK) {
        return err;
    }

    err = nvs_erase_key(nvs_handle, KP_NVS_KEY_NETKEY);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND) {
        nvs_close(nvs_handle);
        return err;
    }

    err = nvs_erase_key(nvs_handle, KP_NVS_KEY_BOOTSTRAP);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND) {
        nvs_close(nvs_handle);
        return err;
    }

    err = nvs_commit(nvs_handle);
    nvs_close(nvs_handle);
    return err;
}

/**
 * @brief Get provisioning status for logging/debugging.
 */
esp_err_t key_provisioning_get_status(bool *is_provisioned, bool *is_bootstrap)
{
    if (is_provisioned == NULL || is_bootstrap == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(KP_NVS_NAMESPACE, NVS_READONLY, &nvs_handle);
    if (err != ESP_OK) {
        *is_provisioned = false;
        *is_bootstrap = false;
        return err;
    }

    /* Check for network key */
    size_t required_size = 0;
    err = nvs_get_blob(nvs_handle, KP_NVS_KEY_NETKEY, NULL, &required_size);
    *is_provisioned = (err == ESP_OK && required_size == CRYPTO_KEY_SIZE);

    /* Check bootstrap marker */
    uint32_t bootstrap_marker = 0;
    err = nvs_get_u32(nvs_handle, KP_NVS_KEY_BOOTSTRAP, &bootstrap_marker);
    *is_bootstrap = (err == ESP_OK && bootstrap_marker == KP_BOOTSTRAP_MARKER);

    nvs_close(nvs_handle);
    return ESP_OK;
}