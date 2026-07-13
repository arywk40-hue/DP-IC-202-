/**
 * key_provisioning.c - Network Key Provisioning via NVS
 *
 * Handles secure provisioning, storage, and loading of network encryption keys
 * from ESP-IDF NVS (Non-Volatile Storage).
 */

#include <string.h>
#include <stdio.h>
#include "esp_log.h"
#include "esp_random.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "key_provisioning.h"
#include "crypto.h"

static const char *TAG = "KEY_PROV";

static nvs_handle_t g_nvs_handle = 0;
static bool g_nvs_initialized = false;

/* ============================================
 * INTERNAL HELPERS
 * ============================================ */

static esp_err_t nvs_open_namespace(void)
{
    if (g_nvs_initialized) {
        return ESP_OK;
    }
    
    esp_err_t err = nvs_open(KEY_PROV_NS, NVS_READWRITE, &g_nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS namespace '%s': %s", KEY_PROV_NS, esp_err_to_name(err));
        return err;
    }
    
    g_nvs_initialized = true;
    return ESP_OK;
}

/* ============================================
 * PUBLIC API
 * ============================================ */

esp_err_t key_provisioning_init(void)
{
    return nvs_open_namespace();
}

esp_err_t key_provisioning_set_network_key(const uint8_t *key)
{
    if (!g_nvs_initialized) {
        esp_err_t err = nvs_open_namespace();
        if (err != ESP_OK) return err;
    }

    uint8_t keybuf[CRYPTO_KEY_SIZE];
    
    if (key == NULL) {
        /* Auto-generate a random key */
        esp_fill_random(keybuf, CRYPTO_KEY_SIZE);
        ESP_LOGW(TAG, "No key provided, generated random network key");
    } else {
        memcpy(keybuf, key, CRYPTO_KEY_SIZE);
    }

    /* Store the key */
    esp_err_t err = nvs_set_blob(g_nvs_handle, KEY_PROV_NETKEY_KEY, keybuf, CRYPTO_KEY_SIZE);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to store network key: %s", esp_err_to_name(err));
        return err;
    }

    /* Set initialized flag */
    err = nvs_set_u8(g_nvs_handle, KEY_PROV_INIT_KEY, 1);
    if (err != ESP_OK) return err;

    /* Set/initialize key ID */
    uint32_t keyid = 1;
    nvs_get_u32(g_nvs_handle, KEY_PROV_KEYID_KEY, &keyid);
    keyid++;
    nvs_set_u32(g_nvs_handle, KEY_PROV_KEYID_KEY, keyid);

    err = nvs_commit(g_nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to commit NVS: %s", esp_err_to_name(err));
        return err;
    }

    ESP_LOGI(TAG, "Network key provisioned (key ID: %lu)", (unsigned long)keyid);
    crypto_print_key_hex(keybuf);
    return ESP_OK;
}

esp_err_t key_provisioning_load_network_key(uint8_t out_key[CRYPTO_KEY_SIZE], bool auto_generate)
{
    if (!g_nvs_initialized) {
        esp_err_t err = nvs_open_namespace();
        if (err != ESP_OK) return err;
    }

    uint8_t keybuf[CRYPTO_KEY_SIZE];
    size_t len = CRYPTO_KEY_SIZE;
    
    esp_err_t err = nvs_get_blob(g_nvs_handle, KEY_PROV_NETKEY_KEY, keybuf, &len);
    if (err == ESP_OK) {
        memcpy(out_key, keybuf, CRYPTO_KEY_SIZE);
        ESP_LOGI(TAG, "Loaded network key from NVS");
        return ESP_OK;
    }

    if (err == ESP_ERR_NVS_NOT_FOUND) {
        if (auto_generate) {
            ESP_LOGW(TAG, "No network key found, generating new one");
            return key_provisioning_set_network_key(NULL);
        }
        ESP_LOGW(TAG, "No network key found in NVS");
        return ESP_ERR_NOT_FOUND;
    }

    ESP_LOGE(TAG, "Failed to read network key: %s", esp_err_to_name(err));
    return err;
}

esp_err_t key_provisioning_get_keyid(uint32_t *out_keyid)
{
    if (!g_nvs_initialized) {
        esp_err_t err = nvs_open_namespace();
        if (err != ESP_OK) return err;
    }

    uint32_t keyid = 0;
    esp_err_t err = nvs_get_u32(g_nvs_handle, KEY_PROV_KEYID_KEY, &keyid);
    if (err == ESP_OK) {
        *out_keyid = keyid;
        return ESP_OK;
    }
    return err;
}

esp_err_t key_provisioning_rotate_key(void)
{
    if (!g_nvs_initialized) {
        esp_err_t err = nvs_open_namespace();
        if (err != ESP_OK) return err;
    }

    /* Generate new key */
    uint8_t new_key[CRYPTO_KEY_SIZE];
    esp_fill_random(new_key, CRYPTO_KEY_SIZE);

    /* Get current key ID and increment */
    uint32_t keyid = 0;
    nvs_get_u32(g_nvs_handle, KEY_PROV_KEYID_KEY, &keyid);
    keyid++;

    /* Store new key */
    esp_err_t err = nvs_set_blob(g_nvs_handle, KEY_PROV_NETKEY_KEY, new_key, CRYPTO_KEY_SIZE);
    if (err != ESP_OK) return err;

    err = nvs_set_u32(g_nvs_handle, KEY_PROV_KEYID_KEY, keyid);
    if (err != ESP_OK) return err;

    err = nvs_commit(g_nvs_handle);
    if (err != ESP_OK) return err;

    ESP_LOGI(TAG, "Key rotated to ID: %lu", (unsigned long)keyid);
    crypto_print_key_hex(new_key);
    return ESP_OK;
}

esp_err_t key_provisioning_erase_all(void)
{
    if (!g_nvs_initialized) {
        esp_err_t err = nvs_open_namespace();
        if (err != ESP_OK) return err;
    }

    esp_err_t err = nvs_erase_all(g_nvs_handle);
    if (err != ESP_OK) return err;

    err = nvs_commit(g_nvs_handle);
    if (err != ESP_OK) return err;

    g_nvs_initialized = false;
    ESP_LOGI(TAG, "All provisioned keys erased");
    return ESP_OK;
}

bool key_provisioning_is_provisioned(void)
{
    if (!g_nvs_initialized) {
        esp_err_t err = nvs_open_namespace();
        if (err != ESP_OK) return false;
    }

    uint8_t keybuf[CRYPTO_KEY_SIZE];
    size_t len = CRYPTO_KEY_SIZE;
    esp_err_t err = nvs_get_blob(g_nvs_handle, KEY_PROV_NETKEY_KEY, keybuf, &len);
    return (err == ESP_OK);
}

void key_provisioning_print_key(void)
{
    if (!g_nvs_initialized) {
        esp_err_t err = nvs_open_namespace();
        if (err != ESP_OK) return;
    }

    uint8_t keybuf[CRYPTO_KEY_SIZE];
    size_t len = CRYPTO_KEY_SIZE;
    esp_err_t err = nvs_get_blob(g_nvs_handle, KEY_PROV_NETKEY_KEY, keybuf, &len);
    if (err == ESP_OK) {
        crypto_print_key_hex(keybuf);
    } else {
        ESP_LOGW(TAG, "No key to print");
    }
}