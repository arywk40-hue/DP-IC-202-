# INDRA Six-Sensor Forecast Model

Train, test and export a six-hour environmental forecast model for ESP32-S3.
Inputs: **temperature, relative humidity, pressure, PM2.5, PM10 and wind speed**.
Outputs: the same six measurements, forecast six hours ahead.

## Trained model and dataset

The retained model family is **`uci_beijing_6h`**, trained on
[UCI Beijing Multi-Site Air Quality (501)](https://doi.org/10.24432/C5RK5G):
420,768 hourly observations, 12 stations, March 2013–February 2017, CC BY 4.0.
After splitting and missing-value filtering, each head uses 216,849–219,194
training rows. Humidity is derived from temperature/dew point in this source;
the model itself accepts only the six listed inputs.

| Model directory | Purpose | Architecture | Training data |
|---|---|---|---|
| [teacher](ml/models/uci_beijing_6h/teacher/) | Offline accuracy benchmark and student training | Six temporal XGBoost heads, 66 features derived from six sensor channels | UCI Beijing 501 |
| [esp32_student](ml/models/uci_beijing_6h/esp32_student/) | Compact model exported to ESP32 | Six XGBoost heads, six current inputs, 16 trees/head, depth 3 | UCI Beijing 501, with teacher-assisted targets |

Both beat persistence MAE on all six targets in the future-time and held-out
station tests. This is a research measurement forecast, not validated
storm/flood detection or India field performance. ESP32 compilation and host
C parity passed; physical flashing is pending a connected board.

## Repository layout

```text
ARCHITECTURE.md                  Architecture, measured results and limitations
requirements.txt                 Tested Python dependency versions
data/uci_beijing_air_quality/     Dataset description and provenance manifest
ml/six_sensor_forecast/           Download, features, training, inference, C export
ml/models/uci_beijing_6h/          Trained teacher/student heads and reports
esp32/model_test/                 Isolated ESP32-S3 forecast test
tests/                           Pipeline, model artifact and C parity tests
.github/workflows/ci.yml          Python checks and ESP32 build
```

See [model files and target names](ml/models/uci_beijing_6h/README.md),
[dataset details](data/uci_beijing_air_quality/README.md), and
[architecture/results](ARCHITECTURE.md).

## Run from the repository root

Python 3.11 or newer and a C compiler are required for host tests/export.

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests

# Download the pinned dataset, train, and verify the C export:
python3 -m ml.six_sensor_forecast.data
python3 -m ml.six_sensor_forecast.train
python3 -m ml.six_sensor_forecast.export

# Run the saved compact model:
python3 -m ml.six_sensor_forecast.predict --input data/uci_beijing_air_quality/observations.csv --kind student --output /tmp/indra_forecasts.csv

# Build the isolated board test (requires PlatformIO):
pio run -d esp32/model_test
```

Download/train commands are optional when using the retained trained artifacts.
The raw ZIP and observation CSV are local, Git-ignored files; the provenance
manifest and trained models are retained in the repository. Board upload
instructions are in [esp32/model_test/README.md](esp32/model_test/README.md).
