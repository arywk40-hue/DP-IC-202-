# INDRA — Pan-India Meteorological Forecasting, Catchment Mesh & Edge Intelligence Platform

[![CI/CD Pipeline](https://github.com/arywk40-hue/DP-IC-202-/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/arywk40-hue/DP-IC-202-/actions/workflows/ci.yml)
[![Tests Passing](https://img.shields.io/badge/tests-402%20passed-success)](https://github.com/arywk40-hue/DP-IC-202-/actions)
[![C++ Parity](https://img.shields.io/badge/C%2B%2B%20Parity-%3C%200.00013-blue)](esp32/ml_integration/)
[![Dynamic Heap](https://img.shields.io/badge/Dynamic%20Heap-0%20Bytes-brightgreen)](esp32/ml_integration/)
[![Patent Claims](https://img.shields.io/badge/Patent%20Claims-25%20Statutory-orange)](patent/CLAIMS.md)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**INDRA** (*Integrated Network for Decentralized Real-Time Atmospheric hazard intelligence*) is an edge-native, end-to-end meteorological forecasting, spatial intelligence, and distributed catchment monitoring platform engineered for India's extreme terrain and varied agro-climatic zones.

The platform bridges high-performance machine learning ensembles, embedded C++17 runtimes executing on **ESP32-S3** microcontrollers with zero dynamic heap allocations, resilient **catchment multi-node mesh networking** (1 Master Gateway + 2 Peripheral Slaves in the physical pilot, architecturally scalable to an arbitrary $N$ nodes), and a progressive Web Dashboard featuring direct **Web Serial USB streaming** at 115200 baud.

```
                         ┌────────────────────────────────────────────────────────┐
                         │              Central Sovereign Cloud / SDMA            │
                         │          (FastAPI Gateway + React 18 / Vite 5)         │
                         └───────────────────────────▲────────────────────────────┘
                                                     │ (HTTPS / Cellular LTE / Web-Serial)
                         ┌───────────────────────────┴────────────────────────────┐
                         │                 MASTER NODE (Node 0)                   │
                         │             "Catchment Base Station Gateway"           │
                         │                                                        │
                         │ • ESP-NOW Receiver & Dynamic N-Peer Registry           │
                         │ • TabularV2 +6h Edge Forecaster (66 feats, zero heap)  │
                         │ • M-of-N Byzantine Consensus Engine (indra_consensus)  │
                         │ • Catchment Spatial Lapse Rate Calculator (∇T, ∇P, ∇W) │
                         │ • Local UART USB / Cellular Uplink Streamer            │
                         └──────────────────────▲──────────────▲──────────────────┘
                                                │              │
                   ESP-NOW 82-byte Frame (Peer ID 1)          ESP-NOW 82-byte Frame (Peer ID 2)
                                                │              │
 ┌──────────────────────────────────────────────┴──────┐     ┌─┴────────────────────────────────────────────┐
 │                SLAVE NODE 1 (Node 1)                │     │             SLAVE NODE 2 (Node 2)            │
 │            "Upstream Mountain Ridge"                │     │          "Downvalley Riverbed Basin"         │
 │ • Elev: 1,280 m (Steep Orographic Slope)            │     │ • Elev: 710 m (Drainage Channel Floor)       │
 │ • BME280: T, RH, High-Altitude P (873 hPa)          │     │ • BME280: T, RH, Valley Floor P (935 hPa)    │
 │ • PMS5003: PM2.5 / PM10 Dust Influx                 │     │ • PMS5003: Valley Smog & Particulate Basin   │
 │ • Pulse Anemometer: Ridge Wind Speed (6.8 m/s)      │     │ • Pulse Anemometer: Floor Wind Speed         │
 │ • INA219: Solar / Battery Monitor (3.98 V)          │     │ • INA219: Solar / Battery Monitor (4.05 V)   │
 │ • HMAC-SHA256 82-Byte Zero-Heap Frame Packer        │     │ • HMAC-SHA256 82-Byte Zero-Heap Frame Packer │
 └─────────────────────────────────────────────────────┘     └──────────────────────────────────────────────┘
                         ▲                                                         ▲
                         │                                                         │
                         └────────────── Dynamic Extension to N Nodes ─────────────┘
                                        (Node 3 ... Node N-1)
```

> [!IMPORTANT]
> **Data & Evidence Scope:** Continuous background data is retrieved from Open-Meteo's numerical weather prediction (ECMWF IFS) and air-quality (CAMS Global) model grids, with optional direct streaming from physical ESP32 sensors via USB Web Serial. With one active coordinate, the system renders discrete point observations and does not fabricate multi-site heatmaps without at least 3 synchronized non-collinear nodes. Cloudburst, flash-flood, and landslide percentages represent synthetic Monte Carlo simulation fractions under specified hydrological and rainfall assumptions—they are **not calibrated real-event probabilities, public warnings, or observed disaster forecasts**.

---

## Key Capabilities & Architecture

### 1. Six-Channel +6h Numerical Forecasting (`india_mandi_tabular_v2`)
* Predicts **Ambient Temperature (°C)**, **Relative Humidity (%)**, **Surface Atmospheric Pressure (hPa)**, **$PM_{2.5}$ (µg/m³)**, **$PM_{10}$ (µg/m³)**, and **Wind Speed (m/s)**.
* Blends **LightGBM decision trees**, a **residual MLP neural network (`mlp_v2`)**, a **legacy history XGBoost/ridge hybrid**, and physical persistence into a convex simplex ensemble.
* Derives **66 causal meteorological features** from a 25-consecutive-hour sliding window (24 hours of history + current reading).
* Achieves **50.2% to 82.8% MAE skill improvement over persistence** on out-of-sample test archives.

### 2. Pan-India Agro-Climatic Intelligence (587 Stations across 6 Zones)
* Routes predictions and hazard diagnostics across all 28 Indian States and 8 Union Territories covering 6 agro-climatic zones:
  1. **Western Himalayas (Mandi, Leh, Shimla):** Orographic rainfall, cloudbursts, snowstorms.
  2. **Arid Northwest (Jaipur, Jodhpur):** Convective dust storms (*Andhi*), extreme dry gales, *Loo* heatwaves.
  3. **Indo-Gangetic Plains (Delhi-NCR, Lucknow):** Winter temperature inversions, toxic particulate smog trapping.
  4. **Western Ghats & Coastal (Mumbai, Kochi):** Torrential Southwest Monsoon deluges, storm surges.
  5. **Central Deccan Plateau (Bengaluru, Hyderabad):** Pre-monsoon squall lines, diurnal swings.
  6. **Northeast Hills (Guwahati, Cherrapunji):** Extreme rainfall records, riverine flooding, landslides.
* Evaluates kinetic wind power density ($P_{\text{wind}} = \frac{1}{2}\rho v^3$), moist air density ($\rho$), and vapor pressure deficit (VPD).

### 3. Distributed Catchment Multi-Node Mesh (1 Master + 2 Slaves → $N$ Nodes)
* **Physical Pilot ($N=3$):** 1 Master Gateway Node (`indra-master-01`, Mandi Base 760m) + 2 Peripheral Slave Nodes (Slave 1 Uphill Ridge 1,280m; Slave 2 Riverbed Basin 710m).
* **Zero-Code Scaling to $N$ Nodes:** Adding Slave $3, 4, \dots N-1$ requires no code modifications; nodes are assigned unique IDs via the flashing CLI (`--node-id <id>`), and the Master's ESP-NOW listener dynamically indexes peers.
* **82-Byte Zero-Allocation Wire Protocol (`indra_peer_protocol.h`):** Compact binary frame authenticated with symmetric HMAC-SHA256 and CRC16 checksum. Airtime $< 1.2\text{ ms}$ over 2.4 GHz ESP-NOW.
* **Byzantine Fault Tolerance ($M$-of-$N$ Quorum):** Evaluates $M = \lfloor \frac{2}{3} N \rfloor + 1$ with $\ge 2$ independent failure domains. Suppresses single-node sensor false alarms while instantly confirming true catchment hazards.
* **Spatial Lapse Rate Engine:** Calculates vertical temperature lapse rate ($\Gamma = -\frac{\Delta T}{\Delta Z}$), barometric gradient ($\Delta P$), and wind shear across elevation steps in real time.

### 4. ESP32-S3 Embedded Edge ML Runtime
* Standalone C++17 runtime (`esp32/ml_integration/src/mandi_v2_main.cpp`) executing the full Mandi v2 ensemble, 10 synthetic weather patterns, and the Jaipur windstorm model directly on the microcontroller.
* Resource usage: **2.96 MB / 3.34 MB Flash (88.7%)**, **19.9 KB Static RAM (6.1%)**, and **0 Bytes Dynamic Heap**.
* Ultra-fast edge execution latency: **$1,420\ \mu\text{s}$ ($1.42\text{ ms}$)**.
* High numerical parity with 64-bit Python reference: maximum absolute difference **$< 0.0001203$** on forecasts and **$< 3.3 \times 10^{-8}$** on pattern scores.
* 115200 baud serial interface supporting `INFO`, `SELFTEST`, `RESET`, and raw telemetry streaming.

### 5. Web Dashboard & Browser Web Serial Hardware Link
* Built with **React 18 + Vite 5** as a responsive Progressive Web App (PWA).
* **Direct USB Web Serial API (`navigator.serial`):** Operators on Chrome/Edge can connect physical ESP32 boards via USB and stream real-time sensor packets at 115200 baud.
* Interactive **Catchment Mesh Topology View:** Visualizes live node statuses, battery mV, link RSSI, vertical lapse rates, and Byzantine consensus voting in real time.
* Interactive **Pan-India Station Explorer:** Allows searching across 587 IMD/NOAA stations with DEM elevation, slope, and climate zone data.

### 6. Automated Hardware Flashing & Ingestion Tooling
* **1-Command Provisioning Tool (`esp32/tools/flash_esp32.py`):** Auto-scans USB ports, compiles target profiles (`--role master`, `--role slave`, `--node-id <N>`), uploads firmware, and performs an automated post-flash verification handshake.
* **Continuous Ingestion Daemon (`server/scripts/run_mandi_daemon.py`):** Resilient hourly collection loop with exponential backoff and Linux `systemd` service integration.

### 7. Cryptographic Provenance & EVM Blockchain Anchor
* Transactional audit logging (`indra_audit_json_v1`) capturing hash-linked event chains.
* Domain-separated SHA-256 Merkle root generator (`indra_batch_v1`).
* Smart contract ([`contracts/IndraAnchor.sol`](contracts/IndraAnchor.sol)) for immutable batch anchoring on EVM-compatible blockchains.

---

## Executive Verification Metrics Summary

| Verification Category | Benchmark / Standard | Achieved Metric | Status |
| :--- | :--- | :---: | :---: |
| **+6h Forecast Accuracy** | Validation MAE on 35,520 observations | **T: 1.14°C, P: 0.68 hPa, PM2.5: 5.42 µg/m³** | **PASS** |
| **Skill Over Persistence** | Out-of-sample 5-day test archive | **+50.2% to +82.8% Skill Improvement** | **PASS** |
| **C++ Parity: Mandi v2** | Max absolute difference vs 64-bit Python | **$\epsilon < 0.0001203$** | **PASS** |
| **C++ Parity: Patterns** | Max absolute difference vs 64-bit Python | **$\epsilon < 3.297 \times 10^{-8}$** | **PASS** |
| **C++ Parity: Jaipur** | Windstorm & Andhi classification match | **100% Exact Parity** | **PASS** |
| **ESP32 Flash Footprint** | Application Partition (3.34 MB ceiling) | **2.96 MB (88.7% capacity)** | **PASS** |
| **ESP32 Static RAM** | Internal SRAM (320 KB ceiling) | **19.9 KB (6.1% usage)** | **PASS** |
| **Dynamic Heap Allocation** | Memory leak prevention | **0 Bytes (Strict Fixed Stack)** | **PERFECT ZERO** |
| **Edge Inference Latency** | Dual-Core Xtensa LX7 @ 240 MHz | **$1,420\ \mu\text{s}$ ($1.42\text{ ms}$)** | **PASS** |
| **Wire Protocol Frame** | ESP-NOW / LoRa fixed binary frame | **82 Bytes, HMAC-SHA256 Signed** | **PASS** |
| **Byzantine Consensus** | Quorum rule: $M = \lfloor \frac{2}{3} N \rfloor + 1$ | **1 of 3 suppressed; 3 of 3 corroborated** | **PASS** |
| **Pan-India Coverage** | 6 agro-climatic zones across India | **587 IMD/NOAA stations mapped** | **PASS** |
| **Unit & Parity Tests** | Pytest test suite across all modules | **402 / 402 tests passing (100%)** | **PASS** |
| **UI E2E Browser Tests** | Playwright Desktop & Mobile Chromium | **3 / 3 suites passing** | **PASS** |
| **CI/CD Pipeline** | GitHub Actions Ubuntu 24.04 runners | **100% Green (`model`, `dashboard`, `esp32-model`)**| **PASS** |
| **Patent Application** | Formal statutory manifest integrity | **25 claims, 8 drawings, 100% SHA-256 match** | **PASS** |

*For the complete metric-by-metric breakdown, see the [Final Submission Metrics Report](docs/reports/FINAL_SUBMISSION_METRICS_REPORT.md).*

---

## Quickstart & Operational Runbook

### Prerequisites
* **Python:** 3.11 – 3.13 (`.venv` virtual environment)
* **Node.js:** 20+ (Node 22 LTS recommended)
* **PlatformIO Core:** For ESP32 microcontroller compilation and flashing
* **C++ Compiler:** `clang` or `gcc` with C++17 support

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/arywk40-hue/DP-IC-202-.git
cd DP-IC-202-

# Set up Python virtual environment and dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r server/requirements.txt

# Install frontend dependencies
npm ci --prefix ui
```

### 2. Launch Local Sovereign Dashboard

```bash
# Run production deployment (builds frontend, verifies model artifacts, starts gateway)
.venv/bin/python server/scripts/deploy_production.py --port 8080 --enable-demo-auth
```

Open **http://127.0.0.1:8080** in your browser.

*For UI development with hot module replacement (HMR):*
```bash
# Terminal 1: Backend service
.venv/bin/python -m server.dashboard --port 8080 --enable-demo-auth

# Terminal 2: Vite development server
npm run dev --prefix ui
```
Open **http://127.0.0.1:5173** (API calls are automatically proxied to port 8080).

---

## Live Sensor Integration (ESP32 → Server → Dashboard)

Physical readings take their own path, separate from the Open-Meteo model grid:

```
ESP32 (esp32/operational_node) ──WiFi POST──┐
ESP32 ──USB── serial_bridge.py ─────────────┼──► POST /api/ingest ──► ml/data/sensors/sensors.sqlite
ESP32 ──USB── browser "Connect board" ──────┘                              │
                                     GET /api/sensors/combined ◄───────────┘ ──► "Live sensors" tab
```

**1. Start the server** (`--host 0.0.0.0` only if boards upload over WiFi):
```bash
.venv/bin/pip install -r server/requirements.txt
.venv/bin/python -m server.dashboard --port 8080 --host 0.0.0.0 --ingest-token CHANGE_ME
```

**2. Configure each board** — copy `esp32/operational_node/include/device_config.example.h` to
`device_config.h` (git-ignored), set `physical_mode=true`, your real pins (`-1` for any sensor not fitted),
the site elevation, and fixed lat/lon if there is no GPS. For WiFi, also set SSID, password,
`indra_server_url()` (your computer's LAN IP, e.g. `http://192.168.1.20:8080`) and the token.

**3. Flash** — the node id is baked in from `--node-id` (or `--node-name`):
```bash
.venv/bin/python esp32/tools/flash_esp32.py --role slave --node-id 1 --node-name ridge-01
```

**4. Get readings in** — WiFi boards post on their own. For USB boards either click
**Live sensors → Connect board** in Chrome/Edge, or run:
```bash
.venv/bin/python server/scripts/serial_bridge.py --token CHANGE_ME                 # all plugged-in boards
.venv/bin/python server/scripts/serial_bridge.py --port /dev/cu.usbmodem1101 --node-id lab-01 \
    --lat 28.61 --lon 77.21 --elevation 216 --token CHANGE_ME
```

**Test without hardware:**
```bash
curl -X POST http://127.0.0.1:8080/api/ingest -H 'Content-Type: application/json' -H 'X-Indra-Token: CHANGE_ME' \
  -d '{"node_id":"test-01","temperature_c":21.4,"relative_humidity_pct":60,"pressure_hpa":1008}'
```

| Endpoint | Purpose |
| :--- | :--- |
| `POST /api/ingest` | Firmware JSON, flat reading, list of readings, or `indra_hmac_v1` signed envelope |
| `GET /api/sensors/combined` | Every node's latest reading + network mean/min/max/spread, lapse rate (nodes within 50 km), +6 h forecast per node |
| `GET /api/sensors` | Node list with ONLINE (<2 min) / STALE (<15 min) / OFFLINE status |
| `GET /api/sensors/{id}/history?hours=24` · `/hourly` · `/forecast` · `/latest` | Per-node data |
| `POST /api/sensors/{id}/register` | Set name / lat / lon / elevation for a node without GPS |

The +6 h forecast runs on hourly means and needs 25 consecutive complete hours; until then it reports
`WARMING_UP_PERSISTENCE`. Out-of-range values are stored as null, never clamped. Use `--cors-origins
http://localhost:3000` if a frontend on another origin calls the API. Signed packets: set
`INDRA_INGEST_HMAC_KEY` (hex, ≥32 bytes).

### Master + slaves without WiFi (ESP-NOW)

```
Slave 1 ─┐  ESP-NOW (128-byte HMAC-signed frame, every 10 s)
Slave 2 ─┼──────────► Master ──USB──► serial_bridge.py ──► POST /api/ingest
```

1. **Flash the master first** and note the MAC it prints (`INDRA node master-00 role=master mac=AA:BB:...`):
   `.venv/bin/python esp32/tools/flash_esp32.py --role master --node-id 0 --node-name master-00`
2. In `device_config.h` set on **all three** boards: the same `indra_espnow_channel()` and the same
   `indra_mesh_key_hex()` (`python3 -c "import secrets; print(secrets.token_hex(32))"`). On the slaves also
   set `indra_master_mac()` to the master's MAC, plus each slave's `fixed_latitude/longitude` and elevation.
3. Flash the slaves:
   `flash_esp32.py --role slave --node-id 1 --node-name ridge-01` and `--node-id 2 --node-name basin-02`.
4. Plug **only the master** into the laptop and run
   `.venv/bin/python server/scripts/serial_bridge.py --token CHANGE_ME` (no `--node-id`).

The master prints its own reading and every verified slave reading as JSON; the bridge forwards each under its
own node id (`transport: espnow`, with RSSI). Duplicates and replays are dropped by sequence number; frames with
a wrong key are rejected and counted (`rx_bad` in the master's status line, alongside per-slave `lost` counts).
If the master later joins WiFi, set every board's channel to the router's channel.

---

## Physical Hardware Deployment & Flashing Guide

INDRA includes an automated flashing and diagnostic tool ([`esp32/tools/flash_esp32.py`](esp32/tools/flash_esp32.py)) that automatically detects serial ports, builds the correct PlatformIO environment, uploads the firmware, and validates post-flash health over UART:

### 1. Flash Master Gateway Node (Node 0)
Connect the ESP32-S3 DevKitC-1 N8 board via USB and run:
```bash
.venv/bin/python esp32/tools/flash_esp32.py --role master --node-id 0
```
*Compiles `esp32-s3-mandi-v2`, uploads firmware, and performs `INFO` and `SELFTEST` handshakes.*

### 2. Flash Peripheral Slave Node 1 (Ridge Unit)
Connect Slave Node 1 via USB and run:
```bash
.venv/bin/python esp32/tools/flash_esp32.py --role slave --node-id 1
```

### 3. Flash Peripheral Slave Node 2 (Basin Unit)
Connect Slave Node 2 via USB and run:
```bash
.venv/bin/python esp32/tools/flash_esp32.py --role slave --node-id 2
```

### 4. Flash Any Future Slave Node $N$ ($N \in [3, 512]$)
```bash
.venv/bin/python esp32/tools/flash_esp32.py --role slave --node-id <N>
```

### Physical Sensor Wiring Specification
Connect sensors to the ESP32 GPIOs as specified in the [Deployment Readiness Report](docs/reports/ESP32_DEPLOYMENT_SPECIFICATION_AND_READINESS.md):
* **Bosch BME280 (T, RH, P):** `SDA -> GPIO 21`, `SCL -> GPIO 22`, `VCC -> 3.3V`, `GND -> GND` (I2C `0x76`).
* **Plantower PMS5003 (PM2.5, PM10):** `TX -> GPIO 16 (RX2)`, `RX -> GPIO 17 (TX2)`, `VCC -> 5V`, `GND -> GND` (`9600 baud`).
* **Pulse Anemometer (Wind Speed):** `Signal -> GPIO 34 (ADC1_CH6 / Pulse Interrupt)`, `VCC -> 5V/12V`, `GND -> GND`.
* **Texas Instruments INA219 (Solar/Battery):** `SDA -> GPIO 21`, `SCL -> GPIO 22`, `VCC -> 3.3V` (I2C `0x40`).

---

## Interactive Dashboard Views

The web dashboard is organized into operational modules accessible from the navigation bar:

1. **Observations (`/`)**: Real-time 6-channel observation cards, 24-hour historical sparklines, +6h forecast predictions, and Monte Carlo hazard scenario simulations for Mandi, HP.
2. **Parameter Heatmaps (`/#parameters`)**: Continuous 2D IDW surface contour maps across all six physical parameters with adaptive resolution settings.
3. **Pan-India National Operations (`/#national`)**:
   - Interactive search explorer across **587 IMD/NOAA stations** and 28 States / 8 UTs.
   - Live forecast and hazard assessments for all 6 agro-climatic zones.
   - **🔌 Direct USB Web Serial connection** to physical ESP32 hardware at 115200 baud.
   - One-click research hazard injection vectors (Cloudburst, Snowstorm, Andhi, Gale, Loo, Smog).
4. **Catchment Multi-Node Mesh (`/#national` → Mesh Tier)**:
   - Interactive topology displaying **1 Master + 2 Slaves (scalable to $N$ nodes)**.
   - Live vertical lapse rate ($\nabla T$), pressure gradient ($\Delta P$), and wind shear displays.
   - **Byzantine Consensus Tester:** Demonstrates single-node false alarm suppression (1/3 votes rejected) vs. coordinated catchment warning confirmation (3/3 votes corroborated).
   - Dynamic "+ Add Peripheral Slave" scaling tester.
5. **API Explorer (`/#apis`)**: Built-in REST testing console allowing operators to query endpoints, inspect response headers, and view raw JSON payloads.
6. **Data & System (`/#system`)**: Cryptographic provenance journal, Merkle tree batch verification, and Model Lab detailing blend weights and validation traces.

---

## REST API Reference

| Category | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Catchment Mesh**| `GET` | `/api/mesh/topology` | Active 1 Master + N Slaves topology, consensus state, and spatial lapse rates |
| **Telemetry** | `GET` | `/api/nodes` | List active observation nodes and freshness status |
| | `GET` | `/api/nodes/{id}/telemetry` | Full telemetry snapshot, 24h history, +6h forecast, and hazard outputs |
| | `GET` | `/api/status` | System health, feed freshness, active ML model, and uptime |
| **National** | `GET` | `/api/national/zones` | List all 6 agro-climatic zones and metadata |
| | `GET` | `/api/national/stations` | Query the 587-station directory with search and zone filtering |
| | `GET` | `/api/national/forecast` | On-demand +6h forecast for any latitude/longitude coordinate across India |
| | `GET` | `/api/national/jaipur/wind-risk` | Arid Northwest convective windstorm, Andhi, and kinetic power density evaluation |
| | `POST` | `/api/national/esp32/infer` | Direct sensor reading inference executing the embedded C++17 logic |
| **Spatial** | `GET` | `/api/kriging/heatmap` | Single-channel continuous spatial surface (GeoJSON) |
| | `GET` | `/api/parameter-heatmaps` | All six parameter spatial estimations simultaneously |
| **Provenance** | `GET` | `/api/provenance` | Transactional audit events, Merkle root, and local batch proof |
| **Auth** | `GET` | `/api/auth/config` | Authentication configuration and Google Client ID |
| | `POST` | `/api/auth/demo-login` | 1-click local operator login (when `--enable-demo-auth` is active) |
| | `GET` | `/api/auth/me` | Fetch verified identity from `Authorization: Bearer <token>` |
| | `POST` | `/api/auth/logout` | Revoke active session token |

---

## Automated Test Suite & Quality Assurance

Run the test suite from the repository root:

```bash
# 1. Run all 402 Python Unit, Integration, and Parity Tests
.venv/bin/pytest

# 2. Run C++ to Python Parity Verification
.venv/bin/python esp32/ml_integration/tools/test_mandi_v2_parity.py

# 3. Run Hardware Flasher Tool Tests
.venv/bin/pytest ml/tests/test_flash_tool.py -v

# 4. Run Frontend Unit and Contract Tests
npm test --prefix ui

# 5. Run Playwright End-to-End Browser Tests (Desktop & Mobile)
npm run test:e2e --prefix ui

# 6. Verify PlatformIO Embedded Firmware Compilation
PLATFORMIO_CORE_DIR=/tmp/indra-pio pio run -d esp32/ml_integration -e esp32-s3-mandi-v2 -e esp32-s3-mandi-v2-usb

# 7. Verify Statutory Patent Package Evidentiary Integrity
.venv/bin/python patent/tools/compile_patent_package.py
```

---

## Repository Directory Map

```text
Dp-indra-six-sensor/
├── ml/                      # Machine learning models, pipelines, and evaluation
│   ├── configs/             # Versioned scenario, feature, and dataset configurations
│   ├── data/                # Data receipts, 587-station directory, field caches
│   ├── himachal/            # Hazard scenarios, weather categories, parameter maps
│   ├── india_mandi/         # Mandi tabular v2 ensemble, neural heads, live ingestion
│   ├── models/              # Serialized model weights and catalog
│   ├── national/            # Pan-India 6-zone router, Jaipur windstorm runtime
│   ├── scripts/             # Training, evaluation, and live reporting scripts
│   ├── six_sensor_forecast/ # Core contract definitions, feature builder, C export
│   └── tests/               # 402 unit, integration, and C++ parity tests
├── server/                  # FastAPI backend and production services
│   ├── auth.py              # Google OAuth 2.0 verification and session store
│   ├── dashboard.py         # Main FastAPI application and API routes
│   ├── scripts/             # Production deployment, daemon, and verification scripts
│   └── tests/               # Backend integration and auth tests
├── ui/                      # React 18 + Vite 5 Progressive Web App
│   ├── src/components/      # NationalDeployPanel, MeshTopologyPanel, MapView, etc.
│   ├── src/context/         # React Auth context provider
│   ├── tests/               # Contract, auth, and Playwright E2E browser tests
│   └── vite.config.js       # Vite configuration with PWA plugin
├── esp32/                   # Embedded edge firmware & hardware tooling
│   ├── ml_integration/      # Standalone C++ Mandi v2 + Jaipur windstorm runtime
│   ├── himachal_node/       # Decentralized P2P mesh & Byzantine consensus firmware
│   ├── operational_node/    # Physical sensor driver hub (BME280, PMS5003, Anemometer)
│   └── tools/               # Automated 1-command flasher CLI (flash_esp32.py)
├── contracts/               # Cryptographic provenance & smart contracts
│   ├── IndraAnchor.sol      # Solidity append-only Merkle anchor contract
│   ├── provenance.py        # Merkle tree and audit journal engine
│   └── tests/               # Audit journal and EVM integration tests
├── patent/                  # Formal statutory patent application filing package
│   ├── SPECIFICATION.md     # Complete statutory patent specification
│   ├── CLAIMS.md            # 25 formal statutory claims
│   ├── DRAWINGS.md          # 8 formal patent drawings & logic diagrams
│   ├── INVENTION_DISCLOSURE_REPORT.md # Prior art analysis & Alice/Section 3(k) assessment
│   ├── FILING_CHECKLIST_AND_FORMS.md  # Official filing forms (Form 1, 2, 3, 5, ADS, PCT)
│   ├── tools/               # Package compiler & cryptographic evidence verification
│   ├── tests/               # Test suite validating patent claims against codebase
│   └── compiled/            # Unified application Markdown, HTML, and JSON manifest
└── docs/                    # Consolidated handbook, reports, and architecture plans
    ├── EVERYTHING.md        # Complete presentation handbook and historical records
    ├── plans/               # Active dashboard scope and architecture specifications
    └── reports/             # Detailed readiness reviews and final submission metrics
        ├── FINAL_SUBMISSION_METRICS_REPORT.md # Exhaustive submission report
        └── ESP32_DEPLOYMENT_SPECIFICATION_AND_READINESS.md # Hardware runbook
```

---

## Detailed Documentation & Patent Package

* **[FINAL_SUBMISSION_METRICS_REPORT.md](docs/reports/FINAL_SUBMISSION_METRICS_REPORT.md):** Exhaustive final submission report containing all model accuracy, embedded footprint, mesh network, and CI/CD metrics.
* **[ESP32_DEPLOYMENT_SPECIFICATION_AND_READINESS.md](docs/reports/ESP32_DEPLOYMENT_SPECIFICATION_AND_READINESS.md):** Hardware wiring, pinout diagrams, flashing runbooks, and microcontroller verification specifications.
* **[patent/SPECIFICATION.md](patent/SPECIFICATION.md):** Complete formal patent specification detailing system architecture, mathematical derivations, and preferred embodiments.
* **[patent/CLAIMS.md](patent/CLAIMS.md):** 25 statutory patent claims covering the 66-causal feature engine, convex simplex ensemble, tri-family Monte Carlo simulator, and ESP32-S3 runtime.
* **[patent/DRAWINGS.md](patent/DRAWINGS.md):** Detailed patent figures and logic flowcharts (FIGS. 1–8) with reference numerals.
* **[patent/INVENTION_DISCLOSURE_REPORT.md](patent/INVENTION_DISCLOSURE_REPORT.md):** In-depth patentability assessment, prior art comparison matrix, and statutory eligibility analysis.
* **[patent/FILING_CHECKLIST_AND_FORMS.md](patent/FILING_CHECKLIST_AND_FORMS.md):** Statutory filing forms and step-by-step submission guides for IPO (InPASS), USPTO (Patent Center), and WIPO (PCT).
* **[docs/EVERYTHING.md](docs/EVERYTHING.md):** Consolidated project handbook covering full system architecture, model training history, data provenance, and evaluation records.
