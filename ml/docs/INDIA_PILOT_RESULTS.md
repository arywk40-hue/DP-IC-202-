# India Pilot Results

## Data assembled

The first actual India pilot was assembled from two separately tracked sources:

```text
Weather:    Open-Meteo historical API, 14 configured locations, daily aggregates
Air quality: [AQI-Of-India city_hour.csv](https://huggingface.co/datasets/AdityaaXD/AQI-Of-India), 2015–2020, city-level CPCB-derived data
Join:       city + UTC date; AQ timestamps converted from Asia/Kolkata to UTC
Output:     ml/data_india_pilot/real_weather_india.csv
Rows:       16,949
Locations:  13 matched cities
Coverage:   2015-01-01 through 2020-06-30
```

One configured city did not have matching usable air-quality rows and was
excluded by the inner join. Rows without observed PM2.5 were also excluded.

The raw air-quality file is retained at:

```text
ml/data_india_pilot/raw/city_hour.csv
```

The pilot is useful for integration and geographic-transfer testing. It is not
yet a national hazard benchmark: weather is reanalysis rather than station
observations, the AQ source is a secondary curated copy, CO2 and lightning are
still synthetic in the feature builder, and the four hazard labels remain
heuristic.

## Model and split

The model uses the existing 14-feature, four-head XGBoost edge contract. The
test set contains complete held-out locations:

- Train: 13,571 rows, 10 locations
- Test: 3,378 rows, 3 locations
- Holdout: Mumbai, Patna, Thiruvananthapuram
- Trees: 16 per hazard head

Artifacts:

- Prepared data: `ml/data_india_pilot/prepared/`
- Models and metrics: `ml/model_india_pilot/`
- C export: `ml/generated/model_data_india_pilot.h`

## Geographic-holdout results

| Hazard | Precision | Recall | F1 | Accuracy |
|---|---:|---:|---:|---:|
| Wildfire | 0.9922 | 1.0000 | 0.9961 | 0.9997 |
| Flood | 0.9897 | 1.0000 | 0.9948 | 0.9994 |
| Storm | 0.9968 | 0.9904 | 0.9936 | 0.9976 |
| Air quality | 0.9961 | 0.8683 | 0.9278 | 0.9414 |

Air quality is the first meaningful warning sign: recall drops on unseen
locations even though accuracy remains high. This supports using geographic
holdouts and class-specific calibration rather than relying on accuracy.

## Next gate

Before using the model operationally:

1. add all 26 cities or station-level data;
2. add a second seasonal/weather source and independently verify units;
3. replace heuristic wildfire/flood/storm labels with event records;
4. evaluate a future-time holdout in addition to the geographic holdout;
5. compare station observations against reanalysis inputs;
6. rerun Python/C prediction parity on golden vectors.

## 26-city expansion

The same pipeline was expanded using all 26 cities present in the downloaded
air-quality archive:

```text
Weather rows: 52,234 daily rows
Joined rows:  24,861
Locations:    26
Train:        19,289 rows across 20 locations
Test:         5,572 rows across 6 complete locations
Holdout:      Mumbai, Patna, Shillong, Talcher, Thiruvananthapuram, Visakhapatnam
```

| Hazard | Precision | Recall | F1 | Accuracy |
|---|---:|---:|---:|---:|
| Wildfire | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Flood | 0.9791 | 1.0000 | 0.9894 | 0.9987 |
| Storm | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Air quality | 0.9953 | 0.7457 | 0.8526 | 0.8807 |

The air-quality F1 decreased from 0.9278 on the 13-city pilot to 0.8526 on
the broader six-city holdout. This is a useful generalization result, not a
failure of the pipeline. It indicates that city coverage and pollutant
distribution materially affect the model and that the air-quality head needs
better calibration, broader station data, and independent labels.

The 26-city model was exported to `ml/generated/model_data_india_26.h` and the
header passed C syntax validation. It remains a research artifact because the
weather input is reanalysis, CO2/lightning are synthetic, and the hazard labels
are heuristic.

## Combined geographic + future-time holdout

To test both spatial transfer and future generalization, a stricter run trained
only on 20 non-held-out cities before `2019-12-09` and tested on:

- all dates from six held-out cities;
- the future period from the remaining cities;
- 15,481 training rows and 9,380 test rows.

| Hazard | Precision | Recall | F1 | Accuracy |
|---|---:|---:|---:|---:|
| Wildfire | 1.0000 | 0.9977 | 0.9989 | 0.9999 |
| Flood | 0.9869 | 1.0000 | 0.9934 | 0.9995 |
| Storm | 0.9994 | 0.9960 | 0.9977 | 0.9991 |
| Air quality | 0.9973 | 0.7157 | 0.8334 | 0.8741 |

The stricter split lowers air-quality F1 from 0.8526 to 0.8334. This is the
current validation result to use for architecture decisions. The combined
model’s C export is `ml/generated/model_data_india_26_geo_temporal.h` and passed
C syntax validation.

## Station-level status

The downloaded `stations.csv` contains station IDs, names, cities, and states,
but no latitude/longitude fields. The station-hour archive download was stopped
after becoming rate-limited and is retained only as
`station_hour.csv.partial`; it is not used by any training run. Until a valid
station-coordinate table and complete station observations are available, the
26-city result is the largest defensible experiment in this repository.

## Rich offline feature experiment

The same combined geographic-plus-future split was rerun with a non-edge
19-feature schema containing real PM10, CO, SO2, O3, and NO2, plus precipitation
and seasonal features. This is an offline teacher experiment and is not
exportable to the current 14-feature firmware contract.

| Hazard | Edge 14-feature F1 | Rich offline F1 |
|---|---:|---:|
| Wildfire | 0.9989 | 0.9966 |
| Flood | 0.9934 | 0.9934 |
| Storm | 0.9977 | 0.5467 |
| Air quality | 0.8334 | 0.9727 |

The air-quality improvement shows that the edge model is losing useful
pollutant information, not merely suffering from insufficient tree count. The
storm degradation is expected: the current storm label depends on synthetic
lightning, which is absent from the real-pollutant offline schema and must be
redesigned around real lightning or verified storm labels.

### Architecture decision

Use a two-model path:

```text
rich India data -> offline teacher -> calibrated hazard probabilities
                                      |
                                      v
                       distillation / feature selection
                                      |
                                      v
                         14-feature ESP32 edge student
```

Do not expand the firmware feature vector until sensor availability is proven.
The next experiment is to distill the rich air-quality teacher into the edge
feature set and compare recall and calibration, rather than shipping the
19-feature offline model directly.

## Distillation result

The first 50/50 hard-label and teacher-probability distillation run produced:

| Edge candidate | Precision | Recall | F1 | Accuracy |
|---|---:|---:|---:|---:|
| Hard-label student | 0.9973 | 0.7157 | 0.8334 | 0.8741 |
| Distilled student | 0.9911 | 0.7290 | 0.8401 | 0.8779 |

The distilled student improves recall and F1 modestly without changing the
14-feature schema. The other three hazard heads remain the geographic/future
edge models unchanged. The complete candidate was exported to
`ml/generated/model_data_india_26_distilled.h` and passed C syntax validation.

Threshold calibration was run on the same strict geo-temporal holdout and is
recorded in `ml/model_india_26_distilled/calibration.json`:

| Air-quality operating point | Threshold | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Default precision-first | 0.65 | 0.9911 | 0.7290 | 0.8401 |
| Best holdout F1 | 0.46 | 0.9274 | 0.8049 | 0.8618 |
| Recall at least 0.90 | 0.25 | 0.7216 | 0.9089 | 0.8045 |

The firmware default remains 0.65 until an operating point is selected from a
deployment cost analysis; the lower thresholds are validation evidence, not an
automatic production change. Python/C golden-vector parity now passes for the
complete distilled model with maximum absolute probability error `2.96e-08`
(gate `3e-05`). The exporter preserves nine decimal places for tree values and
normalization constants and includes each XGBoost base-score logit.

This is still not a release decision. The next required gate is evaluation on
independently verified station/event labels, followed by a complete station-
level India dataset and sensor-availability review.

## Larger weather-teacher path

Before the national archive is processed, the offline teacher path was run on
the complete 26-city weather table (`52,234` daily rows). It predicts the next
day’s weather from current weather and seasonal features, using a chronological
cutoff at `2019-01-01`:

| Target | MAE | RMSE |
|---|---:|---:|
| Temperature (°C) | 0.7044 | 0.9790 |
| Humidity (%) | 4.0900 | 5.6743 |
| Pressure (mb) | 0.9066 | 1.2016 |
| Wind (km/h) | 1.6929 | 2.3298 |
| Precipitation (mm) | 3.1689 | 7.7640 |

The trainer is `ml/real_india_data/train_weather_teacher.py` and its output is
`ml/model_india_weather_teacher/`. This is an offline weather-context teacher,
not a hazard benchmark. The same trainer can consume the weather table emitted
by `prepare_indiaweatherbench.py` after the larger archive is available.

## Expanded 56-city weather run

The larger weather-only stage was expanded to 56 Indian cities using the same
Open-Meteo historical adapter:

```text
Rows:       112,504 daily records
Locations:  56
Coverage:   2015-01-01 through 2020-07-01
```

The combined table is `ml/data_india_pilot/weather_56_cities.csv`; its source
hash and units are recorded in `ml/data_india_pilot/weather_56_manifest.json`.
The 56-city teacher was trained into `ml/model_india_weather_teacher_56/` with
the same `2019-01-01` chronological cutoff:

| Target | MAE | RMSE |
|---|---:|---:|
| Temperature (°C) | 0.7408 | 1.0339 |
| Humidity (%) | 4.2785 | 5.9381 |
| Pressure (mb) | 0.9394 | 1.2620 |
| Wind (km/h) | 1.6442 | 2.2633 |
| Precipitation (mm) | 3.0526 | 8.2716 |

This is the first actual larger-dataset training run in the repository. It is
still a weather forecasting teacher, not proof of hazard-alert quality; hazard
retraining waits for independent event and station labels.

The stronger geo-temporal evaluation is in
`ml/model_india_weather_teacher_56_geo_temporal/`. It trains on 44 cities
before `2019-01-01` and tests on 12 completely held-out cities plus future
dates from the training cities:

| Target | MAE | RMSE |
|---|---:|---:|
| Temperature (°C) | 0.9297 | 1.8228 |
| Humidity (%) | 4.2720 | 5.9872 |
| Pressure (mb) | 0.9548 | 1.3660 |
| Wind (km/h) | 1.6059 | 2.2143 |
| Precipitation (mm) | 3.1439 | 8.5034 |

This geo-temporal run is the teacher checkpoint to use for later hazard
feature extraction; the easier time-only result should not be used as the
deployment comparison.

## Weather-context hazard teacher and distillation

The 56-city geo-temporal teacher was applied to the 26-city labeled rows to
produce five additional next-day context features. A 24-feature offline hazard
teacher was then trained on the strict geo-temporal hazard split:

| Hazard | Precision | Recall | F1 |
|---|---:|---:|---:|
| Wildfire | 0.9954 | 0.9977 | 0.9966 |
| Flood | 0.9867 | 0.9815 | 0.9841 |
| Storm | 0.6038 | 0.5074 | 0.5514 |
| Air quality | 0.9853 | 0.9578 | 0.9714 |

The context-enriched teacher is in `ml/model_india_26_teacher_context/`; its
24-feature input is intentionally offline-only. Its air-quality probabilities
were distilled into the 14-feature edge student:

| Student | Precision | Recall | F1 |
|---|---:|---:|---:|
| Hard-label edge student | 0.9973 | 0.7157 | 0.8334 |
| Weather-context distilled student | 0.9901 | 0.7290 | 0.8398 |

The complete context-distilled candidate is exported as
`ml/generated/model_data_india_26_distilled_context.h` and passes Python/C
parity with maximum absolute probability error `3.02e-08`. This validates the
planned large-teacher-to-small-edge handoff, but the hazard labels are still
weak labels and must be replaced with independently verified events before
deployment claims are made.

The same IMD event conversion was checked against all 56 weather locations:
53 city-level event intervals produced 25 positive daily rows across 26 cities
and 52,234 labeled weather rows. The additional cities improved coverage, but
the positive rate is still only about `0.05%`; a storm model from this slice
would remain statistically underpowered. The next step is longer historical
weather coverage and/or a broader verified severe-weather event source, not
more tuning of the current classifier.

## First independent storm-label run

The official IMD/RSMC New Delhi best-track workbook was downloaded to
`ml/data_india_pilot/raw/imd_best_tracks_1982_2026.xlsx`. The adapter
`prepare_imd_storm_events.py` converted 2015–2020 track points into 33
city-level events using a 250 km radius and a 34 kt minimum storm threshold.
The event intervals were joined without converting unknown periods into
negatives:

```text
Known storm-labeled rows: 11,370
Positive rows:             9
Cities with events:        15
```

A storm-only geo-temporal model was trained with the shared edge normalization
and tested on 5 positive rows from the held-out/future partition. It produced
precision, recall, and F1 of `0.0` at threshold `0.5`; this is a data-coverage
failure, not evidence that the model detects no storms. The 4 positive training
rows are insufficient for a useful storm model. The result is retained as a
label-quality gate rather than hidden behind the high accuracy (`0.9988`).

The mixed candidate with this verified storm head is
`ml/generated/model_data_india_26_verified_storm_candidate.h` and passes
Python/C parity (`3.02e-08` maximum error). It is not approved for deployment
until the storm event set is enlarged and balanced across regions/seasons.

## Long-window verified storm teacher

The successfully downloaded 16-city subset extends weather coverage from 1982
through 2020 and contains `227,920` daily rows. Joining the IMD best-track
archive produced 81 verified city-event intervals, 142,450 known weather rows,
and 48 positive storm rows.

The weather-only offline storm teacher was evaluated with a geographic-plus-
future split and achieved precision `0.0447`, recall `1.0000`, and F1 `0.0856`.
The low precision reflects sparse event coverage and the broad 250 km labeling
radius; it is a more honest result than the weak-label storm score. The model
is retained at `ml/model_india_storm_weather_verified_1982_2020/` for further
data expansion, not deployment.

## Public OpenAQ station slice

The OpenAQ public S3 archive was used without an API key for New Delhi station
`8118` during 2020. It yielded 8,164 hourly PM2.5 observations, 183 valid daily
weather/AQ rows after quality filtering, and next-day PM2.5 targets. A
weather-only regression teacher achieved MAE `32.56 µg/m³` and RMSE
`34.41 µg/m³` on the final 20% time holdout. The teacher is in
`ml/model_india_aq_teacher_openaq_delhi_2020/`.

This validates the independent AQ ingestion and leakage-safe target design, but
one station and 183 daily examples are not sufficient for national AQ hazard
training. More OpenAQ station partitions must be added before using this head
for edge distillation.

The Mumbai station (`8039`) added 4,141 hourly observations and 176 valid daily
rows. Combining Delhi and Mumbai produced 359 daily examples. In a strict split
trained on Delhi before the cutoff and tested on held-out Mumbai plus future
Delhi dates, the weather-only PM2.5 teacher achieved MAE `30.20 µg/m³` and RMSE
`35.40 µg/m³`. This is the first cross-city independent AQ evaluation; its
error shows that city transfer needs more stations and longer coverage before
AQ hazard distillation.

The public S3 archive was then expanded to a common Jan–Jun 2020 window for
Kolkata (station `10851`) and Hyderabad (station `8557`); a Bengaluru station
was catalogued but had no PM2.5 rows in this slice. The combined Delhi,
Mumbai, Kolkata, and Hyderabad dataset contains 701 daily examples. A
geo-temporal split trained on Delhi and Hyderabad before the cutoff and held
out Kolkata and Mumbai produced MAE `28.20 µg/m³` and RMSE `34.39 µg/m³`.
The model is in `ml/model_india_aq_teacher_openaq_4cities_geo_temporal/`.

This is a stronger independent cross-city regression check, but it is still
not a deployment-ready AQ hazard head: the window is short, the station
coverage is uneven, and the result has not yet been converted into verified
hazard labels or distilled into the edge model.

## Masked multi-source teacher checkpoint

The new `train_masked_teacher.py` experiment combines the 24-feature weather
context table with per-hazard label masks. Weak labels remain available for
wildfire, flood, and air quality; the storm column is replaced by the
independent IMD label join and rows outside IMD coverage are excluded from the
storm loss. On the same strict geo-temporal split, the result was:

| Head | Label source | Labeled train/test rows | Test positives | F1 | PR-AUC |
|---|---|---:|---:|---:|---:|
| Wildfire | weak | 15,481 / 9,380 | 437 | 0.9977 | 0.99999 |
| Flood | weak | 15,481 / 9,380 | 378 | 0.9921 | 0.99947 |
| Storm | IMD verified | 5,553 / 5,817 | 5 | 0.1212 | 0.15922 |
| Air quality | weak | 15,481 / 9,380 | 4,126 | 0.9847 | 0.99688 |

The storm result is the important gate: the masked architecture correctly
avoids fabricating negatives, but only five verified storm positives remain in
the test partition. The trained research teacher is stored in
`ml/model_india_26_masked_verified_teacher_context/`; it is not a deployment
candidate until the verified event coverage is expanded.

The masked teacher was also distilled into a 14-feature, 16-tree edge student
using `distill_masked_teacher.py`. The exporter initially rejected a 32-tree
student, so the student was retrained at the declared firmware ceiling rather
than silently truncated. The resulting header is
`ml/generated/model_data_india_26_masked_distilled_edge.h`; Python/C parity
passed with maximum absolute probability error `2.99e-08`. This validates the
larger-teacher-to-edge handoff, but the storm head remains `NOT_READY` and the
student's AQ metrics are only against the existing weak labels.

## 56-city verified storm scale-up

The official IMD event adapter was then applied to the full 56-city weather
table. It produced 52,234 known storm-label rows and 25 positive daily rows
across 26 cities, while preserving 60,270 unknown rows. Training the
weather-only storm teacher on this larger geographic table gave precision
`0.0781`, recall `0.3571`, and F1 `0.1282` on the geo-temporal holdout, which
contained 14 positive test rows. This is a larger geographic experiment, not
deployment evidence: the positive count remains too low and the model needs
more balanced verified storm events. The model is stored at
`ml/model_india_storm_weather_verified_56/` and the label join is stored at
`ml/data_india_pilot/imd_storm_labeled_56/`.

## Independent flood-label scale-up

The IIT Delhi India Flood Inventory-Impacts v3 was added from its Zenodo
record. It contains IMD-sourced flood events from 1967–2023. The adapter
`prepare_ifi_flood_events.py` uses only explicit city/district tokens, excludes
state-only rows, removes malformed intervals, and merges overlapping matches.
The resulting join against the 56-city weather table contains 86,387 known
flood-label rows and 6,602 positive daily rows; 26,117 rows remain unknown.

A 56-city geo-temporal flood teacher achieved precision `0.2078`, recall
`0.5704`, and F1 `0.3046` on the holdout, with 3,799 positive test rows. The
model is stored at `ml/model_india_flood_weather_verified_56/`. This is the
first independent flood head in the larger architecture. Its moderate score
and conservative spatial matching indicate the next work is calibration and
district-level spatial validation, not threshold tuning alone.

## Five-city OpenAQ expansion

An additional CPCB/TNPCB Chennai station (`11578`, Royapuram) supplied 5,402
hourly rows in the public archive. The matching late-2020 weather window
produced 46 valid daily next-day targets. Combining Chennai with Delhi,
Mumbai, Kolkata, and Hyderabad yielded 747 daily examples. The strict
geo-temporal AQ teacher, trained on Chennai/Delhi/Hyderabad and held out on
Kolkata/Mumbai plus future dates, achieved MAE `19.50 µg/m³` and RMSE
`24.94 µg/m³`. The model is stored at
`ml/model_india_aq_teacher_openaq_5cities_geo_temporal/`. The small Chennai
slice improves coverage but is not yet enough for national AQ deployment.
