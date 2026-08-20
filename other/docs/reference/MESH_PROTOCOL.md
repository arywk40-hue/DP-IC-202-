# Mesh Protocol Specification

## Packet Format

### Wire Format (Serialized)

```
Byte 0:       version (4 bits) | flags (4 bits)
Bytes 1-4:    source_id (uint32_t, big-endian)
Bytes 5-8:    dest_id (uint32_t, big-endian)  — 0xFFFFFFFF = broadcast
Bytes 9-12:   seq_num (uint32_t, big-endian)
Bytes 13-16:  timestamp_ms (uint32_t, big-endian, boot time)
Byte 17:      ttl (uint8_t, 0-255)
Byte 18:      payload_len (uint8_t, 0-240)
Byte 19:      reserved (uint8_t, must be 0)
Bytes 20..N:  payload (payload_len bytes)
Byte N+1:     crc8 (Dallas/Maxim, polynomial 0x31)
```

### C Structure (`mesh_packet_t`)

```c
typedef struct __attribute__((packed)) {
    uint8_t  version_flags;      // version<<4 | flags
    uint32_t source_id;
    uint32_t dest_id;
    uint32_t seq_num;
    uint32_t timestamp_ms;
    uint8_t  ttl;
    uint8_t  payload_len;
    uint8_t  reserved;
    uint8_t  payload[MAX_PACKET_PAYLOAD];
    // CRC8 appended during serialization
} mesh_packet_t;
```

---

## Flags (4 bits)

| Bit | Flag | Value | Description |
|-----|------|-------|-------------|
| 0 | `MESH_FLAG_ACK_REQ` | 0x01 | Request ACK from destination |
| 1 | `MESH_FLAG_ACK` | 0x02 | This packet is an ACK |
| 2 | `MESH_FLAG_ALERT` | 0x04 | Payload contains hazard alert |
| 3 | (reserved) | 0x08 | Future use |

---

## CRC8

- **Polynomial**: 0x31 (x⁸ + x⁵ + x⁴ + 1) — Dallas/Maxim
- **Init**: 0x00
- **Reflect**: No
- **XOR out**: 0x00
- **Computed over**: All bytes except the CRC byte itself

```c
static const uint8_t CRC8_TABLE[256] = { ... };  // See mesh.c

uint8_t crc8(const uint8_t *data, size_t len) {
    uint8_t crc = 0;
    for (size_t i = 0; i < len; i++) {
        crc = CRC8_TABLE[crc ^ data[i]];
    }
    return crc;
}
```

---

## Routing Algorithm

### Flooding with TTL

1. **On TX**: Originator sets `ttl = MESH_DEFAULT_TTL` (5)
2. **On RX**: 
   - If `dest_id == node_id` or `dest_id == BROADCAST`: deliver to app
   - If `ttl > 1`: decrement TTL, re-serialize, forward
   - If `ttl == 1`: drop (do not forward)
3. **Duplicate suppression**: Cache `(src_id, seq_num)` in 64-entry ring buffer

### ACK/Retry (Unicast Only)

1. Sender sets `MESH_FLAG_ACK_REQ`, stores pending ACK
2. Receiver sees `ACK_REQ`, sends ACK packet:
   - `dest_id = original_src`, `seq_num = original_seq`
   - `flags = MESH_FLAG_ACK`, `ttl = 1`, `payload_len = 0`
3. Sender on ACK: clears pending, stops retries
4. No ACK after timeout → retry (max 3):
   - Retry 1: +500ms
   - Retry 2: +1000ms
   - Retry 3: +2000ms
5. Max retries exceeded → drop, log failure

---

## Heartbeat / Neighbor Discovery

- **Interval**: 30 seconds (broadcast)
- **Packet**: `ttl=1`, `payload_len=0`, no flags
- **Neighbor table entry**:
  - `node_id`, `rssi_last`, `snr_last`, `last_seen_ms`, `packets_rx`, `hop_count=1`
- **Timeout**: 90 seconds (3 missed heartbeats) → prune

---

## Alert Payload (Broadcast, `MESH_FLAG_ALERT`)

| Offset | Size | Field |
|--------|------|-------|
| 0 | 1 | `class_id` (0=wildfire, 1=flood, 2=storm, 3=air_quality) |
| 1 | 4 | `confidence` (float, IEEE 754) |
| 5 | 4 | `pm25` (float) |
| 9 | 4 | `temperature` (float) |
| 13 | 4 | `lightning_dist` (float) |
| **Total** | **17** | bytes |

---

## API Summary

| Function | Description |
|----------|-------------|
| `mesh_init(node_id)` | Initialize mesh layer |
| `mesh_set_lora_handle(handle)` | Bind SX1276 radio |
| `mesh_set_rx_callback(cb)` | Register app receive callback |
| `mesh_send(dest, payload, len, flags)` | Transmit packet |
| `mesh_receive(data, len, rssi, snr)` | Process raw radio bytes |
| `mesh_periodic(now_ms)` | Call every ~100ms (retries, pruning) |
| `mesh_send_heartbeat()` | Broadcast presence |
| `mesh_get_stats(&stats)` | Get counters |
| `mesh_get_neighbor(idx, &entry)` | Neighbor table access |

---

## Constants

```c
#define MESH_BROADCAST_ID       0xFFFFFFFF
#define MESH_DEFAULT_TTL        5
#define MAX_PACKET_PAYLOAD      240
#define MAX_NEIGHBORS           8
#define MESH_HEARTBEAT_INTERVAL_MS  30000
#define MESH_NEIGHBOR_TIMEOUT_MS    90000
#define MESH_ACK_TIMEOUT_MS         2000
#define MESH_MAX_RETRIES            3
```

---

## Sequence Diagrams

### Alert Broadcast

```
Node A                          Node B                          Node C
  │                               │                               │
  ├─ mesh_send(BROADCAST, alert)─►│                               │
  │  (seq=42, ttl=5, ALERT)       │                               │
  │                               ├─ mesh_receive()              │
  │                               │  → deliver to app            │
  │                               │  → forward (ttl=4) ─────────►│
  │                               │                               ├─ deliver
  │                               │                               └─ forward (ttl=3)
```

### Unicast with ACK

```
Node A                          Node B
  │                               │
  ├─ mesh_send(B, data, ACK_REQ)─►│
  │  (seq=100, ttl=5)             │
  │                               ├─ mesh_receive()
  │                               │  → deliver to app
  │                               │  → send ACK (seq=100)
  │◄─ ACK (seq=100, ttl=1) ───────┤
  │  (ACK received, done)         │
```

---

## Error Codes

| Code | Meaning |
|------|---------|
| `ESP_OK` | Success |
| `ESP_ERR_INVALID_STATE` | Not initialized |
| `ESP_ERR_INVALID_ARG` | NULL ptr, bad len |
| `ESP_ERR_INVALID_SIZE` | Payload > MAX |
| `ESP_ERR_INVALID_CRC` | CRC mismatch |
| `ESP_FAIL` | Radio TX failed |