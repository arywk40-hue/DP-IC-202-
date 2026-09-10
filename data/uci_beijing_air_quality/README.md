# Training dataset: UCI Beijing Multi-Site Air Quality (501)

All models in `ml/models/uci_beijing_6h/` use this dataset.

- Source: https://archive.ics.uci.edu/dataset/501/beijing
- Citation: Chen, S. (2017). Beijing Multi-Site Air Quality. UCI Machine Learning Repository.
- DOI: https://doi.org/10.24432/C5RK5G
- License: Creative Commons Attribution 4.0 (CC BY 4.0).
- Coverage: 420,768 hourly rows, 12 Beijing stations, March 2013–February 2017.
- Input fields retained: temperature, relative humidity, pressure, PM2.5, PM10, wind speed.
- Humidity: derived using the Magnus relation from observed temperature and dew point.
- Targets: observed values of the same six measurements exactly six hours later.
- Station/time: metadata for causal alignment and holdout splitting only.
- Missing readings: remain unknown; no future filling or synthetic sensor readings.
- Geography: Beijing benchmark; not India field validation or verified hazard-event labels.

| File | Purpose | In Git? |
|---|---|---|
| `dataset_manifest.json` | Source hash, processed data hash, license, dates, columns and missing counts | Yes |
| `source.zip` | Complete pinned original UCI archive | No; downloadable |
| `observations.csv` | Adapted six-channel station-hour observations | No; regenerated |

From the repository root, run `python3 -m ml.six_sensor_forecast.data` to download
and rebuild the observations. The downloader verifies the original archive
checksum. `training_report.json` in the model directory contains a copy of the
manifest from the actual training run, plus exact split and fitted row counts.
