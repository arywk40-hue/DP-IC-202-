# India Data Adapter

This directory contains the adapter for the real India weather/air-quality
export used by the project. The source spreadsheets are not checked into the
repository.

## Expected inputs

Place these four files in a local input directory:

```text
Location_information.xlsx
Weather_data.xlsx
Air_quality_information.xlsx
Astronomical.xlsx
```

Each file must contain a unique `last_updated_epoch` column. The merger joins
the files on that key; it does not assume that rows are in the same order.

The weather and air-quality exports must provide at least:

```text
location_name
last_updated
temperature_celsius
humidity
pressure_mb
wind_kph
air_quality_PM2.5
air_quality_PM10
air_quality_Carbon_Monoxide
air_quality_Ozone
air_quality_Nitrogen_dioxide
air_quality_Sulphur_dioxide
```

If available, `latitude` and `longitude` are preserved for geographic holdout
and spatial analysis.

## Build the India dataset

```bash
cd ml/real_india_data
python3 merge_real_dataset.py \
  --input-dir /path/to/india_exports \
  --output real_weather_india.csv

# For the Open-Meteo pilot, if Python cannot locate the system CA bundle:
python3 download_weather_pilot.py \
  --locations locations_26_cities.csv \
  --start 2015-01-01 --end 2020-07-01 \
  --output ../data_india_pilot/weather_26_cities.csv \
  --ca-file /etc/ssl/cert.pem

python3 prepare_dataset_real.py \
  --input real_weather_india.csv \
  --output ../data_india/
```

The prepared output contains `features.csv`, `labels.csv`, `identifiers.csv`,
`dataset.csv`, and `metadata.json`. `identifiers.csv` must remain row-aligned
with `features.csv` and `labels.csv`; it is required for time- and
location-aware evaluation.

## Current limitations

- CO2 and lightning distance remain synthetic until matching sensor/event data
  is supplied.
- The current four hazard labels are weak heuristic labels, not verified event
  records.
- The source described by the existing metadata covers 543 locations from
  Aug–Oct 2023, which is a useful India integration test but not yet a large,
  multi-season India training set.

Before production training, add longer time coverage and independently sourced
event labels, then create chronological and held-out-location splits.

## IndiaWeatherBench scale-up adapter

The national weather-backbone stage uses the IndiaWeatherBench HDF5 release.
The archive is large, so begin with a bounded directory containing a few HDF5
timesteps and validate the extraction before processing the full train split:

```bash
python3 prepare_indiaweatherbench.py \
  --input-dir /path/to/indiaweatherbench_h5/train \
  --locations locations_26_cities.csv \
  --max-files 16 \
  --output ../data_india_weatherbench_slice/
```

This writes `weather_context.csv` and a `manifest.json` containing input file
hashes, time coverage, grid shape, units, license, and source provenance. The
adapter extracts nearest grid cells for the configured locations and does not
create wildfire, flood, storm, or air-quality labels. Join independently sourced
event/station labels before hazard training; weather-only rows are suitable for
the offline weather teacher and context-feature extraction.

The offline teacher can be smoke-tested on the current 26-city weather table:

```bash
python3 train_weather_teacher.py \
  --input ../data_india_pilot/weather_26_cities.csv \
  --output ../model_india_weather_teacher \
  --cutoff 2019-01-01
```

For the larger evaluation, use `--split-strategy geo-temporal`; it holds out
complete locations as well as future dates:

```bash
python3 train_weather_teacher.py \
  --input ../data_india_pilot/weather_56_cities.csv \
  --output ../model_india_weather_teacher_56_geo_temporal \
  --cutoff 2019-01-01 \
  --split-strategy geo-temporal
```

For hazard retraining, use `events.template.csv` as the contract for an
independent event source and join it with:

```bash
python3 join_independent_events.py \
  --weather ../data_india_weatherbench_slice/weather_context.csv \
  --events /path/to/verified_events.csv \
  --output ../data_india_weatherbench_labeled/
```

Every source must declare its coverage window. Weather rows outside that window
remain unknown; they are never silently converted into negative labels.

The weather downloader supports `--cache-dir`, `--retries`, and
`--continue-on-error` so long multi-city runs can resume without repeating
successful API requests. The checked-in 56-city expansion uses
`locations_56_cities.csv`.

The weather-context handoff can be reproduced with
`add_weather_teacher_context.py`, followed by `build_offline_features.py` and
`train_india_pilot.py`. The resulting context teacher is not edge-exportable;
use `distill_air_quality.py --teacher-data ...` to transfer its air-quality
head back to the 14-feature student.

When an OpenAQ API key is available, collect station observations without
committing the secret:

```bash
export OPENAQ_API_KEY='provided-outside-the-repository'
python3 download_openaq_days.py \
  --start 2015-01-01 --end 2020-07-01 \
  --max-locations 100 \
  --output ../data_india_pilot/raw/openaq_india_days.csv
```

The output remains long-form and includes sensor IDs, parameter units, and
observed/expected coverage counts. It is not a hazard-label file.

The official IMD storm-label path is:

```bash
python3 prepare_imd_storm_events.py \
  --workbook ../data_india_pilot/raw/imd_best_tracks_1982_2026.xlsx \
  --locations locations_26_cities.csv \
  --output ../data_india_pilot/raw/imd_storm_events_2015_2020.csv \
  --years 2015 2016 2017 2018 2019 2020

python3 join_independent_events.py \
  --weather ../data_india_pilot/real_weather_india_26.csv \
  --events ../data_india_pilot/raw/imd_storm_events_2015_2020.csv \
  --output ../data_india_pilot/imd_storm_labeled_26
```

The current slice has only nine positive city-days, so it is a validation of
the label pipeline rather than a deployable storm training set.

The public OpenAQ S3 archive can be downloaded without an API key:

```bash
python3 download_openaq_s3_days.py \
  --location-id 8118 \
  --start 2020-01-01 --end 2020-12-31 \
  --cache-dir /tmp/openaq_8118_2020 \
  --output ../data_india_pilot/raw/openaq_8118_2020.csv \
  --ca-file /etc/ssl/cert.pem

python3 join_openaq_weather.py \
  --air-quality ../data_india_pilot/raw/openaq_8118_2020.csv \
  --weather ../data_india_pilot/weather_26_cities.csv \
  --location-name Delhi \
  --output ../data_india_pilot/openaq_delhi_weather_2020.csv
```

The next-day PM2.5 teacher is trained with
`train_verified_aq_teacher.py`; current output is intentionally a one-station
validation artifact, not a national model.
