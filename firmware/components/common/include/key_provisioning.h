/**
 * key_provisioning.h - Network Key Provisioning
 * 
 * Handles secure storage and retrieval of the 16-byte network encryption key
 * using ESP-IDF NVS (Non-Volatile Storage). Supports:
 * - First-boot key generation using hardware RNG
 * - Manual key provisioning via Kconfig
 * - Key rotation support (future)
 * - Warning logs for bootstrap-generated keys
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

/**
 * @brief Initialize the key provisioning system.
 * Opens NVS namespace and prepares for key operations.
 * @return ESP_OK on success, error code on failure.
 */
esp_err_t key_provisioning_init(void);

/**
 * @brief Load the network key from NVS, generating one if not found.
 * @param out_key  Output buffer for 16-byte network key.
 * @param generate_if_missing  If true, generate and store a new key when missing.
 * @return ESP_OK on success, ESP_ERR_NOT_FOUND if key missing and generate=false,
 *         ESP_ERR_NO_MEM if NVS full, other errors on failure.
 */
esp_err_t key_provisioning_load_network_key(uint8_t out_key[CRYPTO_KEY_SIZE], bool generate_if_missing);

/**
 * @brief Store a network key to NVS (for manual provisioning).
 * @param key  16-byte network key to store.
 * @return ESP_OK on success.
 */
esp_err_t key_provisioning_store_network_key(const uint8_t key[CRYPTO_KEY_SIZE]);

/**
 * @brief Check if a network key exists in NVS.
 * @return true if key exists, false otherwise.
 */
bool key_provisioning_has_network_key(void);

/**
 * @brief Delete the network key from NVS (for key rotation/re-provisioning).
 * @return ESP_OK on success.
 */
esp_err_t key_provisioning_delete_network_key(void);

/**
 * @brief Get provisioning status for logging/debugging.
 * @param is_provisioned  Output: true if key exists in NVS.
 * @param is_bootstrap    Output: true if key was auto-generated (not manually provisioned).
 * @return ESP_OK on success.
 */
esp_err_t key_provisioning_get_status(bool *is_provisioned, bool *is_bootstrap);

#ifdef __cplusplus
}
#endif

#endif /* KEY_PROVISIONING_H */