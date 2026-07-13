/**
 * crypto.c - AES-128-GCM Encryption Implementation
 * 
 * End-to-end encryption for mesh packets using AES-128-GCM
 * with nonce derived from (source_id || seq_num || 4_zero_bytes).
 * 
 * Uses ESP-IDF's bundled mbedtls for hardware-accelerated AES.
 */

#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "esp_log.h"
#include "esp_random.h"
#include "mbedtls/aes.h"
#include "mbedtls/gcm.h"
#include "crypto.h"

static const char *TAG = "CRYPTO";

/* ============================================
 * INTERNAL HELPERS
 * ============================================ */

static void build_nonce(uint32_t source_id, uint32_t seq_num, uint8_t nonce[CRYPTO_NONCE_SIZE])
{
    nonce[0] = (source_id >> 24) & 0xFF;
    nonce[1] = (source_id >> 16) & 0xFF;
    nonce[2] = (source_id >> 8) & 0xFF;
    nonce[3] = source_id & 0xFF;
    nonce[4] = (seq_num >> 24) & 0xFF;
    nonce[5] = (seq_num >> 16) & 0xFF;
    nonce[6] = (seq_num >> 8) & 0xFF;
    nonce[7] = seq_num & 0xFF;
    nonce[8] = 0x00;
    nonce[9] = 0x00;
    nonce[10] = 0x00;
    nonce[11] = 0x00;
}

static esp_err_t gcm_crypt_and_tag(mbedtls_gcm_context *gcm,
                                    int mode,
                                    const uint8_t *key,
                                    const uint8_t nonce[CRYPTO_NONCE_SIZE],
                                    const uint8_t *input,
                                    uint8_t *output,
                                    size_t length,
                                    uint8_t tag[CRYPTO_TAG_SIZE])
{
    mbedtls_gcm_init(gcm);
    
    int ret = mbedtls_gcm_setkey(gcm, MBEDTLS_CIPHER_ID_AES, key, CRYPTO_KEY_SIZE * 8);
    if (ret != 0) {
        mbedtls_gcm_free(gcm);
        return ESP_FAIL;
    }
    
    ret = mbedtls_gcm_crypt_and_tag(gcm, mode, length, nonce, CRYPTO_NONCE_SIZE,
                                     NULL, 0, input, output, CRYPTO_TAG_SIZE, tag);
    
    mbedtls_gcm_free(gcm);
    return (ret == 0) ? ESP_OK : ESP_FAIL;
}

/* ============================================
 * PUBLIC API
 * ============================================ */

esp_err_t crypto_init(crypto_context_t *ctx, const uint8_t key[CRYPTO_KEY_SIZE])
{
    if (ctx == NULL || key == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    memcpy(ctx->key, key, CRYPTO_KEY_SIZE);
    ctx->initialized = true;
    
    ESP_LOGI(TAG, "Crypto initialized with network key");
    return ESP_OK;
}

esp_err_t crypto_derive_session_key(const crypto_context_t *ctx,
                                     uint32_t local_id,
                                     uint32_t peer_id,
                                     uint8_t session_key[CRYPTO_KEY_SIZE])
{
    if (ctx == NULL || !ctx->initialized || session_key == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    /* Simple KDF: HKDF-like using SHA-256
     * session_key = HMAC-SHA256(master_key, local_id || peer_id || "mesh-session")
     * truncated to 16 bytes
     * 
     * For simplicity in constrained environment, we use a simpler approach:
     * session_key = AES-CMAC(master_key, local_id || peer_id || counter)
     * 
     * This is a placeholder - production should use proper HKDF.
     */
    
    uint8_t input[12];
    input[0] = (local_id >> 24) & 0xFF;
    input[1] = (local_id >> 16) & 0xFF;
    input[2] = (local_id >> 8) & 0xFF;
    input[3] = local_id & 0xFF;
    input[4] = (peer_id >> 24) & 0xFF;
    input[5] = (peer_id >> 16) & 0xFF;
    input[6] = (peer_id >> 8) & 0xFF;
    input[7] = peer_id & 0xFF;
    input[8] = 0x6D; // 'm'
    input[9] = 0x65; // 'e'
    input[10] = 0x73; // 's'
    input[11] = 0x68; // 'h'
    
    /* Use mbedtls AES-CMAC for key derivation */
    mbedtls_cmac_context_t cmac;
    mbedtls_cmac_init(&cmac);
    
    int ret = mbedtls_cmac_setkey(&cmac, MBEDTLS_CIPHER_ID_AES, ctx->key, CRYPTO_KEY_SIZE * 8);
    if (ret != 0) {
        mbedtls_cmac_free(&cmac);
        return ESP_FAIL;
    }
    
    ret = mbedtls_cmac_starts(&cmac);
    if (ret != 0) {
        mbedtls_cmac_free(&cmac);
        return ESP_FAIL;
    }
    
    ret = mbedtls_cmac_update(&cmac, input, sizeof(input));
    if (ret != 0) {
        mbedtls_cmac_free(&cmac);
        return ESP_FAIL;
    }
    
    ret = mbedtls_cmac_finish(&cmac, session_key);
    mbedtls_cmac_free(&cmac);
    
    if (ret != 0) {
        return ESP_FAIL;
    }
    
    ESP_LOGD(TAG, "Derived session key for 0x%08lX <-> 0x%08lX",
             (unsigned long)local_id, (unsigned long)peer_id);
    return ESP_OK;
}

esp_err_t crypto_encrypt(const crypto_context_t *ctx,
                          uint32_t source_id,
                          uint32_t seq_num,
                          const uint8_t *plaintext,
                          uint8_t plaintext_len,
                          uint8_t *ciphertext,
                          uint8_t tag_out[CRYPTO_TAG_SIZE])
{
    if (ctx == NULL || !ctx->initialized || plaintext == NULL || 
        ciphertext == NULL || tag_out == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    if (plaintext_len > MAX_PACKET_PAYLOAD) {
        return ESP_ERR_INVALID_SIZE;
    }
    
    uint8_t nonce[CRYPTO_NONCE_SIZE];
    build_nonce(source_id, seq_num, nonce);
    
    mbedtls_gcm_context gcm;
    esp_err_t ret = gcm_crypt_and_tag(&gcm, MBEDTLS_GCM_ENCRYPT,
                                       ctx->key, nonce,
                                       plaintext, ciphertext, plaintext_len,
                                       tag_out);
    
    if (ret == ESP_OK) {
        ESP_LOGD(TAG, "Encrypted %d bytes from 0x%08lX seq=%lu",
                 plaintext_len, (unsigned long)source_id, (unsigned long)seq_num);
    }
    
    return ret;
}

esp_err_t crypto_decrypt(const crypto_context_t *ctx,
                          uint32_t source_id,
                          uint32_t seq_num,
                          const uint8_t *ciphertext,
                          uint8_t ciphertext_len,
                          const uint8_t tag_in[CRYPTO_TAG_SIZE],
                          uint8_t *plaintext)
{
    if (ctx == NULL || !ctx->initialized || ciphertext == NULL || 
        tag_in == NULL || plaintext == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    if (ciphertext_len > MAX_PACKET_PAYLOAD) {
        return ESP_ERR_INVALID_SIZE;
    }
    
    /* Zero output buffer first (security: never return partial plaintext on failure) */
    memset(plaintext, 0, ciphertext_len);
    
    uint8_t nonce[CRYPTO_NONCE_SIZE];
    build_nonce(source_id, seq_num, nonce);
    
    mbedtls_gcm_context gcm;
    mbedtls_gcm_init(&gcm);
    
    int ret = mbedtls_gcm_setkey(&gcm, MBEDTLS_CIPHER_ID_AES, ctx->key, CRYPTO_KEY_SIZE * 8);
    if (ret != 0) {
        mbedtls_gcm_free(&gcm);
        return ESP_FAIL;
    }
    
    ret = mbedtls_gcm_auth_decrypt(&gcm, ciphertext_len,
                                    nonce, CRYPTO_NONCE_SIZE,
                                    NULL, 0,
                                    tag_in, CRYPTO_TAG_SIZE,
                                    ciphertext, plaintext);
    
    mbedtls_gcm_free(&gcm);
    
    if (ret == 0) {
        ESP_LOGD(TAG, "Decrypted %d bytes from 0x%08lX seq=%lu",
                 ciphertext_len, (unsigned long)source_id, (unsigned long)seq_num);
        return ESP_OK;
    }
    
    /* Authentication failed - plaintext already zeroed */
    ESP_LOGW(TAG, "GCM auth failed for packet from 0x%08lX seq=%lu",
             (unsigned long)source_id, (unsigned long)seq_num);
    return ESP_ERR_INVALID_CRC;
}

void crypto_build_nonce(uint32_t source_id, uint32_t seq_num, uint8_t nonce[CRYPTO_NONCE_SIZE])
{
    build_nonce(source_id, seq_num, nonce);
}

/* ============================================
 * KEY PROVISIONING HELPER
 * ============================================ */

esp_err_t crypto_generate_random_key(uint8_t key[CRYPTO_KEY_SIZE])
{
    if (key == NULL) return ESP_ERR_INVALID_ARG;
    
    esp_fill_random(key, CRYPTO_KEY_SIZE);
    ESP_LOGI(TAG, "Generated random network key");
    return ESP_OK;
}

void crypto_print_key_hex(const uint8_t key[CRYPTO_KEY_SIZE])
{
    char hex[33];
    for (int i = 0; i < CRYPTO_KEY_SIZE; i++) {
        sprintf(&hex[i*2], "%02x", key[i]);
    }
    hex[32] = '\0';
    ESP_LOGI(TAG, "Key: %s", hex);
}