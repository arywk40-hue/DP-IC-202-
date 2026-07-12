/**
 * mesh.c - LoRa Mesh Networking Implementation
 *
 * Stub implementation for Phase 1.
 * Will be replaced with a full mesh protocol (Phase 5) including
 * neighbor discovery, packet forwarding, duplicate suppression,
 * and acknowledgement handling.
 *
 * Current behavior:
 * - mesh_init() allocates state, sets node ID.
 * - mesh_send() logs intent but does not transmit.
 * - mesh_receive() validates stub CRC and calls application callback.
 * - All functions return properly typed error codes.
 */

#include <string.h>
#include "esp_log.h"
#include "mesh.h"

static const char *TAG = "MESH";

/* Static state — no malloc */
static uint32_t        g_node_id = 0;
static bool            g_initialized = false;
static uint32_t        g_seq_num = 0;
static mesh_rx_callback_t g_rx_callback = NULL;

/* Neighbor table — fixed-size array */
static mesh_neighbor_t g_neighbor_table[MAX_NEIGHBORS];
static uint8_t         g_neighbor_count = 0;

/* Statistics */
static mesh_stats_t    g_stats = {0};

/*
 * Simple XOR checksum for packet integrity.
 * Not cryptographically secure — wire in a proper CRC8/CRC16 in Phase 4.
 */
static uint8_t calc_checksum(const uint8_t *data, uint8_t len)
{
    uint8_t sum = 0;
    for (uint8_t i = 0; i < len; i++) {
        sum ^= data[i];
    }
    return sum;
}

esp_err_t mesh_init(uint32_t node_id)
{
    if (g_initialized) {
        ESP_LOGW(TAG, "Mesh already initialized");
        return ESP_ERR_INVALID_STATE;
    }

    g_node_id = node_id;
    g_seq_num = 0;
    g_neighbor_count = 0;
    memset(&g_stats, 0, sizeof(g_stats));
    memset(g_neighbor_table, 0, sizeof(g_neighbor_table));

    g_initialized = true;
    ESP_LOGI(TAG, "Mesh initialized (node ID: 0x%08lX)", (unsigned long)node_id);
    return ESP_OK;
}

esp_err_t mesh_send(uint32_t dest_id, const uint8_t *payload,
                    uint8_t len, uint8_t flags)
{
    if (!g_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    if (payload == NULL && len > 0) {
        return ESP_ERR_INVALID_ARG;
    }
    if (len > MAX_PACKET_PAYLOAD) {
        return ESP_ERR_INVALID_SIZE;
    }

    g_stats.packets_sent++;
    g_seq_num++;

    ESP_LOGI(TAG, "Send to 0x%08lX (seq=%lu, len=%u, flags=0x%02x) — stub, no TX",
             (unsigned long)dest_id, (unsigned long)g_seq_num, len, flags);
    return ESP_OK;
}

esp_err_t mesh_receive(const uint8_t *data, uint8_t len,
                       int16_t rssi, float snr)
{
    if (!g_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    if (data == NULL || len < sizeof(mesh_packet_t) - MAX_PACKET_PAYLOAD) {
        return ESP_ERR_INVALID_ARG;
    }

    /* Validate checksum */
    const mesh_packet_t *pkt = (const mesh_packet_t *)data;
    uint8_t crc = calc_checksum(data, len - 1);
    if (crc != data[len - 1]) {
        ESP_LOGW(TAG, "Checksum mismatch — dropping packet");
        g_stats.packets_dropped++;
        return ESP_ERR_INVALID_CRC;
    }

    g_stats.packets_received++;

    /* Update neighbor table */
    bool found = false;
    for (uint8_t i = 0; i < g_neighbor_count; i++) {
        if (g_neighbor_table[i].node_id == pkt->source_id) {
            g_neighbor_table[i].rssi_last = rssi;
            g_neighbor_table[i].snr_last = snr;
            g_neighbor_table[i].last_seen_ms = pkt->timestamp_ms;
            g_neighbor_table[i].packets_rx++;
            found = true;
            break;
        }
    }
    if (!found && g_neighbor_count < MAX_NEIGHBORS) {
        g_neighbor_table[g_neighbor_count].node_id = pkt->source_id;
        g_neighbor_table[g_neighbor_count].rssi_last = rssi;
        g_neighbor_table[g_neighbor_count].snr_last = snr;
        g_neighbor_table[g_neighbor_count].last_seen_ms = pkt->timestamp_ms;
        g_neighbor_table[g_neighbor_count].packets_rx = 1;
        g_neighbor_count++;
    }

    /* Deliver to application callback */
    if (g_rx_callback != NULL) {
        g_rx_callback(pkt, pkt->source_id, rssi, snr);
    }

    ESP_LOGI(TAG, "RX from 0x%08lX (seq=%lu, RSSI=%d, SNR=%.1f)",
             (unsigned long)pkt->source_id, (unsigned long)pkt->seq_num,
             rssi, (double)snr);
    return ESP_OK;
}

uint32_t mesh_get_node_id(void)
{
    return g_node_id;
}

uint8_t mesh_neighbor_count(void)
{
    return g_neighbor_count;
}

esp_err_t mesh_get_neighbor(uint8_t index, mesh_neighbor_t *entry)
{
    if (entry == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    if (index >= g_neighbor_count) {
        return ESP_ERR_NOT_FOUND;
    }
    *entry = g_neighbor_table[index];
    return ESP_OK;
}

void mesh_get_stats(mesh_stats_t *stats)
{
    if (stats != NULL) {
        g_stats.neighbor_count = g_neighbor_count;
        *stats = g_stats;
    }
}

void mesh_set_rx_callback(mesh_rx_callback_t cb)
{
    g_rx_callback = cb;
}
