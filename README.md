# INDRA — Six-Channel Weather Forecasting & Himalayan Hazard Platform

INDRA is an end-to-end meteorological forecasting, spatial intelligence, and experimental hazard-simulation platform configured for **Mandi, Himachal Pradesh** (31.71° N, 76.93° E). The system ingests six hourly atmospheric and particulate channels, generates six-hour numerical forecasts via a multi-model ensemble, computes continuous spatial parameter maps, simulates Himalayan hazard scenarios, maintains a cryptographic audit trail with local blockchain anchoring, and features an embedded C++ inference runtime for the ESP32-S3 microcontroller.

```
                                  ┌───────────────────────────┐
                                  │   Open-Meteo Model Grid   │
                                  │   (ECMWF IFS & CAMS Glob) │
                                  └─────────────┬─────────────┘
                                                │ Polled every 15m
                                                ▼
┌─────────────────────────┐       ┌───────────────────────────┐       ┌─────────────────────────┐
│     ESP32-S3 Edge ML    │       │     FastAPI Gateway       │       │    Interactive PWA UI   │
│   • C++ Mandi v2 engine │◄─────►│   • india_mandi_tabular_v2│◄─────►│   • Observations Map    │
│   • 10 synthetic patterns│ Serial│   • 10 Weather Patterns   │ REST  │   • Parameter Heatmaps  │
│   • Monte Carlo scenarios│  CSV  │   • Monte Carlo Scenarios │ JSON  │   • API Explorer        │
│   • Fits N8 DevKit (3MB)│       │   • Merkle Audit Journal  │       │   • Provenance & System │
└─────────────────────────┘       └─────────────┬─────────────┘       └─────────────────────────┘
                                                │
                                                ▼
                                  ┌───────────────────────────┐
                                  │   EVM Smart Contract      │
                                  │   IndraAnchor (Solidity)  │
                                  └───────────────────────────┘
```

> [!IMPORTANT]
> **Data & Evidence Scope:** Current readings are sourced from Open-Meteo's numerical weather prediction (ECMWF IFS) and air-quality (CAMS Global) model grids; they are modeled estimates, not local physical station readings. With one active coordinate, the system renders a discrete point marker and does not fabricate multi-site heatmaps. Cloudburst, flash-flood, and landslide percentages are synthetic Monte Carlo simulation fractions under specified hydrological and rainfall assumptions—they are **not calibrated real-event probabilities, public warnings, or observed disaster forecasts**.

---

## Key Capabilities

1. **Six-Channel +6h Numerical Forecasting**:
   - Predicts **temperature (°C)**, **relative humidity (%)**, **surface pressure (hPa)**, **PM2.5 (µg/m³)**, **PM10 (µg/m³)**, and **wind speed (m/s)**.
   - Versioned ensemble (`india_mandi_tabular_v2`) blending LightGBM, a residual MLP (`mlp_v2`), a legacy history XGBoost/ridge hybrid, and persistence.
   - Derives 66 causal features from 25 consecutive hourly observations (24 hours of history). Reports explicit persistence warm-up if history is incomplete.

2. **Himalayan Hazard & Weather Pattern Scenarios**:
   - **Current Weather Patterns (`WeatherCategories`)**: 10 overlapping category scores based on 13 raw, current, and change features over a 7-reading window, trained on 24,000 synthetic episodes with engineering proxy labels. Scores express pattern similarity, not event probabilities.
   - **Hazard Scenarios (`HazardScenarios`)**: Reproducible 6-hour Monte Carlo engine (2,048 draws) modeling cloudburst rainfall (≥ 100 mm/h threshold), flash-flood runoff (Rational Method), and landslide triggers (intensity-duration threshold). Reports outcome fractions across **drier**, **central**, and **wetter** assumption families with full parameter provenance.

3. **Spatial Interpolation & Parameter Maps**:
   - Continuous 2D Inverse Distance Weighting (IDW) surface engine (`ml/himachal/parameter_maps.py`) generating GeoJSON contours across all six physical parameters.
   - Requires at least 3 synchronized, non-collinear locations to produce an area heatmap; when connected to a single point, it displays the location and explains data constraints.

4. **Cryptographic Provenance & Blockchain Anchor**:
   - SQLite-backed transactional audit log (`indra_audit_json_v1`) capturing hash-linked event chains.
   - Domain-separated SHA-256 Merkle root generator (`indra_batch_v1`) producing verified export batches.
   - Solidity smart contract (`IndraAnchor.sol`) for immutably anchoring batch Merkle roots to EVM blockchains.

5. **ESP32-S3 Embedded Edge ML**:
   - Standalone C++ inference engine (`esp32/ml_integration/src/mandi_v2_main.cpp`) exporting the full Mandi v2 ensemble, 10 synthetic pattern scores, and Monte Carlo scenario simulator.
   - Fits ESP32-S3 DevKitC-1 N8 partitions (~2.97 MB flash, ~20 KB RAM).
   - High-precision parity with Python (< 0.00013 max absolute difference on forecast, < 3.3e-8 on patterns).
   - 115200 baud serial protocol supporting `INFO`, `SELFTEST`, `RESET`, and CSV telemetry streaming.

6. **Full-Stack Application & Interactive API Explorer**:
   - Modern React 18 + Vite 5 Progressive Web App (PWA) with offline caching and responsive desktop/mobile layouts.
   - In-app **API Explorer** (`/#apis`) for testing REST endpoints in real time.
   - Secure authentication supporting Google OAuth 2.0 and local operator 1-click demo access, with SHA-256 token hashing and 7-day session expiration.

---

## Quickstart

### Prerequisites

- **Python**: 3.11 – 3.13
- **Node.js**: 20+ (Node 22 tested)
- **C/C++ Compiler**: `clang` or `gcc` (for model parity verification)

### Installation

From the repository root:

```sh
# Set up Python virtual environment and dependencies
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r server/requirements.txt

# Install frontend dependencies
npm ci --prefix ui
```

### Production Deployment

INDRA includes a unified production deployment runner that builds the frontend with Vite, verifies ML model artifacts and SHA-256 hashes, and starts the gateway:

```sh
.venv/bin/python server/scripts/deploy_production.py --port 8080
```

Open **http://127.0.0.1:8080** in your browser.

#### Common Production Deployment Options:

```sh
# Enable 1-click local operator demo login (loopback only)
.venv/bin/python server/scripts/deploy_production.py --port 8080 --enable-demo-auth

# Adjust Open-Meteo polling interval (default: 900 seconds / 15 minutes; minimum 60s)
.venv/bin/python server/scripts/deploy_production.py --port 8080 --refresh-seconds 300

# Skip UI build if ui/dist is already built
.venv/bin/python server/scripts/deploy_production.py --port 8080 --skip-build
```

### Frontend Development Mode

For UI development with hot module replacement (HMR):

```sh
# Terminal 1: Start backend API service
.venv/bin/python -m server.dashboard --port 8080 --enable-demo-auth

# Terminal 2: Start Vite development server
npm run dev --prefix ui
```

Open **http://127.0.0.1:5173** (API calls are automatically proxied to port 8080).

---

## Interactive Dashboard Views

The web dashboard is organized into four main operational views accessible from the top navigation bar:

1. **Observations (`/`)**:
   - Interactive Leaflet map centered at Mandi (31.71° N, 76.93° E).
   - Real-time telemetry cards for all six channels with measurement units.
   - 24-hour historical sparklines and six-hour numerical forecast predictions.
   - Sensor pattern matches and Monte Carlo hazard scenario simulations with expandable methodological provenance.

2. **Parameter Heatmaps (`/#parameters`)**:
   - Visualizes continuous spatial distribution across all six parameters.
   - Supports selecting channels and contour resolutions. Indicates when additional synchronized nodes are needed for multi-point surfaces.

3. **API Explorer (`/#apis`)**:
   - Built-in REST API testing console allowing operators and developers to execute queries, inspect headers, and examine structured JSON responses directly in the UI.

4. **Data & System (`/#system`)**:
   - Cryptographic provenance and Merkle batch audit status.
   - Model Lab detailing architecture components, blend weights, and evaluation metrics.
   - Device technical details, registration identities, and connection status.

---

## REST API Reference

The FastAPI gateway exposes a comprehensive REST API. Explore and test these live at `/#apis`:

| Group | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Telemetry** | `GET` | `/api/nodes` | List active observation nodes and freshness status |
| | `GET` | `/api/nodes/{id}/telemetry` | Full telemetry snapshot, 24h history, +6h forecast, and hazard outputs |
| | `GET` | `/api/status` | System health, feed freshness, active ML model, and uptime |
| **Spatial** | `GET` | `/api/kriging/heatmap` | Single-channel IDW continuous spatial surface (GeoJSON) |
| | `GET` | `/api/parameter-heatmaps` | All six parameter spatial estimations simultaneously |
| **Provenance** | `GET` | `/api/provenance` | Transactional audit events, Merkle root, and local batch proof |
| **Auth** | `GET` | `/api/auth/config` | Authentication status and configured Google Client ID |
| | `POST` | `/api/auth/google` | Verify Google identity token and issue session token |
| | `POST` | `/api/auth/demo-login` | 1-click demo login (when `--enable-demo-auth` is active) |
| | `GET` | `/api/auth/me` | Fetch verified identity from `Authorization: Bearer <token>` |
| | `POST` | `/api/auth/logout` | Revoke active session token |

---

## Authentication & Security

INDRA includes an authentication module (`server/auth.py`):

- **Google OAuth 2.0**: Set `GOOGLE_CLIENT_ID` in your environment. The client verifies audience, issuer, expiry, and email verification flags before issuing an opaque session token.
- **Local Demo Login**: Pass `--enable-demo-auth` to `deploy_production.py` or `dashboard.py`. Restricted to loopback addresses (`127.0.0.1`, `::1`).
- **Privacy & Storage**: Bearer tokens are never stored in plaintext. The SQLite database stores only the SHA-256 hash (`token_hash`) with a 7-day TTL and automatic expired-session purging.

---

## ESP32-S3 Embedded Edge ML

The firmware in `esp32/ml_integration/` runs the complete Mandi v2 machine learning ensemble directly on an ESP32-S3 microcontroller:

- **Ensemble on Device**: LightGBM, MLP, legacy hybrid, and persistence running in standalone C++ (`indra_mandi_v2_runtime.h`).
- **Hazard Scenarios on Device**: Monte Carlo simulation engine with deterministic on-board PRNG (`indra_xorshift64star_boxmuller_v1`).
- **Target Hardware**: ESP32-S3 DevKitC-1 N8 (8 MB Octal Flash, no PSRAM required). Memory usage: **~2.97 MB / 3.34 MB Flash**, **~20 KB RAM**.

### Export & Parity Verification

```sh
# Generate C++ model headers and verify host-side parity with Python
MPLCONFIGDIR=/tmp/indra-mpl .venv/bin/python esp32/ml_integration/tools/export_mandi_v2.py
MPLCONFIGDIR=/tmp/indra-mpl .venv/bin/python esp32/ml_integration/tools/test_mandi_v2_parity.py

# Verify PlatformIO compilation for UART and USB CDC environments
PLATFORMIO_CORE_DIR=/tmp/indra-platformio pio run -d esp32/ml_integration -e esp32-s3-mandi-v2 -e esp32-s3-mandi-v2-usb
```

### Serial Protocol (115200 baud)

Send one line per exact hourly observation:
```text
unix_seconds,temperature_c,relative_humidity_pct,pressure_hpa,pm25_ug_m3,pm10_ug_m3,wind_speed_mps
```
Example: `1767225600,20.0,50.0,1013.0,35.0,60.0,2.0`

Device commands:
- `INFO`: Reports firmware identity, model SHA-256, and buffer status.
- `SELFTEST`: Executes on-device verification vector.
- `RESET`: Clears the historical observation buffer.

---

## Model Evaluation & Performance

The `india_mandi_tabular_v2` model was evaluated on 35,520 hourly positions (October 2022 – 19 October 2026) across 33,570 training, 738 validation, and **1,170 future-test pairs** with 6-hour boundary purges:

| Target Channel (+6h) | Hybrid MAE | Unit |
| :--- | :---: | :--- |
| **Temperature** | 1.4264 | °C |
| **Relative humidity** | 6.8214 | percentage points |
| **Surface pressure** | 0.9412 | hPa |
| **PM2.5** | 6.5932 | µg/m³ |
| **PM10** | 8.6987 | µg/m³ |
| **Wind speed** | 0.3019 | m/s |

A subsequent retrospective evaluation on an untouched 5-day Open-Meteo archive (120 six-hour pairs from 20–24 October 2026) demonstrated **50.2% to 82.8% MAE skill improvement over persistence**:

| Target Channel (+6h) | Model MAE | Persistence MAE | Skill vs Persistence |
| :--- | :---: | :---: | :---: |
| **Temperature** | 1.27 °C | 7.40 °C | **+82.8%** |
| **Relative humidity** | 7.03 % | 26.83 % | **+73.8%** |
| **Surface pressure** | 0.68 hPa | 1.98 hPa | **+66.0%** |
| **PM2.5** | 5.23 µg/m³ | 11.32 µg/m³ | **+53.8%** |
| **PM10** | 6.09 µg/m³ | 12.22 µg/m³ | **+50.2%** |
| **Wind speed** | 0.32 m/s | 0.65 m/s | **+50.7%** |

*Note: Evaluated on Open-Meteo modeled-grid data. Does not establish field physical-sensor accuracy.*

---

## Testing & Quality Assurance

Run the complete test suite from the repository root:

```sh
# 1. Python Unit and Integration Tests (FastAPI, Scenarios, Auth, Models)
.venv/bin/python -m pytest ml/tests/test_hazard_scenarios.py server/tests/ -q

# 2. Blockchain and Merkle Provenance Tests
.venv/bin/python -m pytest contracts/tests/ -q

# 3. Frontend Unit and Contract Tests
npm test --prefix ui

# 4. End-to-End Browser Tests (Playwright desktop & mobile)
npm run test:e2e --prefix ui

# 5. Live Dashboard Verification (against live Open-Meteo receipt)
.venv/bin/python server/scripts/verify_mandi_dashboard.py --url http://127.0.0.1:8080
```

---

## Repository Map

```text
Dp-indra-six-sensor/
├── ml/                      # Machine learning models, pipelines, and evaluation
│   ├── configs/             # Versioned scenario, feature, and dataset configurations
│   ├── data/                # Data receipts, field stores, and local caches
│   ├── himachal/            # Hazard scenarios, weather categories, parameter maps
│   ├── india_mandi/         # Mandi tabular v2 ensemble, neural heads, and live ingestion
│   ├── models/              # Serialized model weights and catalog
│   ├── scripts/             # Training, evaluation, and live reporting scripts
│   ├── six_sensor_forecast/ # Core contract definitions, feature builder, C export
│   └── tests/               # Pytest suite for ML components and scenarios
├── server/                  # FastAPI backend and production services
│   ├── auth.py              # Google OAuth 2.0 verification and session store
│   ├── dashboard.py         # Main FastAPI application and API routes
│   ├── scripts/             # Production deployment and verification scripts
│   └── tests/               # Backend integration and auth tests
├── ui/                      # React 18 + Vite 5 Progressive Web App
│   ├── src/components/      # Observations, ParameterMaps, ApiExplorer, Provenance
│   ├── src/context/         # React Auth context provider
│   ├── tests/               # Contract, auth, and Playwright E2E browser tests
│   └── vite.config.js       # Vite configuration with PWA plugin
├── contracts/               # Cryptographic provenance & smart contracts
│   ├── IndraAnchor.sol      # Solidity append-only Merkle anchor contract
│   ├── provenance.py        # Merkle tree and audit journal engine
│   ├── scripts/             # Compilation, export, and EVM test runners
│   └── tests/               # Audit journal and EVM integration tests
├── esp32/                   # Embedded edge firmware
│   ├── ml_integration/      # Standalone C++ Mandi v2 runtime & PlatformIO configs
│   ├── himachal_node/       # Operational telemetry node firmware
│   └── india_sensor/        # Sensor driver integrations
├── simulator/               # LoRa radio and network simulation engine
│   ├── network.py           # Multi-node network simulator and contention model
│   └── radio.py             # Airtime, modulation, and duty cycle calculations
├── patent/                  # Formal patent application filing package
│   ├── SPECIFICATION.md     # Complete statutory patent specification (USPTO / IPO)
│   ├── CLAIMS.md            # 25 formal statutory claims (system, method, device, medium)
│   ├── DRAWINGS.md          # Formal patent drawings & logic diagrams (FIGS. 1–8)
│   ├── INVENTION_DISCLOSURE_REPORT.md # Prior art analysis & Alice/Section 3(k) assessment
│   ├── FILING_CHECKLIST_AND_FORMS.md  # Official filing forms (Form 1, 2, 3, 5, ADS, PCT)
│   ├── tools/               # Package compiler & cryptographic evidence verification
│   ├── tests/               # Test suite validating patent claims against codebase
│   └── compiled/            # Unified application Markdown, HTML, and JSON manifest
└── docs/                    # Consolidated handbook, reports, and architecture plans
    ├── EVERYTHING.md        # Complete presentation handbook and historical records
    ├── plans/               # Active dashboard scope and architecture specifications
    └── reports/             # Detailed readiness reviews and model evaluations
```

---

## Detailed Documentation & Patent Package

- [patent/SPECIFICATION.md](patent/SPECIFICATION.md): Complete formal patent specification detailing system architecture, mathematical derivations, and preferred embodiments.
- [patent/CLAIMS.md](patent/CLAIMS.md): 25 statutory patent claims covering the 66-causal feature engine, convex simplex ensemble, tri-family Monte Carlo simulator, and ESP32-S3 runtime.
- [patent/DRAWINGS.md](patent/DRAWINGS.md): Detailed patent figures and logic flowcharts (FIGS. 1–8) with reference numerals.
- [patent/INVENTION_DISCLOSURE_REPORT.md](patent/INVENTION_DISCLOSURE_REPORT.md): In-depth patentability assessment, prior art comparison matrix, and statutory eligibility analysis.
- [patent/FILING_CHECKLIST_AND_FORMS.md](patent/FILING_CHECKLIST_AND_FORMS.md): Statutory filing forms and step-by-step submission guides for IPO (InPASS), USPTO (Patent Center), and WIPO (PCT).
- [docs/EVERYTHING.md](docs/EVERYTHING.md): Consolidated project handbook covering full system architecture, model training history, data provenance, and evaluation records.
- [docs/plans/unified_dashboard_views.md](docs/plans/unified_dashboard_views.md): Active dashboard view specifications and data contracts.
- [docs/reports/INDRA_READINESS_2026-10-25.md](docs/reports/INDRA_READINESS_2026-10-25.md): Comprehensive system readiness review, live feed verification, and archive evaluation.
- [docs/reports/ESP32_MANDI_V2_READINESS.md](docs/reports/ESP32_MANDI_V2_READINESS.md): Hardware readiness report, C++ parity results, and flashing guide.
- [esp32/ml_integration/README.md](esp32/ml_integration/README.md): Detailed serial command specification, memory maps, and embedded C++ integration details.
