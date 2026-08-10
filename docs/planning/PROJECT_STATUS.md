# Project Status and Gap Review

## What The Repo Already Does Well

- The concept is consistent across the README, sensor guide, proposal, and implementation paper.
- The target system architecture is clear: ESP32-S3, 12 sensors, local inference, and LoRa mesh.
- The low-cost BOM story is strong and well documented.
- The hardware work has started: the repo now contains an ESP-IDF tree with LoRa and sensor driver components.

## Completed Prompts

| Prompt | Description | Status |
|--------|-------------|--------|
| **1** | Firmware app entrypoint & task orchestration (main.c) | ✅ Complete |
| **2** | Sensor driver completion (11 sensor drivers: I2C, UART, ADC, 1-Wire) | ✅ Complete |
| **3** | ML pipeline (training, export, XGBoost inference) | ✅ Complete |
| **4** | Mesh networking layer (heartbeat, neighbor discovery, TTL forwarding, ACK handling, duplicate suppression, CSMA/CA + CAD) | ✅ Complete |
| **5** | Mesh secure send/receive API (AES-128-GCM encryption, fragmentation/reassembly, CSMA/CA, ACK/retry) | ✅ Complete |
| **6** | NVS session key + IV persistence (key provisioning, auto-generation, bootstrap detection) | ✅ Complete |
| **7** | Full LoRa parameter set + mode switch helpers (SX1276 extended API, mode switching) | ✅ Complete |
| **8** | Unit tests for crypto/mesh/fragmentation (crypto round-trip, mesh serialize/deserialize, fragmentation) | ✅ Complete |
| **9** | Benchmarks/flash/RAM report (size_report.py, benchmarks.sh) | ✅ Complete |
| **10** | Firmware build script + CI gate (build.sh, GitHub Actions CI) | ✅ Complete |
| **11** | Security design doc + API reference (SECURITY_ARCHITECTURE.md) | ✅ Complete |

---

## Code Bugs Found and Fixed (Repository Audit — August 2026)

The following bugs were discovered during a full source audit against both project PDFs.
All were fixed in the same session.

| # | File | Bug | Fix Applied |
|---|------|-----|-------------|
| B1 | `code/ml/prepare_dataset.py` line 96 | Extra closing `)` on `.fillna(0))` — SyntaxError, file cannot be imported or run | Removed the stray `)` |
| B2 | `firmware/components/mesh/src/mesh.c` | `mesh_set_lora_handle()` defined twice — linker error (duplicate symbol) | Removed the second definition |
| B3 | `firmware/components/mesh/src/mesh.c` | `mesh_get_time_ms()` defined twice — linker error (duplicate symbol) | Removed the second definition |
| B4 | `firmware/components/mesh/src/mesh.c` | `reassembly_entry_t` typedef declared **inside** the anonymous `g_mesh` struct body — invalid C99, GCC rejects it | Moved typedef to file scope before the `g_mesh` struct |
| B5 | `firmware/main/test_mesh_standalone.c` | Missing opening `#ifdef CONFIG_MESH_TEST_MODE` — the matching `#endif` was at the bottom but the guard was never opened, causing a stray-`#endif` compile error | Added `#ifdef CONFIG_MESH_TEST_MODE` after the `#include` block |
| B6 | `firmware/main/test_mesh_standalone.c` | Called `mesh_acquire_mutex()` and wrote directly to `g_mesh.stats.packets_received++` — both are `static` private to `mesh.c`; linker error | Replaced with comment; `mesh_get_stats()` (public API) maintains the counter |
| B7 | `firmware/main/test_mesh_standalone.c` | Entry point named `mesh_test_mode_init()` but `main.c` calls `mesh_test_init()` — linker error | Renamed to `mesh_test_init()` |
| B8 | `benchmarks.sh` | Two heredocs use `<< 'EOF'` (single-quoted), so `$(date)` and `$(idf.py --version)` are written as literal strings instead of being expanded | Changed to `<< EOF` so expressions expand at runtime |

### Structural Issues Fixed

| # | Issue | Fix Applied |
|---|-------|-------------|
| S1 | `code/acceptance_test.py` misplaced in the ML source tree — it is a hardware test runner | Moved to `scripts/acceptance_test.py` |
| S2 | No root `.gitignore` — `.DS_Store` files committed throughout | Created root `.gitignore`; deleted all existing `.DS_Store` files |
| S3 | README paths pointed to `docs/PROJECT_STATUS.md` / `docs/FOUR_MONTH_BUILD_PLAN.md` (wrong location) | Fixed to `docs/planning/` paths |
| S4 | `scripts/` directory and `PDF_GAP_ANALYSIS.md` absent from README tree | Added both |

## Remaining: Baseline Bring-Up Test

| Item | Description | Status |
|------|-------------|--------|
| **Bring-Up Test** | Two-node encrypted mesh bring-up with fragmentation round-trip, negative key test, range testing at 10m/100m/10km | 🔄 In Progress |

This is the final item before baseline acceptance per [ACCEPTANCE_TESTS.md](./ACCEPTANCE_TESTS.md).

---

## Completed Architecture

```
firmware/
├── main/
│   ├── main.c                    # App entry, sensor_ml_task (Core 0) + mesh_comms_task (Core 1)
│   ├── test_mesh_standalone.c    # MESH_TEST_MODE: sender/listener standalone test
├── components/
│   ├── common/                   # sensor_reading_t, feature_vector_t, error codes
│   ├── crypto/                   # AES-128-GCM (crypto.c), NVS key provisioning (key_provisioning.c)
│   ├── sensors/                  # 11 drivers: BME280, PMS5003, DS18B20, Anemometer, SEN0575, LTR390, SCD41, SGP41, MICS6814, AS3935, Battery
│   ├── lora/                     # SX1276 driver + CSMA/CA + full param API + mode switching
│   ├── mesh/                     # TTL flooding, CRC8, dup suppression, neighbor table, heartbeat, ACK/retry, fragmentation, AES-GCM integration
│   ├── ml/                       # XGBoost inference (model_data.h, normalization.h, iterative tree traversal)
│   └── ml/include/               # Auto-generated: model_data.h, normalization.h, model_metadata.h
```

---

## Verified Capabilities

| Capability | Verified |
|------------|----------|
| AES-128-GCM encryption/decryption with nonce from (source_id \|\| seq_num) | ✅ Unit tested |
| Packet fragmentation (≤240B payload, 6-byte frag header, 16B GCM tag) | ✅ Unit tested |
| CSMA/CA with CAD + exponential backoff + jitter | ✅ Implemented |
| Mesh TTL-based flooding with duplicate suppression (64-entry cache) | ✅ Implemented |
| Neighbor table with 90s timeout + heartbeat (30s interval) | ✅ Implemented |
| ACK/retry for unicast (3 retries, exponential backoff) | ✅ Implemented |
| NVS key provisioning (auto-gen on first boot, manual override via PROVISION_KEY_HEX) | ✅ Implemented |
| Key rotation API (incrementing key_id, grace period) | ✅ Implemented |
| Secure send/recv API (mesh_secure_send / mesh_set_secure_rx_callback) | ✅ Implemented |
| XGBoost inference (14 features, 4 classes, 16 trees/class, depth ≤4) | ✅ Implemented |
| 11 sensor drivers (I2C×5, UART×1, ADC×4, 1-Wire×1) | ✅ Implemented |
| Unit tests (crypto + mesh) | ✅ 27 tests |
| CI pipeline (build, lint, model verify, test, size report) | ✅ Configured |

---

## Next Steps

1. **Flash two nodes** with `CONFIG_MESH_TEST_MODE=y`, one as `sender`, one as `listener`
2. **Run bring-up test** per `docs/guides/LORA_BRINGUP.md`
2. **Record results** at 10m, 100m, and max range
3. **Complete ACCEPTANCE_TESTS.md** checklist
4. **Tag release** v1.0-baseline

---

## Best Supporting Docs

- [4-Month Build Plan](./FOUR_MONTH_BUILD_PLAN.md)
- [Sensor Reference](./SENSORS.md)
- [Quick Start](./QUICK_START.md)
- [Security Architecture](./SECURITY_ARCHITECTURE.md)
- [LORA Bring-Up Guide](../guides/LORA_BRINGUP.md)

# DP-IC-202- — Next 20 Prompts (12–31)

Continues the numbering in `docs/planning/PROJECT_STATUS.md`, which has 1–11 marked
✅ Complete. These take the project from "firmware complete, zero acceptance tests run"
to a signed-off 2-node baseline per `ACCEPTANCE_TESTS.md`, closing the two real gaps I
found reading the actual source (OTA partitions missing `ota_0`/`ota_1`; `crypto.c` has
its own comment admitting a placeholder key derivation), and covering the Month 2–4
deliverables in `FOUR_MONTH_BUILD_PLAN.md` that aren't represented in the repo yet.

Paste each into Claude Code (with write access to the repo) one at a time, in order —
several depend on the previous one's output (e.g. 16 needs 15's self-test log format).

---

### 12 — Two-node LoRa bring-up test harness
```
Using firmware/main/test_mesh_standalone.c and docs/guides/LORA_BRINGUP.md as the
starting point, build the actual sender/listener bring-up procedure into a documented,
repeatable test run. Add a serial log parser (Python, pyserial) that monitors both
nodes' UART output during a bring-up run, extracts heartbeat TX/RX events, RSSI/SNR,
sequence numbers, and duplicate-filter counts, and auto-fills the N1–N6 (single node)
and N7–N12 (two-node pair) rows of docs/planning/ACCEPTANCE_TESTS.md's Test Execution
Template — including the fragmentation round-trip and negative-key test called out as
the "Remaining: Baseline Bring-Up Test" item in PROJECT_STATUS.md. Output should be a
single markdown report per run, timestamped, saved under a new field-logs/ directory.
```

### 13 — Fix the OTA partition table and wire up real OTA
```
firmware/partitions.csv currently defines nvs, otadata, phy_init, and a single 3MB
factory app partition — there is no ota_0/ota_1 slot, so an OTA update cannot actually
happen despite ACCEPTANCE_TESTS.md test I4 expecting `idf.py ota` to boot new firmware
and preserve NVS. Redesign the partition table with two ota_0/ota_1 app slots sized to
fit the current firmware image (check actual size via scripts/size_report.py first),
implement the esp_ota_ops-based update flow in firmware/main (a minimal serial or
esp_https_ota path is fine for prototype stage), and verify NVS + calibration data
survive the swap. Update docs/guides/FLASH_GUIDE.md with the new OTA procedure.
```

### 14 — Replace the placeholder key derivation in crypto.c
```
firmware/components/crypto/src/crypto.c contains a comment at line 98 reading "This is
a placeholder - production should use proper HKDF." Replace it with a real HKDF-SHA256
implementation (mbedtls has one built into ESP-IDF — use mbedtls_hkdf), re-derive
session keys through it, re-run the existing crypto unit tests in
firmware/components/crypto/test/test_crypto.c and add new test vectors specifically for
the HKDF derivation path (known-answer test against RFC 5869 test vectors). Update
docs/reference/SECURITY_ARCHITECTURE.md's key-derivation section to describe the real
scheme instead of the placeholder.
```

### 15 — Automated hardware bring-up self-test mode (H1–H10)
```
Add a CONFIG_HW_SELFTEST_MODE Kconfig option (alongside the existing
CONFIG_MESH_TEST_MODE) that makes app_main() run an automated hardware bring-up
sequence instead of the normal task loop: I2C bus scan expecting exactly 5 devices at
0x76 (BME280), 0x53 (LTR390), 0x62 (SCD41), 0x59 (SGP41), 0x03 (AS3935); SX1276 SPI
register read confirming version 0x12; PMS5003 UART frame + checksum check; ADC divider
read against a known 1.65V reference; DS18B20 1-Wire presence pulse and ROM read. Print
a single structured PASS/FAIL block per test matching the H1–H10 rows in
ACCEPTANCE_TESTS.md exactly, so a flash+monitor run is one step away from filling in the
Sign-off Matrix's Hardware Bring-up row.
```

### 16 — Sensor calibration wizard (S1–S17)
```
Write a Python serial-connected CLI tool (code/tools/calibration_wizard.py) that walks
an operator through sensors S1–S17 in ACCEPTANCE_TESTS.md one at a time: prints the
procedure text, prompts for the reference-instrument reading, reads the node's live
value over serial, computes the delta, and checks it against that row's pass criteria.
At the end it emits a filled Test Execution Template block per sensor plus a single
calibration log file in the format defined by
firmware/components/common/include/calibration_log.h, so the log the wizard produces
is directly consumable by the firmware's calibration_log.c persistence path, not just a
human-readable report.
```

### 17 — Real-world dataset collection pipeline
```
Month 2 of docs/planning/FOUR_MONTH_BUILD_PLAN.md calls for "a first real dataset from
repeated indoor and outdoor tests" — right now code/ml/prepare_dataset.py only has
dataset/weatherHistory.csv (a historical proxy dataset) to work from. Add a field-
logging mode to main.c (behind a Kconfig flag) that timestamps and writes every
sensor_reading_t plus the derived 14-feature vector to a CSV over serial or to an SD/
flash log, in a schema prepare_dataset.py can already ingest. Document the indoor/
outdoor test protocol (duration, cadence, environmental conditions to vary) in a new
docs/guides/DATA_COLLECTION.md, matching the "CSV or JSON dataset schema" and
"calibration log format" deliverables from Month 2.
```

### 18 — Retrain the model on real collected data
```
Once code/tools/calibration_wizard.py (prompt 16) and the field-logging mode (prompt
17) have produced real sensor data, rerun code/ml/train_model.py against that dataset
instead of dataset/weatherHistory.csv, regenerate firmware/components/ml/include/
model_data.h, normalization.h, and model_metadata.h, and diff the new metrics
(accuracy/AUC per hazard class, inference time, RAM/flash usage) against the current
model. Update docs/reference/ML_INFERENCE.md with the real numbers, and re-run
ACCEPTANCE_TESTS.md tests M1–M8 against the retrained model to confirm nothing
regressed (especially M7 flash usage — retrained trees may not stay under 64KB).
```

### 19 — Power and battery validation harness (P1–P8)
```
P1, P2, and P8 in ACCEPTANCE_TESTS.md need multi-hour/multi-day current measurement
that can't be eyeballed. Build a bench logging setup: either an INA219/INA226 current
sensor on a second ESP32 logging the node's supply current over I2C to a CSV, or (if no
current sensor is available yet) a documented multimeter-logging protocol with a
sampling script that timestamps manual readings. Automate the math for P8's 7-day
autonomy projection from measured active-current (P1) and deep-sleep-current (P2)
numbers, duty-cycled at the real 60s poll interval, and produce the "Power consumption
report" deliverable called for in Month 4 of FOUR_MONTH_BUILD_PLAN.md.
```

### 20 — Simulated 3-node TTL forwarding test (N11)
```
N11 in ACCEPTANCE_TESTS.md requires three physical nodes in a line to verify TTL
forwarding (5→3→1), but the project currently targets 2 physical nodes. Add a
MESH_TEST_MODE variant (or a third virtual role in test_mesh_standalone.c) where one
ESP32 runs two independent mesh_packet_t contexts with different node_ids and
deliberately-throttled RSSI to emulate a middle hop, letting TTL decrement and
forwarding be verified with only 2 physical boards. Document clearly in
docs/planning/ACCEPTANCE_TESTS.md that N11's real 3-node hardware test is deferred to
the field-trial phase, with this simulated version as the interim sign-off evidence.
```

### 21 — EMI interference test procedure (E6)
```
E6 in ACCEPTANCE_TESTS.md ("433 MHz transmitter 1m away → no LoRa packet corruption")
needs a precise, repeatable procedure, not just a pass/fail line. Write the exact test
setup (transmitter type, distance, duration, node placement), and add a firmware debug
counter exposed via mesh_get_stats() (or a new field) that tracks CRC failures and
dropped-for-CRC packets specifically during a marked test window, so the pass criteria
becomes a concrete before/during/after packet-loss-rate comparison rather than a
subjective "sounds fine" judgment call.
```

### 22 — Environmental chamber test templates (E1–E5)
```
E1–E5 (temperature range, humidity/condensing, rain ingress, vibration, UV exposure)
each need standardized data sheets since they depend on lab equipment access. Produce
one markdown template per test under docs/planning/env-tests/, pre-filled with the
procedure and pass criteria from ACCEPTANCE_TESTS.md and blank fields matching its Test
Execution Template format, plus a short equipment/access note (e.g., "requires
environmental chamber — check IIT Mandi [dept] lab booking") so these can be scheduled
independently of the firmware-side work above.
```

### 23 — Auto-generate the Sign-off Matrix from raw test logs
```
Once prompts 12, 15, 16, 19, 21, and 22 are all producing individual Test Execution
Template blocks (as markdown files, one per test run), write a script
(code/tools/build_signoff.py) that scans all of them, matches each to its test ID
(H1–H10, S1–S22, M1–M8, N1–N12, P1–P8, E1–E6, I1–I6), and regenerates the Sign-off
Matrix table and category checkboxes at the bottom of ACCEPTANCE_TESTS.md automatically
— so the matrix can never silently drift out of sync with the actual underlying logs.
```

### 24 — PCB wiring diagram and pin assignment deliverable
```
Month 1 of FOUR_MONTH_BUILD_PLAN.md calls for a "Final BOM and wiring diagram" and
"Pin assignment sheet" — docs/reference/PIN_MAP.md exists but there's no visual wiring
diagram in the repo yet. Turn PIN_MAP.md into an actual schematic: either a KiCad
project (firmware/hardware/ or a new hardware/ dir at repo root) if you want a real PCB
path, or at minimum a clean wiring diagram image generated in the same "Attention Is All
You Need"-style flat vector diagram convention already used for system_architecture.png
and firmware_architecture.png, showing every sensor's exact GPIO/I2C-address/bus
connection to the ESP32-S3 for both nodes.
```

### 25 — Hardware bring-up and power-path assembly checklist
```
Write the physical assembly and power-on checklist that H2 (Power-On) and H3 (Solar
Charge) assume already exists: correct order to connect 18650 cell → CN3065 → solar
panel → ESP32-S3 3.3V rail, what to check with a multimeter before first power-on
(polarity, no shorts across rails), and what to do if the 3.3V rail doesn't land within
±0.1V. This is the "Hardware bring-up checklist" deliverable named in Month 1 of
FOUR_MONTH_BUILD_PLAN.md that doesn't have a standalone doc yet — save it as
docs/guides/HARDWARE_BRINGUP.md.
```

### 26 — Extend CI to cover the new host-side tooling
```
.github/workflows/ci.yml currently builds firmware, lints, verifies the model, runs the
crypto/mesh unit tests, and generates the size report. Extend it with a host-side-only
job (no hardware needed) that dry-runs code/tools/calibration_wizard.py and
code/tools/build_signoff.py against fixture/sample data, and lints/type-checks
code/ml/prepare_dataset.py, so regressions in the new Python tooling from prompts
16/18/23 get caught the same way firmware regressions already do.
```

### 27 — Add a Validation Results section to the IEEE paper
```
Once bring-up (prompt 12), self-test (15), and power validation (19) produce real
numbers, add a new section to implementation/edge-ai-weather-mesh-main.tex — after the
existing architecture sections — presenting actual measured results: LoRa range test
distance(s), active/deep-sleep current draw, inference time and RAM/flash usage from
ml_last_inference_us()/ml_model_ram_usage()/ml_model_flash_usage(), and the overall
Sign-off Matrix outcome. Keep all figures pinned to your own measured data — don't
backfill placeholder numbers — and note explicitly which ACCEPTANCE_TESTS.md categories
are still pending if the paper is submitted before full sign-off.
```

### 28 — Field trial log format and ground-truth hazard logging
```
Month 4's "field trial log" deliverable needs a way to check the 4 hazard classes
against real events, not just synthetic triggers. Design a lightweight logging format
(markdown or CSV) for recording actual local weather/hazard events — genuine rain,
high wind, smoke/haze days, lightning — timestamped alongside the node's own alert
history (pulled from mesh_get_stats() / NVS alert log), so wildfire/flood/storm/
air-quality predictions can eventually be scored against ground truth instead of only
against the M1–M8 synthetic-vector tests.
```

### 29 — Threat model follow-up to SECURITY_ARCHITECTURE.md
```
SECURITY_ARCHITECTURE.md (prompt 11) covers the AES-128-GCM design; add a short
follow-up threat-model doc addressing three things the current doc doesn't: (1) key
exfiltration risk if a field-deployed node is physically captured/tampered with, (2)
sequence-number wraparound behavior for replay protection over long unattended uptimes,
and (3) a node-revocation procedure — if a node's key is known-compromised, how the
rest of the mesh excludes it (key rotation grace period already exists per
key_provisioning.c; document how revocation actually triggers it in the field).
```

### 30 — Demo script for live presentation
```
Write the run-of-show for presenting the 2-node system live (Prayas 4.0 review, IAF
Compendium demo, or similar): what to show and in what order (boot → sensor readings →
triggered hazard alert → mesh hop → peer log), a fallback plan if a live LoRa range
test isn't feasible indoors (pre-recorded range-test clip or the field-log data from
prompt 12), and a tight script for handling the "what happens if a sensor fails
mid-demo" question using the graceful-degradation behavior already covered by test S21.
```

### 31 — v1.0-baseline release prep
```
Once the above land and ACCEPTANCE_TESTS.md's Sign-off Matrix is fully checked, do
release prep: reconcile docs/index.md's "Current Status" table (currently stale —
still shows only prompts 1–4 complete) against the authoritative 1–31 list in
PROJECT_STATUS.md, generate a CHANGELOG.md from commit history, draft GitHub release
notes, and do a final README-vs-actual-tree sync pass so new contributors don't land on
a repo map that's already out of date. Tag the release v1.0-baseline.
```