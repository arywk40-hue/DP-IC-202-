# Node collection contract (core weather + optional particles)

Collect native samples at **1 Hz**; upload **one-minute aggregates** and retain local samples/diagnostic counters. Create hourly aggregates for training only after the UTC hour closes. Do not silently call a 10-second gust an hourly mean wind. Preserve UTC start/end and actual receive/availability time.

| Column | Unit / rule |
|---|---|
| `schema_version`, `source_id`, `license_id`, `firmware_version`, `calibration_version` | Explicit versioned identifiers; owner establishes data-use rights |
| `node_id`, `physical_site_id`, `instrument_id`, `boot_id`, `sequence` | Stable physical-site ID; new site after relocation; monotonic sequence within each boot |
| `interval_start_utc`, `interval_end_utc`, `received_at_utc` | RFC3339 UTC ending in `Z`; explicit time-sync quality and offset uncertainty; no assumed local timezone |
| `latitude_deg`, `longitude_deg`, `coordinate_accuracy_m` | WGS84 decimal degrees, surveyed static position or GNSS fix and fix quality |
| `elevation_m`, `elevation_datum`, `elevation_source`, `elevation_asset_sha256` | SRTM ground elevation EGM96, separately retain measured antenna/sensor elevation and datum; GNSS ellipsoidal height must not be substituted directly |
| `temperature_c`, `relative_humidity_pct` | degC, %, ventilated radiation shield; preserve valid count/min/max/std |
| `pressure_hpa`, `pressure_reference` | hPa, **station** absolute pressure; retain raw Pa if instrument supplies it; keep sea-level-adjusted pressure in a different field |
| `wind_speed_mps`, `wind_direction_deg`, `wind_gust_mps` | m/s and meteorological degrees; distinguish mean, sample duration and gust; record mast height, exposure and obstruction |
| `pm25_ug_m3`, `pm10_ug_m3` | Optional ug/m3; absent = null + missing mask, never zero; optical estimates with RH influence retained |
| `sensor_model`, `serial_number`, `measurement_height_m`, `calibrated_at_utc` | Per channel, actual installed part and calibration reference; don't infer part from units |
| `sample_count`, `expected_sample_count`, `qc_flags`, `battery_v`, `rssi_dbm` | Per-channel completeness, timeout/stuck/range flags and maintenance diagnostics |

Record the exact manufacturer, model, part revision and serial number for the T/RH sensor, absolute-pressure sensor, anemometer and optional particulate sensor. Installed hardware models have **not been verified**; do not substitute a guessed part name or treat uncalibrated readings as reference truth. Measure T/RH around 2 m; wind ideally standardized at 10 m, or record actual mesh-node height and train with that feature. Record obstacles, enclosure/shield, terrain/slope and station photos in site metadata.

Validate finite values, physical ranges and coordinates at both node and server; flag flatlines using duration/neighbor evidence instead of automatically calling legitimate calm wind invalid. Retain the invalid raw sample with a reason. Never forward-fill a failed sensor into labels. Reject replayed boot/sequence IDs, duplicate site/channel/time records and stale arrivals; preserve late records for audit, exclude them from earlier prediction features. Authenticate node payloads and the receiver; use replay protection and rate limits. Do not put shared deployment keys in the repository.

For a mesh experiment collect colocated reference instruments plus independent query-site truth **between nodes**, spanning 1, 5, 10 and 20 km, monsoon/winter, mountain/valley and elevation differences. Use whole physical sites and whole weather episodes for held-out tests. The current national archive cannot replace this field validation.
