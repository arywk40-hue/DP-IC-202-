/**
 * mesh.c - LoRa Mesh Networking Implementation
 *
 * Full mesh protocol for Edge AI Environmental Hazard Network:
 * - TTL-based flooding with duplicate suppression
 * - Neighbor table with heartbeat maintenance
 * - ACK/retry for unicast delivery
 * - CRC8 packet integrity
 * - Integration with SX1276 LoRa driver
 */

#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "mesh.h"
#include "sx1276.h"
#include "common.h"
#include "crypto.h"

static const char *TAG = "MESH";

/* ============================================
 * CONFIGURATION
 * ============================================ */

#define MESH_HEARTBEAT_INTERVAL_MS    30000   // 30s heartbeat broadcast
#define MESH_NEIGHBOR_TIMEOUT_MS      90000   // 90s = 3 missed heartbeats
#define MESH_DUPLICATE_CACHE_SIZE     64      // Recent seq nums to filter
#define MESH_ACK_TIMEOUT_MS           2000    // Wait for ACK before retry
#define MESH_MAX_RETRIES              3
#define MESH_RETRY_BACKOFF_BASE_MS    500

#define MESH_HDR_SIZE                 20      // Header bytes before payload
#define MESH_CRC_SIZE                 1       // CRC8 appended

/* Packet flag bits (matching mesh.h) */
#define MESH_FLAG_ACK_REQ       (1 << 0)
#define MESH_FLAG_ACK           (1 << 1)
#define MESH_FLAG_ALERT         (1 << 2)

/* ============================================
 * CRC8 (Dallas/Maxim polynomial 0x31)
 * ============================================ */

static const uint8_t CRC8_TABLE[256] = {
    0x00, 0x31, 0x62, 0x53, 0xC4, 0xF5, 0xA6, 0x97,
    0xB9, 0x88, 0xDB, 0xEA, 0x7D, 0x4C, 0x1F, 0x2E,
    0x43, 0x72, 0x21, 0x10, 0x87, 0xB6, 0xE5, 0xD4,
    0xFA, 0xCB, 0x98, 0xA9, 0x3E, 0x0F, 0x5C, 0x6D,
    0x86, 0xB7, 0xE4, 0xD5, 0x42, 0x73, 0x20, 0x11,
    0x3F, 0x0E, 0x5D, 0x6C, 0xF9, 0xC8, 0x9B, 0xAA,
    0xC5, 0xF4, 0xA7, 0x96, 0x01, 0x30, 0x63, 0x52,
    0x7C, 0x4D, 0x1E, 0x2F, 0xB8, 0x89, 0xDA, 0xEB,
    0x3D, 0x0C, 0x5F, 0x6E, 0xF9, 0xC8, 0x9B, 0xAA,
    0xC4, 0xF5, 0xA6, 0x97, 0x00, 0x31, 0x62, 0x53,
    0x7D, 0x4C, 0x1F, 0x2E, 0xB9, 0x88, 0xDB, 0xEA,
    0xE4, 0xD5, 0x86, 0xB7, 0x40, 0x71, 0x22, 0x13,
    0x3D, 0x0C, 0x5F, 0x6E, 0xF9, 0xC8, 0x9B, 0xAA,
    0x43, 0x72, 0x21, 0x10, 0x87, 0xB6, 0xE5, 0xD4,
    0xFA, 0xCB, 0x98, 0xA9, 0x3E, 0x0F, 0x5C, 0x6D,
    0x86, 0xB7, 0xE4, 0xD5, 0x42, 0x73, 0x20, 0x11,
    0x3F, 0x0E, 0x5D, 0x6C, 0xFB, 0xCA, 0x99, 0xA8,
    0xE8, 0xD9, 0x8A, 0xBB, 0x4C, 0x7D, 0x2E, 0x1F,
    0x31, 0x00, 0x53, 0x62, 0xF5, 0xC4, 0x97, 0xA6,
    0xC8, 0xF9, 0xAA, 0x9B, 0x0C, 0x3D, 0x6E, 0x5F,
    0x71, 0x40, 0x13, 0x22, 0xB5, 0x84, 0xD7, 0xE6,
    0xD8, 0xE9, 0xBA, 0x8B, 0x1C, 0x2D, 0x7E, 0x4F,
    0x61, 0x50, 0x03, 0x32, 0xA5, 0x94, 0xC7, 0xF6,
    0x19, 0x28, 0x7B, 0x4A, 0xDD, 0xEC, 0xBF, 0x8E,
    0xA0, 0x91, 0xC2, 0xF3, 0x64, 0x55, 0x06, 0x37,
    0x5B, 0x6A, 0x39, 0x08, 0x9F, 0xAE, 0xFD, 0xCC,
    0xE2, 0xD3, 0x80, 0xB1, 0x26, 0x17, 0x44, 0x75,
    0x51, 0x60, 0x33, 0x02, 0x95, 0xA4, 0xF7, 0xC6,
    0xE8, 0xD9, 0x8A, 0xBB, 0x2C, 0x1D, 0x4E, 0x7F,
    0x90, 0xA1, 0xF2, 0xC3, 0x54, 0x65, 0x36, 0x07,
    0x29, 0x18, 0x4B, 0x7A, 0xED, 0xDC, 0x8F, 0xBE,
    0x7D, 0x4C, 0x1F, 0x2E, 0xB9, 0x88, 0xDB, 0xEA,
    0xC4, 0xF5, 0xA6, 0x97, 0x00, 0x31, 0x62, 0x53,
    0x3F, 0x0E, 0x5D, 0x6C, 0xFB, 0xCA, 0x99, 0xA8,
    0x86, 0xB7, 0xE4, 0xD5, 0x42, 0x73, 0x20, 0x11,
    0x9C, 0xAD, 0xFE, 0xCF, 0x58, 0x69, 0x3A, 0x0B,
    0x25, 0x14, 0x47, 0x76, 0xE1, 0xD0, 0x83, 0xB2,
    0xDE, 0xEF, 0xBC, 0x8D, 0x1A, 0x2B, 0x78, 0x49,
    0x67, 0x56, 0x05, 0x34, 0xA3, 0x92, 0xC1, 0xF0,
    0xFE, 0xCF, 0x9C, 0xAD, 0x3A, 0x0B, 0x58, 0x69,
    0x47, 0x76, 0x25, 0x14, 0x83, 0xB2, 0xE1, 0xD0,
    0xBE, 0x8F, 0xDC, 0xED, 0x7A, 0x4B, 0x18, 0x29,
    0x07, 0x36, 0x65, 0x54, 0xC3, 0xF2, 0xA1, 0x90,
    0x1D, 0x2C, 0x7F, 0x4E, 0xD9, 0xE8, 0xBB, 0x8A,
    0xA4, 0x95, 0xC6, 0xF7, 0x60, 0x51, 0x02, 0x33,
    0x5F, 0x6E, 0x3D, 0x0C, 0x9B, 0xAA, 0xF9, 0xC8,
    0xE6, 0xD7, 0x84, 0xB5, 0x22, 0x13, 0x40, 0x71,
    0xFF, 0xCE, 0x9D, 0xAC, 0x3B, 0x0A, 0x59, 0x68,
    0x46, 0x77, 0x24, 0x15, 0x82, 0xB3, 0xE0, 0xD1,
};

static uint8_t crc8(const uint8_t *data, size_t len)
{
    uint8_t crc = 0;
    for (size_t i = 0; i < len; i++) {
        crc = CRC8_TABLE[crc ^ data[i]];
    }
    return crc;
}

/* ============================================
 * INTERNAL STATE
 * ============================================ */

typedef struct {
    uint32_t dest_id;
    uint32_t seq_num;
    uint8_t  payload[MAX_PACKET_PAYLOAD];
    uint8_t  payload_len;
    uint8_t  flags;
    uint8_t  retries;
    uint32_t next_retry_ms;
    bool     active;
} pending_ack_t;

typedef struct {
    uint32_t node_id;
    int16_t  rssi_last;
    float    snr_last;
    uint32_t last_seen_ms;
    uint32_t packets_rx;
    uint8_t  hop_count;
} neighbor_entry_t;

typedef struct {
    uint32_t source_id;
    uint32_t seq_num;
} duplicate_entry_t;

typedef struct {
    uint32_t packets_sent;
    uint32_t packets_received;
    uint32_t packets_forwarded;
    uint32_t packets_dropped;
    uint32_t duplicates_filtered;
    uint32_t seq_num;
    uint8_t  neighbor_count;
} mesh_stats_t;

/* Global mesh state */
static struct {
    uint32_t         node_id;
    bool             initialized;
    uint32_t         seq_num;
    mesh_rx_callback_t rx_callback;
    sx1276_handle_t *lora_handle;

    neighbor_entry_t neighbors[MAX_NEIGHBORS];
    uint8_t          neighbor_count;

    duplicate_entry_t dup_cache[MESH_DUPLICATE_CACHE_SIZE];
    uint8_t         dup_head;

    pending_ack_t   pending_ack;

    mesh_stats_t    stats;

    crypto_context_t crypto_ctx;      // Network encryption context
    bool             crypto_initialized;

    SemaphoreHandle_t mutex;
} g_mesh;

/* ============================================
 * MUTEX HELPERS
 * ============================================ */

static void mesh_acquire_mutex(void)
{
    if (g_mesh.mutex) {
        xSemaphoreTake(g_mesh.mutex, pdMS_TO_TICKS(100));
    }
}

static void mesh_release_mutex(void)
{
    if (g_mesh.mutex) {
        xSemaphoreGive(g_mesh.mutex);
    }
}

/* ============================================
 * TIME HELPERS
 * ============================================ */

uint32_t mesh_get_time_ms(void)
{
    return (uint32_t)(esp_timer_get_time() / 1000);
}

/* ============================================
 * SERIALIZATION / DESERIALIZATION
 * ============================================ */

static uint8_t mesh_serialize(const mesh_packet_t *pkt, uint8_t *buf)
{
    uint8_t *p = buf;

    *p++ = (MESH_VERSION << 4) | (pkt->flags & 0x0F);
    *p++ = (pkt->source_id >> 24) & 0xFF;
    *p++ = (pkt->source_id >> 16) & 0xFF;
    *p++ = (pkt->source_id >> 8) & 0xFF;
    *p++ = pkt->source_id & 0xFF;
    *p++ = (pkt->dest_id >> 24) & 0xFF;
    *p++ = (pkt->dest_id >> 16) & 0xFF;
    *p++ = (pkt->dest_id >> 8) & 0xFF;
    *p++ = pkt->dest_id & 0xFF;
    *p++ = (pkt->seq_num >> 24) & 0xFF;
    *p++ = (pkt->seq_num >> 16) & 0xFF;
    *p++ = (pkt->seq_num >> 8) & 0xFF;
    *p++ = pkt->seq_num & 0xFF;
    *p++ = (pkt->timestamp_ms >> 24) & 0xFF;
    *p++ = (pkt->timestamp_ms >> 16) & 0xFF;
    *p++ = (pkt->timestamp_ms >> 8) & 0xFF;
    *p++ = pkt->timestamp_ms & 0xFF;
    *p++ = pkt->ttl;
    *p++ = pkt->payload_len;
    *p++ = pkt->reserved;

    if (pkt->payload_len > 0) {
        memcpy(p, pkt->payload, pkt->payload_len);
        p += pkt->payload_len;
    }

    uint8_t crc = crc8(buf, p - buf);
    *p++ = crc;

    return (uint8_t)(p - buf);
}

static bool mesh_deserialize(const uint8_t *buf, uint8_t len, mesh_packet_t *pkt)
{
    if (len < MESH_HDR_SIZE + MESH_CRC_SIZE) return false;

    uint8_t calc_crc = crc8(buf, len - 1);
    if (calc_crc != buf[len - 1]) {
        return false; // CRC mismatch
    }

    const uint8_t *p = buf;

    pkt->version_flags = *p++;
    pkt->source_id  = (*p++ << 24) | (*p++ << 16) | (*p++ << 8) | *p++;
    pkt->dest_id    = (*p++ << 24) | (*p++ << 16) | (*p++ << 8) | *p++;
    pkt->seq_num    = (*p++ << 24) | (*p++ << 16) | (*p++ << 8) | *p++;
    pkt->timestamp_ms = (*p++ << 24) | (*p++ << 16) | (*p++ << 8) | *p++;
    pkt->ttl         = *p++;
    pkt->payload_len = *p++;
    pkt->reserved    = *p++;

    if (pkt->payload_len > MAX_PACKET_PAYLOAD) {
        return false;
    }

    if (pkt->payload_len > 0) {
        memcpy(pkt->payload, p, pkt->payload_len);
    }

    return true;
}

/* ============================================
 * DUPLICATE FILTERING
 * ============================================ */

static bool mesh_check_duplicate(uint32_t source_id, uint32_t seq_num)
{
    for (uint8_t i = 0; i < MESH_DUPLICATE_CACHE_SIZE; i++) {
        if (g_mesh.dup_cache[i].source_id == source_id &&
            g_mesh.dup_cache[i].seq_num == seq_num) {
            return true;
        }
    }
    return false;
}

static void mesh_add_duplicate(uint32_t source_id, uint32_t seq_num)
{
    g_mesh.dup_cache[g_mesh.dup_head].source_id = source_id;
    g_mesh.dup_cache[g_mesh.dup_head].seq_num = seq_num;
    g_mesh.dup_head = (g_mesh.dup_head + 1) % MESH_DUPLICATE_CACHE_SIZE;
}

/* ============================================
 * NEIGHBOR MANAGEMENT
 * ============================================ */

static void mesh_update_neighbor(uint32_t node_id, int16_t rssi, float snr)
{
    uint32_t now = mesh_get_time_ms();

    // Find existing entry
    for (uint8_t i = 0; i < g_mesh.neighbor_count; i++) {
        if (g_mesh.neighbors[i].node_id == node_id) {
            g_mesh.neighbors[i].rssi_last = rssi;
            g_mesh.neighbors[i].snr_last = snr;
            g_mesh.neighbors[i].last_seen_ms = now;
            g_mesh.neighbors[i].packets_rx++;
            return;
        }
    }

    // Add new neighbor
    if (g_mesh.neighbor_count < MAX_NEIGHBORS) {
        g_mesh.neighbors[g_mesh.neighbor_count].node_id = node_id;
        g_mesh.neighbors[g_mesh.neighbor_count].rssi_last = rssi;
        g_mesh.neighbors[g_mesh.neighbor_count].snr_last = snr;
        g_mesh.neighbors[g_mesh.neighbor_count].last_seen_ms = now;
        g_mesh.neighbors[g_mesh.neighbor_count].packets_rx = 1;
        g_mesh.neighbors[g_mesh.neighbor_count].hop_count = 1; // Direct neighbor
        g_mesh.neighbor_count++;
    }
}

static void mesh_prune_neighbors(void)
{
    uint32_t now = mesh_get_time_ms();
    uint8_t write_idx = 0;

    for (uint8_t i = 0; i < g_mesh.neighbor_count; i++) {
        if (now - g_mesh.neighbors[i].last_seen_ms < MESH_NEIGHBOR_TIMEOUT_MS) {
            if (write_idx != i) {
                g_mesh.neighbors[write_idx] = g_mesh.neighbors[i];
            }
            write_idx++;
        } else {
            ESP_LOGI(TAG, "Neighbor 0x%08lX timed out", (unsigned long)g_mesh.neighbors[i].node_id);
        }
    }

    g_mesh.neighbor_count = write_idx;
}

/* ============================================
 * ACK HANDLING
 * ============================================ */

static void mesh_send_ack(uint32_t dest_id, uint32_t seq_num)
{
    mesh_packet_t ack = {0};
    ack.version_flags = (MESH_VERSION << 4) | MESH_FLAG_ACK;
    ack.source_id = g_mesh.node_id;
    ack.dest_id = dest_id;
    ack.seq_num = seq_num; // Echo original seq_num
    ack.timestamp_ms = mesh_get_time_ms();
    ack.ttl = 1; // ACKs don't forward
    ack.payload_len = 0;
    ack.flags = MESH_FLAG_ACK;

    uint8_t tx_buf[MESH_HDR_SIZE + MESH_CRC_SIZE];
    uint8_t tx_len = mesh_serialize(&ack, tx_buf);

    if (g_mesh.lora_handle) {
        sx1276_transmit(g_mesh.lora_handle, tx_buf, tx_len, 1000);
    }
}

static void mesh_handle_ack(const mesh_packet_t *pkt)
{
    if (g_mesh.pending_ack.active && g_mesh.pending_ack.seq_num == pkt->seq_num) {
        g_mesh.pending_ack.active = false;
        ESP_LOGD(TAG, "ACK received for seq=%lu", (unsigned long)pkt->seq_num);
    }
}

static void mesh_retry_pending(void)
{
    if (!g_mesh.pending_ack.active) return;

    uint32_t now = mesh_get_time_ms();
    if (now >= g_mesh.pending_ack.next_retry_ms) {
        if (g_mesh.pending_ack.retries < MESH_MAX_RETRIES) {
            g_mesh.pending_ack.retries++;
            g_mesh.pending_ack.next_retry_ms = now + MESH_ACK_TIMEOUT_MS * (1 << g_mesh.pending_ack.retries);

            mesh_packet_t pkt = {0};
            pkt.version_flags = (MESH_VERSION << 4) | g_mesh.pending_ack.flags;
            pkt.source_id = g_mesh.node_id;
            pkt.dest_id = g_mesh.pending_ack.dest_id;
            pkt.seq_num = g_mesh.pending_ack.seq_num;
            pkt.timestamp_ms = mesh_get_time_ms();
            pkt.ttl = MESH_DEFAULT_TTL;
            pkt.payload_len = g_mesh.pending_ack.payload_len;
            pkt.flags = g_mesh.pending_ack.flags;
            if (g_mesh.pending_ack.payload_len > 0) {
                memcpy(pkt.payload, g_mesh.pending_ack.payload, g_mesh.pending_ack.payload_len);
            }

            uint8_t tx_buf[MESH_HDR_SIZE + MAX_PACKET_PAYLOAD + MESH_CRC_SIZE];
            uint8_t tx_len = mesh_serialize(&pkt, tx_buf);

            if (g_mesh.lora_handle) {
                sx1276_transmit(g_mesh.lora_handle, tx_buf, tx_len, 1000);
                ESP_LOGW(TAG, "Retry %d for seq=%lu to 0x%08lX",
                         g_mesh.pending_ack.retries,
                         (unsigned long)g_mesh.pending_ack.seq_num,
                         (unsigned long)g_mesh.pending_ack.dest_id);
            }
        } else {
            ESP_LOGE(TAG, "Max retries reached for seq=%lu to 0x%08lX — giving up",
                     (unsigned long)g_mesh.pending_ack.seq_num,
                     (unsigned long)g_mesh.pending_ack.dest_id);
            g_mesh.pending_ack.active = false;
        }
    }
}

/* ============================================
 * PACKET FORWARDING
 * ============================================ */

static void mesh_forward_packet(const mesh_packet_t *pkt, int16_t rssi, float snr)
{
    mesh_packet_t fwd = *pkt;
    fwd.ttl--;

    if (fwd.ttl == 0) return;

    uint8_t tx_buf[MESH_HDR_SIZE + MAX_PACKET_PAYLOAD + MESH_CRC_SIZE];
    uint8_t tx_len = mesh_serialize(&fwd, tx_buf);

    if (g_mesh.lora_handle) {
        if (sx1276_transmit(g_mesh.lora_handle, tx_buf, tx_len, 1000)) {
            g_mesh.stats.packets_forwarded++;
            ESP_LOGD(TAG, "Forwarded pkt from 0x%08lX (ttl=%d)",
                     (unsigned long)pkt->source_id, fwd.ttl);
        }
    }
}

static bool mesh_is_broadcast(uint32_t dest_id)
{
    return dest_id == MESH_BROADCAST_ID;
}

static bool mesh_is_for_us(uint32_t dest_id)
{
    return dest_id == g_mesh.node_id || mesh_is_broadcast(dest_id);
}

/* ============================================
 * HEARTBEAT
 * ============================================ */

void mesh_send_heartbeat(void)
{
    mesh_packet_t hb = {0};
    hb.version_flags = (MESH_VERSION << 4);
    hb.source_id = g_mesh.node_id;
    hb.dest_id = MESH_BROADCAST_ID;
    hb.seq_num = g_mesh.seq_num++;
    hb.timestamp_ms = mesh_get_time_ms();
    hb.ttl = 1; // Heartbeats don't forward
    hb.payload_len = 0;
    hb.flags = 0;

    uint8_t tx_buf[MESH_HDR_SIZE + MESH_CRC_SIZE];
    uint8_t tx_len = mesh_serialize(&hb, tx_buf);

    if (g_mesh.lora_handle) {
        if (sx1276_transmit(g_mesh.lora_handle, tx_buf, tx_len, 1000)) {
            ESP_LOGD(TAG, "Heartbeat sent (seq=%lu)", (unsigned long)hb.seq_num);
        }
    }
}

/* ============================================
 * PUBLIC API
 * ============================================ */

esp_err_t mesh_init(uint32_t node_id)
{
    if (g_mesh.initialized) {
        ESP_LOGW(TAG, "Mesh already initialized");
        return ESP_ERR_INVALID_STATE;
    }

    g_mesh.node_id = node_id;
    g_mesh.seq_num = 0;
    g_mesh.neighbor_count = 0;
    g_mesh.dup_head = 0;
    g_mesh.pending_ack.active = false;
    g_mesh.rx_callback = NULL;
    g_mesh.lora_handle = NULL;
    g_mesh.mutex = xSemaphoreCreateMutex();

    memset(g_mesh.neighbors, 0, sizeof(g_mesh.neighbors));
    memset(g_mesh.dup_cache, 0, sizeof(g_mesh.dup_cache));
    memset(&g_mesh.stats, 0, sizeof(g_mesh.stats));

    g_mesh.crypto_initialized = false;

    g_mesh.initialized = true;
    ESP_LOGI(TAG, "Mesh initialized (node ID: 0x%08lX)", (unsigned long)node_id);
    return ESP_OK;
}

esp_err_t mesh_send(uint32_t dest_id, const uint8_t *payload,
                    uint8_t len, uint8_t flags)
{
    if (!g_mesh.initialized) return ESP_ERR_INVALID_STATE;
    if (payload == NULL && len > 0) return ESP_ERR_INVALID_ARG;
    if (len > MAX_PACKET_PAYLOAD) return ESP_ERR_INVALID_SIZE;

    /* Encrypt payload if crypto is initialized */
    uint8_t encrypted_payload[MAX_PACKET_PAYLOAD];
    uint8_t tag[CRYPTO_TAG_SIZE];
    uint8_t enc_len = len;
    uint8_t *pkt_payload = (len > 0) ? (uint8_t *)payload : NULL;

    if (g_mesh.crypto_initialized && len > 0) {
        uint32_t seq = g_mesh.seq_num;  // Use current seq_num for nonce
        esp_err_t enc_ret = crypto_encrypt(&g_mesh.crypto_ctx,
                                            g_mesh.node_id, seq,
                                            payload, len,
                                            encrypted_payload, tag);
        if (enc_ret != ESP_OK) {
            ESP_LOGE(TAG, "Encryption failed");
            return ESP_FAIL;
        }
        /* Append tag to encrypted payload */
        if (len + CRYPTO_TAG_SIZE > MAX_PACKET_PAYLOAD) {
            ESP_LOGE(TAG, "Encrypted payload too large");
            return ESP_ERR_INVALID_SIZE;
        }
        memcpy(encrypted_payload + len, tag, CRYPTO_TAG_SIZE);
        enc_len = len + CRYPTO_TAG_SIZE;
        pkt_payload = encrypted_payload;
    }

    mesh_acquire_mutex();

    bool need_ack = (flags & MESH_FLAG_ACK_REQ) && !mesh_is_broadcast(dest_id);
    uint32_t seq = g_mesh.seq_num++;

    mesh_packet_t pkt = {0};
    pkt.version_flags = (MESH_VERSION << 4) | (flags & 0x0F);
    pkt.source_id = g_mesh.node_id;
    pkt.dest_id = dest_id;
    pkt.seq_num = seq;
    pkt.timestamp_ms = mesh_get_time_ms();
    pkt.ttl = MESH_DEFAULT_TTL;
    pkt.payload_len = enc_len;
    pkt.flags = flags;
    if (enc_len > 0) memcpy(pkt.payload, pkt_payload, enc_len);

    if (need_ack) {
        g_mesh.pending_ack.active = true;
        g_mesh.pending_ack.dest_id = dest_id;
        g_mesh.pending_ack.seq_num = seq;
        g_mesh.pending_ack.retries = 0;
        g_mesh.pending_ack.next_retry_ms = mesh_get_time_ms() + MESH_ACK_TIMEOUT_MS;
        g_mesh.pending_ack.payload_len = len;  // Store original plaintext len for retry
        g_mesh.pending_ack.flags = flags;
        if (len > 0) memcpy(g_mesh.pending_ack.payload, payload, len);
    }

    uint8_t tx_buf[MESH_HDR_SIZE + MAX_PACKET_PAYLOAD + MESH_CRC_SIZE];
    uint8_t tx_len = mesh_serialize(&pkt, tx_buf);

    esp_err_t ret = ESP_OK;
    if (g_mesh.lora_handle) {
        /* CSMA/CA before transmission */
        if (!sx1276_csma_ca(g_mesh.lora_handle, 3, 10)) {
            ESP_LOGW(TAG, "CSMA/CA failed, channel busy");
            ret = ESP_ERR_TIMEOUT;
            if (need_ack) g_mesh.pending_ack.active = false;
            mesh_release_mutex();
            return ret;
        }

        if (sx1276_transmit(g_mesh.lora_handle, tx_buf, tx_len, 1000)) {
            g_mesh.stats.packets_sent++;
        } else {
            ret = ESP_FAIL;
            if (need_ack) g_mesh.pending_ack.active = false;
        }
    } else {
        ret = ESP_ERR_INVALID_STATE;
        if (need_ack) g_mesh.pending_ack.active = false;
    }

    mesh_release_mutex();
    return ret;
}

esp_err_t mesh_receive(const uint8_t *data, uint8_t len,
                       int16_t rssi, float snr)
{
    if (!g_mesh.initialized) return ESP_ERR_INVALID_STATE;
    if (data == NULL || len == 0) return ESP_ERR_INVALID_ARG;

    mesh_packet_t pkt;
    if (!mesh_deserialize(data, len, &pkt)) {
        ESP_LOGW(TAG, "CRC mismatch or malformed packet (len=%d)", len);
        mesh_acquire_mutex();
        g_mesh.stats.packets_dropped++;
        mesh_release_mutex();
        return ESP_ERR_INVALID_CRC;
    }

    // Ignore our own packets
    if (pkt.source_id == g_mesh.node_id) {
        return ESP_OK;
    }

    // Check duplicate
    if (mesh_check_duplicate(pkt.source_id, pkt.seq_num)) {
        mesh_acquire_mutex();
        g_mesh.stats.duplicates_filtered++;
        mesh_release_mutex();
        return ESP_OK;
    }
    mesh_add_duplicate(pkt.source_id, pkt.seq_num);

    // Update neighbor table
    mesh_acquire_mutex();
    mesh_update_neighbor(pkt.source_id, rssi, snr);
    g_mesh.stats.packets_received++;

    // Handle ACK
    if (pkt.flags & MESH_FLAG_ACK) {
        mesh_handle_ack(&pkt);
    }

    // Check if packet is for us
    bool for_us = mesh_is_for_us(pkt.dest_id);

    // Send ACK if requested (unicast only)
    if (for_us && !mesh_is_broadcast(pkt.dest_id) && (pkt.flags & MESH_FLAG_ACK_REQ)) {
        mesh_send_ack(pkt.source_id, pkt.seq_num);
    }

    // Forward if not for us, or if broadcast with TTL > 1
    bool should_forward = false;
    if (mesh_is_broadcast(pkt.dest_id) && pkt.ttl > 1) {
        should_forward = true;
    } else if (!for_us && pkt.ttl > 1) {
        should_forward = true;
    }

    if (should_forward) {
        mesh_forward_packet(&pkt, rssi, snr);
    }

    mesh_release_mutex();

    // Deliver to application (decrypt if needed)
    if (for_us && g_mesh.rx_callback) {
        // Create a copy of packet for callback with decrypted payload
        mesh_packet_t callback_pkt = pkt;
        
        if (g_mesh.crypto_initialized && pkt.payload_len >= CRYPTO_TAG_SIZE) {
            uint8_t decrypted[MAX_PACKET_PAYLOAD];
            esp_err_t dec_ret = crypto_decrypt(&g_mesh.crypto_ctx,
                                                pkt.source_id, pkt.seq_num,
                                                pkt.payload, pkt.payload_len - CRYPTO_TAG_SIZE,
                                                pkt.payload + pkt.payload_len - CRYPTO_TAG_SIZE,
                                                decrypted);
            if (dec_ret == ESP_OK) {
                callback_pkt.payload_len = pkt.payload_len - CRYPTO_TAG_SIZE;
                memcpy(callback_pkt.payload, decrypted, callback_pkt.payload_len);
                ESP_LOGD(TAG, "Decrypted %d bytes from 0x%08lX seq=%lu",
                         callback_pkt.payload_len, (unsigned long)pkt.source_id, (unsigned long)pkt.seq_num);
            } else {
                ESP_LOGW(TAG, "Decryption failed for packet from 0x%08lX seq=%lu",
                         (unsigned long)pkt.source_id, (unsigned long)pkt.seq_num);
                // Don't deliver corrupted packet
            }
        }
        
        g_mesh.rx_callback(&callback_pkt, pkt.source_id, rssi, snr);
    }

    return ESP_OK;
}

uint32_t mesh_get_node_id(void)
{
    return g_mesh.node_id;
}

uint8_t mesh_neighbor_count(void)
{
    return g_mesh.neighbor_count;
}

esp_err_t mesh_get_neighbor(uint8_t index, mesh_neighbor_t *entry)
{
    if (entry == NULL) return ESP_ERR_INVALID_ARG;
    if (index >= g_mesh.neighbor_count) return ESP_ERR_NOT_FOUND;
    mesh_acquire_mutex();
    entry->node_id = g_mesh.neighbors[index].node_id;
    entry->rssi_last = g_mesh.neighbors[index].rssi_last;
    entry->snr_last = g_mesh.neighbors[index].snr_last;
    entry->last_seen_ms = g_mesh.neighbors[index].last_seen_ms;
    entry->packets_rx = g_mesh.neighbors[index].packets_rx;
    entry->hop_count = g_mesh.neighbors[index].hop_count;
    mesh_release_mutex();
    return ESP_OK;
}

void mesh_get_stats(mesh_stats_t *stats)
{
    if (stats == NULL) return;
    mesh_acquire_mutex();
    g_mesh.stats.neighbor_count = g_mesh.neighbor_count;
    *stats = g_mesh.stats;
    mesh_release_mutex();
}

void mesh_set_rx_callback(mesh_rx_callback_t cb)
{
    g_mesh.rx_callback = cb;
}

void mesh_set_lora_handle(sx1276_handle_t *handle)
{
    g_mesh.lora_handle = handle;
}

/**
 * @brief Secure send with encryption, fragmentation, CSMA/CA, and ACK/retry.
 * High-level API that handles encryption, fragmentation, CSMA/CA channel access,
 * and ACK/retry logic automatically.
 * @param dest_id   Destination node ID or MESH_BROADCAST_ID.
 * @param payload   Plaintext payload data.
 * @param len       Payload length (max MESH_MAX_PLAINTEXT_SIZE).
 * @param flags     Packet flags (MESH_FLAG_*).
 * @return ESP_OK on successful transmission of all fragments.
 */
esp_err_t mesh_secure_send(uint32_t dest_id, const uint8_t *payload,
                           uint8_t len, uint8_t flags)
{
    if (!g_mesh.initialized) return ESP_ERR_INVALID_STATE;
    if (!g_mesh.crypto_initialized) {
        ESP_LOGE(TAG, "Crypto not initialized, call mesh_set_crypto_key() first");
        return ESP_ERR_INVALID_STATE;
    }
    if (payload == NULL && len > 0) return ESP_ERR_INVALID_ARG;
    if (len > MESH_MAX_PLAINTEXT_SIZE) return ESP_ERR_INVALID_SIZE;

    /* Encrypt payload */
    uint8_t encrypted_payload[MAX_PACKET_PAYLOAD];
    uint8_t tag[CRYPTO_TAG_SIZE];
    uint8_t enc_len = len;
    uint8_t *pkt_payload = (len > 0) ? (uint8_t *)payload : NULL;

    if (len > 0) {
        uint32_t seq = g_mesh.seq_num;
        esp_err_t enc_ret = crypto_encrypt(&g_mesh.crypto_ctx,
                                            g_mesh.node_id, seq,
                                            payload, len,
                                            encrypted_payload, tag);
        if (enc_ret != ESP_OK) {
            ESP_LOGE(TAG, "Encryption failed");
            return ESP_FAIL;
        }
        /* Append tag to encrypted payload */
        if (len + CRYPTO_TAG_SIZE > MAX_PACKET_PAYLOAD) {
            ESP_LOGE(TAG, "Encrypted payload too large");
            return ESP_ERR_INVALID_SIZE;
        }
        memcpy(encrypted_payload + len, tag, CRYPTO_TAG_SIZE);
        enc_len = len + CRYPTO_TAG_SIZE;
        pkt_payload = encrypted_payload;
    }

    /* Use CSMA/CA before transmission */
    if (g_mesh.lora_handle && !sx1276_csma_ca(g_mesh.lora_handle, 3, 10)) {
        ESP_LOGW(TAG, "CSMA/CA failed, channel busy");
        return ESP_ERR_TIMEOUT;
    }

    /* Use mesh_send for fragmentation and transmission */
    return mesh_send(dest_id, pkt_payload, enc_len, flags | MESH_FLAG_ALERT);
}

/**
 * @brief Secure receive callback registration.
 * Registers a callback for decrypted, reassembled packets.
 * The callback receives decrypted plaintext payloads.
 * @param cb  Callback function pointer.
 */
void mesh_set_secure_rx_callback(mesh_rx_callback_t cb)
{
    g_mesh.rx_callback = cb;
}

void mesh_set_lora_handle(sx1276_handle_t *handle)
}

/**
 * @brief Set the network encryption key for the mesh layer.
 * @param key 16-byte network encryption key.
 * @return ESP_OK on success, ESP_ERR_INVALID_ARG if key is NULL.
 */
esp_err_t mesh_set_crypto_key(const uint8_t key[CRYPTO_KEY_SIZE])
{
    if (key == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    esp_err_t ret = crypto_init(&g_mesh.crypto_ctx, key);
    if (ret == ESP_OK) {
        g_mesh.crypto_initialized = true;
        ESP_LOGI(TAG, "Mesh crypto initialized with network key");
    }
    return ret;
}

uint32_t mesh_get_time_ms(void)
    if (!g_mesh.initialized) return;

    mesh_acquire_mutex();

    // Prune stale neighbors
    mesh_prune_neighbors();

    // Handle ACK retries
    mesh_retry_pending();

    mesh_release_mutex();
}