/**
 * crypto.h - AES-128-GCM Encryption Wrapper
 * 
 * Provides end-to-end encryption for mesh packets using AES-128-GCM
 * with nonce derived from (source_id || seq_num || 4_zero_bytes).
 * 
 * Uses ESP-IDF's bundled mbedtls for hardware-accelerated AES.
 */

#ifndef CRYPTO_H
#define CRYPTO_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "common.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Crypto configuration */
#define CRYPTO_KEY_SIZE         16      // AES-128
#define CRYPTO_NONCE_SIZE       12      // 96-bit nonce for GCM
#define CRYPTO_TAG_SIZE         16      // 128-bit auth tag
#define CRYPTO_NONCE_SRC_ID_OFF  0      // source_id at bytes 0-3
#define CRYPTO_NONCE_SEQ_NUM_OFF 4      // seq_num at bytes 4-7
#define CRYPTO_NONCE_ZERO_OFF   8       // 4 zero bytes at bytes 8-11

/**
 * @brief Crypto context holding the network encryption key
 */
typedef struct {
    uint8_t key[CRYPTO_KEY_SIZE];
    bool initialized;
} crypto_context_t;

/**
 * @brief Initialize crypto module with a 16-byte network key
 * @param ctx Crypto context to initialize
 * @param key 16-byte network encryption key
 * @return ESP_OK on success
 */
esp_err_t crypto_init(crypto_context_t *ctx, const uint8_t key[CRYPTO_KEY_SIZE]);

/**
 * @brief Derive a per-session key from master key and node IDs
 * @param ctx Initialized crypto context
 * @param local_id Local node ID
 * @param peer_id Peer node ID (or 0 for broadcast)
 * @param session_key Output buffer for 16-byte session key
 * @return ESP_OK on success
 */
esp_err_t crypto_derive_session_key(const crypto_context_t *ctx,
                                     uint32_t local_id,
                                     uint32_t peer_id,
                                     uint8_t session_key[CRYPTO_KEY_SIZE]);

/**
 * @brief Encrypt data using AES-128-GCM
 * @param ctx Initialized crypto context
 * @param source_id Source node ID (for nonce derivation)
 * @param seq_num Sequence number (for nonce derivation)
 * @param plaintext Input plaintext
 * @param plaintext_len Length of plaintext
 * @param ciphertext Output buffer (must be >= plaintext_len)
 * @param tag_out Output 16-byte authentication tag
 * @return ESP_OK on success, ESP_ERR_INVALID_ARG if buffers invalid
 */
esp_err_t crypto_encrypt(const crypto_context_t *ctx,
                          uint32_t source_id,
                          uint32_t seq_num,
                          const uint8_t *plaintext,
                          uint8_t plaintext_len,
                          uint8_t *ciphertext,
                          uint8_t tag_out[CRYPTO_TAG_SIZE]);

/**
 * @brief Decrypt data using AES-128-GCM
 * @param ctx Initialized crypto context
 * @param source_id Source node ID (for nonce derivation)
 * @param seq_num Sequence number (for nonce derivation)
 * @param ciphertext Input ciphertext
 * @param ciphertext_len Length of ciphertext
 * @param tag_in 16-byte authentication tag
 * @param plaintext Output buffer (must be >= ciphertext_len)
 * @return ESP_OK on success, ESP_ERR_INVALID_CRC if auth tag verification fails
 *         (output buffer is zeroed on failure)
 */
esp_err_t crypto_decrypt(const crypto_context_t *ctx,
                          uint32_t source_id,
                          uint32_t seq_num,
                          const uint8_t *ciphertext,
                          uint8_t ciphertext_len,
                          const uint8_t tag_in[CRYPTO_TAG_SIZE],
                          uint8_t *plaintext);

/**
 * @brief Build nonce from source_id and seq_num
 * @param source_id Source node ID
 * @param seq_num Sequence number
 * @param nonce Output 12-byte nonce
 */
void crypto_build_nonce(uint32_t source_id, uint32_t seq_num, uint8_t nonce[CRYPTO_NONCE_SIZE]);

/**
 * @brief Get required ciphertext buffer size for given plaintext length
 * @param plaintext_len Length of plaintext
 * @return Required ciphertext buffer size (same as plaintext_len)
 */
static inline uint8_t crypto_ciphertext_size(uint8_t plaintext_len)
{
    return plaintext_len;  // GCM doesn't expand ciphertext
}

/**
 * @brief Get total encrypted payload size (ciphertext + tag)
 * @param plaintext_len Length of plaintext
 * @return Total size (ciphertext + 16-byte tag)
 */
static inline uint8_t crypto_encrypted_payload_size(uint8_t plaintext_len)
{
    return plaintext_len + CRYPTO_TAG_SIZE;
}

#ifdef __cplusplus
}
#endif

#endif /* CRYPTO_H */