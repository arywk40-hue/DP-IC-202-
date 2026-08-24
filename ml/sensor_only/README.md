# INDRA Sensor-Only Retraining

This pipeline defines the model that can eventually run on the approved INDRA
hardware:

- BME280
- PMS7003
- 600-PPR wind encoder
- Neo-M8N GPS
- DS3231 RTC
- INA219 for telemetry and power health only

CO2 and lightning features are forbidden. PM1, PM10, altitude, voltage,
current, and power remain telemetry fields but are not hazard-model inputs.

## 1. Build the Feature Matrix

Run from the repository root:

```bash
python3 -m ml.sensor_only.prepare_dataset \
  --prepared ml/data_india_pilot/prepared_26 \
  --output ml/data_sensor_only_v1
```

The builder uses only trailing history for pressure trend, drops the first
row of each location where a trend cannot be calculated, converts humidity to
percent and wind from km/h to m/s, and writes the exact schema order to
`metadata.json`.

## 2. Weak-Label Integration Baseline

The existing `prepared_26/labels.csv` is not independent ground truth. Its
storm and air-quality labels include synthetic lightning or CO2 dependencies.
The trainer therefore refuses those labels unless the limitation is explicitly
accepted:

```bash
python3 -m ml.sensor_only.train_model \
  --data ml/data_sensor_only_v1 \
  --output ml/model_sensor_only_v1_weak \
  --allow-weak-labels
```

This run tests pipeline integration only. Its precision, recall, F1, PR-AUC,
and Brier scores are not valid INDRA sensor-only performance claims. The model
manifest remains `NOT_READY`.

## 3. Valid Retraining

Replace the weak labels with independently sourced event labels aligned to the
same rows. Update `metadata.json` with documented label provenance, coverage,
and per-hazard masks. Train without `--allow-weak-labels`. A head with only one
class in train, validation, or geographic test is automatically blocked.

The split policy is:

- earlier rows from development locations: training;
- later rows from development locations: threshold calibration;
- complete unseen locations: final geographic test.

## 4. Firmware Export

Export is blocked while the model manifest is `NOT_READY`:

```bash
python3 -m ml.sensor_only.export_model \
  --model ml/model_sensor_only_v1 \
  --output ml/generated/model_data_sensor_only_v1.h
```

`--allow-not-ready` exists only for compile and integration testing. A generated
header is not promoted to `firmware/` until label provenance, geographic
testing, Python/C parity, and on-device tests pass.

