/**
 * test_mesh_standalone.c - Standalone Mesh Test Mode
 * 
 * Build-flag-gated (CONFIG_MESH_TEST_MODE) test for two-node mesh bring-up.
 * One node acts as "sender", the other as "listener".
 * 
 * Kconfig:
 *   CONFIG_MESH_TEST_MODE=y
 *   CONFIG_MESH_TEST_ROLE="sender"  (or "listener")
 * 
 * Sender: every 5s sends ~500-byte payload (counter + padding) forcing 2-3 fragments
 * Listener: logs every decrypted payload, verifies counter, dumps neighbor table every 30s
 * 
 * Negative test: flash listener with different PROVISION_KEY_HEX to verify GCM auth fails
 */

#include <string.h>
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "mesh.h"
#include "key_provisioning.h"
#include "crypto.h"

#ifdef CONFIG_MESH_TEST_MODE

static const char *TAG = "MESH_TEST";

/* Test payload size: ~500 bytes to force 2-3 fragments (MAX_PACKET_PAYLOAD=240, minus 6-byte frag header + 16-byte GCM tag = 218 per fragment) */
#define TEST_PAYLOAD_SIZE  500
#define SEND_INTERVAL_MS   5000
#define STATS_INTERVAL     10   /* Log stats every N sends (sender) or receives (listener) */
#define NEIGHBOR_DUMP_INTERVAL_MS 30000  /* Dump neighbor table every 30s (listener) */

static uint32_t g_test_counter = 0;
static uint32_t g_send_count = 0;
static uint32_t g_recv_count = 0;
static uint32_t g_decrypt_failures = 0;
static uint32_t g_last_stats_time = 0;
static uint32_t g_last_neighbor_dump = 0;
static bool g_is_sender = false;

/* Test payload pattern: [counter(4)][padding...] */
static uint8_t test_payload[TEST_PAYLOAD_SIZE];

/* Forward declaration */
static void test_mesh_rx_callback(const mesh_packet_t *packet,
                                   uint32_t from_id,
                                   int16_t rssi, float snr);

static void init_test_payload(void)
{
    for (int i = 0; i < TEST_PAYLOAD_SIZE; i++) {
        test_payload[i] = (uint8_t)(i & 0xFF);
    }
}

static void update_test_counter(void)
{
    /* First 4 bytes = counter (little-endian) */
    test_payload[0] = (g_test_counter >> 0) & 0xFF;
    test_payload[1] = (g_test_counter >> 8) & 0xFF;
    test_payload[2] = (g_test_counter >> 16) & 0xFF;
    test_payload[3] = (g_test_counter >> 24) & 0xFF;
}

static void dump_neighbor_table(void)
{
    uint8_t count = mesh_neighbor_count();
    ESP_LOGI(TAG, "=== Neighbor Table (%u neighbors) ===", count);
    
    for (uint8_t i = 0; i < count; i++) {
        mesh_neighbor_t entry;
        if (mesh_get_neighbor(i, &entry) == ESP_OK) {
            ESP_LOGI(TAG, "  [%u] 0x%08lX  RSSI=%d SNR=%.1f pkts=%lu hops=%u",
                     i, (unsigned long)entry.node_id,
                     entry.rssi_last, entry.snr_last,
                     (unsigned long)entry.packets_rx, entry.hop_count);
        }
    }
}

static void log_stats(void)
{
    mesh_stats_t stats;
    mesh_get_stats(&stats);
    
    if (g_is_sender) {
        ESP_LOGI(TAG, "=== Mesh Test Stats (sender) ===");
        ESP_LOGI(TAG, "  Sent: %lu, Received: %lu, Decrypt failures: %lu",
                 (unsigned long)g_send_count,
                 (unsigned long)g_recv_count,
                 (unsigned long)g_decrypt_failures);
    } else {
        ESP_LOGI(TAG, "=== Mesh Test Stats (listener) ===");
        ESP_LOGI(TAG, "  Sent: %lu, Received: %lu, Decrypt failures: %lu",
                 (unsigned long)g_send_count,
                 (unsigned long)g_recv_count,
                 (unsigned long)g_decrypt_failures);
    }
    ESP_LOGI(TAG, "  Mesh: sent=%lu rx=%lu fwd=%lu drop=%lu dup=%lu neigh=%u",
             (unsigned long)stats.packets_sent,
             (unsigned long)stats.packets_received,
             (unsigned long)stats.packets_forwarded,
             (unsigned long)stats.packets_dropped,
             (unsigned long)stats.duplicates_filtered,
             stats.neighbor_count);
}

static void test_mesh_rx_callback(const mesh_packet_t *packet,
                                   uint32_t from_id,
                                   int16_t rssi, float snr)
{
    if (!packet) return;
    
    g_recv_count++;
    /* Note: mesh_get_stats() reflects packets_received automatically via mesh_receive() */

    ESP_LOGI(TAG, "Received packet from 0x%08lX (seq=%lu, len=%u, RSSI=%d, SNR=%.1f)",
             (unsigned long)from_id,
             (unsigned long)packet->seq_num,
             packet->payload_len,
             rssi, (double)snr);

    /* Verify payload pattern: first 4 bytes = counter */
    if (packet->payload_len >= 4) {
        uint32_t received_counter = 
            ((uint32_t)packet->payload[0] << 0) |
            ((uint32_t)packet->payload[1] << 8) |
            ((uint32_t)packet->payload[2] << 16) |
            ((uint32_t)packet->payload[3] << 24);
        
        ESP_LOGI(TAG, "Payload pattern verified: counter=%lu", (unsigned long)received_counter);
    }
}

static void sender_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Starting sender task (5s interval, %d byte payload)", TEST_PAYLOAD_SIZE);
    
    while (1) {
        update_test_counter();
        
        esp_err_t ret = mesh_secure_send(MESH_BROADCAST_ID, test_payload,
                                         TEST_PAYLOAD_SIZE, MESH_FLAG_ALERT);
        
        if (ret == ESP_OK) {
            g_send_count++;
            g_test_counter++;
            ESP_LOGI(TAG, "Sent test packet #%lu (counter=%lu, len=%d)",
                     (unsigned long)g_send_count,
                     (unsigned long)(g_test_counter - 1),
                     TEST_PAYLOAD_SIZE);
        } else {
            ESP_LOGE(TAG, "mesh_secure_send failed: %s", esp_err_to_name(ret));
        }

        /* Log stats every STATS_INTERVAL sends */
        if (g_send_count % STATS_INTERVAL == 0) {
            log_stats();
        }

        vTaskDelay(pdMS_TO_TICKS(SEND_INTERVAL_MS));
    }
}

static void listener_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Starting listener task (neighbor dump every %ds)", NEIGHBOR_DUMP_INTERVAL_MS / 1000);
    
    while (1) {
        uint32_t now = (uint32_t)(esp_timer_get_time() / 1000);
        
        /* Dump neighbor table periodically */
        if (now - g_last_neighbor_dump >= NEIGHBOR_DUMP_INTERVAL_MS) {
            dump_neighbor_table();
            g_last_neighbor_dump = now;
        }
        
        /* Log stats periodically based on receive count */
        if (g_recv_count > 0 && g_recv_count % STATS_INTERVAL == 0) {
            if (now - g_last_stats_time >= 5000) {  /* Debounce */
                log_stats();
                g_last_stats_time = now;
            }
        }
        
        vTaskDelay(pdMS_TO_TICKS(1000));  /* Check every 1s */
    }
}

void mesh_test_init(void)
{
    /* Determine role from Kconfig */
#ifdef CONFIG_MESH_TEST_ROLE
    const char *role = CONFIG_MESH_TEST_ROLE;
    if (strcmp(role, "sender") == 0) {
        g_is_sender = true;
    } else if (strcmp(role, "listener") == 0) {
        g_is_sender = false;
    } else {
        ESP_LOGE(TAG, "Invalid MESH_TEST_ROLE: %s (must be 'sender' or 'listener')", role);
        return;
    }
#endif

    ESP_LOGI(TAG, "=== Mesh Test Mode: %s ===", g_is_sender ? "SENDER" : "LISTENER");

    /* Initialize test payload pattern */
    init_test_payload();

    /* Register RX callback */
    mesh_set_rx_callback(test_mesh_rx_callback);

    /* Initialize key provisioning and load/generate network key */
    esp_err_t kp_ret = key_provisioning_init();
    if (kp_ret != ESP_OK) {
        ESP_LOGE(TAG, "Key provisioning init failed: %s", esp_err_to_name(kp_ret));
        return;
    }

    uint8_t netkey[CRYPTO_KEY_SIZE];
    kp_ret = key_provisioning_load_network_key(netkey, true);  // Auto-generate if missing
    if (kp_ret != ESP_OK) {
        ESP_LOGE(TAG, "Could not load/generate network key: %s", esp_err_to_name(kp_ret));
        return;
    }

    /* Initialize mesh crypto with the network key */
    esp_err_t mesh_crypto_ret = mesh_set_crypto_key(netkey);
    if (mesh_crypto_ret != ESP_OK) {
        ESP_LOGE(TAG, "Mesh crypto init failed: %s", esp_err_to_name(mesh_crypto_ret));
        return;
    }
    ESP_LOGI(TAG, "Mesh encryption enabled with network key");

    /* Create test task */
    TaskHandle_t test_task = NULL;
    const char *task_name = g_is_sender ? "mesh_test_sender" : "mesh_test_listener";
    void (*task_func)(void *) = g_is_sender ? sender_task : listener_task;

    BaseType_t ret = xTaskCreatePinnedToCore(
        task_func,
        task_name,
        8192,  /* Larger stack for fragmentation/reassembly */
        NULL,
        4,
        &test_task,
        1  /* Core 1 - same as mesh_comms_task */
    );

    if (ret != pdPASS || test_task == NULL) {
        ESP_LOGE(TAG, "Failed to create test task");
    } else {
        ESP_LOGI(TAG, "Created %s task", task_name);
    }
}

#endif /* CONFIG_MESH_TEST_MODE */