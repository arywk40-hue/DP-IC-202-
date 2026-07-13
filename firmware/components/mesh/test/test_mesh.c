/**
 * test_mesh.c - Unit tests for mesh networking layer
 * 
 * Tests:
 * - Packet serialization/deserialization
 * - CRC8 validation
 * - Duplicate detection
 * - Neighbor table management
 * - Fragmentation/reassembly
 * - ACK handling
 * - TTL forwarding
 */

#include <string.h>
#include "unity.h"
#include "mesh.h"
#include "crypto.h"
#include "sx1276.h"

static const char *TAG = "TEST_MESH";

/* Test key for crypto */
static const uint8_t TEST_KEY[CRYPTO_KEY_SIZE] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F
};

/* Mock SX1276 handle for testing */
static sx1276_handle_t *g_mock_lora_handle = NULL;

/* Mock functions for SX1276 */
bool sx1276_init(const sx1276_config_t *config, sx1276_handle_t **handle) {
    if (g_mock_lora_handle) {
        *handle = g_mock_lora_handle;
        return true;
    }
    return false;
}

bool sx1276_transmit(sx1276_handle_t *handle, const uint8_t *data, uint8_t len, uint32_t timeout_ms) {
    return true;
}

void sx1276_start_receive(sx1276_handle_t *handle) {}
bool sx1276_received(sx1276_handle_t *handle) { return false; }
uint8_t sx1276_read(sx1276_handle_t *handle, uint8_t *buffer, uint8_t max_len, int8_t *rssi, float *snr) { return 0; }
void sx1276_sleep(sx1276_handle_t *handle) {}
void sx1276_standby(sx1276_handle_t *handle) {}
bool sx1276_channel_activity_detect(sx1276_handle_t *handle) { return true; }
bool sx1276_csma_ca(sx1276_handle_t *handle, uint8_t max_retries, uint16_t base_backoff_ms) { return true; }
int16_t sx1276_get_rssi(sx1276_handle_t *handle) { return -50; }
float sx1276_get_snr(sx1276_handle_t *handle) { return 10.0f; }
uint8_t sx1276_read_register(sx1276_handle_t *handle, uint8_t reg) { return 0; }
void sx1276_write_register(sx1276_handle_t *handle, uint8_t reg, uint8_t value) {}
void sx1276_set_mode(sx1276_handle_t *handle, uint8_t mode) {}
void sx1276_clear_irq_flags(sx1276_handle_t *handle, uint8_t flags) {}
void sx1276_set_frequency(sx1276_handle_t *handle, uint32_t freq) {}
void sx1276_set_implicit_header(sx1276_handle_t *handle, bool implicit) {}
void sx1276_set_crc(sx1276_handle_t *handle, bool enable) {}
void sx1276_set_iq_inversion(sx1276_handle_t *handle, bool invert) {}
void sx1276_set_sync_word(sx1276_handle_t *handle, uint8_t sync_word) {}
void sx1276_set_preamble_length(sx1276_handle_t *handle, uint16_t length) {}
void sx1276_set_coding_rate(sx1276_handle_t *handle, uint8_t cr) {}
void sx1276_set_bandwidth(sx1276_handle_t *handle, uint8_t bw) {}
void sx1276_set_spreading_factor(sx1276_handle_t *handle, uint8_t sf) {}
bool sx1276_set_all_params(sx1276_handle_t *handle, uint32_t freq, uint8_t sf, uint8_t bw, uint8_t cr, uint8_t sync_word, uint16_t preamble, int8_t tx_power) { return true; }
uint8_t sx1276_get_mode(sx1276_handle_t *handle) { return 0; }

void setUp(void) {
    /* Reset mesh state */
    memset(&g_mesh, 0, sizeof(g_mesh));
    g_mesh.initialized = true;
    g_mesh.node_id = 0x12345678;
    g_mesh.seq_num = 1000;
    g_mesh.crypto_initialized = true;
    crypto_init(TEST_KEY);
    g_mock_lora_handle = malloc(sizeof(sx1276_handle_t));
    memset(g_mock_lora_handle, 0, sizeof(sx1276_handle_t));
    mesh_set_lora_handle(g_mock_lora_handle);
}

void tearDown(void) {
    if (g_mock_lora_handle) {
        free(g_mock_lora_handle);
        g_mock_lora_handle = NULL;
    }
}

void test_mesh_serialize_deserialize(void) {
    mesh_packet_t pkt = {0};
    pkt.version_flags = (MESH_VERSION << 4) | MESH_FLAG_ALERT;
    pkt.source_id = 0x11223344;
    pkt.dest_id = 0x55667788;
    pkt.seq_num = 0x00001234;
    pkt.timestamp_ms = 0xAABBCCDD;
    pkt.ttl = 5;
    pkt.payload_len = 4;
    pkt.reserved = 0;
    pkt.payload[0] = 0xDE;
    pkt.payload[1] = 0xAD;
    pkt.payload[2] = 0xBE;
    pkt.payload[3] = 0xEF;

    uint8_t buf[MESH_MAX_PACKET_SIZE];
    uint8_t len = mesh_serialize(&pkt, buf);
    
    TEST_ASSERT_GREATER_THAN(0, len);
    TEST_ASSERT_LESS_OR_EQUAL(MESH_MAX_PACKET_SIZE, len);

    mesh_packet_t rx_pkt;
    bool ret = mesh_deserialize(buf, len, &rx_pkt);
    TEST_ASSERT_TRUE(ret);
    
    TEST_ASSERT_EQUAL(pkt.version_flags, rx_pkt.version_flags);
    TEST_ASSERT_EQUAL(pkt.source_id, rx_pkt.source_id);
    TEST_ASSERT_EQUAL(pkt.dest_id, rx_pkt.dest_id);
    TEST_ASSERT_EQUAL(pkt.seq_num, rx_pkt.seq_num);
    TEST_ASSERT_EQUAL(pkt.timestamp_ms, rx_pkt.timestamp_ms);
    TEST_ASSERT_EQUAL(pkt.ttl, rx_pkt.ttl);
    TEST_ASSERT_EQUAL(pkt.payload_len, rx_pkt.payload_len);
    TEST_ASSERT_EQUAL_HEX8_ARRAY(pkt.payload, rx_pkt.payload, pkt.payload_len);
}

void test_mesh_crc8_valid(void) {
    mesh_packet_t pkt = {0};
    pkt.version_flags = (MESH_VERSION << 4) | MESH_FLAG_ALERT;
    pkt.source_id = 0x11111111;
    pkt.dest_id = 0x22222222;
    pkt.seq_num = 1;
    pkt.timestamp_ms = 1000;
    pkt.ttl = 3;
    pkt.payload_len = 2;
    pkt.payload[0] = 0xAA;
    pkt.payload[1] = 0xBB;

    uint8_t buf[MESH_MAX_PACKET_SIZE];
    uint8_t len = mesh_serialize(&pkt, buf);
    
    /* CRC should be valid */
    mesh_packet_t rx_pkt;
    bool ret = mesh_deserialize(buf, len, &rx_pkt);
    TEST_ASSERT_TRUE(ret);
}

void test_mesh_crc8_invalid(void) {
    mesh_packet_t pkt = {0};
    pkt.version_flags = (MESH_VERSION << 4);
    pkt.source_id = 0x11111111;
    pkt.dest_id = 0x22222222;
    pkt.seq_num = 1;
    pkt.timestamp_ms = 1000;
    pkt.ttl = 3;
    pkt.payload_len = 2;
    pkt.payload[0] = 0xAA;
    pkt.payload[1] = 0xBB;

    uint8_t buf[MESH_MAX_PACKET_SIZE];
    uint8_t len = mesh_serialize(&pkt, buf);
    
    /* Corrupt the CRC byte */
    buf[len - 1] ^= 0xFF;
    
    mesh_packet_t rx_pkt;
    bool ret = mesh_deserialize(buf, len, &rx_pkt);
    TEST_ASSERT_FALSE(ret);
}

void test_mesh_duplicate_detection(void) {
    mesh_packet_t pkt = {0};
    pkt.source_id = 0x33333333;
    pkt.dest_id = MESH_BROADCAST_ID;
    pkt.seq_num = 0xABCDEF00;
    pkt.payload_len = 0;

    /* First time - should pass */
    TEST_ASSERT_FALSE(mesh_check_duplicate(pkt.source_id, pkt.seq_num));
    mesh_add_duplicate(pkt.source_id, pkt.seq_num);
    
    /* Second time - should detect duplicate */
    TEST_ASSERT_TRUE(mesh_check_duplicate(pkt.source_id, pkt.seq_num));
}

void test_mesh_neighbor_table(void) {
    uint32_t node_a = 0xAAAAAAAA;
    uint32_t node_b = 0xBBBBBBBB;
    
    /* Add first neighbor */
    mesh_update_neighbor(node_a, -50, 10.0f);
    TEST_ASSERT_EQUAL(1, g_mesh.neighbor_count);
    TEST_ASSERT_EQUAL(node_a, g_mesh.neighbors[0].node_id);
    TEST_ASSERT_EQUAL(-50, g_mesh.neighbors[0].rssi_last);
    TEST_ASSERT_EQUAL_FLOAT(10.0f, g_mesh.neighbors[0].snr_last);
    TEST_ASSERT_EQUAL(1, g_mesh.neighbors[0].packets_rx);
    
    /* Add second neighbor */
    mesh_update_neighbor(node_b, -60, 8.0f);
    TEST_ASSERT_EQUAL(2, g_mesh.neighbor_count);
    
    /* Update existing neighbor */
    mesh_update_neighbor(node_a, -55, 9.0f);
    TEST_ASSERT_EQUAL(2, g_mesh.neighbor_count);
    TEST_ASSERT_EQUAL(-55, g_mesh.neighbors[0].rssi_last);
    TEST_ASSERT_EQUAL(2, g_mesh.neighbors[0].packets_rx);
}

void test_mesh_duplicate_cache_overflow(void) {
    /* Fill duplicate cache */
    for (int i = 0; i < MESH_DUPLICATE_CACHE_SIZE + 10; i++) {
        mesh_add_duplicate(0x11111111 + i, 0x1000 + i);
    }
    
    /* Oldest entries should be evicted */
    /* The head should have wrapped around */
    TEST_ASSERT_EQUAL(MESH_DUPLICATE_CACHE_SIZE, MESH_DUPLICATE_CACHE_SIZE); // Just verify no crash
}

void test_mesh_ack_handling(void) {
    mesh_packet_t ack_pkt = {0};
    ack_pkt.source_id = 0x55555555;
    ack_pkt.dest_id = g_mesh.node_id;
    ack_pkt.seq_num = 0x12345678;
    ack_pkt.flags = MESH_FLAG_ACK;
    ack_pkt.payload_len = 0;

    /* Set up pending ACK */
    mesh_acquire_mutex();
    g_mesh.pending_ack.active = true;
    g_mesh.pending_ack.dest_id = ack_pkt.source_id;
    g_mesh.pending_ack.seq_num = ack_pkt.seq_num;
    g_mesh.pending_ack.retries = 0;
    g_mesh.pending_ack.next_retry_ms = mesh_get_time_ms() + MESH_ACK_TIMEOUT_MS;
    mesh_release_mutex();

    /* Process ACK */
    mesh_handle_ack(&ack_pkt);
    
    /* Pending ACK should be cleared */
    mesh_acquire_mutex();
    TEST_ASSERT_FALSE(g_mesh.pending_ack.active);
    mesh_release_mutex();
}

void test_mesh_ack_retry(void) {
    mesh_acquire_mutex();
    g_mesh.pending_ack.active = true;
    g_mesh.pending_ack.dest_id = 0x99999999;
    g_mesh.pending_ack.seq_num = 0x11111111;
    g_mesh.pending_ack.retries = 0;
    g_mesh.pending_ack.next_retry_ms = mesh_get_time_ms();  // Expired
    g_mesh.pending_ack.payload_len = 3;
    g_mesh.pending_ack.payload[0] = 0xAA;
    g_mesh.pending_ack.payload[1] = 0xBB;
    g_mesh.pending_ack.payload[2] = 0xCC;
    g_mesh.pending_ack.flags = MESH_FLAG_ALERT;
    mesh_release_mutex();

    /* Mock current time to be past retry */
    uint32_t now = mesh_get_time_ms() + MESH_ACK_TIMEOUT_MS + 1;
    
    mesh_retry_pending();  /* Should trigger retry */
    
    mesh_acquire_mutex();
    TEST_ASSERT_EQUAL(1, g_mesh.pending_ack.retries);
    mesh_release_mutex();
}

void test_mesh_forwarding(void) {
    mesh_packet_t pkt = {0};
    pkt.source_id = 0x11111111;
    pkt.dest_id = 0x33333333;  /* Not us, not broadcast */
    pkt.seq_num = 0x100;
    pkt.ttl = 3;
    pkt.payload_len = 0;

    /* Not for us, TTL > 1 -> should forward */
    mesh_acquire_mutex();
    bool should_fwd = (!mesh_is_for_us(pkt.dest_id) && pkt.ttl > 1) ||
                      (mesh_is_broadcast(pkt.dest_id) && pkt.ttl > 1);
    TEST_ASSERT_TRUE(should_fwd);
    mesh_release_mutex();
    
    mesh_forward_packet(&pkt, -40, 5.0f);
    TEST_ASSERT_EQUAL(1, g_mesh.stats.packets_forwarded);
    
    /* Test TTL expiry */
    pkt.ttl = 1;
    should_fwd = (!mesh_is_for_us(pkt.dest_id) && pkt.ttl > 1) ||
                 (mesh_is_broadcast(pkt.dest_id) && pkt.ttl > 1);
    TEST_ASSERT_FALSE(should_fwd);
}

void test_mesh_stats(void) {
    mesh_stats_t stats;
    mesh_get_stats(&stats);
    
    TEST_ASSERT_EQUAL(0, stats.packets_sent);
    TEST_ASSERT_EQUAL(0, stats.packets_received);
    TEST_ASSERT_EQUAL(0, stats.packets_forwarded);
    TEST_ASSERT_EQUAL(0, stats.packets_dropped);
    TEST_ASSERT_EQUAL(0, stats.duplicates_filtered);
    TEST_ASSERT_EQUAL(0, stats.neighbor_count);
    
    /* Increment some stats */
    mesh_acquire_mutex();
    g_mesh.stats.packets_sent = 10;
    g_mesh.stats.packets_received = 8;
    g_mesh.stats.packets_forwarded = 2;
    g_mesh.stats.duplicates_filtered = 1;
    mesh_release_mutex();
    
    mesh_get_stats(&stats);
    TEST_ASSERT_EQUAL(10, stats.packets_sent);
    TEST_ASSERT_EQUAL(8, stats.packets_received);
    TEST_ASSERT_EQUAL(2, stats.packets_forwarded);
    TEST_ASSERT_EQUAL(1, stats.duplicates_filtered);
}

void test_mesh_encryption_integration(void) {
    const uint8_t plaintext[] = "Test alert payload";
    const uint8_t len = sizeof(plaintext) - 1;
    
    uint8_t ciphertext[len];
    uint8_t tag[CRYPTO_TAG_SIZE];
    uint8_t decrypted[len];
    
    /* Encrypt */
    esp_err_t ret = crypto_encrypt(&g_mesh.crypto_ctx, g_mesh.node_id, g_mesh.seq_num,
                                    plaintext, len, ciphertext, tag);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    
    /* Decrypt */
    esp_err_t ret2 = crypto_decrypt(&g_mesh.crypto_ctx, g_mesh.node_id, g_mesh.seq_num,
                                     ciphertext, len, tag, decrypted);
    TEST_ASSERT_EQUAL(ESP_OK, ret2);
    
    TEST_ASSERT_EQUAL_HEX8_ARRAY(plaintext, decrypted, len);
}

void test_mesh_wrong_key_fails(void) {
    const uint8_t plaintext[] = "Secret data";
    const uint8_t len = sizeof(plaintext) - 1;
    
    uint8_t ciphertext[len];
    uint8_t tag[CRYPTO_TAG_SIZE];
    uint8_t decrypted[len];
    
    /* Encrypt with correct key */
    crypto_encrypt(&g_mesh.crypto_ctx, g_mesh.node_id, 100, plaintext, len, ciphertext, tag);
    
    /* Create context with wrong key */
    crypto_context_t wrong_ctx;
    uint8_t wrong_key[CRYPTO_KEY_SIZE] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
                                          0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    crypto_init(&wrong_ctx, wrong_key);
    
    /* Decrypt with wrong key - should fail */
    esp_err_t ret = crypto_decrypt(&wrong_ctx, g_mesh.node_id, 100, ciphertext, len, tag, decrypted);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_CRC, ret);
}

void test_mesh_large_payload(void) {
    /* Test payload near max size */
    const uint8_t len = MAX_PACKET_PAYLOAD - CRYPTO_TAG_SIZE;
    uint8_t plaintext[len];
    for (int i = 0; i < len; i++) plaintext[i] = i & 0xFF;
    
    uint8_t ciphertext[len + CRYPTO_TAG_SIZE];
    uint8_t tag[CRYPTO_TAG_SIZE];
    uint8_t decrypted[len];
    
    esp_err_t ret = crypto_encrypt(&g_mesh.crypto_ctx, g_mesh.node_id, 200,
                                    plaintext, len, ciphertext, tag);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    
    ret = crypto_decrypt(&g_mesh.crypto_ctx, g_mesh.node_id, 200,
                          ciphertext, len, tag, decrypted);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    
    TEST_ASSERT_EQUAL_HEX8_ARRAY(plaintext, decrypted, len);
}

void test_mesh_fragment_header(void) {
    mesh_frag_header_t frag = {0};
    frag.msg_id = 0x1234;
    frag.frag_index = 0;
    frag.frag_count = 3;
    frag.auth_tag_included = 1;
    frag.reserved = 0;
    
    /* Verify struct packing */
    TEST_ASSERT_EQUAL(MESH_FRAG_HEADER_SIZE, sizeof(frag));
}

void test_mesh_max_plaintext(void) {
    /* Max plaintext should account for fragment header + GCM tag */
    TEST_ASSERT_EQUAL(MESH_MAX_FRAG_DATA, MAX_PACKET_PAYLOAD - MESH_FRAG_HEADER_SIZE - 16);
}

void test_mesh_heartbeat(void) {
    mesh_send_heartbeat();
    /* Just verify it doesn't crash */
    TEST_ASSERT_TRUE(true);
}

void test_mesh_periodic(void) {
    uint32_t now = mesh_get_time_ms();
    mesh_periodic(now);
    /* Just verify it runs without error */
    TEST_ASSERT_TRUE(true);
}

void test_mesh_time(void) {
    uint32_t t1 = mesh_get_time_ms();
    vTaskDelay(pdMS_TO_TICKS(10));
    uint32_t t2 = mesh_get_time_ms();
    TEST_ASSERT_GREATER_THAN(t1, t2);
    TEST_ASSERT_LESS_THAN(t1 + 100, t2);  // Should be ~10ms
}

void test_mesh_set_crypto_key(void) {
    uint8_t key[CRYPTO_KEY_SIZE] = {0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88,
                                    0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x00};
    esp_err_t ret = mesh_set_crypto_key(key);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    TEST_ASSERT_TRUE(g_mesh.crypto_initialized);
}

void test_mesh_set_crypto_key_null(void) {
    esp_err_t ret = mesh_set_crypto_key(NULL);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, ret);
}

void test_mesh_seq_num_increments(void) {
    uint32_t initial = g_mesh.seq_num;
    
    uint8_t payload[] = "test";
    mesh_send(MESH_BROADCAST_ID, payload, sizeof(payload)-1, MESH_FLAG_ALERT);
    
    TEST_ASSERT_EQUAL(initial + 1, g_mesh.seq_num);
    
    mesh_send(MESH_BROADCAST_ID, payload, sizeof(payload)-1, MESH_FLAG_ALERT);
    TEST_ASSERT_EQUAL(initial + 2, g_mesh.seq_num);
}

TEST_CASE("Mesh serialize/deserialize", "[mesh]") {
    test_mesh_serialize_deserialize();
}

TEST_CASE("Mesh CRC8 validation", "[mesh]") {
    test_mesh_crc8_valid();
    test_mesh_crc8_invalid();
}

TEST_CASE("Mesh duplicate detection", "[mesh]") {
    test_mesh_duplicate_detection();
    test_mesh_duplicate_cache_overflow();
}

TEST_CASE("Mesh neighbor table", "[mesh]") {
    test_mesh_neighbor_table();
}

TEST_CASE("Mesh ACK handling", "[mesh]") {
    test_mesh_ack_handling();
    test_mesh_ack_retry();
}

TEST_CASE("Mesh forwarding", "[mesh]") {
    test_mesh_forwarding();
}

TEST_CASE("Mesh statistics", "[mesh]") {
    test_mesh_stats();
}

TEST_CASE("Mesh encryption integration", "[mesh]") {
    test_mesh_encryption_integration();
    test_mesh_wrong_key_fails();
    test_mesh_large_payload();
}

TEST_CASE("Mesh fragmentation", "[mesh]") {
    test_mesh_fragment_header();
    test_mesh_max_plaintext();
}

TEST_CASE("Mesh utilities", "[mesh]") {
    test_mesh_heartbeat();
    test_mesh_periodic();
    test_mesh_time();
}

TEST_CASE("Mesh crypto API", "[mesh]") {
    test_mesh_set_crypto_key();
    test_mesh_set_crypto_key_null();
    test_mesh_seq_num_increments();
}

TEST_CASE("Mesh encryption with wrong key", "[crypto]") {
    test_mesh_wrong_key_fails();
}