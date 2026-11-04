# INDRA Machine Learning Model Evaluation & Real-Data Forecast Report

**Date of Evaluation:** 5 November 2026  
**Active Model:** `india_mandi_tabular_v2` (SHA-256: `79eae97fa522973e69db6b8ef825e849534e26060c00f132d4fe6b9482486fc6`)  
**Geographic Target:** Mandi, Himachal Pradesh (31.71° N, 76.93° E)  
**Data Sources:** Open-Meteo ECMWF IFS (0.1° grid) & Copernicus CAMS Global (0.4° grid)  
**Evaluation Cohorts:** 720 continuous hourly observations (2026-09-25 00:00 UTC to 2026-10-24 23:00 UTC)  

---

## 1. Executive Summary

This report delivers a rigorous retrospective evaluation of INDRA's six-channel tabular forecast ensemble and experimental hazard simulation engine using real atmospheric and particulate telemetry from Mandi, Himachal Pradesh.

### Key Highlights:
- **Consistent Superiority over Persistence:** The `india_mandi_tabular_v2` model outperforms persistence across all six channels, achieving **50.2% to 82.8% MAE skill improvements** on the untouched 5-day holdout archive (120 test pairs).
- **Sub-1.3 °C Temperature Error:** Forecast temperature MAE reached **1.27 °C** with an $R^2$ correlation of **0.914**.
- **Pressure Stability:** Surface pressure MAE reached **0.68 hPa** ($R^2 = 0.853$), critical for micro-barometric altimetry and orographic pressure drop detection.
- **Embedded C++ Hardware Parity:** The C++ standalone runtime running on the ESP32-S3 microcontroller matches 64-bit Python reference models with a maximum absolute difference of $< 0.00013$.
- **Explicit Hazard Modeling Boundaries:** Hazard scenario outputs are confirmed as assumption-conditioned Monte Carlo simulation fractions, properly tagged with `field_validated: false`, `calibrated: false`, and without automated public warnings.

---

## 2. Six-Channel Forecast Evaluation on Real Data

### 2.1 Untouched 5-Day Holdout Cohort (120 Prediction Pairs)
- **Issue Window:** 2026-10-19 18:00 UTC to 2026-10-24 17:00 UTC
- **Target Horizon:** 2026-10-20 00:00 UTC to 2026-10-24 23:00 UTC (+6 hours)
- **Constraint:** Zero weights were fitted, tuned, or updated on these target dates.

| Target Channel | Model MAE | RMSE | $R^2$ Score | Persistence MAE | MAE Skill vs Persistence |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Temperature (°C)** | **1.2725** | 1.7205 | **0.9141** | 7.4017 | **+82.8%** |
| **Relative Humidity (%)** | **7.0331** | 10.2582 | **0.7829** | 26.8250 | **+73.8%** |
| **Surface Pressure (hPa)** | **0.6751** | 0.8422 | **0.8532** | 1.9833 | **+66.0%** |
| **PM2.5 (µg/m³)** | **5.2287** | 7.0095 | **0.4977** | 11.3242 | **+53.8%** |
| **PM10 (µg/m³)** | **6.0862** | 8.2392 | **0.4328** | 12.2167 | **+50.2%** |
| **Wind Speed (m/s)** | **0.3189** | 0.4339 | **0.3069** | 0.6468 | **+50.7%** |

---

### 2.2 Full 30-Day Evaluation Cohort (690 Prediction Pairs)
- **Issue Window:** 2026-09-26 00:00 UTC to 2026-10-24 17:00 UTC
- **Target Horizon:** 2026-09-26 06:00 UTC to 2026-10-24 23:00 UTC (+6 hours)
- **Exclusions:** 24 rows without ready 24h history; 6 rows without completed +6h target labels.

| Target Channel | Model MAE | RMSE | $R^2$ Score | Persistence MAE | MAE Skill vs Persistence |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Temperature (°C)** | **1.5087** | 2.0037 | **0.8556** | 5.8629 | **+74.3%** |
| **Relative Humidity (%)** | **7.3611** | 9.9695 | **0.7470** | 22.4638 | **+67.2%** |
| **Surface Pressure (hPa)** | **0.9513** | 1.2214 | **0.7999** | 1.9077 | **+50.1%** |
| **PM2.5 (µg/m³)** | **5.7096** | 7.5480 | **0.6849** | 9.5978 | **+40.5%** |
| **PM10 (µg/m³)** | **7.4676** | 9.8642 | **0.6719** | 12.0165 | **+37.9%** |
| **Wind Speed (m/s)** | **0.3244** | 0.4149 | **0.3083** | 0.5754 | **+43.6%** |

---

## 3. Real-Data Himalayan Hazard & Hydrological Simulation

The Monte Carlo hazard simulation engine ([`ml/himachal/hazard_scenarios.py`](../../ml/himachal/hazard_scenarios.py)) was executed over 2,048 stochastic iterations using real atmospheric vectors from Mandi.

### Coupling Mechanism:
Precipitation intensity is coupled to atmospheric pressure drops ($\Delta P_6$), relative humidity, and surface cooling using the liquid-phase sigmoid function:
$$S_{rain} = \sigma\left(\beta_0 + \beta_{rh} \frac{RH - 70}{20} + \beta_p \left(\frac{-\Delta P_6}{3}\right) + \beta_w \left(\frac{W}{10}\right) + \beta_t \left(\frac{-\Delta T}{3}\right)\right) \times \sigma\left(\frac{T - 1.5}{1.0}\right)$$

### Tri-Family Simulation Outcomes:
| Hazard Target | Model & Equation | Drier Assumptions | Central Assumptions | Wetter Assumptions |
| :--- | :--- | :---: | :---: | :---: |
| **Cloudburst** | Rainfall rate $\ge 100\text{ mm/h}$ | 0.0488% | 0.0977% | 0.6836% |
| **Flash Flood** | Rational Method $Q = \frac{1}{3.6} C I A \ge Q_{cap}$ | 0.1465% | 1.8555% | 10.7422% |
| **Landslide** | Intensity-Duration $I_{crit} = 73.9 \cdot D^{-0.79}$ | 0.1465% | 1.5137% | 5.9082% |

*Interpretation:* The percentages above represent the fraction of 2,048 stochastic simulations where thresholds were exceeded under the stated hydrological assumptions. They illustrate physical sensitivity to unobserved soil moisture and drainage capacity; they are **not calibrated real-event probabilities or public alarms**.

---

## 4. Embedded ESP32-S3 C++ Edge Runtime Parity

The compiled firmware ([`esp32/ml_integration/src/mandi_v2_main.cpp`](../../esp32/ml_integration/src/mandi_v2_main.cpp)) was validated against the 64-bit Python reference pipeline across 8 historical windows and 32 pattern episodes:

| Check | Metric | Result | Status |
| :--- | :--- | :---: | :---: |
| **Forecast Numerical Parity** | Max Absolute Error across 6 channels | `0.00012030` | **PASSED** |
| **Pattern Score Parity** | Max Absolute Error across 10 classes | `0.00000003` | **PASSED** |
| **Monte Carlo RNG Repetition** | Deterministic seed repeat (4 cases) | Identical | **PASSED** |
| **Flash Partition Footprint** | App size / Partition capacity | 2.97 MB / 3.34 MB | **PASSED (Fits N8 DevKit)** |
| **Static RAM Footprint** | Static variables / 320 KB SRAM | 19.9 KB / 327 KB | **PASSED (< 7% SRAM)** |

---

## 5. Testing & Verification Runbook for Tomorrow

Use the following step-by-step commands to test and demonstrate the ML and dashboard systems tomorrow:

### A. Run Core ML Unit & Contract Tests:
```sh
# 1. Test feature engineering, hazard scenarios, and ensemble weights
.venv/bin/python -m pytest ml/tests/test_hazard_scenarios.py ml/tests/test_mandi_tabular_v2.py -v

# 2. Test dashboard integration and mock feed handling
.venv/bin/python -m pytest server/tests/test_dashboard_integration.py -v
```

### B. Reproduce the Real Mandi Model Evaluation:
```sh
.venv/bin/python ml/scripts/evaluate_mandi_snapshot.py \
  --input ml/data/himachal/mandi_api/2026-09-25_2026-10-24 \
  --output ml/reports/mandi_live_check/2026-11-05
```

### C. Launch the Live Production Dashboard:
```sh
# Start production service with 1-click demo auth enabled for local testing
.venv/bin/python server/scripts/deploy_production.py --port 8080 --enable-demo-auth
```
- Open **http://127.0.0.1:8080**
- Test the **Observations View** (Live gauges, 24h history sparklines, +6h forecast, hazard scenarios).
- Test the **API Explorer** (`/#apis`) (Execute live REST calls against `/api/nodes`, `/api/status`, `/api/parameter-heatmaps`).
- Test the **Data & System View** (`/#system`) (Inspect Model Lab blend weights, retrospective performance, and the cryptographic audit trail).

### D. Verify ESP32-S3 Model Parity:
```sh
MPLCONFIGDIR=/tmp/indra-mpl .venv/bin/python esp32/ml_integration/tools/test_mandi_v2_parity.py
```

