/**
 * main.c - Edge AI Weather Station Main Firmware
 * 
 * ESP32-S3 + 12 sensors + XGBoost + LoRa mesh
 * Reads sensors, runs ML inference, sends alerts
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "nvs_flash.h"

#include "sensor_pipeline.h"
#include "ml_pipeline.h"
#include "mesh_comm.h"

static const char *TAG = "MAIN";

/* ============================================
 * CONFIGURATION
 * ============================================ */

#define NODE_ID                 1           // Unique node ID (0-255)
#define SENSOR_READ_INTERVAL_MS 5000        // 5 seconds
#define HEARTBEAT_INTERVAL_S    300         // 5 minutes
#define ALERT_THRESHOLD         60          // Alert if threat > 60%
#define CRITICAL_THRESHOLD      80          // Critical alert threshold
#define BATTERY_LOW_VOLTAGE     3.3f        // Low battery threshold
#define BATTERY_CRITICAL_VOLTAGE 3.0f       // Critical battery

/* ============================================
 * STATE
 * ============================================ */

static QueueHandle_t sensor_queue;
static QueueHandle_t alert_queue;

typedef struct {
    ml_feature_t features;
    ml_result_t result;
    uint32_t timestamp;
} sensor_event_t;

typedef struct {
    mesh_alert_t alert;
    bool critical;
} alert_event_t;

/* ============================================
 * SENSOR TASK
 * ============================================ */

static void sensor_task(void *pvParameters) {
    ESP_LOGI(TAG, "Sensor task started");
    
    TickType_t last_wake = xTaskGetTickCount();
    
    while (1) {
        // Read all sensors and compute features
        ml_feature_t features = sensor_get_features();
        
        // Run ML inference
        ml_result_t result;
        uint32_t inference_us = ml_inference((float *)&features, &result);
        
        ESP_LOGI(TAG, "Inference: %lu us | Threat: %d%% | Wildfire: %d%% | Flood: %d%% | Storm: %d%% | AQ: %d%%",
                 inference_us, result.overall_threat, result.wildfire_risk,
                 result.flood_risk, result.storm_risk, result.air_quality);
        
        // Create sensor event
        sensor_event_t event = {
            .features = features,
            .result = result,
            .timestamp = (uint32_t)(esp_timer_get_time() / 1000000),
        };
        
        // Send to queues
        xQueueOverwrite(sensor_queue, &event);
        
        if (result.overall_threat > ALERT_THRESHOLD) {
            alert_event_t alert_event = {
                .alert = {
                    .header = {
                        .packet_type = PKT_ALERT,
                        .source_id = NODE_ID,
                        .dest_id = 0xFF,
                        .hop_count = 0,
                        .max_hops = 5,
                        .sequence = 0,
                        .ttl = 60,
                    },
                    .alert_code = result.alert_code,
                    .wildfire_risk = result.wildfire_risk,
                    .flood_risk = result.flood_risk,
                    .storm_risk = result.storm_risk,
                    .air_quality = result.air_quality,
                    .overall_threat = result.overall_threat,
                    .battery_pct = 100,  // Update from ADC
                    .timestamp = event.timestamp,
                },
                .critical = (result.overall_threat > CRITICAL_THRESHOLD),
            };
            xQueueSend(alert_queue, &alert_event, 0);
        }
        
        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(SENSOR_READ_INTERVAL_MS));
    }
}

/* ============================================
 * MESH TASK
 * ============================================ */

static void mesh_task(void *pvParameters) {
    ESP_LOGI(TAG, "Mesh task started");
    
    uint32_t last_heartbeat = 0;
    uint32_t sequence = 0;
    
    while (1) {
        // Check for outgoing alerts
        alert_event_t alert_event;
        if (xQueueReceive(alert_queue, &alert_event, pdMS_TO_TICKS(100))) {
            alert_event.alert.header.sequence = sequence++;
            
            if (mesh_send_alert(&alert_event.alert)) {
                ESP_LOGW(TAG, "ALERT SENT: Threat=%d%% Code=0x%04X %s",
                         alert_event.alert.overall_threat,
                         alert_event.alert.alert_code,
                         alert_event.critical ? "[CRITICAL]" : "");
            }
        }
        
        // Send periodic heartbeat
        uint32_t now = (uint32_t)(esp_timer_get_time() / 1000000);
        if ((now - last_heartbeat) >= HEARTBEAT_INTERVAL_S) {
            sensor_event_t sensor_event;
            if (xQueuePeek(sensor_queue, &sensor_event, 0)) {
                mesh_heartbeat_t hb = {
                    .header = {
                        .packet_type = PKT_HEARTBEAT,
                        .source_id = NODE_ID,
                        .dest_id = 0xFF,
                        .hop_count = 0,
                        .max_hops = 3,
                        .sequence = sequence++,
                        .ttl = 30,
                    },
                    .temperature = sensor_event.features.temp_current,
                    .humidity = sensor_event.features.humidity_current,
                    .pressure = sensor_event.features.pressure_current,
                    .battery_voltage = 3.7f,  // Read from ADC
                    .neighbors = 0,
                };
                mesh_send_heartbeat(&hb);
                last_heartbeat = now;
            }
        }
        
        // Check for incoming packets
        mesh_alert_t incoming;
        uint8_t len = mesh_receive(&incoming, sizeof(incoming), pdMS_TO_TICKS(50));
        
        if (len > 0 && incoming.header.packet_type == PKT_ALERT) {
            // Forward alert if not from this node and hop count < max
            if (incoming.header.source_id != NODE_ID && 
                incoming.header.hop_count < incoming.header.max_hops) {
                incoming.header.hop_count++;
                mesh_send_alert(&incoming);
                ESP_LOGW(TAG, "FORWARDED alert from node %d (hop %d/%d)",
                         incoming.header.source_id,
                         incoming.header.hop_count,
                         incoming.header.max_hops);
            }
        }
    }
}

/* ============================================
 * MONITOR TASK
 * ============================================ */

static void monitor_task(void *pvParameters) {
    ESP_LOGI(TAG, "Monitor task started");
    
    while (1) {
        // Get mesh statistics
        uint32_t tx, rx;
        uint8_t neighbors;
        int8_t rssi;
        mesh_get_stats(&tx, &rx, &neighbors, &rssi);
        
        // Get latest sensor data
        sensor_event_t event;
        if (xQueuePeek(sensor_queue, &event, 0)) {
            ESP_LOGI(TAG, "=== STATUS ===");
            ESP_LOGI(TAG, "Uptime: %lu s", (uint32_t)(esp_timer_get_time() / 1000000));
            ESP_LOGI(TAG, "Temp: %.1f C | Hum: %.1f%% | Pres: %.1f hPa",
                     event.features.temp_current,
                     event.features.humidity_current,
                     event.features.pressure_current);
            ESP_LOGI(TAG, "Battery: %.2f V", 3.7f);
            ESP_LOGI(TAG, "Mesh TX: %lu | RX: %lu | RSSI: %d dBm", tx, rx, rssi);
            ESP_LOGI(TAG, "ML Model: %d trees | Threat: %d%%",
                     ml_get_metadata().num_trees, event.result.overall_threat);
        }
        
        // Check battery
        float battery_v = 3.7f;  // Read from ADC
        if (battery_v < BATTERY_CRITICAL_VOLTAGE) {
            ESP_LOGE(TAG, "CRITICAL BATTERY: %.2fV", battery_v);
        } else if (battery_v < BATTERY_LOW_VOLTAGE) {
            ESP_LOGW(TAG, "LOW BATTERY: %.2fV", battery_v);
        }
        
        vTaskDelay(pdMS_TO_TICKS(30000));  // Print every 30 seconds
    }
}

/* ============================================
 * MAIN
 * ============================================ */

void app_main(void) {
    ESP_LOGI(TAG, "=== Edge AI Weather Station ===");
    ESP_LOGI(TAG, "Node ID: %d", NODE_ID);
    
    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }
    
    // Create queues
    sensor_queue = xQueueCreate(1, sizeof(sensor_event_t));
    alert_queue = xQueueCreate(10, sizeof(alert_event_t));
    
    // Initialize subsystems
    ESP_LOGI(TAG, "Initializing sensor pipeline...");
    if (!sensor_pipeline_init()) {
        ESP_LOGE(TAG, "Sensor pipeline init failed!");
        return;
    }
    
    ESP_LOGI(TAG, "Initializing ML pipeline...");
    if (!ml_pipeline_init()) {
        ESP_LOGE(TAG, "ML pipeline init failed!");
        return;
    }
    
    ESP_LOGI(TAG, "Initializing mesh network...");
    if (!mesh_init(NODE_ID)) {
        ESP_LOGE(TAG, "Mesh init failed!");
        return;
    }
    
    ESP_LOGI(TAG, "All subsystems initialized");
    
    // Create tasks
    xTaskCreatePinnedToCore(sensor_task, "sensor", 4096, NULL, 5, NULL, 0);
    xTaskCreatePinnedToCore(mesh_task, "mesh", 4096, NULL, 4, NULL, 1);
    xTaskCreatePinnedToCore(monitor_task, "monitor", 2048, NULL, 3, NULL, 1);
    
    ESP_LOGI(TAG, "Tasks created, entering normal operation");
    
    // Main loop (idle task)
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
