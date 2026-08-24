# India Data Expansion Plan

## Recommended source stack

### 1. Weather backbone: IndiaWeatherBench / IMDAA

Use IndiaWeatherBench for large-scale India weather representation learning and
offline forecasting experiments. Its published repository provides raw and
preprocessed archives, including a 216 GB dataset, and the benchmark describes
high-resolution IMDAA-based regional weather fields.

This is not an ESP32 input dataset. It is a dense grid with many atmospheric
channels. Use it to learn or extract weather context, then distill that context
into the small edge feature vector.

Source:

```text
https://huggingface.co/datasets/tungnd/IndiaWeatherBench
https://github.com/tung-nd/IndiaWeatherBench
```

The published dataset is CC BY-NC-SA 4.0. Keep its license and attribution in
the dataset manifest before using it in a distributed product.

### 2. Air quality: OpenAQ and India OGD/CPCB data

Use OpenAQ for timestamped station measurements and the India Open Government
Data/CPCB catalog for government-published historical station data. These can
provide PM2.5, PM10, NO2, SO2, CO, O3, temperature, and humidity where a station
reports them.

Sources:

```text
https://docs.openaq.org/
https://www.data.gov.in/catalog/historical-daily-ambient-air-quality-data
```

For a reproducible pilot when an OpenAQ key or CPCB bulk export is not yet
available, use the published **Air Quality Data in India (2015–2020)** dataset
as an explicitly secondary source. It contains hourly and daily station data
across 26 Indian cities, including PM2.5, PM10, AQI, and other pollutants:

```text
https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india
```

The pilot must record this source separately from government/first-party data,
retain the original `City` and `Date` fields, and never treat its AQI-derived
labels as equivalent to independently verified hazard events.

Do not assume OpenAQ covers every Indian station or that all providers have the
same calibration and continuity. Store provider, station, parameter, unit, and
license metadata for every observation.

The current OpenAQ v3 API requires an API key for requests. The repository must
therefore accept the key through an environment variable or a local secret
store; it must never be committed with the dataset. OpenAQ's daily/hourly
resources expose coverage information, which should be retained when deciding
whether an unobserved day is unknown or a valid negative label.

For bounded historical pulls, OpenAQ also publishes a no-credential S3 archive
partitioned by location, year, month, and day. The repository adapter
`download_openaq_s3_days.py` uses that archive and retains the raw sensor
metadata before joining it to weather.

Source: `https://docs.openaq.org/aws/about`

### 3. Storm labels: IMD best-track records

For the storm head, use the India Meteorological Department / RSMC New Delhi
best-track archive rather than a weather-derived storm rule. The archive lists
annual best-track records, including 2015–2020, and the IMD API documents a
cyclone-track endpoint. Convert each track point into an event interval and
join it to locations using a documented radius; do not label a city positive
merely because a cyclone existed somewhere in the basin.

Sources:

```text
https://rsmcnewdelhi.imd.gov.in/report.php?internal_menu=MzM
https://api.imd.gov.in/public/api_reference.html
```

The current repository run also retains the official workbook at
`ml/data_india_pilot/raw/imd_best_tracks_1982_2026.xlsx`; its 2015–2020 sheets
were converted into city-level event intervals and evaluated separately from
the heuristic storm labels.

### 4. Event labels: IMD warnings and verified records

Weather fields alone do not create trustworthy hazard labels. For a production
comparison, join observations to independently defined event records:

- IMD severe-weather warnings and bulletins for storm/heavy-rain events;
- flood occurrence records for flood labels;
- wildfire/fire occurrence records for wildfire labels;
- measured PM2.5 exceedance windows for air-quality labels.

Threshold-derived labels may remain as a weak-label experiment, but must be
reported separately from independently sourced event labels.

## Two-stream architecture

```text
IndiaWeatherBench / ERA5 grid ------------------+
                                                  |
                                    spatial/time alignment
                                                  v
OpenAQ / CPCB station AQ ------------------> canonical hourly table
                                                  |
                              event label + quality/provenance joins
                                                  v
                         offline teacher / feature extraction
                                                  |
                                      edge-compatible features
                                                  v
                                  four hazard heads + calibration
```

The weather grid and air-quality station data should not be blindly concatenated
by row. Align by UTC time and location, with an explicit spatial policy:

1. nearest grid cell within a documented radius;
2. or bilinear interpolation for continuous weather variables;
3. station aggregation only after recording the number of contributing
   observations and coverage;
4. reject matches outside the time tolerance rather than forward-filling across
   long gaps.

## Staged use of the large data

### Scale-up A: cheap integration slice

Start with a small, reproducible slice before touching the full 216 GB archive:

- one monsoon and one dry-season period;
- a bounded India region or a fixed set of cities/stations;
- only the surface variables needed by the current model;
- a fixed train/validation/future-test time range.

The output must satisfy the existing canonical schema and produce an
`identifiers.csv` file with location and timestamp. This validates ingestion,
alignment, missingness, and label construction.

The first practical pilot is therefore:

1. download the 26-city air-quality dataset;
2. query the Open-Meteo historical weather API for the same city coordinates
   and date range;
3. join on `(city, UTC date)` and retain source/provenance columns;
4. train/evaluate the air-quality head first;
5. do not fabricate storm, flood, or wildfire event labels from this join.

### Scale-up B: full offline weather representation

Train an offline teacher on the larger weather grid. Candidate targets are
next-hour to next-24-hour temperature, pressure, wind, and precipitation. Use
the teacher to produce compact, location/time-aligned context features or a
distilled edge model.

### Scale-up C: hazard fine-tuning

Fine-tune the four hazard heads using event-labeled station/time windows. Keep
the weather-only teacher score and the edge model score as separate baselines.
Do not claim that a weather reconstruction metric proves hazard-alert quality.

## Minimum manifest for every downloaded source

```json
{
  "source_name": "",
  "source_url": "",
  "retrieved_at_utc": "",
  "coverage_start_utc": "",
  "coverage_end_utc": "",
  "spatial_extent": "",
  "variables": [],
  "units": {},
  "license": "",
  "sha256": "",
  "processing_script": "",
  "synthetic_fields": [],
  "label_provenance": ""
}
```

## Decision for this repository

The first independent flood source now available in the workspace is the
India Flood Inventory-Impacts v3 (IIT Delhi/IMD, 1967–2023). Its raw file is
`ml/data_india_pilot/raw/India_Flood_Inventory_v3.csv`. Because many records
are state-level and many district names are text-only, the adapter records an
explicit city/district-token policy and leaves non-matching weather rows
unknown. It must be evaluated as a regional/district event source until a
geospatial district join is added.

For wildfire, the next source to ingest is the Forest Survey of India Large
Forest Fire archival search (`https://fsiforestfire.gov.in/LargeforestFire/ArchivalData`).
The FSI/NRSC fire-monitoring products are satellite detections, so the adapter
must keep detection date, coordinates, sensor, confidence, and forest/agri
classification. A hotspot is an observed fire signal, not automatically a
wildfire event; the future join should use a spatial forest mask and a
multi-detection/event-window rule, with unmatched weather rows left unknown.

Keep the existing XGBoost four-head model as the edge target. Use the large
India weather archive for offline context/pretraining, not as a reason to put a
large neural network on the ESP32. Promote a new edge model only when it passes
the same 14-feature/schema, geographic holdout, calibration, and Python/C
parity gates documented in `INDIA_WEATHER_ARCHITECTURE.md`.
