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
 * Security:  AES-128-GCM end-to-end payload encryption + CRC8 hop integrity
 *            + sequence numbers for replay protection.
 * Fragmentation: Large payloads split into fragments with mesh_frag_header_t
 *                inside payload, reassembled before decryption.
 */

#ifndef MESH_H
#define MESH_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "common.h"
#include "crypto.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Mesh protocol constants */
#define MESH_BROADCAST_ID       0xFFFFFFFF
#define MESH_DEFAULT_TTL        5
#define MESH_MAX_PACKET_SIZE    (sizeof(mesh_packet_t))
#define MESH_HEARTBEAT_INTERVAL_MS    30000   // 30s heartbeat broadcast
#define MESH_NEIGHBOR_TIMEOUT_MS      90000   // 90s = 3 missed heartbeats

/* Fragmentation constants */
#define MESH_FRAG_HEADER_SIZE       6   // msg_id(2) | frag_index(1) | frag_count(1) | auth_tag_included(1) | reserved(1)
#define MESH_MAX_FRAG_DATA          (MAX_PACKET_PAYLOAD - MESH_FRAG_HEADER_SIZE - 16)  // payload - frag_hdr - GCM tag
#define MESH_MAX_PLAINTEXT_SIZE     (MESH_MAX_FRAG_DATA * 4)  // max 4 fragments = 872 bytes

/**
 * @brief Fragment header — lives inside mesh_packet_t.payload[]
 * 
 * Layout (packed):
 *   [0-1]  msg_id          (uint16_t, random per logical message, same across fragments)
 *   [2]    frag_index      (uint8_t, 0-based)
 *   [3]    frag_count      (uint8_t, total fragments for this msg_id)
 *   [4]    auth_tag_included (uint8_t, 1 only on last fragment, else 0)
 *   [5]    reserved        (uint8_t, for future use)
 */
typedef struct __attribute__((packed)) {
    uint16_t msg_id;
    uint8_t  frag_index;
    uint8_t  frag_count;
    uint8_t  auth_tag_included;
    uint8_t  reserved;
} mesh_frag_header_t;

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
#define MESH_FLAG_PRE_ENCRYPTED (1 << 3)  /* Payload is already encrypted (with GCM tag appended) */

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
 * @brief Send a packet into the mesh network (with fragmentation if needed).
 * If dest_id is MESH_BROADCAST_ID, all reachable nodes receive it.
 * Large payloads are automatically fragmented, encrypted, and transmitted
 * as multiple fragments with mesh_frag_header_t headers.
 * @param dest_id   Destination node ID or MESH_BROADCAST_ID.
 * @param payload   Payload data (plaintext, will be encrypted+fragmented).
 * @param len       Payload length (must be <= MESH_MAX_PLAINTEXT_SIZE).
 * @param flags     Packet flags (MESH_FLAG_*).
 * @return ESP_OK on successful local transmission of all fragments.
 */
esp_err_t mesh_send(uint32_t dest_id, const uint8_t *payload,
                    uint8_t len, uint8_t flags);

/**
 * @brief Process a received packet from the radio layer.
 * Validates CRC, checks duplicates, decrements TTL,
 * forwards if applicable, reassembles fragments, decrypts,
 * and delivers to application callback.
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
 * or is a broadcast. The payload is already decrypted and reassembled.
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
 * @brief Set the network encryption key for the mesh layer.
 * Must be called before any encrypted communication.
 * @param key 16-byte network encryption key.
 * @return ESP_OK on success, ESP_ERR_INVALID_ARG if key is NULL.
 */
esp_err_t mesh_set_crypto_key(const uint8_t key[CRYPTO_KEY_SIZE]);

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
                           uint8_t len, uint8_t flags);

/**
 * @brief Secure receive callback registration.
 * Registers a callback for decrypted, reassembled packets.
 * The callback receives decrypted plaintext payloads.
 * @param cb  Callback function pointer.
 */
void mesh_set_secure_rx_callback(mesh_rx_callback_t cb);

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
