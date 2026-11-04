# INDRA Research Atmospheric Hazard Scenarios & Mandi API Evaluation Report
**Date of Verification**: 2026-11-05  
**Evaluation Scope**: Real Mandi ECMWF/CAMS Observation Dataset, IMD Cloudburst Threshold Vectors, Western Disturbance Snowstorm Vectors, and Monsoon Rain Burst Deluge Vectors  
**Model Under Test**: `india_mandi_tabular_v2` (SHA256 Profile: `79eae97fa522...`)  
**Hazard Simulators**: `himalayan_synthetic_scenarios_v1`, `himachal_sensor_patterns_v1`  
**Test Suite**: [`ml/tests/test_research_scenarios.py`](file:///Users/ariyanbhakat/Desktop/Dp-indra-six-sensor/ml/tests/test_research_scenarios.py) (4/4 Passed in 2.75s)  
**Artifact Data**: [`ml/reports/research_hazards_and_mandi_api_evaluation.json`](file:///Users/ariyanbhakat/Desktop/Dp-indra-six-sensor/ml/reports/research_hazards_and_mandi_api_evaluation.json)

---

## 1. Executive Summary

This report establishes the verified performance and sensitivity of the INDRA environmental intelligence stack across two critical domains:
1. **Real-world Mandi Observation Dataset Inference**: Feeding actual hourly Open-Meteo ECMWF IFS / CAMS Global grid observations from Mandi, Himachal Pradesh (31.71° N, 76.93° E) directly into the production `india_mandi_tabular_v2` model. The model generates physically coherent +6h forecasts reflecting realistic diurnal mountain boundary layer dynamics (morning radiative heating, relative humidity decline, and stable mountain valley air quality).
2. **Research-Grounded Hazard Scenarios**: Evaluating the synthetic sensor-pattern classifier and Monte Carlo hazard simulator against published literature vectors for **Cloudbursts**, **Snowstorms / Blizzards**, and **Rain Bursts**. The engines demonstrate high pattern sensitivity (pattern scores $> 0.99$) and physically correct latent simulation behavior (sub-zero blizzard conditions suppress liquid runoff, while convective cloudburst conditions produce elevated flash-flood and landslide trigger fractions).

> [!IMPORTANT]
> **Truth-in-Advertising & Safety Notice**:
> In strict accordance with platform ethics and regulatory guidelines:
> - The 720-hour Mandi observation archive is modeled grid data (Open-Meteo ECMWF IFS / CAMS Global), not physical station readings.
> - The hazard simulations represent unweighted, conditional Monte Carlo fractions derived from documented engineering priors. They are intended for decision-support stress testing and do **not** constitute official IMD weather alerts or real event probabilities.

---

## 2. Research Grounding & Published Literature Citations

The synthetic test vectors are constructed strictly based on established atmospheric research and meteorological literature:

| Scenario | Published Research Basis | Key Documented Meteorological Signature |
| :--- | :--- | :--- |
| **Cloudburst** | **Singh & Thapliyal (2022)**, *MAUSAM*, 73(1): 100 mm/h convective threshold; **Das et al. (2020)** | Pre-storm barometric plunge ($\Delta P_{6\text{h}} \le -3.0\text{ hPa}$, $\Delta P_{1\text{h}} \le -1.5\text{ hPa}$), extreme saturation ($RH \ge 90\%$), severe downdraft cooling ($\Delta T_{1\text{h}} \le -2.0^\circ\text{C}$), gale gust ($W \ge 10-15\text{ m/s}$), aerosol scavenging ($-\Delta \text{PM}_{2.5} \ge 10\text{ }\mu\text{g/m}^3$). |
| **Snowstorm / Blizzard** | **Shekhar et al. (2010)**, *Cold Reg. Sci. Tech.*; **Dimri et al. (2015)**, *Rev. Geophys.* (Western Disturbances) | Sub-zero ambient temperature ($T \le 0^\circ\text{C}$, e.g. $-5.0^\circ\text{C}$), high relative humidity ($RH \ge 85-95\%$), deep synoptic barometric trough ($\Delta P_{6\text{h}} \le -6.0\text{ hPa}$), sustained blizzard winds ($W \ge 10-15\text{ m/s}$). |
| **Rain Burst / Deluge** | **IMD Heavy Rain Criteria**; **Bhan et al. (2015)** | Warm saturated monsoon boundary layer ($T \approx 20^\circ\text{C}$, $RH \ge 90\%$), rapid convective cooling ($\Delta T \le -3.0^\circ\text{C}$), barometric fall ($\Delta P_{6\text{h}} \le -3.0\text{ hPa}$), sustained downpour, particulate washout. |
| **Landslide Trigger** | **Dahal & Hasegawa (2008)**, *Geomorphology* ($I = 73.90 \cdot D^{-0.79}$) | Empirical intensity-duration rainfall exceedance threshold transferred from Nepal Himalaya for steep mountain slopes. |
| **Flash Flood** | **TxDOT Rational Method**; **WMO Flash Flood Guidance (FFG)** | Rational runoff conversion: $Q = \frac{1}{3.6} \cdot C \cdot I \cdot A$ exceedance over catchment capacity. |

---

## 3. Real Mandi API Live Observation Evaluation

The production `india_mandi_tabular_v2` model was evaluated on the untouched archive of Mandi hourly observations ([`observations.csv`](file:///Users/ariyanbhakat/Desktop/Dp-indra-six-sensor/ml/data/himachal/mandi_api/2026-09-25_2026-10-24/observations.csv)).

### Observation Snapshot & +6h Model Prediction

* **Current Observed UTC**: `2026-10-24 23:00:00+00:00` (04:30 AM IST, Autumn pre-dawn)
* **Forecast Valid UTC**: `2026-10-25 05:00:00+00:00` (10:30 AM IST, Autumn morning)
* **Inference Engine**: `india_mandi_tabular_v2` (Status: `HYBRID_READY`)

| Meteorological Channel | Current Observed | +6h Forecast | Delta ($\Delta$) | Physical Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **Temperature ($T$)** | **11.40 °C** | **21.59 °C** | **+10.19 °C** | Rapid solar insolation post-sunrise in Beas valley |
| **Relative Humidity ($RH$)** | **90.00 %** | **50.66 %** | **-39.34 %** | Strong diurnal drying as mountain air warms |
| **Barometric Pressure ($P$)** | **926.70 hPa** | **929.77 hPa** | **+3.07 hPa** | Post-dawn semi-diurnal atmospheric tidal rise |
| **Particulate Matter ($PM_{2.5}$)** | **10.90 µg/m³** | **7.76 µg/m³** | **-3.14 µg/m³** | Boundary layer deepening diluting valley particulates |
| **Particulate Matter ($PM_{10}$)** | **11.30 µg/m³** | **10.94 µg/m³** | **-0.36 µg/m³** | Stable background coarse aerosol concentrations |
| **Surface Wind Speed ($W$)** | **1.27 m/s** | **1.14 m/s** | **-0.13 m/s** | Calm valley drainage winds |

### Mandi Live Vector Pattern & Hazard Output

* **Weather Categories**: Normal mild autumn valley profile (all storm pattern scores $< 0.10$).
* **Simulated Hazard Fractions**:
  * **Drier Catchment Family**: Cloudburst 0.05%, Flash Flood 0.15%, Landslide 0.49%
  * **Central Catchment Family**: Cloudburst 0.24%, Flash Flood 2.34%, Landslide 2.10%
  * **Wetter Catchment Family**: Cloudburst 0.93%, Flash Flood 12.21%, Landslide 7.13%

---

## 4. Cloudburst Research Vector Evaluation

### Research Vector Trajectory (Singh & Thapliyal 2022)
* **6h History**: Moistening ($70\% \rightarrow 94\%$), pressure gradual drop ($930.0 \rightarrow 927.5\text{ hPa}$).
* **Hour 7 (Current Signature)**: $T = 17.5^\circ\text{C}$ (cooling downdraft $\Delta T_{1\text{h}} = -2.5^\circ\text{C}$), $RH = 96\%$, $P = 925.0\text{ hPa}$ (pressure plunge $\Delta P_{1\text{h}} = -2.5\text{ hPa}$, $\Delta P_{6\text{h}} = -5.0\text{ hPa}$), Wind $= 14.5\text{ m/s}$, PM rain scavenging ($PM_{2.5} = 10.0\text{ }\mu\text{g/m}^3, PM_{10} = 16.0\text{ }\mu\text{g/m}^3$).

### Pattern Classification Results
* **`cloudburst_like` Score**: **`0.99998`** (Threshold: `0.6500`) $\rightarrow$ **MATCHED (`True`)**
* **`rain` Score**: **`0.9944`** (Threshold: `0.3500`) $\rightarrow$ **MATCHED (`True`)**
* Non-storm categories (`dust_storm`, `heatwave`, `wildfire`): **`0.0000`**

### Monte Carlo Latent Hazard Fractions (2,048 draws)
* **Drier Sensitivity Family**: Cloudburst **3.08%**, Flash Flood **10.06%**, Landslide **7.28%**
* **Central Sensitivity Family**: Cloudburst **11.38%**, Flash Flood **40.23%**, Landslide **27.05%**
* **Wetter Sensitivity Family**: Cloudburst **26.90%**, Flash Flood **73.97%**, Landslide **52.25%**

---

## 5. Snowstorm / Himalayan Blizzard Research Vector Evaluation

### Research Vector Trajectory (Shekhar et al. 2010)
* **6h History**: Sub-zero temperature progression ($-1.0^\circ\text{C} \rightarrow -4.0^\circ\text{C}$), high humidity ($82\% \rightarrow 92\%$), barometric drop ($880.0 \rightarrow 877.0\text{ hPa}$).
* **Hour 7 (Current Signature)**: $T = -5.0^\circ\text{C}$ (sub-zero freeze), $RH = 94\%$, $P = 874.0\text{ hPa}$ ($\Delta P_{6\text{h}} = -6.0\text{ hPa}$ deep Western Disturbance trough), Wind $= 13.5\text{ m/s}$ (blizzard gale), $PM_{2.5} = 8.0\text{ }\mu\text{g/m}^3, PM_{10} = 12.0\text{ }\mu\text{g/m}^3$.

### Pattern Classification Results
* **`snowstorm` Score**: **`0.9999`** (Threshold: `0.6500`) $\rightarrow$ **MATCHED (`True`)**
* **`rain` Score**: **`0.0006`** $\rightarrow$ Suppressed (`False`)
* Other categories: **`0.0000`**

### Monte Carlo Latent Hazard Fractions (Liquid Phase Physics Check)
* **Central Sensitivity Family**: Cloudburst **0.05%**, Flash Flood **0.15%**, Landslide **0.10%**
* **Physical Sanity Verification**: Because ambient temperature is $-5.0^\circ\text{C}$, the liquid-phase function ($\text{expit}((T - 1)/2)$) correctly evaluates near zero ($\approx 0.047$). Sub-zero solid precipitation does **not** generate immediate liquid rational runoff or rain-induced landslide failure, confirming the physical consistency of the simulator.

---

## 6. Rain Burst / Monsoon Deluge Research Vector Evaluation

### Research Vector Trajectory (IMD Heavy Rainfall Criteria)
* **6h History**: Warm monsoon boundary layer ($24.0^\circ\text{C}$), humidity $78\% \rightarrow 88\%$, pressure $928.0 \rightarrow 925.6\text{ hPa}$.
* **Hour 7 (Current Signature)**: $T = 20.0^\circ\text{C}$ (rapid downdraft $\Delta T_{1\text{h}} = -4.0^\circ\text{C}$), $RH = 92\%$, $P = 924.4\text{ hPa}$ ($\Delta P_{6\text{h}} = -3.6\text{ hPa}$ monsoon trough), Wind $= 11.5\text{ m/s}$ (gusty monsoon surge), $PM_{2.5} = 12.0\text{ }\mu\text{g/m}^3, PM_{10} = 18.0\text{ }\mu\text{g/m}^3$ (rainout).

### Pattern Classification Results
* **`rainstorm` Score**: **`0.9993`** (Threshold: `0.6500`) $\rightarrow$ **MATCHED (`True`)**
* **`rain` Score**: **`0.9928`** (Threshold: `0.3500`) $\rightarrow$ **MATCHED (`True`)**
* Non-rain categories: **`0.0000`**

### Monte Carlo Latent Hazard Fractions (2,048 draws)
* **Drier Sensitivity Family**: Cloudburst **1.12%**, Flash Flood **4.74%**, Landslide **4.44%**
* **Central Sensitivity Family**: Cloudburst **5.52%**, Flash Flood **25.49%**, Landslide **19.34%**
* **Wetter Sensitivity Family**: Cloudburst **14.94%**, Flash Flood **59.18%**, Landslide **40.53%**

---

## 7. Comparative Synthesis Table

| Scenario Vector | Primary Pattern Match | Category Score | Central Cloudburst Fraction | Central Flash-Flood Fraction | Central Landslide Fraction |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Mandi Live API (Calm)** | None (Normal) | $< 0.10$ | 0.24 % | 2.34 % | 2.10 % |
| **Cloudburst (IMD Threshold)** | `cloudburst_like` | **0.99998** | **11.38 %** | **40.23 %** | **27.05 %** |
| **Snowstorm (Western Disturbance)** | `snowstorm` | **0.9999** | 0.05 % *(liquid-suppressed)* | 0.15 % *(liquid-suppressed)* | 0.10 % *(liquid-suppressed)* |
| **Rain Burst (Monsoon Deluge)** | `rainstorm` + `rain` | **0.9993** | **5.52 %** | **25.49 %** | **19.34 %** |

---

## 8. CLI Reproduction & Verification Commands

To re-run these tests tomorrow or in CI/CD:

```bash
# 1. Run the dedicated research scenario & Mandi live API unit tests
.venv/bin/python -m pytest ml/tests/test_research_scenarios.py -v

# 2. Run the full evaluation script and regenerate the JSON artifact
.venv/bin/python ml/scripts/test_research_hazards_and_mandi.py

# 3. Inspect the structured JSON output
.venv/bin/python -m json.tool ml/reports/research_hazards_and_mandi_api_evaluation.json | head -n 40
```

