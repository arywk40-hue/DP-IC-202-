/**
 * key_provisioning.h - Network Key Provisioning via NVS
 *
 * Handles secure provisioning, storage, and loading of network encryption keys
 * from ESP-IDF NVS (Non-Volatile Storage). Supports both auto-generated keys
 * for development and manual provisioning for production deployments.
 */

#ifndef KEY_PROVISIONING_H
#define KEY_PROVISIONING_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "crypto.h"

#ifdef __cplusplus
extern "C" {
#endif

/* NVS namespace and keys */
#define KEY_PROV_NS           "mesh_sec"
#define KEY_PROV_NETKEY_KEY   "netkey"
#define KEY_PROV_KEYID_KEY    "keyid"
#define KEY_PROV_INIT_KEY     "initialized"

/**
 * @brief Initialize the key provisioning system.
 * Opens NVS namespace and prepares for key operations.
 * @return ESP_OK on success
 */
esp_err_t key_provisioning_init(void);

/**
 * @brief Provision a network key into NVS.
 * If key is NULL, generates a random key and stores it.
 * If key is provided, stores the provided key.
 * @param key  16-byte network key, or NULL to auto-generate
 * @return ESP_OK on success, ESP_ERR_INVALID_ARG if key is wrong size
 */
esp_err_t key_provisioning_set_network_key(const uint8_t *key);

/**
 * @brief Load the network key from NVS.
 * If no key exists and auto_generate is true, generates and stores a new key.
 * @param out_key  Output buffer for 16-byte network key
 * @param auto_generate  If true, generates key if none exists
 * @return ESP_OK on success, ESP_ERR_NOT_FOUND if no key and auto_generate=false
 */
esp_err_t key_provisioning_load_network_key(uint8_t out_key[CRYPTO_KEY_SIZE], bool auto_generate);

/**
 * @brief Get the key ID (version) of the stored network key.
 * @param out_keyid  Output key ID
 * @return ESP_OK on success, ESP_ERR_NOT_FOUND if no key
 */
esp_err_t key_provisioning_get_keyid(uint32_t *out_keyid);

/**
 * @brief Rotate the network key.
 * Generates a new key, stores it with incremented key ID.
 * Old key is preserved for a transition period (future use).
 * @return ESP_OK on success
 */
esp_err_t key_provisioning_rotate_key(void);

/**
 * @brief Erase all provisioned keys from NVS.
 * Use with caution - will require re-provisioning.
 * @return ESP_OK on success
 */
esp_err_t key_provisioning_erase_all(void);

/**
 * @brief Check if a network key is provisioned.
 * @return true if key exists in NVS
 */
bool key_provisioning_is_provisioned(void);

/**
 * @brief Print the stored network key in hex format (for debugging).
 * Only works if CONFIG_KEY_PROV_DEBUG_PRINT is enabled.
 */
void key_provisioning_print_key(void);

#ifdef __cplusplus
}
#endif

#endif /* KEY_PROVISIONING_H */