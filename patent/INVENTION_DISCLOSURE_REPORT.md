# INVENTION DISCLOSURE REPORT & PATENTABILITY ASSESSMENT

**CONFIDENTIAL — PREPARED FOR INTELLECTUAL PROPERTY COUNSEL & PATENT OFFICE SUBMISSION**

**INVENTION TITLE:**  
SYSTEMS AND METHODS FOR MULTI-CHANNEL MICRO-METEOROLOGICAL EDGE FORECASTING, LATENT HYDROLOGICAL HAZARD SIMULATION, AND CRYPTOGRAPHIC PROVENANCE ANCHORING

**INVENTOR(S):**  
Ariyan Bhakat, et al.

**PROJECT / REPOSITORY:**  
INDRA (`Dp-indra-six-sensor`)

**DATE OF DISCLOSURE:**  
November 2026

---

## 1. EXECUTIVE SUMMARY & INVENTIVE ESSENCE

The INDRA platform solves an acute, unaddressed problem in environmental monitoring: **the lack of high-fidelity, strictly causal, edge-executable micro-meteorological forecasting coupled with assumption-explicit disaster risk simulation and verifiable tamper-proof audit trails.**

In high-altitude, mountainous geographies like the Indian Himalayas, microclimatic variations trigger catastrophic sudden-onset disasters—specifically cloudbursts, flash floods, and debris flows/landslides. Conventional approaches fail because synoptic numerical weather models lack local spatial resolution, standard IoT nodes lack the computational capacity for non-linear multi-model inference, and existing warning systems suffer from high false-alarm rates or vulnerable data tampering.

INDRA introduces an integrated technological architecture comprising:
1. **6-Channel 25-Hour Sliding Window Causal Feature Engineering (66 Features):** Eliminates temporal data leakage and interpolation artifacts.
2. **Multi-Model Tabular Ensemble on a Non-Negative Convex Unit Simplex:** Formulated as a linear programming optimization problem to achieve high predictive skill across heterogeneous atmospheric regimes.
3. **Tri-Family Monte Carlo Hazard & Hydrological Simulator:** Explicitly couples surface weather to precipitation intensity and models three distinct disaster dynamics (cloudburst, flash flood, landslide) across three paired latent parameter regimes (Drier, Central, Wetter).
4. **Standalone Embedded C++ Microcontroller Runtime:** Fully transpiles the feature builder, ensemble models, and Monte Carlo simulator into an ultra-low-memory firmware package running on an ESP32-S3 microcontroller ($\le 2.97\text{ MB}$ flash, $\le 20\text{ KB}$ RAM) with sub-float mathematical parity.
5. **Spatial Cardinality Guard ($K \ge 3$):** Prevents spatial hallucination by enforcing multi-site geometry before continuous 2D surface generation.
6. **Domain-Separated Merkle Blockchain Anchoring:** Guarantees regulatory and historical immutability via `0x00`/`0x01` domain-separated Merkle trees anchored to an EVM smart contract (`IndraAnchor.sol`).

---

## 2. STATUTORY PATENT ELIGIBILITY ANALYSIS

### 2.1 United States Patent Law (35 U.S.C. § 101 — Alice / Mayo Framework)

Under the two-step *Alice/Mayo* framework for patent eligibility:

#### Step 1: Does the claim recite an abstract idea or mathematical algorithm?
While the invention incorporates mathematical operations (e.g., linear programming simplex, logistic sigmoids, Merkle tree hashing), the claims are directed to an integrated, physical, micro-meteorological edge forecasting and embedded hardware simulation apparatus.

#### Step 2: Does the claim contain an "inventive concept" (significantly more)?
The claims satisfy Step 2 under multiple established USPTO and Federal Circuit precedents (*Enfish, LLC v. Microsoft Corp.*, *Berkheimer v. HP Inc.*):
1. **Improvement in Computer Functionality and Embedded Systems:**  
   The invention specifically solves the severe memory and computational constraints of edge microcontrollers (320 KB SRAM). By engineering a fixed 25-sample circular FIFO buffer and in-place causal feature calculations without dynamic heap allocation, the system enables complex multi-model ensemble inference and 2,048-draw Monte Carlo simulation directly on low-power silicon.
2. **Physical Transformation of Real-World Environmental Signals:**  
   The claims recite specific environmental parameter bounds, physical sensor transducers, temporal sampling cadences, and transformation of ambient temperature, humidity, pressure, and particulate matter into mechanical discharge rates ($Q$ in $\text{m}^3/\text{s}$) and geotechnical threshold exceedances.
3. **Technical Solution to a Technical Problem:**  
   The multi-node cardinality guard ($K \ge 3$) directly solves the technical problem of spatial contour hallucination in computer graphics and GIS systems.

### 2.2 Indian Patent Law (The Patents Act, 1970 — Section 3(k) Guidelines for Computer-Related Inventions)

Section 3(k) bars patents on *"a mathematical or business method or a computer programme per se or algorithms"*. However, under the official Guidelines for Examination of Computer-Related Inventions (CRIs) issued by the Indian Patent Office (CGPDTM), the claims are fully patentable because:
1. **Technical Effect & Technical Contribution:**  
   The claimed invention produces a clear, practical technical effect: the real-time physical monitoring and hazard simulation of catastrophic environmental events, yielding measurable electrical and serial signals.
2. **Hardware-Software Co-Design:**  
   The software cannot be detached from the underlying physical apparatus. Claim 19 explicitly claims the physical embedded microcontroller (ESP32-S3), its dual-core 32-bit architecture, flash memory partitioning, SRAM constraints, and serial hardware interface.
3. **Industrial Applicability (Section 2(1)(ac)):**  
   The platform has immediate industrial application in early warning infrastructure, autonomous hydroelectric dam safety, smart mountain highways, and civil defense.

---

## 3. COMPREHENSIVE PRIOR ART COMPARISON

| Feature / Dimension | Conventional Synoptic NWP (ECMWF / GFS / WRF) | Commercial IoT Weather Stations (Davis / Campbell) | Standard Disaster Warning Alarms (USGS / IMD) | INDRA Platform (Present Invention) |
| :--- | :--- | :--- | :--- | :--- |
| **Execution Location** | High-performance supercomputer clusters | Cloud backend or local datalogger | Regional forecasting offices | **Dual-Target: Edge Microcontroller (ESP32-S3) & Local Gateway** |
| **Edge Compute Footprint** | Gigabytes/Terabytes of RAM | Minimal telemetry forwarder (no ML) | Centralized servers | **Fits $\le 2.97\text{ MB}$ Flash, $\le 20\text{ KB}$ RAM on ESP32-S3** |
| **Feature Engineering** | Multi-grid 3D atmospheric dynamics | None (raw scalars only) | Single-variable rainfall accumulation | **66 strictly causal features across 6 channels; zero future leakage** |
| **Ensemble Optimization** | Physical parameterization ensembles | None | Fixed statistical regression | **Non-negative convex unit simplex LP (HiGHS) minimizing validation MAE** |
| **Hazard Modeling Approach** | Coarse precipitation grids ($>9\text{ km}$) | Basic threshold alarms (e.g. rain $>25\text{ mm}$) | Uncalibrated empirical warnings / binary alarms | **Tri-Family Monte Carlo (2,048 draws) across Drier, Central, Wetter latent hydrology** |
| **Hydrological Coupling** | Complex numerical Navier-Stokes fluid models | None | Rainfall-only empirical curves | **Rational Method runoff + Power-Law stability + liquid-phase sigmoid coupling** |
| **Spatial Map Safeguards** | Grid interpolation regardless of station density | Blind 2D interpolation / Kriging | Polygon warning zones | **Guarded Cardinality: Enforces $K \ge 3$ non-collinear nodes; blocks single-point hallucination** |
| **Cryptographic Provenance** | Centralized file logs | Centralized proprietary databases | Government bulletins (un-hashed) | **Domain-separated Merkle trees (`0x00`/`0x01`) anchored to EVM smart contract** |

---

## 4. NOVELTY AND INVENTIVE STEP SUMMARY

### Novel Features (35 U.S.C. § 102 / Section 2(1)(j)):
1. The specific 66-dimensional causal feature formulation combining multi-horizon lag deltas (1, 3, 6, 12, 24h), 1h first derivatives, and 6h/24h rolling statistical moments across the six co-located physical parameters.
2. The empirical liquid-phase atmospheric precipitation coupling function incorporating surface cooling, barometric drop, and sigmoid phase transition.
3. The parallel evaluation of cloudburst, Rational Method runoff, and intensity-duration landslide triggers over $N \ge 2,048$ Monte Carlo iterations on an embedded edge microcontroller.
4. The tri-family parameter sensitivity structure reporting outcome fractions for Drier, Central, and Wetter subterranean conditions without fabricating uncalibrated event probabilities.
5. The combination of domain-separated Merkle batching with an append-only EVM smart contract enforcing caller authentication and replay prevention.
6. The automated spatial cardinality guard suppressing 2D continuous surfaces when fewer than 3 non-collinear nodes exist.

### Inventive Step / Non-Obviousness (35 U.S.C. § 103 / Section 2(1)(ja)):
A person having ordinary skill in the art (PHOSITA) of meteorology would not find it obvious to transpile a tabular gradient boosted tree ensemble and residual neural network into an ultra-low-memory C++ runtime fitting an ESP32-S3's 320 KB SRAM. Furthermore, standard hydrological engineering separates rainfall forecasting from catchment runoff modeling; coupling them through an on-chip, multi-family Monte Carlo simulator with cryptographic Merkle anchoring represents a non-obvious synergistic combination yielding unexpected technical benefits in reliability, speed, and auditability.

---

## 5. SOURCE CODE AND IMPLEMENTATION REPOSITORY MAPPING

Every element of the patent disclosure directly corresponds to verified, working implementation code in the repository:

| Patent Element | Codebase Module | Key Function / Class | Line / Verification Reference |
| :--- | :--- | :--- | :--- |
| **6-Channel Input Contract** | `ml/six_sensor_forecast/contract.py` | `RAW_SENSOR_COLUMNS`, `PHYSICAL_RANGES` | Lines 3–19 |
| **66 Causal Features** | `ml/six_sensor_forecast/features.py` | `build_features()`, `validate_observations()` | Lines 50–74 |
| **Convex Simplex LP Ensemble** | `ml/india_mandi/tabular_v2.py` | `convex_weights()`, `TabularV2` | Lines 25–60 |
| **Liquid-Phase Rain Coupling** | `ml/himachal/hazard_scenarios.py` | `rainfall_strength()` | Lines 31–46 |
| **Monte Carlo Tri-Family Engine** | `ml/himachal/hazard_scenarios.py` | `event_outcomes()`, `simulate()` | Lines 48–95 |
| **ESP32-S3 C++ Runtime** | `esp32/ml_integration/src/mandi_v2_main.cpp` | `mandi_v2::Runtime`, `print_result()` | Lines 10–75 |
| **Embedded C++ Header Engine** | `esp32/ml_integration/include/indra_mandi_v2_runtime.h` | `predict()`, `run_scenarios()` | Complete embedded port |
| **Spatial Cardinality Guard** | `ml/himachal/parameter_maps.py` | `parameter_maps()`, `geojson()` | Multi-node check ($K \ge 3$) |
| **Domain-Separated Merkle** | `contracts/provenance.py` | `merkle_root()`, `append()`, `batch()` | Lines 28–74 |
| **Solidity Anchor Contract** | `contracts/IndraAnchor.sol` | `contract IndraAnchor` | Lines 5–17 |
| **FastAPI Production Gateway** | `server/dashboard.py` | `create_app()`, `assess()`, `status()` | Lines 84–145, 254–285 |
| **Production Deployment Tool** | `server/scripts/deploy_production.py` | `build_frontend()`, `verify_models()` | Lines 19–75 |

---

## 6. INVENTOR DECLARATIONS & ASSIGNMENT

The inventors declare that they are the original, first, and sole/joint inventors of the subject matter disclosed and claimed herein. All rights, titles, and interests are assigned to the project entity or assignee in accordance with organizational agreements.

