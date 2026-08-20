/**
 * test_crypto.c - Unit tests for AES-128-GCM crypto component
 * 
 * Tests:
 * - Encryption/decryption round-trip equality
 * - Tag verification (tampered ciphertext fails)
 * - Different nonces produce different ciphertexts
 * - Empty payload handling
 */

#include <string.h>
#include "unity.h"
#include "crypto.h"

static const char *TAG = "TEST_CRYPTO";

/* Test key (16 bytes) */
static const uint8_t TEST_KEY[CRYPTO_KEY_SIZE] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F
};

void setUp(void)
{
    /* Initialize crypto with test key */
    TEST_ASSERT_EQUAL(ESP_OK, crypto_init(TEST_KEY));
}

void tearDown(void)
{
    /* Nothing to clean up */
}

void test_crypto_encrypt_decrypt_roundtrip(void)
{
    const uint8_t plaintext[] = "Hello, Mesh Network! This is a test payload.";
    const size_t len = sizeof(plaintext) - 1;
    const uint32_t source_id = 0x12345678;
    const uint32_t seq_num = 0x00000042;
    
    uint8_t ciphertext[len];
    uint8_t tag[CRYPTO_TAG_SIZE];
    uint8_t decrypted[len];
    
    /* Encrypt */
    esp_err_t ret = crypto_encrypt(source_id, seq_num, plaintext, len, ciphertext, tag);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    
    /* Ciphertext should be different from plaintext */
    TEST_ASSERT_NOT_EQUAL_MEMORY(plaintext, ciphertext, len);
    
    /* Decrypt */
    ret = crypto_decrypt(source_id, seq_num, ciphertext, len, tag, decrypted);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    
    /* Verify round-trip equality */
    TEST_ASSERT_EQUAL_MEMORY(plaintext, decrypted, len);
}

void test_crypto_encrypt_decrypt_empty_payload(void)
{
    const uint8_t plaintext[] = "";
    const size_t len = 0;
    const uint32_t source_id = 0x11111111;
    const uint32_t seq_num = 0x00000001;
    
    uint8_t ciphertext[1];  /* Minimal buffer */
    uint8_t tag[CRYPTO_TAG_SIZE];
    uint8_t decrypted[1];
    
    esp_err_t ret = crypto_encrypt(source_id, seq_num, plaintext, len, ciphertext, tag);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    
    ret = crypto_decrypt(source_id, seq_num, ciphertext, len, tag, decrypted);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
}

void test_crypto_tampered_ciphertext_fails(void)
{
    const uint8_t plaintext[] = "Secret sensor data packet";
    const size_t len = sizeof(plaintext) - 1;
    const uint32_t source_id = 0xDEADBEEF;
    const uint32_t seq_num = 0x00000007;
    
    uint8_t ciphertext[sizeof(plaintext)];
    uint8_t tag[CRYPTO_TAG_SIZE];
    uint8_t decrypted[sizeof(plaintext)];
    
    /* Encrypt */
    esp_err_t ret = crypto_encrypt(source_id, seq_num, plaintext, len, ciphertext, tag);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    
    /* Tamper with ciphertext - flip one bit */
    ciphertext[0] ^= 0x01;
    
    /* Decrypt should fail */
    ret = crypto_decrypt(source_id, seq_num, ciphertext, len, tag, decrypted);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_CRC, ret);
}

void test_crypto_tampered_tag_fails(void)
{
    const uint8_t plaintext[] = "Another test message";
    const size_t len = sizeof(plaintext) - 1;
    const uint32_t source_id = 0xCAFEBABE;
    const uint32_t seq_num = 0x0000000C;
    
    uint8_t ciphertext[sizeof(plaintext)];
    uint8_t tag[CRYPTO_TAG_SIZE];
    uint8_t decrypted[sizeof(plaintext)];
    
    /* Encrypt */
    esp_err_t ret = crypto_encrypt(source_id, seq_num, plaintext, len, ciphertext, tag);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    
    /* Tamper with tag - flip one bit */
    tag[0] ^= 0x01;
    
    /* Decrypt should fail */
    ret = crypto_decrypt(source_id, seq_num, ciphertext, len, tag, decrypted);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_CRC, ret);
}

void test_crypto_wrong_nonce_fails(void)
{
    const uint8_t plaintext[] = "Test with wrong nonce";
    const size_t len = sizeof(plaintext) - 1;
    const uint32_t source_id = 0xFEEDFACE;
    const uint32_t seq_num = 0x00000010;
    
    uint8_t ciphertext[sizeof(plaintext)];
    uint8_t tag[CRYPTO_TAG_SIZE];
    uint8_t decrypted[sizeof(plaintext)];
    
    /* Encrypt with source_id */
    esp_err_t ret = crypto_encrypt(source_id, seq_num, plaintext, len, ciphertext, tag);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    
    /* Try to decrypt with different source_id (different nonce) */
    ret = crypto_decrypt(0x00000000, seq_num, ciphertext, len, tag, decrypted);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_CRC, ret);
}

void test_crypto_wrong_sequence_fails(void)
{
    const uint8_t plaintext[] = "Sequence number test";
    const size_t len = sizeof(plaintext) - 1;
    const uint32_t source_id = 0x1234ABCD;
    const uint32_t seq_num = 0x00000014;
    
    uint8_t ciphertext[sizeof(plaintext)];
    uint8_t tag[CRYPTO_TAG_SIZE];
    uint8_t decrypted[sizeof(plaintext)];
    
    /* Encrypt with seq_num */
    esp_err_t ret = crypto_encrypt(source_id, seq_num, plaintext, len, ciphertext, tag);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    
    /* Try to decrypt with different seq_num */
    ret = crypto_decrypt(source_id, seq_num + 1, ciphertext, len, tag, decrypted);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_CRC, ret);
}

void test_crypto_different_nonces_different_ciphertext(void)
{
    const uint8_t plaintext[] = "Same plaintext, different nonces";
    const size_t len = sizeof(plaintext) - 1;
    const uint32_t source_id = 0x87654321;
    
    uint8_t ciphertext1[len];
    uint8_t tag1[CRYPTO_TAG_SIZE];
    uint8_t ciphertext2[len];
    uint8_t tag2[CRYPTO_TAG_SIZE];
    
    /* Encrypt same plaintext with different seq_nums */
    crypto_encrypt(source_id, 0x100, plaintext, len, ciphertext1, tag1);
    crypto_encrypt(source_id, 0x200, plaintext, len, ciphertext2, tag2);
    
    /* Ciphertexts should be different */
    TEST_ASSERT_NOT_EQUAL_MEMORY(ciphertext1, ciphertext2, len);
    TEST_ASSERT_NOT_EQUAL_MEMORY(tag1, tag2, CRYPTO_TAG_SIZE);
}

void test_crypto_large_payload(void)
{
    /* Test with maximum payload size */
    const size_t len = MAX_PACKET_PAYLOAD;
    uint8_t plaintext[len];
    uint8_t ciphertext[len];
    uint8_t tag[CRYPTO_TAG_SIZE];
    uint8_t decrypted[len];
    
    /* Fill with pattern */
    for (size_t i = 0; i < len; i++) {
        plaintext[i] = (uint8_t)(i & 0xFF);
    }
    
    const uint32_t source_id = 0xFFFFFFFF;
    const uint32_t seq_num = 0xFFFFFFFF;
    
    esp_err_t ret = crypto_encrypt(source_id, seq_num, plaintext, len, ciphertext, tag);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    
    ret = crypto_decrypt(source_id, seq_num, ciphertext, len, tag, decrypted);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    
    TEST_ASSERT_EQUAL_MEMORY(plaintext, decrypted, len);
}

void test_crypto_null_pointers(void)
{
    const uint8_t plaintext[] = "test";
    const uint32_t source_id = 0x12345678;
    const uint32_t seq_num = 0x01;
    uint8_t ciphertext[8];
    uint8_t tag[CRYPTO_TAG_SIZE];
    uint8_t decrypted[8];
    
    /* NULL plaintext */
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, crypto_encrypt(source_id, seq_num, NULL, 4, ciphertext, tag));
    
    /* NULL ciphertext out */
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, crypto_encrypt(source_id, seq_num, (uint8_t*)"test", 4, NULL, tag));
    
    /* NULL tag out */
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, crypto_encrypt(source_id, seq_num, (uint8_t*)"test", 4, ciphertext, NULL));
    
    /* NULL ciphertext in decrypt */
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, crypto_decrypt(source_id, seq_num, NULL, 4, tag, decrypted));
    
    /* NULL tag in decrypt */
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, crypto_decrypt(source_id, seq_num, ciphertext, 4, NULL, decrypted));
    
    /* NULL decrypted out */
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, crypto_decrypt(source_id, seq_num, ciphertext, 4, tag, NULL));
}

void test_crypto_uninitialized_fails(void)
{
    const uint8_t plaintext[] = "test";
    uint8_t ciphertext[8];
    uint8_t tag[CRYPTO_TAG_SIZE];
    
    /* De-initialize by calling init with NULL (if supported) or just test without init */
    /* Our crypto_init doesn't have a deinit, so we test that uninitialized returns error */
    /* This would require a separate test setup - skip for now as crypto is initialized in setUp */
}

TEST_CASE("Crypto round-trip encryption/decryption", "[crypto]")
{
    test_crypto_encrypt_decrypt_roundtrip();
}

TEST_CASE("Crypto empty payload", "[crypto]")
{
    test_crypto_encrypt_decrypt_empty_payload();
}

TEST_CASE("Crypto tampered ciphertext fails", "[crypto]")
{
    test_crypto_tampered_ciphertext_fails();
}

TEST_CASE("Crypto tampered tag fails", "[crypto]")
{
    test_crypto_tampered_tag_fails();
}

TEST_CASE("Crypto wrong nonce fails", "[crypto]")
{
    test_crypto_wrong_nonce_fails();
}

TEST_CASE("Crypto wrong sequence fails", "[crypto]")
{
    test_crypto_wrong_sequence_fails();
}

TEST_CASE("Crypto different nonces produce different ciphertext", "[crypto]")
{
    test_crypto_different_nonces_different_ciphertext();
}

TEST_CASE("Crypto large payload", "[crypto]")
{
    test_crypto_large_payload();
}

TEST_CASE("Crypto null pointer handling", "[crypto]")
{
    test_crypto_null_pointers();
}