# Edge AI Weather Mesh - Security Architecture Document

**Version:** 1.0  
**Date:** July 2026  
**Classification:** Internal - Technical Reference

---

## 1. Executive Summary

This document describes the end-to-end security architecture for the Edge AI Environmental Hazard Detection Network. The system implements defense-in-depth security across the physical, link, network, and application layers to protect sensor data integrity, ensure authentic alert propagation, and resist both passive eavesdropping and active injection attacks.

**Threat Model:**
- **Passive:** Eavesdropping on LoRa traffic to infer environmental conditions
- **Active Injection:** Forged hazard alerts to trigger false alarms or suppress real ones
- **Replay:** Re-transmission of captured alert packets to cause confusion
- **Device Compromise:** Physical access to nodes to extract keys or modify firmware
- **Side-Channel:** Timing/power analysis on cryptographic operations

**Security Goals:**
1. **Confidentiality:** Sensor readings and alert payloads encrypted end-to-end
2. **Integrity:** Tamper-evident packets with cryptographic authentication
3. **Authenticity:** Only nodes with valid network keys can originate alerts
4. **Forward Secrecy:** Compromised long-term keys don't decrypt historical traffic
5. **Availability:** Resistant to jamming, collision, and resource exhaustion

---

## 2. Cryptographic Architecture

### 2.1 Primitive Selection

| Primitive | Algorithm | Rationale |
|-----------|-----------|-----------|
| Symmetric Encryption | AES-128-GCM | Hardware-accelerated on ESP32-S3, authenticated encryption |
| Key Derivation | HKDF-SHA256 | Standardized, FIPS-approved |
| Random Generation | ESP32 TRNG | Hardware true random number generator |
| Hash | SHA-256 | HKDF prerequisite, firmware verification |

### 2.2 Key Hierarchy

```
┌─────────────────────────────────────┐
│     Master Provisioning Key (MPK)   │  ← 128-bit, provisioned at manufacturing
│            (in NVS, encrypted)      │
└─────────────────┬───────────────────┘
                  │ HKDF-SHA256
                  ▼
┌─────────────────────────────────────┐
│     Network Session Key (NSK)       │  ← 128-bit, per deployment
│  (NSK = HKDF(MPK, "mesh-session"))  │
└─────────────────┬───────────────────┘
                  │ HKDF-SHA256
                  ▼
┌─────────────────────────────────────┐
│     Per-Message Traffic Keys        │  ← 128-bit, per packet (nonce-bound)
│  (Derived from NSK + source+seq)    │
└─────────────────────────────────────┘
```

### 2.3 Nonce Construction

**Format (12 bytes / 96 bits):**
```
┌──────────────┬──────────────┬──────────────┐
│  Source ID   │  Sequence #  │   Reserved   │
│   (4 bytes)  │   (4 bytes)  │   (4 bytes)  │
└──────────────┴──────────────┴──────────────┘
   big-endian     big-endian      zeros
```

**Properties:**
- Unique per (source_id, seq_num) pair
- Never repeats within device lifetime (32-bit seq space)
- Predictable for receiver (no nonce transmission overhead)
- Resistant to nonce-reuse under key compromise

---

## 3. Mesh Protocol Security

### 3.1 Packet Structure (On-Air)

```
┌─────────────────────────────────────────────────────────────────┐
│                     MESH PACKET HEADER (20 bytes)               │
├─────────┬──────────┬──────────┬──────────┬──────────┬──────┬────┤
│Ver/Flags│ SourceID │  DestID  │  SeqNum  │ Timestamp│ TTL │ Rsrv │
│  (1)    │  (4)     │   (4)    │   (4)    │   (4)    │ (1) │ (1) │
├─────────┴──────────┴──────────┴──────────┴──────────┴──────┴────┤
│              PAYLOAD (encrypted + tag, max 240 bytes)           │
├─────────────────────────────────────────────────────────────────┤
│                          CRC-8 (1 byte)                         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Encryption Flow (mesh_secure_send)

```
Plaintext Payload (≤ 224 bytes)
         │
         ▼
┌──────────────────────────────────────────┐
│ AES-128-GCM Encrypt                       │
│   Key: Session Key (NSK)                  │
│   Nonce: source_id || seq_num || 0x000000 │
│   AAD: source_id || seq_num || flags      │
└──────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│ Ciphertext (same length) + 16-byte Tag   │
└──────────────────────────────────────────┘
         │
         ▼
   Mesh Packet Payload (ciphertext || tag)
         │
         ▼
   CRC-8 over full packet (header + payload)
         │
         ▼
   SX1276 Transmit (with CSMA/CA)
```

### 3.3 Decryption Flow (mesh_receive)

```
Received Bytes
      │
      ▼
CRC-8 Verify  ──FAIL──▶ Drop + stats
      │
     PASS
      │
      ▼
┌──────────────────────────────────────────┐
│ Parse Mesh Header                         │
│ Extract: source_id, seq_num, payload_len │
└──────────────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────────────┐
│ AES-128-GCM Decrypt                       │
│   Key: Session Key (NSK)                  │
│   Nonce: source_id || seq_num || 0x000000 │
│   AAD: source_id || seq_num || flags      │
│   Ciphertext: payload[0:len-16]           │
│   Tag: payload[len-16:len]                │
└──────────────────────────────────────────┘
      │
      ▼
  FAIL ──▶ Drop + log auth failure
      │
     PASS
      │
      ▼
Plaintext Payload → Application Callback
```

### 3.4 Replay Protection

- **Duplicate Cache:** 64-entry ring buffer of (source_id, seq_num) pairs
- **Window:** Accept packets with seq_num > (last_seen - 32)
- **Action:** Silently drop duplicates, increment counter

---

## 4. Key Provisioning & Lifecycle

### 4.1 Manufacturing Provisioning

```
┌─────────────────────────────────────────┐
│  Manufacturing Station                  │
├─────────────────────────────────────────┤
│  1. Generate MPK = TRNG(16 bytes)      │
│  2. Write MPK to NVS namespace "mesh_sec"│
│     key="netkey", encrypted by efuse    │
│  3. Write key_id = 1 to NVS            │
│  4. Log: "Device provisioned, key_id=1" │
└─────────────────────────────────────────┘
```

### 4.2 Field Deployment (Two-Node Pair)

```
Node A                          Node B
  │                                │
  ├── mesh_set_crypto_key(key) ───►│  (same 16-byte key)
  │                                │
  ├── mesh_init()                 │──► mesh_init()
  │                                │
  └── mesh_secure_send() ─────────►│──► mesh_receive() → decrypt → callback
```

### 4.3 Key Rotation

```
rotate_key():
    1. new_key = TRNG(16)
    2. key_id = nvs_get("keyid") + 1
    3. nvs_set_blob("netkey", new_key)
    4. nvs_set_u32("keyid", key_id)
    5. nvs_commit()
    6. crypto_init(new_key)
    7. Broadcast rekey announcement (encrypted with old key)
```

**Transition:** New packets use new key; receiver accepts both keys for 24-hour grace period.

---

## 5. Key Provisioning API

### 5.1 Header: `key_provisioning.h`

```c
#ifndef KEY_PROVISIONING_H
#define KEY_PROVISIONING_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "crypto.h"

#ifdef __cplusplus
extern "C" {
#endif

#define KEY_PROV_NS           "mesh_sec"
#define KEY_PROV_NETKEY_KEY   "netkey"
#define KEY_PROV_KEYID_KEY    "keyid"
#define KEY_PROV_INIT_KEY     "initialized"

/**
 * @brief Initialize the key provisioning system.
 * Opens NVS namespace and prepares for key operations.
 * @return ESP_OK on success
 */
esp_err_t key_provisioning_init(void);

/**
 * @brief Provision a network key into NVS.
 * If key is NULL, generates a random key.
 * @param key 16-byte network key, or NULL to auto-generate
 * @return ESP_OK on success, ESP_ERR_INVALID_ARG if key is wrong size
 */
esp_err_t key_provisioning_set_network_key(const uint8_t *key);

/**
 * @brief Load the network key from NVS.
 * If no key exists and auto_generate is true, generates and stores a new key.
 * @param out_key Output buffer for 16-byte network key
 * @param auto_generate Generate key if not found
 * @return ESP_OK on success, ESP_ERR_NOT_FOUND if no key and auto_generate=false
 */
esp_err_t key_provisioning_load_network_key(uint8_t out_key[CRYPTO_KEY_SIZE], bool auto_generate);

/**
 * @brief Get the key ID (version) of the stored network key.
 * @param out_keyid Output key ID
 * @return ESP_OK on success, ESP_ERR_NOT_FOUND if no key
 */
esp_err_t key_provisioning_get_keyid(uint32_t *out_keyid);

/**
 * @brief Rotate the network key.
 * Generates new key, increments key ID, stores atomically.
 * @return ESP_OK on success
 */
esp_err_t key_provisioning_rotate_key(void);

/**
 * @brief Erase all provisioned keys from NVS.
 * Use with caution - requires re-provisioning.
 * @return ESP_OK on success
 */
esp_err_t key_provisioning_erase_all(void);

/**
 * @brief Check if a network key is provisioned.
 * @return true if key exists in NVS
 */
bool key_provisioning_is_provisioned(void);

/**
 * @brief Print the stored network key in hex (debug only).
 * Requires CONFIG_KEY_PROV_DEBUG_PRINT=y
 */
void key_provisioning_print_key(void);

#ifdef __cplusplus
}
#endif

#endif /* KEY_PROVISIONING_H */
```

### 5.2 Usage Example

```c
// In app_main(), before mesh_init()
void provision_network_key(void) {
    // Load existing or generate new
    uint8_t netkey[CRYPTO_KEY_SIZE];
    esp_err_t err = key_provisioning_load_network_key(netkey, true);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Key provisioning failed: %s", esp_err_to_name(err));
        return;
    }
    
    // Initialize mesh crypto
    err = mesh_set_crypto_key(netkey);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Mesh crypto init failed: %s", esp_err_to_name(err));
    }
    
    // For production: provision identical key on all nodes
    // key_provisioning_set_network_key(production_key);
}
```

---

## 6. Crypto API Reference

### 6.1 Header: `crypto.h`

```c
#ifndef CRYPTO_H
#define CRYPTO_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define CRYPTO_KEY_SIZE      16
#define CRYPTO_NONCE_SIZE    12
#define CRYPTO_TAG_SIZE      16

typedef struct {
    uint8_t key[CRYPTO_KEY_SIZE];
    bool initialized;
} crypto_context_t;

/**
 * @brief Initialize crypto context with network key.
 * @param ctx Context to initialize
 * @param key 16-byte network encryption key
 * @return ESP_OK on success
 */
esp_err_t crypto_init(crypto_context_t *ctx, const uint8_t key[CRYPTO_KEY_SIZE]);

/**
 * @brief Derive per-session key from master key.
 * @param ctx Initialized crypto context
 * @param local_id Local node ID
 * @param peer_id Peer node ID (0 for broadcast)
 * @param session_key Output 16-byte session key
 * @return ESP_OK on success
 */
esp_err_t crypto_derive_session_key(const crypto_context_t *ctx,
                                     uint32_t local_id,
                                     uint32_t peer_id,
                                     uint8_t session_key[CRYPTO_KEY_SIZE]);

/**
 * @brief Encrypt data using AES-128-GCM.
 * @param ctx Initialized crypto context
 * @param source_id Source node ID (for nonce)
 * @param seq_num Sequence number (for nonce)
 * @param plaintext Input plaintext
 * @param plaintext_len Length of plaintext
 * @param ciphertext Output buffer (must be >= plaintext_len)
 * @param tag_out Output 16-byte authentication tag
 * @return ESP_OK on success
 */
esp_err_t crypto_encrypt(const crypto_context_t *ctx,
                          uint32_t source_id,
                          uint32_t seq_num,
                          const uint8_t *plaintext,
                          uint8_t plaintext_len,
                          uint8_t *ciphertext,
                          uint8_t tag_out[CRYPTO_TAG_SIZE]);

/**
 * @brief Decrypt data using AES-128-GCM.
 * On failure, output buffer is zeroed.
 * @param ctx Initialized crypto context
 * @param source_id Source node ID (for nonce)
 * @param seq_num Sequence number (for nonce)
 * @param ciphertext Input ciphertext
 * @param ciphertext_len Length of ciphertext
 * @param tag_in 16-byte authentication tag
 * @param plaintext Output plaintext buffer
 * @return ESP_OK on success, ESP_ERR_INVALID_CRC on auth failure
 */
esp_err_t crypto_decrypt(const crypto_context_t *ctx,
                          uint32_t source_id,
                          uint32_t seq_num,
                          const uint8_t *ciphertext,
                          uint8_t ciphertext_len,
                          const uint8_t tag_in[CRYPTO_TAG_SIZE],
                          uint8_t *plaintext);

/**
 * @brief Build nonce from source_id and seq_num.
 * @param source_id Source node ID
 * @param seq_num Sequence number
 * @param nonce Output 12-byte nonce
 */
void crypto_build_nonce(uint32_t source_id, uint32_t seq_num, uint8_t nonce[CRYPTO_NONCE_SIZE]);

/**
 * @brief Generate random network key.
 * @param key Output 16-byte key
 * @return ESP_OK on success
 */
esp_err_t crypto_generate_random_key(uint8_t key[CRYPTO_KEY_SIZE]);

/**
 * @brief Print key in hex (debug).
 */
void crypto_print_key_hex(const uint8_t key[CRYPTO_KEY_SIZE]);

#ifdef __cplusplus
}
#endif

#endif /* CRYPTO_H */
```

### 6.2 Mesh Security API: `mesh.h`

```c
/**
 * @brief Set the network encryption key for the mesh layer.
 * Must be called before mesh_send() with encryption.
 * @param key 16-byte network key
 * @return ESP_OK on success
 */
esp_err_t mesh_set_crypto_key(const uint8_t key[CRYPTO_KEY_SIZE]);

/**
 * @brief Secure send with encryption, fragmentation, CSMA/CA, and ACK/retry.
 * High-level API that handles encryption, fragmentation, CSMA/CA, and ACK/retry.
 * @param dest_id Destination node ID or MESH_BROADCAST_ID
 * @param payload Plaintext payload data
 * @param len Payload length (max MESH_MAX_PLAINTEXT_SIZE)
 * @param flags Packet flags (MESH_FLAG_*)
 * @return ESP_OK on successful transmission of all fragments
 */
esp_err_t mesh_secure_send(uint32_t dest_id, const uint8_t *payload,
                           uint8_t len, uint8_t flags);

/**
 * @brief Register secure receive callback.
 * Callback receives decrypted, reassembled plaintext.
 * @param cb Callback function
 */
void mesh_set_secure_rx_callback(mesh_rx_callback_t cb);

/**
 * @brief Periodic maintenance - call from comms task loop.
 * Handles neighbor pruning, ACK retries, heartbeat timer.
 * @param now_ms Current time in milliseconds
 */
void mesh_periodic(uint32_t now_ms);

/**
 * @brief Send periodic heartbeat broadcast.
 */
void mesh_send_heartbeat(void);

/**
 * @brief Get current time in milliseconds since boot.
 * @return Boot time in ms
 */
uint32_t mesh_get_time_ms(void);
```

---

## 7. Mesh Fragmentation Protocol (Extension)

### 7.1 Fragment Header (inside payload)

```
┌────────────────────────────────────────────┐
│           mesh_frag_header_t (6 bytes)     │
├──────────┬────────────┬───────────┬────────┤
│ msg_id   │ frag_index │ frag_count │ flags │
│ (16-bit) │  (8-bit)   │  (8-bit)   │(8-bit)│
└──────────┴────────────┴────────────┴────────┘
```

### 7.2 Reassembly State Machine

```
RECEIVE FRAGMENT
       │
       ▼
┌──────────────────┐
│ Check (src, msg) │──NEW──▶ Create reassembly slot
│ in reassembly    │       (timer = 30s)
│ table            │
└────────┬─────────┘
         │ EXISTING
         ▼
┌──────────────────┐
│ Store fragment   │──▶ Update bitmap
│ at frag_index    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ All frags recv?  │──NO──▶ Wait
└────────┬─────────┘
         │ YES
         ▼
┌──────────────────┐
│ Reassemble       │──▶ Verify auth tag
│ ciphertext||tag  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Decrypt          │──FAIL──▶ Drop + log
└────────┬─────────┘
         │ PASS
         ▼
  Deliver plaintext to callback
```

---

## 8. CSMA/CA Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Max Retries | 3 | CSMA/CA backoff attempts |
| Base Backoff | 10 ms | Initial backoff window |
| Max Backoff | 80 ms | Cap after exponential increase |
| Jitter | ±25% | Randomized to avoid sync collisions |
| CAD Duration | 1 symbol | Channel Activity Detection |
| CAD Threshold | Default | SX1276 default sensitivity |

---

## 9. Security Testing Checklist

| Test Case | Expected Result |
|-----------|-----------------|
| Encrypt → Decrypt round-trip | Plaintext matches exactly |
| Tampered ciphertext (1 bit flip) | Decrypt returns ESP_ERR_INVALID_CRC |
| Tampered auth tag | Decrypt returns ESP_ERR_INVALID_CRC |
| Wrong source_id in decrypt | ESP_ERR_INVALID_CRC |
| Wrong seq_num in decrypt | ESP_ERR_INVALID_CRC |
| Replay same packet twice | Second dropped as duplicate |
| Max payload (224 bytes) | Encrypt/decrypt succeeds |
| Empty payload (0 bytes) | Encrypt/decrypt succeeds |
| Key rotation mid-session | New key used for subsequent packets |
| NVS key survives reboot | Key persists across power cycle |

---

## 10. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-14 | System Architect | Initial release |

---

*End of Security Architecture Document*