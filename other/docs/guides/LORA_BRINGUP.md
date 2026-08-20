# LoRa Mesh Bring-Up Test Procedure

**Version:** 1.0  
**Target:** Two-node encrypted mesh baseline bring-up  
**Firmware:** `MESH_TEST_MODE=y` with `CONFIG_MESH_TEST_ROLE="sender"` / `"listener"`

---

## 1. Prerequisites

### Hardware
- 2× ESP32-S3 nodes with RFM95W/SX1276 (865 MHz)
- Antennas: ¼-wave monopole (8.6 cm) or 865 MHz rubber duck
- USB cables + host PC with ESP-IDF v5.x
- Optional: SDR / spectrum analyzer for interference check

### Firmware
```bash
cd firmware
idf.py menuconfig
# Component config → Mesh Test Mode → Enable (y)
# Component config → Mesh Test Role → "sender" (node A) / "listener" (node B)
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor  # Node A
idf.py -p /dev/ttyUSB1 flash monitor  # Node B
```

### Build Flags
```bash
# Required Kconfig options
CONFIG_MESH_TEST_MODE=y
CONFIG_MESH_TEST_ROLE="sender"     # Node A
CONFIG_MESH_TEST_ROLE="listener"   # Node B
```

---

## 2. Test Procedure

### Phase 1: Bench Validation (10 m)

1. **Place nodes 10 m apart** in open indoor space, antennas vertical
2. **Power on both nodes**, open serial monitors (115200 baud)
3. **Verify boot logs:**
   ```
   I (xxx) KEY_PROV: Loaded network key from NVS
   I (xxx) CRYPTO: Key: 1234567890ABCDEF1234567890ABCDEF
   I (xxx) MESH: Mesh encryption enabled with network key
   I (xxx) MESH: Mesh initialized (node ID: 0x12345678)
   I (xxx) MESH_TEST: Sender task created    (or Listener mode)
   ```
3. **Confirm key match** — both nodes must show identical 32-hex-char key
4. **Observe test traffic** (every 5s):
   - Sender: `Sent test packet #N (500 bytes, counter=X)`
   - Listener: `Received packet from 0x... (len=..., counter=X)` + `Payload pattern verified`
5. **Run for 5 minutes**, record stats every 30s:
   ```
   === Mesh Test Stats ===
     Sent: 60, Received: 60, Decrypt failures: 0
     Mesh: sent=60 rx=60 fwd=0 drop=0 dup=0 neigh=1
     Neighbor table:
       [0] 0xABCDEF12 RSSI=-42 SNR=9.5 pkts=60
   ```

### Phase 2: Fragmentation Verification

1. **Confirm fragmentation** — 500-byte payload > `MESH_MAX_FRAG_DATA` (218 bytes)
   - Expect 3 fragments per packet (6+218+218+16 = 458 → fits 240? No, 218+16=234 per frag data)
   - Verify listener logs: `Received fragment 0/3`, `Received fragment 1/3`, `Received fragment 2/3`
   - Listener logs `Payload pattern verified` after reassembly

### Phase 3: Negative Key Test

1. **Flash listener with different key:**
   ```bash
   # In menuconfig: Component config → Key Provisioning → Provision Key Hex
   # Set different 32-hex-char key (e.g., "DEADBEEFDEADBEEFDEADBEEFDEADBEEF")
   idf.py -p /dev/ttyUSB1 flash monitor
   ```
2. **Observe listener logs:**
   ```
   W (xxx) MESH: Decryption failed for packet from 0x12345678 seq=42
   ```
3. **Confirm no garbage data** — no "Payload pattern verified" logs
4. **Re-flash listener with correct key** to restore

### Phase 4: Range Testing

| Distance | Setup | Duration | Key Metrics |
|----------|-------|----------|-------------|
| 10 m | Indoor, LOS | 10 min | Packet loss, RSSI, SNR, fragment loss |
| 100 m | Outdoor, LOS | 15 min | Packet loss, RSSI, SNR, fragment loss |
| 1 km | Outdoor, LOS | 20 min | Packet loss, RSSI, SNR, fragment loss |
| 5 km | Outdoor, LOS (hilltop) | 30 min | Packet loss, RSSI, SNR, fragment loss |
| 10 km | Outdoor, LOS (hilltop) | 45 min | Packet loss, RSSI, SNR, fragment loss |

#### At each distance:
1. Position nodes, ensure GPS coordinates recorded
2. Run 10 min test
3. Capture stats dump (every 30s) + neighbor table
4. Note: weather, antenna height, obstacles, interference sources

### Phase 5: Stress / Soak Test

- Run sender + listener for **4 hours** at 100 m
- Verify: no memory leaks, no task crashes, stable packet rate
- Check mesh stats: `duplicates_filtered` < 1%, `packets_dropped` = 0

---

## 3. Results Recording Template

### Test Metadata
| Field | Value |
|-------|-------|
| Date / Time | |
| Testers | |
| Node A MAC / ID | |
| Node B MAC / ID | |
| Firmware Git SHA | |
| Weather | |
| Antenna Type / Height | |
| Interference Notes | |

### Per-Distance Results

#### 10 m (Indoor LOS)
| Metric | Value |
|--------|-------|
| Packets Sent | |
| Packets Received | |
| Packet Loss % | |
| Avg RSSI (dBm) | |
| Avg SNR (dB) | |
| Fragments/Packet | |
| Fragment Loss % | |
| Decrypt Failures | |
| Duplicates Filtered | |
| Avg Latency (ms) | |

#### 100 m (Outdoor LOS)
| Metric | Value |
|--------|-------|
| Packets Sent | |
| Packets Received | |
| Packet Loss % | |
| Avg RSSI (dBm) | |
| Avg SNR (dB) | |
| Fragments/Packet | |
| Fragment Loss % | |
| Decrypt Failures | |
| Duplicates Filtered | |
| Avg Latency (ms) | |

#### 1 km (Outdoor LOS)
| Metric | Value |
|--------|-------|
| Packets Sent | |
| Packets Received | |
| Packet Loss % | |
| Avg RSSI (dBm) | |
| Avg SNR (dB) | |
| Fragments/Packet | |
| Fragment Loss % | |
| Decrypt Failures | |
| Duplicates Filtered | |
| Avg Latency (ms) | |

#### 5 km (Outdoor LOS)
| Metric | Value |
|--------|-------|
| Packets Sent | |
| Packets Received | |
| Packet Loss % | |
| Avg RSSI (dBm) | |
| Avg SNR (dB) | |
| Fragments/Packet | |
| Fragment Loss % | |
| Decrypt Failures | |
| Duplicates Filtered | |
| Avg Latency (ms) | |

#### 10 km (Outdoor LOS)
| Metric | Value |
|--------|-------|
| Packets Sent | |
| Packets Received | |
| Packet Loss % | |
| Avg RSSI (dBm) | |
| Avg SNR (dB) | |
| Fragments/Packet | |
| Fragment Loss % | |
| Decrypt Failures | |
| Duplicates Filtered | |
| Avg Latency (ms) | |

### Soak Test (4 hrs @ 100 m)
| Metric | Value |
|--------|-------|
| Total Packets Sent | |
| Total Packets Received | |
| Packet Loss % | |
| Decrypt Failures | |
| Memory Leaks | None / Details |
| Task Crashes | None / Details |
| Watchdog Resets | 0 / Count |

---

## 4. Pass/Fail Criteria

| Test | Pass Condition |
|------|----------------|
| Bench validation (10 m) | Packet loss < 1%, decrypt failures = 0, fragmentation works |
| Negative key test | Listener logs GCM auth failures, no garbage delivered |
| 100 m outdoor | Packet loss < 5%, RSSI > -110 dBm, SNR > 5 dB |
| 1 km outdoor | Packet loss < 10%, RSSI > -115 dBm, SNR > 3 dB |
| Fragmentation | All 3 fragments reassembled, payload pattern verified |
| Soak test (4h) | Zero crashes, zero memory leaks, packet loss < 1% |

---

## 5. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| No packets received | Antenna disconnected / wrong frequency | Check antenna, verify 865 MHz in `sx1276_config_t` |
| High packet loss at short range | CSMA/CA backoff too aggressive | Reduce `MESH_CAD_RETRIES` or increase `base_backoff_ms` |
| Decrypt failures with correct key | Nonce mismatch (seq_num desync) | Verify both nodes use same `seq_num` for nonce |
| Fragment loss at range | Last fragment lost (carries auth tag) | Increase TX power, reduce SF (SF7→SF6) |
| Neighbor table empty | Heartbeats not received | Check `MESH_HEARTBEAT_INTERVAL_MS`, verify TTL > 1 |
| High duplicate count | Duplicate cache too small | Increase `MESH_DUPLICATE_CACHE_SIZE` |

---

## 6. Key Log Patterns

### Successful Round-Trip
```
I (123456) MESH_TEST: Sent test packet #42 (500 bytes, counter=42)
I (123458) MESH_TEST: Received packet from 0x12345678 (seq=100, len=234, RSSI=-45, SNR=9.2)
I (123458) MESH_TEST: Payload pattern verified for counter=42
```

### Fragmentation
```
I (123458) MESH: Received fragment 0/3 (msg=0x1234, frag=0/3, tag=1)
I (123460) MESH: Received fragment 1/3 (msg=0x1234, frag=1/3, tag=0)
I (123462) MESH: Received fragment 2/3 (msg=0x1234, frag=2/3, tag=1)
I (123462) MESH: Reassembled 500-byte message, decrypting...
I (123464) MESH_TEST: Payload pattern verified
```

### Decrypt Failure (Wrong Key)
```
W (123470) MESH: Decryption failed for packet from 0x12345678 seq=105
```

### Neighbor Discovery
```
I (150000) MESH_TEST: Neighbor table:
I (150000) MESH_TEST:   [0] 0x12345678 RSSI=-42 SNR=9.5 pkts=150
```

---

## 7. Appendix: Key Commands Quick Reference

```bash
# Build with test mode
idf.py menuconfig  # Set MESH_TEST_MODE=y, MESH_TEST_ROLE="sender"
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor

# Monitor only
idf.py -p /dev/ttyUSB0 monitor

# Erase flash (for clean key re-provisioning)
idf.py -p /dev/ttyUSB0 erase_flash

# Size report
idf.py size
idf.py size-components
```

---

## 8. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-14 | System Architect | Initial release |

---

*End of LORA_BRINGUP.md*