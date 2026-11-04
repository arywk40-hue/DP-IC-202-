# FORMAL PATENT DRAWINGS SPECIFICATION

**TITLE: SYSTEMS AND METHODS FOR MULTI-CHANNEL MICRO-METEOROLOGICAL EDGE FORECASTING, LATENT HYDROLOGICAL HAZARD SIMULATION, AND CRYPTOGRAPHIC PROVENANCE ANCHORING**

---

## LIST OF FIGURES

- **FIG. 1** is a high-level architectural block diagram illustrating the overall system environment, including data ingestion from external model grids or physical transducers, edge microcontroller processing, gateway server orchestration, distributed ledger anchoring, and client user interface presentation.
- **FIG. 2** is a detailed schematic diagram of the embedded edge microcontroller device (ESP32-S3), showing internal bus architecture, static memory partition allocation, transpiled C++ inference pipeline, circular observation buffer, and serial command interface.
- **FIG. 3** is a time-series feature engineering pipeline diagram illustrating the 25-hour sliding window buffer and the derivation of the 66 strictly causal features without future temporal leakage.
- **FIG. 4** is an architectural flowchart of the multi-model tabular ensemble inference engine, showing the parallel execution of heterogeneous models and the convex unit simplex linear programming optimization.
- **FIG. 5** is a detailed flowchart of the tri-family Monte Carlo hazard and hydrological simulation engine, illustrating atmospheric rain strength coupling, parallel scenario evaluation, and tri-regime sensitivity reporting.
- **FIG. 6** is a block diagram of the cryptographic provenance audit engine, depicting the hash-linked transactional SQLite journal, canonical JSON serialization, and domain-separated Merkle tree construction.
- **FIG. 7** is a state transition and logic flow diagram of the append-only distributed ledger smart contract (`IndraAnchor.sol`), demonstrating owner authorization, zero-root rejection, and replay protection.
- **FIG. 8** is a spatial processing flowchart illustrating continuous Inverse Distance Weighting (IDW) interpolation and the multi-node cardinality guard preventing false 2D heatmap generation.

---

```
                                  FIG. 1
                        OVERALL SYSTEM ARCHITECTURE

 ┌────────────────────────────────────────────────────────────────────────┐
 │ 102 External Meteorological Data Source                                │
 │     • Open-Meteo Grid API (ECMWF IFS 0.1° & CAMS Global 0.4°)          │
 │     • [Optional Physical In-Situ Sensor Transducers (104)]             │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ Periodic Ingestion (e.g. 15 min)
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 100 Multi-Channel Meteorological Edge & Gateway Platform               │
 │                                                                        │
 │   ┌────────────────────────────────────────────────────────────────┐   │
 │   │ 110 Environmental Ingestion & Verification Engine               │   │
 │   │     • Physical bounds validation [-60..85°C, 300..1100 hPa]    │   │
 │   │     • Exact 1-hour temporal grid enforcement                   │   │
 │   └───────────────────────────────┬────────────────────────────────┘   │
 │                                   │ Validated 6-Channel Vector
 │                                   ▼
 │   ┌────────────────────────────────────────────────────────────────┐   │
 │   │ 120 25-Hour Sliding Window Causal Feature Engine               │   │
 │   │     • Circular buffer (t-24h to t)                             │   │
 │   │     • Derives 66 causal features (lags, deltas, rolling std)   │   │
 │   └───────────────────────────────┬────────────────────────────────┘   │
 │                                   │ 66-Dimensional Vector
 │                                   ▼
 │   ┌────────────────────────────────────────────────────────────────┐   │
 │   │ 130 Multi-Model Tabular Forecasting Ensemble                   │   │
 │   │     • LightGBM + Residual MLP + Autoregressive Hybrid          │   │
 │   │     • Convex Simplex Linear Programming Weights                │   │
 │   │     • Yields +6h Forecast for all 6 physical channels          │   │
 │   └───────────────────────────────┬────────────────────────────────┘   │
 │                                   │
 │       ┌───────────────────────────┴───────────────────────────┐
 │       ▼                                                       ▼
 │ ┌───────────────────────────────────┐   ┌──────────────────────────────────┐
 │ │ 140 Tri-Family Monte Carlo Hazard │   │ 150 Continuous Spatial IDW       │
 │ │     Simulation Engine             │   │     Interpolation Engine         │
 │ │     • Atmospheric rain coupling   │   │     • Multi-node guard (K ≥ 3)   │
 │ │     • Cloudburst, Flood, Landslide│   │     • Continuous GeoJSON surface │
 │ └─────────────────┬─────────────────┘   └─────────────────┬────────────────┘
 │                   │                                       │
 │                   └───────────────────┬───────────────────┘
 │                                       │
 │                                       ▼
 │   ┌────────────────────────────────────────────────────────────────┐   │
 │   │ 160 Cryptographic Provenance Audit Engine                      │   │
 │   │     • Transactional SQLite hash-linked journal                 │   │
 │   │     • Domain-separated Merkle batch builder (0x00 / 0x01)      │   │
 │   └───────────────────────────────┬────────────────────────────────┘   │
 └───────────────────────────────────┼────────────────────────────────────┘
                                     │
             ┌───────────────────────┴───────────────────────┐
             │ Merkle Root Anchor                            │ REST / WebSockets
             ▼                                               ▼
 ┌──────────────────────┐                        ┌──────────────────────┐
 │ 170 Distributed      │                        │ 180 Client Dashboard │
 │     Ledger (EVM)     │                        │     & API Explorer   │
 │ • IndraAnchor.sol    │                        │ • Observations Map   │
 │ • Replay Prevention  │                        │ • Parameter Heatmaps │
 │ • Immutable Roots    │                        │ • In-Browser API Test│
 └──────────────────────┘                        └──────────────────────┘
```

---

```
                                  FIG. 2
               EMBEDDED MICROCONTROLLER SUBSYSTEM (ESP32-S3)

 ┌────────────────────────────────────────────────────────────────────────┐
 │ 200 Microcontroller Hardware Enclosure (ESP32-S3 DevKitC-1)            │
 │                                                                        │
 │   ┌────────────────────────────────────────────────────────────────┐   │
 │   │ 202 Dual-Core 32-Bit Xtensa LX7 Microprocessor (240 MHz)       │   │
 │   └───────────────────────────────┬────────────────────────────────┘   │
 │                                   │ Internal Bus (204)
 │          ┌────────────────────────┼────────────────────────┐
 │          ▼                        ▼                        ▼
 │   ┌───────────────┐        ┌───────────────┐        ┌──────────────┐
 │   │ 206 8MB Flash │        │ 208 320KB RAM │        │ 210 Serial   │
 │   │   Partition   │        │   (SRAM)      │        │ Hardware     │
 │   └───────┬───────┘        └───────┬───────┘        └──────┬───────┘
 │           │                        │                       │
 └───────────┼────────────────────────┼───────────────────────┼───────────┘
             │                        │                       │
             ▼                        ▼                       ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 220 Standalone C++ Firmware Runtime (indra_mandi_v2_runtime.h)         │
 │                                                                        │
 │   ┌────────────────────────────────────────────────────────────────┐   │
 │   │ 222 Serial Protocol Parser (115200 Baud)                       │   │
 │   │     • Handles CSV stream (unix_sec, T, RH, P, PM2.5, PM10, W)  │   │
 │   │     • Dispatches INFO, SELFTEST, RESET commands                │   │
 │   └───────────────────────────────┬────────────────────────────────┘   │
 │                                   ▼
 │   ┌────────────────────────────────────────────────────────────────┐   │
 │   │ 224 Circular FIFO Observation History Buffer                   │   │
 │   │     • Fixed array: struct Observation buffer[25]               │   │
 │   │     • Validates exact 3600-second progression                  │   │
 │   │     • Occupies < 2 KB static SRAM                              │   │
 │   └───────────────────────────────┬────────────────────────────────┘   │
 │                                   ▼
 │   ┌────────────────────────────────────────────────────────────────┐   │
 │   │ 226 Transpiled C++ Causal Feature Builder                      │   │
 │   │     • Computes 66 features in-place without dynamic malloc     │   │
 │   └───────────────────────────────┬────────────────────────────────┘   │
 │                                   ▼
 │   ┌────────────────────────────────────────────────────────────────┐   │
 │   │ 228 Transpiled Tabular Ensemble Predictor                      │   │
 │   │     • Nested C++ conditional trees (LightGBM)                  │   │
 │   │     • Compact forward-pass matrix multiplication (MLP)         │   │
 │   │     • Autoregressive history ridge blend                       │   │
 │   │     • Execution footprint: 2.97 MB Flash, 19.9 KB RAM          │   │
 │   │     • Numerical parity error < 0.00013 vs 64-bit IEEE float    │   │
 │   └───────────────────────────────┬────────────────────────────────┘   │
 │                                   ▼
 │   ┌────────────────────────────────────────────────────────────────┐   │
 │   │ 230 Embedded PRNG Monte Carlo Engine                           │   │
 │   │     • indra_xorshift64star_boxmuller_v1 integer RNG            │   │
 │   │     • 2,048 draws per family directly on chip                  │   │
 │   └───────────────────────────────┬────────────────────────────────┘   │
 │                                   ▼
 │   ┌────────────────────────────────────────────────────────────────┐   │
 │   │ 232 Serial JSON Emitter                                        │   │
 │   │     • Streams structured telemetry response                    │   │
 │   │     • Outputs build_sha256, model_sha256, scenario_config_sha  │   │
 │   └────────────────────────────────────────────────────────────────┘   │
 └────────────────────────────────────────────────────────────────────────┘
```

---

```
                                  FIG. 3
            25-HOUR SLIDING WINDOW CAUSAL FEATURE DERIVATION

 Observation Horizon: 24 Hours Elapsed | 25 Exact Hourly Readings
 ────────────────────────────────────────────────────────────────────────► Time (t)
   [t-24h] [t-23h]  ...  [t-12h]  ...  [t-6h]  ...  [t-3h]  [t-1h]   [t]
     │       │             │             │            │       │       │
     └───────┴─────────────┴─────────────┴────────────┴───────┴───────┤
                                                                      │
                                                       Buffer of 25 Hourly Vectors
                                                       (T, RH, P, PM2.5, PM10, W)
                                                                      │
                                                                      ▼
 ┌────────────────────────────────────────────────────────────────────────────────┐
 │ 300 Causal Feature Derivation (Exactly 66 Features)                            │
 │                                                                                │
 │ 1. Raw Telemetry at Time t (6 Features):                                       │
 │    • T(t), RH(t), P(t), PM2.5(t), PM10(t), W(t)                                │
 │                                                                                │
 │ 2. Multi-Horizon Lag Deltas (30 Features = 6 channels × 5 horizons):           │
 │    • Δ_1h  = x(t) - x(t-1h)                                                    │
 │    • Δ_3h  = x(t) - x(t-3h)                                                    │
 │    • Δ_6h  = x(t) - x(t-6h)                                                    │
 │    • Δ_12h = x(t) - x(t-12h)                                                   │
 │    • Δ_24h = x(t) - x(t-24h)                                                   │
 │                                                                                │
 │ 3. First-Order Rate of Change (6 Features):                                    │
 │    • dx/dt = (x(t) - x(t-1h)) / 1.0 hour                                       │
 │                                                                                │
 │ 4. Rolling Statistical Window Moments (24 Features = 6 channels × 2 stats × 2):│
 │    • 6-Hour Rolling Window:                                                    │
 │        - Mean_6h = (1/6) Σ x(t-k) for k=0..5                                   │
 │        - Std_6h  = sqrt( (1/6) Σ (x(t-k) - Mean_6h)^2 )                        │
 │    • 24-Hour Rolling Window:                                                   │
 │        - Mean_24h = (1/24) Σ x(t-k) for k=0..23                                │
 │        - Std_24h  = sqrt( (1/24) Σ (x(t-k) - Mean_24h)^2 )                     │
 │                                                                                │
 │ Total Feature Dimension = 6 + 30 + 6 + 24 = 66 Strictly Causal Features        │
 └────────────────────────────────────────────────────────────────────────────────┘
```

---

```
                                  FIG. 4
               MULTI-MODEL TABULAR ENSEMBLE ARCHITECTURE

                 ┌─────────────────────────────────────────┐
                 │ 400 66-Dimensional Causal Feature Vector│
                 └────────────────────┬────────────────────┘
                                      │ Broadcast to Candidate Models
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
 ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
 │ 410 LightGBM    │         │ 420 Residual    │         │ 430 Autoregress │
 │     Boosted Tree│         │     MLP Neural  │         │     Hybrid (XGB │
 │     Ensemble    │         │     Network     │         │     + Ridge)    │
 └────────┬────────┘         └────────┬────────┘         └────────┬────────┘
          │ ŷ_LGB                     │ ŷ_MLP                     │ ŷ_HYB
          └───────────────────────────┼───────────────────────────┘
                                      │
                                      ▼
                 ┌─────────────────────────────────────────┐
                 │ 440 Fallback Persistence Head (ŷ_PER)   │
                 │     • Inactive when History = 25 Rows   │
                 │     • Active when History < 25 Rows     │
                 └────────────────────┬────────────────────┘
                                      │
                                      ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 450 Non-Negative Convex Simplex Optimization Engine                    │
 │                                                                        │
 │   Objective Formulation:                                               │
 │     min_{w} (1/N) Σ | w_LGB*ŷ_LGB + w_MLP*ŷ_MLP + w_HYB*ŷ_HYB - y |     │
 │                                                                        │
 │   Constraints:                                                         │
 │     w_LGB + w_MLP + w_HYB + w_PER = 1.0                                │
 │     w_i ≥ 0 for all i ∈ {LGB, MLP, HYB, PER}                           │
 │                                                                        │
 │   Solved via High-Performance Simplex (HiGHS LP)                       │
 │   Independently optimized for each of the 6 physical target channels   │
 └────────────────────────────────────┬───────────────────────────────────┘
                                      │ Optimal Convex Blend
                                      ▼
                 ┌─────────────────────────────────────────┐
                 │ 460 +6-Hour Future Numerical Forecast   │
                 │     [T, RH, P, PM2.5, PM10, W] at t+6h  │
                 └─────────────────────────────────────────┘
```

---

```
                                  FIG. 5
               TRI-FAMILY MONTE CARLO HAZARD SIMULATOR

 ┌────────────────────────────────────────────────────────────────────────┐
 │ 500 Real-Time 6-Channel Sliding Observation Vector                     │
 │     • Features: T, RH, P, PM2.5, PM10, W, ΔT, ΔP_6h, ΔW                │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 510 Empirical Liquid-Phase Atmospheric Rain Coupling Function          │
 │                                                                        │
 │   S_rain = σ( β0 + β_rh*(RH-70)/20 + β_p*(-ΔP6/3) + β_w*(W/10)        │
 │              + β_t*(-ΔT/3) ) * σ( (T - T_liquid) / s_liquid )          │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ Coupling Strength S_rain
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 520 Stochastic Precipitation Rate Generator                            │
 │     • Generates 12 half-hour rainfall rates R(t) in mm/h               │
 │     • Driven by seed and pseudo-random normal draws                    │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ Synthetic 6-Hour Rain Hydrograph
          ┌──────────────────────────┼──────────────────────────┐
          ▼                          ▼                          ▼
 ┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
 │ 530 Cloudburst   │       │ 540 Flash Flood  │       │ 550 Landslide    │
 │     Threshold    │       │     Runoff Model │       │     Trigger      │
 │                  │       │                  │       │                  │
 │   Evaluate:      │       │   Rational Method│       │   Power-Law ID:  │
 │   max(R) ≥ 100   │       │   Q = (1/3.6)*C* │       │   I_crit =       │
 │   mm/hour        │       │       I * A      │       │   α * D^(-γ)     │
 │                  │       │   Q ≥ Q_capacity │       │   Trigger on     │
 │                  │       │   (accounting    │       │   susceptible    │
 │                  │       │   for soil/store)│       │   terrain        │
 └────────┬─────────┘       └────────┬─────────┘       └────────┬─────────┘
          │                          │                          │
          └──────────────────────────┼──────────────────────────┘
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 560 Tri-Family Latent Parameter Regime Sensitivity Engine              │
 │     (Evaluated across N ≥ 2,048 draws per family)                      │
 │                                                                        │
 │   Regime A: "Drier Case"                                               │
 │     • Low rainfall scaling, maximum soil storage, low slope risk       │
 │   Regime B: "Central Case"                                             │
 │     • Median parameters representing baseline assumed catchment        │
 │   Regime C: "Wetter Case"                                              │
 │     • High rainfall scaling, saturated soil storage, high slope risk   │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 570 Output Fraction Reporting & Provenance Manifest                    │
 │     • Reports outcome percentages for each regime                      │
 │     • Emits config_sha256, deterministic seed, draw count              │
 │     • Attaches field_validated=false and calibrated=false disclaimers  │
 └────────────────────────────────────────────────────────────────────────┘
```

---

```
                                  FIG. 6
         CRYPTOGRAPHIC PROVENANCE & DOMAIN-SEPARATED MERKLE ENGINE

 ┌────────────────────────────────────────────────────────────────────────┐
 │ 600 Transactional SQLite Audit Event Journal (indra_audit_json_v1)    │
 │                                                                        │
 │   Sequence 1:  [0x00...00] ──► SHA256(Body_1) ──► EventHash_1         │
 │   Sequence 2:  [EventHash_1] ──► SHA256(Body_2) ──► EventHash_2       │
 │   Sequence 3:  [EventHash_2] ──► SHA256(Body_3) ──► EventHash_3       │
 │   ...                                                                  │
 │   Sequence M:  [EventHash_M-1] ──► SHA256(Body_M) ──► EventHash_M     │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 610 Canonical RFC 8785 JSON Serializer                                 │
 │     • Deterministic key ordering, no extraneous whitespace             │
 │     • Finite numbers only (rejection of NaN and Infinite values)       │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 620 Domain-Separated Merkle Tree Builder                               │
 │                                                                        │
 │                         [ Merkle Root ]                                │
 │                                │                                       │
 │              ┌─────────────────┴─────────────────┐                     │
 │        [Branch Hash L1]                    [Branch Hash L2]            │
 │        = SHA256( 0x01 ||                   = SHA256( 0x01 ||           │
 │           Leaf0 || Leaf1 )                    Leaf2 || Leaf3 )         │
 │              │                                   │                     │
 │       ┌──────┴──────┐                     ┌──────┴──────┐              │
 │    [Leaf 0]      [Leaf 1]              [Leaf 2]      [Leaf 3]          │
 │    = SHA256(     = SHA256(             = SHA256(     = SHA256(         │
 │      0x00 ||       0x00 ||               0x00 ||       0x00 ||         │
 │      Hash_1 )      Hash_2 )              Hash_3 )      Hash_4 )        │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 630 Batch Manifest & Digital Signature Generator                      │
 │     • batch_id = SHA256(manifest_json)                                 │
 │     • Ed25519 Elliptic Curve Signature over batch_id                   │
 │     • Ready for On-Chain Publication                                   │
 └────────────────────────────────────────────────────────────────────────┘
```

---

```
                                  FIG. 7
         DISTRIBUTED LEDGER SMART CONTRACT (IndraAnchor.sol)

                Transaction Submitted: anchor(batchId, root)
                                      │
                                      ▼
                      ┌───────────────────────────────┐
                      │ 700 msg.sender == owner?      │
                      └───────────────┬───────────────┘
                                      │
                         Yes ─────────┴───────── No
                          │                       │
                          ▼                       ▼
          ┌───────────────────────────────┐   ┌───────────────────────────┐
          │ 710 root != bytes32(0)?       │   │ Revert: "Unauthorized"   │
          └───────────────┬───────────────┘   └───────────────────────────┘
                          │
             Yes ─────────┴───────── No
              │                       │
              ▼                       ▼
┌───────────────────────────────┐   ┌───────────────────────────┐
│ 720 roots[batchId] == 0?      │   │ Revert: "Empty root"      │
│ (Replay Prevention)           │   └───────────────────────────┘
└───────────────┬───────────────┘
                │
   Yes ─────────┴───────── No
    │                       │
    ▼                       ▼
┌───────────────────────────────┐   ┌───────────────────────────┐
│ 730 Record State:             │   │ Revert: "Duplicate batch" │
│ roots[batchId] = root         │   └───────────────────────────┘
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ 740 Emit Event:               │
│ emit Anchored(batchId, root)  │
└───────────────────────────────┘
```

---

```
                                  FIG. 8
            SPATIAL IDW SURFACE GENERATION WITH CARDINALITY GUARD

                      Incoming Spatial Heatmap Request
                                      │
                                      ▼
                      ┌───────────────────────────────┐
                      │ 800 Retrieve Active Nodes     │
                      └───────────────┬───────────────┘
                                      │
                                      ▼
                      ┌───────────────────────────────┐
                      │ 810 Node Count K ≥ 3?         │
                      └───────────────┬───────────────┘
                                      │
                         Yes ─────────┴───────── No
                          │                       │
                          ▼                       │
          ┌───────────────────────────────┐       │
          │ 820 Nodes Non-Collinear?      │       │
          └───────────────┬───────────────┘       │
                          │                       │
             Yes ─────────┴───────── No           │
              │                       │           │
              ▼                       └─────► ┌───┴───────────────────────┐
┌───────────────────────────────┐             │ 830 Multi-Node Guard      │
│ 840 Continuous 2D Inverse     │             │     Triggered             │
│     Distance Weighting (IDW)  │             │ • Suppress 2D Heatmap     │
│ • Compute grid weights:       │             │ • Emit Discrete Point(s)  │
│   w_i = 1 / d(x, x_i)^p       │             │ • Return Explanatory Data │
│ • Interpolate parameter values│             │   Constraint Reason       │
│ • Construct GeoJSON Polygons  │             └───────────────────────────┘
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ 850 Return Multi-Layer Heatmap│
│     GeoJSON to Client Map     │
└───────────────────────────────┘
```

