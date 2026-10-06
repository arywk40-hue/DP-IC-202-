# INDRA weather mesh

**Confidential: do not publish before IP review.**

Start with [the project overview](docs/PROJECT_OVERVIEW.md): what was built, measured results and losses, requirements, limitations and next steps.

[Documentation index](docs/README.md) · [Full inventory and move manifest](DOC_INVENTORY.md).

This is a research prototype for IIT Mandi. Two-node field reliability and ESP32 spatial inference remain unverified.

Latest software work: [offline completion report](reports/offline_phase/REPORT.md), [full metrics and losses](reports/offline_phase/RESULTS.md), [commands](ml/india_sensor/README.md). Disaster outputs are disabled; physical deployment is unvalidated.

```sh
python3 -m pytest -q
# Synthetic same-node forecast from committed India weights; no raw data needed.
python3 -m ml.india_sensor.predict --config configs/india_sensor_offline.json --model-dir ml/models/india_sensor_v1 --input esp32/india_sensor/example_hourly.csv
# Existing synthetic two-node current-weather interpolation.
python3 -m reports.practicum.demo --input reports/two_node_phase/examples/readings.json
# New ESP32 research smoke firmware: compile only.
pio run -d esp32/india_sensor
```

Python dependencies: `requirements-india-sensor.txt` for the measured India run; older spatial/CI environments retain their own pins.

Current additive phase: [independent Indian hazard-label audit](docs/hazard_label_audit.md), [ERA5 context report](reports/hazard_context_phase/REPORT.md), [commands](ml/hazard_context/README.md). Sensor-only results stay frozen; real ERA5 access and admissible event/negative data remain missing. Disaster outputs stay disabled.
