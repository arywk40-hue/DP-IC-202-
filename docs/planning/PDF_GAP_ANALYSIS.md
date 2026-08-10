# PDF Gap Analysis — Implementation vs Specification

**Date:** August 2026  
**Author:** Ariyan Bhakat  
**PDFs analysed:**
- `tinyml_esp32_architecture_report.pdf` — ML subsystem specification
- `implementation/dp_202.pdf` — IEEE-format architecture and feasibility paper

This document compares every concrete requirement stated in the two PDFs against the
current state of the repository. Each row describes what the spec requires, what exists
today, and what action (if any) is needed before the item can be signed off.

---

## Legend

| Status | Meaning |
|--------|---------|
| ✅ Done | Implemented and matches the spec |
| ⚠️ Partial | Implemented but diverges from spec in a meaningful way |
| ❌ Missing | Spec requirement exists; no implementation present |

---

## 1. ML Subsystem (`tinyml_esp32_architecture_report.pdf`)

### 1.1 Input Feature Vector

| Requirement | Current Status | Gap / Notes | Action |
|-------------|----------------|-------------|--------|
| **22-element input vector** (11 absolute + 11 delta values) | ⚠️ Partial | Firmware and ML pipeline use **14 features** — 7 raw sensor values + 7 derived (heat index, dew point, fire/flood risk, etc.). The PDF specifies a 22-element vector with an absolute+delta scheme where each sensor contributes its current value **and** its change from the previous cycle. | Extend `compute_derived_features()` in `main.c` and `prepare_dataset.py` to add 7 delta features (prev-cycle values from RTC memory) and rename the 22-feature contract throughout. |
| **Min-max normalisation** with per-feature training-time min/max constants | ⚠️ Partial | Code uses **z-score (mean/std)** normalisation instead. PDF explicitly requires min-max with clamping to [0, 1] and a division-by-zero guard. | Replace z-score with min-max in `train_model.py`, `convert_to_c.py` (`normalize_features()`), `normalization.h`, and `ml.c`. |
| **RTC memory persistence** of previous feature vector across deep-sleep cycles | ❌ Missing | No `RTC_DATA_ATTR` variables or RTC save/restore logic exists anywhere in `main.c` or the sensor pipeline. | Add `RTC_DATA_ATTR static float g_prev_features[11]` and populate delta features on wake. |
| Delta features computed as `Δᵢ = xᵢ(t) − xᵢ(t−1)` | ❌ Missing | No delta computation exists; the 14-feature pipeline only uses current-cycle readings. | Implement alongside RTC persistence above. |
| Feature clamping to [0, 1] after scaling | ❌ Missing | No clamp in `normalize_features()`. | Add `fmaxf(0.0f, fminf(1.0f, ...))` after normalisation. |
| Validity flag per feature; unavailable values mapped to explicit safe constant (not silent zero) | ⚠️ Partial | `sensor_mask` bits are set/cleared correctly per sensor. However `compute_derived_features()` does not check `reading.sensor_mask` before using sensor values — a failed BME280 silently supplies 0.0°C to the model. | Gate each feature on its `SENSOR_MASK_*` bit; substitute the training-time mean or a documented safe constant when the bit is clear. |

### 1.2 Classification Schema

| Requirement | Current Status | Gap / Notes | Action |
|-------------|----------------|-------------|--------|
| **5 output classes**: Normal, Rain, Thunderstorm, High PM2.5, Radiation Spike | ⚠️ Partial | Current implementation uses **4 classes**: wildfire, flood, storm, air_quality. Missing "Normal" as an explicit output class, and "Rain" / "Radiation Spike" are not represented. "Wildfire" is not in the PDF class list. | Reconcile class schema. The most defensible path: keep wildfire (it is supported by the hardware and the dp_202.pdf use-case narrative) but add Normal as class 0 to match the PDF. Rain and Radiation Spike require the corresponding sensors (pluviometer counts, BPW34) to be wired up. Until hardware supports them, document the difference explicitly. |
| Binary sigmoid output per class | ✅ Done | `ml_confidence()` applies sigmoid; `ml_predict()` returns raw log-odds. Matches spec. | — |
| Inference result struct: `{anomaly_class, confidence, valid_features}` | ⚠️ Partial | `main.c` calls `ml_predict()` and `ml_confidence()` inline; there is no `InferenceResult` struct as specified. `valid_features` (sensor validity mask) is not included in the alert payload. | Define `inference_result_t` matching the PDF interface and populate `valid_features` from `reading.sensor_mask`. |
| Inference must not directly transmit packets or operate the radio | ✅ Done | `ml_predict()` returns a float; all transmission is done in `mesh_comms_task`. Correct separation. | — |
| **F1 score ≥ 0.88** (macro, all classes) | ❌ Missing | No trained model metrics exist in the repo (no `metrics.json`, no confusion matrix). `model_data.h` is the pre-generated export from synthetic/proxy data. | Run `train_model.py` on a real labelled dataset, measure macro-F1, and commit `metrics.json` + confusion matrix image. |

### 1.3 Dataset Design

| Requirement | Current Status | Gap / Notes | Action |
|-------------|----------------|-------------|--------|
| **≥ 500 labelled samples** covering all anomaly classes | ⚠️ Partial | `dataset/weatherHistory.csv` (16 MB, ~96k rows of historical Kaggle weather data) is used as a proxy. It has no radiation/acoustic columns, no explicit event labels, and no node-level metadata. | Collect real field data per the Stage 1/Stage 2 protocol in `docs/guides/DATA_COLLECTION.md` (to be created, Prompt 17 in PROJECT_STATUS). |
| Record format: `node_id, timestamp, raw sensors, prev-cycle readings, delta features, battery voltage, sensor validity flags, label` | ❌ Missing | `prepare_dataset.py` produces only current-cycle features with rule-based labels. No node_id, no timestamp, no prev-cycle readings, no battery voltage, no validity flags in the output schema. | Add these columns to `prepare_dataset.py` output and `train_model.py` input ingestion. |
| Event-based train/val split (not random row split) | ❌ Missing | `train_model.py` uses `train_test_split(random_state=42)`. Adjacent samples from the same event can leak across the split boundary. | Replace random split with time- or event-based split grouping. |
| Separate validation set grouped by event and time period | ❌ Missing | Same as above — no event grouping in the split. | Implement alongside event-based split. |
| Labels from human-verified external evidence (rain gauge, calibrated reference, lightning observation) | ❌ Missing | Labels in `prepare_dataset.py` are generated algorithmically from threshold rules on the same features used for inference. | Requires real data collection and human annotation. |
| Pre-event / event / recovery windows in dataset | ❌ Missing | Not implemented — rule-based labels fire only at the peak threshold. | Implement with a time-windowing step in `prepare_dataset.py`. |

### 1.4 Model Export and Deployment Bundle

| Requirement | Current Status | Gap / Notes | Action |
|-------------|----------------|-------------|--------|
| Export bundle = model + feature order + scaling constants + class map + missing-value policy + version number | ⚠️ Partial | `convert_to_c.py` exports trees, mean/std, feature names, and class names. Missing: min-max constants (used by spec), missing-value policy (substitution values), and a version field. | Add min-max constants and a `MODEL_VERSION` `#define` to `model_data.h`; document missing-value policy in `model_metadata.h`. |
| **Python-vs-firmware equivalence test** on identical serialised input vectors | ❌ Missing | No equivalence test exists. Acceptance test M2–M4 define the criteria but the test harness is not implemented. | Implement a comparison script: read a test corpus through Python `predict_proba`, serialise the normalised vectors, feed through firmware, assert outputs match within 1e-4. |
| Inference time < 15 ms (per the PDF estimate; firmware doc says < 100 µs for 4 classes) | ✅ Done | `ml_last_inference_us()` measures elapsed time; spec target is ~15 ms, firmware claims ~50 µs (well under). Acceptance test M7 validates this. | — |

### 1.5 Embedded Inference Interface

| Requirement | Current Status | Gap / Notes | Action |
|-------------|----------------|-------------|--------|
| `run_inference(const float features[22])` returns `InferenceResult` | ⚠️ Partial | `ml_predict(features, class_id, &output)` exists but takes 14 features and returns a single float per class. Does not match the PDF's proposed API (22-element input, struct output, single call for all classes). | Define the PDF interface as a wrapper in `ml.h`/`ml.c` so external callers see the specified API while the underlying 14-feature model is called internally. |
| Rule-based fallback until model meets recall requirements | ❌ Missing | No fallback; if `ml_init()` fails the firmware simply disables inference with a warning. | Add a threshold-based fallback in `sensor_ml_task` that fires alerts based on raw sensor thresholds when `g_initialized == false`. |

---

## 2. System Architecture (`implementation/dp_202.pdf`)

### 2.1 Sensor Array

| Requirement | Current Status | Gap / Notes | Action |
|-------------|----------------|-------------|--------|
| **12-parameter sensor suite** matching Table I of the paper | ✅ Done | All 11 drivers (BME280, PMS5003, DS18B20, Anemometer, SEN0575, LTR390, SCD41, SGP41, MICS6814, AS3935, Battery) implemented. Paper lists 12 parameters — battery ADC counts as the 12th. | — |
| Sequential sensor acquisition with power gating for high-power peripherals | ⚠️ Partial | Sensors are read sequentially in `sensor_ml_task`. There is no GPIO power-gating logic — PMS5003 and MICS6814 (high warm-up current) are always powered. | Add GPIO power-gate lines and `gpio_set_level()` calls around the PMS5003 and MICS6814 read sequence. Not blocking for prototype stage. |
| ULP coprocessor for continuous low-power sensor polling | ❌ Missing | Firmware uses a 60s FreeRTOS `vTaskDelay`. The paper and spec both call for ULP polling so the main cores sleep between events. | Deferred to post-prototype. Not blocking for two-node baseline. |

### 2.2 Firmware Architecture

| Requirement | Current Status | Gap / Notes | Action |
|-------------|----------------|-------------|--------|
| Three FreeRTOS tasks: Sensor (Core 0), Mesh (Core 1), Monitor (Core 1) | ⚠️ Partial | Two tasks created: `sensor_ml_task` (Core 0) and `mesh_comms_task` (Core 1). The Monitor task (periodic status reporting, battery monitoring, mesh stats) is handled inline inside `app_main()`'s while-loop rather than as a dedicated task. | Low priority — current approach works. Optional to split out. |
| `sensor_pipeline.c/.h` Hardware Abstraction Layer for all 12 sensors | ⚠️ Partial | Sensor HAL exists as individual component drivers under `firmware/components/sensors/`. The paper names `sensor_pipeline.c/.h` but the repo uses per-sensor files. Functionally equivalent. | Document the naming difference in `docs/reference/FIRMWARE_API.md`. |
| ML pipeline file named `ml_pipeline.c/.h` | ⚠️ Partial | Implemented as `firmware/components/ml/src/ml.c` and `include/ml.h`. Functionally correct; file name differs from the paper. | Cosmetic — no action required. |
| Mesh module named `mesh_comm.c/.h` | ⚠️ Partial | Implemented as `firmware/components/mesh/src/mesh.c` and `include/mesh.h`. | Cosmetic — no action required. |

### 2.3 Communication Layer

| Requirement | Current Status | Gap / Notes | Action |
|-------------|----------------|-------------|--------|
| SX1276/RFM95W at 865 MHz ISM band | ✅ Done | `sx1276_config_t` sets `frequency = 865000000`. | — |
| Multi-hop mesh routing | ✅ Done | TTL-based flooding with `MESH_DEFAULT_TTL=5`, duplicate suppression, and forwarding in `mesh.c`. | — |
| Packet types: alerts, heartbeats, sensor data, model updates | ⚠️ Partial | Alerts (`MESH_FLAG_ALERT`) and heartbeats are implemented. Raw sensor data packets and model update packets (for federated learning) are not. | Federated learning is out of scope for prototype stage. Document as future work. |
| ~10 km range in mountainous terrain | ❌ Missing | Not validated — no range test has been run. Target RSSI and SNR margins are defined in `LORA_BRINGUP.md`. | Requires bring-up test (Prompt 12 / Acceptance tests N7–N12). |

### 2.4 Edge AI Decision Flow

| Requirement | Current Status | Gap / Notes | Action |
|-------------|----------------|-------------|--------|
| ULP threshold breach wakes main cores for inference | ❌ Missing | As noted above, ULP not implemented. | Deferred. |
| AI gate controls transmission decision (no raw telemetry) | ✅ Done | `sensor_ml_task` only queues an alert packet when `confidence >= threshold`. No raw sensor data is transmitted over LoRa. | — |
| Per-class confidence thresholds (configurable) | ✅ Done | `ALERT_THRESHOLD_WILDFIRE=0.70`, `ALERT_THRESHOLD_FLOOD=0.70`, `ALERT_THRESHOLD_STORM=0.75`, `ALERT_THRESHOLD_AIR_QUALITY=0.65`. | — |

### 2.5 Power Architecture

| Requirement | Current Status | Gap / Notes | Action |
|-------------|----------------|-------------|--------|
| 18650 + 5W solar + CN3065 charge controller | ✅ Done (BOM) | Components in BOM; firmware monitors battery voltage via `battery.c`. | — |
| 5–7 day autonomy with solar recharge | ❌ Missing | Not validated. Acceptance test P8 defines the calculation target. | Requires power measurement (Prompt 19). |
| Deep-sleep between polls | ❌ Missing | `sensor_ml_task` uses `vTaskDelay(60s)`. Full deep-sleep with wake timer not implemented. | Required for autonomy target. Add `esp_deep_sleep_start()` path after alert queue drain. |

### 2.6 Security

| Requirement | Current Status | Gap / Notes | Action |
|-------------|----------------|-------------|--------|
| AES-128-GCM end-to-end encryption | ✅ Done | `crypto.c` implements AES-128-GCM via mbedTLS. | — |
| NVS key provisioning with auto-generate | ✅ Done | `key_provisioning.c` handles NVS storage, auto-generation, and key rotation. | — |
| `crypto_derive_session_key()` uses real HKDF | ⚠️ Partial | **Placeholder comment in `crypto.c` line ~98**: "This is a placeholder - production should use proper HKDF." Currently uses AES-CMAC. | Replace with `mbedtls_hkdf` (available in ESP-IDF mbedTLS). This is Prompt 14 in PROJECT_STATUS. |

### 2.7 OTA Update

| Requirement | Current Status | Gap / Notes | Action |
|-------------|----------------|-------------|--------|
| `idf.py ota` boots new firmware and preserves NVS (Acceptance test I4) | ❌ Missing | `firmware/partitions.csv` has only a single `factory` app slot — no `ota_0`/`ota_1`. OTA cannot function. | Redesign partition table with two OTA slots + implement `esp_ota_ops` update flow. This is Prompt 13 in PROJECT_STATUS. |

---

## 3. Summary Counts

| Category | ✅ Done | ⚠️ Partial | ❌ Missing |
|----------|---------|-----------|----------|
| ML — Feature vector | 1 | 2 | 3 |
| ML — Classification | 2 | 2 | 1 |
| ML — Dataset | 0 | 1 | 5 |
| ML — Export bundle | 1 | 1 | 1 |
| ML — Inference interface | 0 | 1 | 1 |
| System — Sensors | 1 | 1 | 1 |
| System — Firmware arch | 0 | 4 | 0 |
| System — Comms | 2 | 2 | 1 |
| System — Power | 1 | 0 | 2 |
| System — Security | 2 | 1 | 0 |
| System — OTA | 0 | 0 | 1 |
| **Total** | **10** | **15** | **16** |

---

## 4. Priority Gaps (Blocking for Baseline Sign-off)

The following gaps must be resolved before the two-node prototype can be signed off
against the acceptance criteria in `docs/planning/ACCEPTANCE_TESTS.md`:

1. **22-feature vector + delta features + RTC persistence** — the deployed model and the
   spec are misaligned on the input contract. This affects every ML acceptance test (M1–M8).
2. **Min-max normalisation** — the spec requires min-max; the repo uses z-score. Mismatched
   normalisation means the Python-vs-firmware equivalence test will fail.
3. **Event-based train/val split** — random row splits leak adjacent samples; reported F1
   will be artificially high and will not hold in field deployment.
4. **OTA partition table** — without `ota_0`/`ota_1`, acceptance test I4 cannot pass.
5. **HKDF key derivation** — acknowledged placeholder in `crypto.c`; production deployment
   must fix this before the security architecture is considered complete.
6. **LoRa range validation** — acceptance tests N7–N12 are completely unsigned; no bring-up
   has been run yet.

---

## 5. Non-Blocking Gaps (Document and Defer)

- ULP coprocessor polling (complex; not required for 2-node prototype)
- GPIO power gating for PMS5003 / MICS6814 (useful for battery life; not blocking)
- Radiation Spike and Rain explicit classes (requires BPW34 + pluviometer hardware)
- Federated learning / model-update packet type (Month 4+ scope)
- Deep-sleep implementation (needed for P8 autonomy test, not for functional sign-off)
- Monitor task as separate FreeRTOS task (current inline approach is functionally equivalent)

---

*Generated from full read of both PDFs and the complete repository source, August 2026.*
