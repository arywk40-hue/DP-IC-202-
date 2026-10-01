# INDRA Six-Sensor Forecast Model

Train, test and export a six-hour environmental forecast model for ESP32-S3.
Inputs: **temperature, relative humidity, pressure, PM2.5, PM10 and wind speed**.
Outputs: the same six measurements, forecast six hours ahead.

## Required release: all six inputs

The deployment requirement is temperature, humidity, **station-level pressure**,
PM2.5, PM10 and wind. The existing five-/two-input Indian experiments do not
meet that requirement and are not the default ESP32 build. The original six-input
Beijing model is the only complete six-input trained baseline currently retained.

[Official IMD northern data access findings](data/imd_north_access/README.md)
record the downloaded station catalogue, actual API responses, and the historical
observations still needed before six-input Indian training/testing can run.

## Indian reduced-input experiments (not the required six-input release)

Two research candidates now use the available Indian measurements:

| Family | Sensors used | Evidence |
|---|---|---|
| `india_cpcb_5sensor_6h` | Temperature, humidity, PM2.5, PM10, wind | Improves all five future-time MAEs over matched Beijing student; Baddi humidity regresses |
| `india_cpcb_pm_6h` | PM2.5, PM10 | PM-only student does not beat matched Beijing student; PM2.5 falls back to persistence |

Pressure is excluded because the Indian source units are unresolved. Baddi is
held out entirely; there is no Mandi field validation. Profiles are selected
subsets of the six funded channels, with no invented measurements.

Read [Indian results and reproduction commands](ml/evaluation/INDIA_RESULTS.md).
The original six-input model remains unchanged; model comparisons also retain
explicitly named five-input and two-input Beijing baselines.

## Original six-input baseline and dataset

The original baseline model family is **`uci_beijing_6h`**, trained on
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
ml/models/                       Named Beijing/Indian profiles and reports
ml/evaluation/                   Paired Indian and Baddi test results
esp32/model_test/                 Isolated ESP32-S3 forecast test
tests/                           Pipeline, model artifact and C parity tests
.github/workflows/ci.yml          Python checks and ESP32 build
```

See [model files and target names](ml/models/uci_beijing_6h/README.md),
[dataset details](data/uci_beijing_air_quality/README.md), and
[architecture/results](ARCHITECTURE.md).

An [Indian station coverage audit](data/india_station_audit/README.md) now
records seven downloaded station samples and their missing-input/unit issues.
The Indian research profiles exclude unresolved channels and document their
remaining source assumptions.

Two newer [Delhi station exports](data/india_delhi_station_samples/README.md)
are retained locally with a reproducible audit in Git. The raw CSVs are
excluded from Git. Jahangirpuri has
simultaneous values for all six channels in many 15-minute rows, but its
pressure header conflicts with its numeric values; CRRI Mathura Road lacks all
four weather channels in this export. Neither is approved for six-input
training or Mandi validation until source units, pressure reference, time and
quality checks are resolved.

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

## ESP32-S3 forecast and event integration

[ML integration firmware and board test](esp32/ml_integration/README.md) runs
both retained models, computes event features from seven hourly snapshots,
and verifies serial replay against Python reference predictions. Both UART
and native-USB build targets are provided. This stage uses serial inputs;
LoRa transport and live sensor drivers remain separate integration work.

## Prototype readiness and field validation

[Readiness guide](docs/PROTOTYPE_READINESS.md) documents synchronized,
history-aware heatmaps (both strategies), verified event inference, independent
field evaluation and chronological calibration. The supplied Himachal files
and newly downloaded official rainfall source have reproducible coverage audits.
Field deployment remains gated on complete local measurements, independent
positive and negative event labels, spatial validation and physical testing.
See [model inputs and outputs](docs/MODEL_INPUTS_AND_OUTPUTS.md) for the exact
six-channel and event-score contracts.
