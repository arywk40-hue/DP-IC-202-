/**
 * mesh.h - LoRa Mesh Networking Layer
 *
 * Lightweight multi-hop mesh network for hazard alert dissemination.
 * Each node maintains a neighbor table, forwards packets with TTL,
 * filters duplicates, and supports broadcast/acknowledged delivery.
 *
 * Integrates with the SX1276 LoRa driver (components/lora/).
 *
 * Topology:  Decentralized peer-to-peer mesh.
 * Routing:   Flooding with TTL + duplicate suppression + optional route cache.
 * Security:  Packet CRC, sequence numbers for replay protection.
 */

#ifndef MESH_H
#define MESH_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "common.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Mesh protocol constants */
#define MESH_BROADCAST_ID       0xFFFFFFFF
#define MESH_DEFAULT_TTL        5
#define MESH_MAX_PACKET_SIZE    (sizeof(mesh_packet_t))
#define MESH_HEARTBEAT_INTERVAL_MS    30000   // 30s heartbeat broadcast
#define MESH_NEIGHBOR_TIMEOUT_MS      90000   // 90s = 3 missed heartbeats

/**
 * @brief Mesh packet header — fixed-size, precedes payload.
 *
 * Layout:
 *   [0]    version      (4 bits) | flags (4 bits)
 *   [1-4]  source_id    (uint32_t, network byte order)
 *   [5-8]  dest_id      (uint32_t, or MESH_BROADCAST_ID)
 *   [9-12] seq_num      (uint32_t)
 *   [13-16] timestamp   (uint32_t, boot ms)
 *   [17]   ttl          (uint8_t)
 *   [18]   payload_len  (uint8_t)
 *   [19]   reserved     (uint8_t)
 *   [20-]  payload      (variable, up to MAX_PACKET_PAYLOAD bytes)
 *   [+N+1] crc8         (uint8_t, XOR of all preceding bytes)
 */
typedef struct __attribute__((packed)) {
    uint8_t  version_flags;
    uint32_t source_id;
    uint32_t dest_id;
    uint32_t seq_num;
    uint32_t timestamp_ms;
    uint8_t  ttl;
    uint8_t  payload_len;
    uint8_t  reserved;
    uint8_t  payload[MAX_PACKET_PAYLOAD];
    /* crc8 appended after payload during serialization */
} mesh_packet_t;

/* Packet flag bits */
#define MESH_FLAG_ACK_REQ       (1 << 0)
#define MESH_FLAG_ACK           (1 << 1)
#define MESH_FLAG_ALERT         (1 << 2)

/* Packet version */
#define MESH_VERSION            0x01

/**
 * @brief Neighbor table entry.
 * Maintained by periodic heartbeat exchange.
 */
typedef struct {
    uint32_t    node_id;
    int16_t     rssi_last;          /* Last received RSSI (dBm) */
    float       snr_last;           /* Last received SNR */
    uint32_t    last_seen_ms;       /* Boot ms of last contact */
    uint32_t    packets_rx;         /* Total packets received from this node */
    uint8_t     hop_count;          /* Estimated hop distance */
} mesh_neighbor_t;

/**
 * @brief Initialize mesh networking layer.
 * Sets up neighbor table, sequence counter, and default parameters.
 * @param node_id  Unique 32-bit identifier for this node.
 * @return ESP_OK on success.
 */
esp_err_t mesh_init(uint32_t node_id);

/**
 * @brief Send a packet into the mesh network.
 * If dest_id is MESH_BROADCAST_ID, all reachable nodes receive it.
 * @param dest_id   Destination node ID or MESH_BROADCAST_ID.
 * @param payload   Payload data.
 * @param len       Payload length (must be <= MAX_PACKET_PAYLOAD).
 * @param flags     Packet flags (MESH_FLAG_*).
 * @return ESP_OK on successful local transmission.
 */
esp_err_t mesh_send(uint32_t dest_id, const uint8_t *payload,
                    uint8_t len, uint8_t flags);

/**
 * @brief Process a received packet from the radio layer.
 * Validates CRC, checks duplicates, decrements TTL,
 * forwards if applicable, and delivers to application callback.
 * @param data      Raw received bytes (including header).
 * @param len       Total received length.
 * @param rssi      RSSI of the received packet.
 * @param snr       SNR of the received packet.
 * @return ESP_OK if the packet was valid.
 */
esp_err_t mesh_receive(const uint8_t *data, uint8_t len,
                       int16_t rssi, float snr);

/**
 * @brief Get the local node ID.
 * @return 32-bit node identifier.
 */
uint32_t mesh_get_node_id(void);

/**
 * @brief Get the number of known neighbors.
 * @return Neighbor count.
 */
uint8_t mesh_neighbor_count(void);

/**
 * @brief Get a neighbor table entry by index.
 * @param index  0-based index (must be < mesh_neighbor_count()).
 * @param entry  Output — copy of the neighbor entry.
 * @return ESP_OK if index is valid.
 */
esp_err_t mesh_get_neighbor(uint8_t index, mesh_neighbor_t *entry);

/**
 * @brief Get mesh statistics.
 */
typedef struct {
    uint32_t packets_sent;
    uint32_t packets_received;
    uint32_t packets_forwarded;
    uint32_t packets_dropped;
    uint32_t duplicates_filtered;
    uint32_t seq_num;
    uint8_t  neighbor_count;
} mesh_stats_t;

void mesh_get_stats(mesh_stats_t *stats);

/**
 * @brief Application callback for received mesh packets.
 * Called by mesh_receive() when a packet is addressed to this node
 * or is a broadcast. Implemented by the application layer.
 */
typedef void (*mesh_rx_callback_t)(const mesh_packet_t *packet,
                                    uint32_t from_id,
                                    int16_t rssi, float snr);

/**
 * @brief Register the application-layer receive callback.
 * @param cb  Callback function pointer.
 */
void mesh_set_rx_callback(mesh_rx_callback_t cb);

/**
 * @brief Set the LoRa radio handle for transmit operations.
 * Must be called before mesh_send() will transmit.
 * @param handle  SX1276 handle from sx1276_init().
 */
void mesh_set_lora_handle(sx1276_handle_t *handle);

/**
 * @brief Periodic maintenance — call from mesh_comms_task loop.
 * Handles neighbor pruning, ACK retries, heartbeat timer.
 * @param now_ms  Current time in milliseconds (esp_timer_get_time()/1000).
 */
void mesh_periodic(uint32_t now_ms);

/**
 * @brief Send periodic heartbeat broadcast.
 * Call every MESH_HEARTBEAT_INTERVAL_MS (~30s) to announce presence.
 */
void mesh_send_heartbeat(void);

/**
 * @brief Get current time in milliseconds since boot.
 * @return Boot time in ms.
 */
uint32_t mesh_get_time_ms(void);

#ifdef __cplusplus
}
#endif

#endif /* MESH_H */
