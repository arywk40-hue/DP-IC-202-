/**
 * mesh_comm.h - LoRa mesh communication layer
 * 
 * Multi-hop mesh networking for ESP32-S3 + SX1276
 * Event-driven alert transmission
 */

#ifndef MESH_COMM_H
#define MESH_COMM_H

#include <stdint.h>
#include <stdbool.h>

/* ============================================
 * MESH PACKET STRUCTURES
 * ============================================ */

// Packet types
#define PKT_ALERT          0x01
#define PKT_HEARTBEAT      0x02
#define PKT_SENSOR_DATA    0x03
#define PKT_MODEL_UPDATE   0x04
#define PKT_MODEL_EXPORT   0x05
#define PKT_ACK            0x06
#define PKT_FLOOD          0x07

// Maximum payload size (SX1276)
#define MAX_PAYLOAD_SIZE   50

// Mesh packet header
typedef struct {
    uint8_t packet_type;     // PKT_* constant
    uint8_t source_id;       // Node ID (0-255)
    uint8_t dest_id;         // Destination (0xFF = broadcast)
    uint8_t hop_count;       // Current hop count
    uint8_t max_hops;        // Maximum allowed hops
    uint32_t sequence;       // Packet sequence number
    uint8_t ttl;             // Time to live (seconds)
} mesh_header_t;

// Alert packet
typedef struct {
    mesh_header_t header;
    uint8_t alert_code;      // Bitfield of active alerts
    uint8_t wildfire_risk;   // 0-100%
    uint8_t flood_risk;      // 0-100%
    uint8_t storm_risk;      // 0-100%
    uint8_t air_quality;     // 0-100%
    uint8_t overall_threat;  // 0-100%
    float latitude;          // Optional GPS
    float longitude;
    uint32_t timestamp;      // Epoch seconds
    uint8_t battery_pct;     // Battery level
    uint8_t checksum;        // XOR checksum
} mesh_alert_t;

// Heartbeat packet
typedef struct {
    mesh_header_t header;
    float temperature;
    float humidity;
    float pressure;
    float battery_voltage;
    uint8_t neighbors;       // Number of known neighbors
    uint8_t checksum;
} mesh_heartbeat_t;

// Sensor data packet (compressed)
typedef struct {
    mesh_header_t header;
    int16_t temp_x10;        // Temperature * 10
    uint16_t humidity_x10;   // Humidity * 10
    uint16_t pressure_x10;   // (Pressure - 900) * 10
    uint16_t wind_speed_x10; // Wind speed * 10
    uint16_t pm25;
    uint16_t co2_x10;        // CO2 * 10
    uint8_t lightning_dist;
    uint8_t checksum;
} mesh_sensor_t;

/* ============================================
 * MESH NETWORK API
 * ============================================ */

/**
 * Initialize mesh communication
 * @param node_id - unique node identifier (0-255)
 * @return true if initialized successfully
 */
bool mesh_init(uint8_t node_id);

/**
 * Send alert to mesh network
 * @param alert - alert data to transmit
 * @return true if packet sent successfully
 */
bool mesh_send_alert(const mesh_alert_t *alert);

/**
 * Send heartbeat (periodic status)
 * @param heartbeat - heartbeat data
 * @return true if sent
 */
bool mesh_send_heartbeat(const mesh_heartbeat_t *heartbeat);

/**
 * Send compressed sensor data
 * @param sensor - sensor data packet
 * @return true if sent
 */
bool mesh_send_sensor_data(const mesh_sensor_t *sensor);

/**
 * Broadcast model update to all nodes
 * @param model_data - model weights/parameters
 * @param size - data size in bytes
 * @return true if sent
 */
bool mesh_broadcast_model(const uint8_t *model_data, uint16_t size);

/**
 * Receive packet from mesh
 * @param buffer - output buffer
 * @param max_size - buffer size
 * @param timeout_ms - receive timeout
 * @return packet type, or 0 if timeout
 */
uint8_t mesh_receive(void *buffer, uint16_t max_size, uint32_t timeout_ms);

/**
 * Get mesh statistics
 */
void mesh_get_stats(uint32_t *packets_sent, uint32_t *packets_received, 
                    uint8_t *neighbor_count, int8_t *signal_strength);

/**
 * Set transmit power
 * @param power - 2-20 dBm
 */
void mesh_set_power(uint8_t power);

/**
 * Set frequency
 * @param freq_hz - frequency in Hz (e.g., 865000000 for India)
 */
void mesh_set_frequency(uint32_t freq_hz);

#endif // MESH_COMM_H
