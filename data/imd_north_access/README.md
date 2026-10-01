# Official IMD northern India access check

**Six required inputs remain mandatory. No new IMD-trained model is claimed.**
The five-/two-input experiments do not meet this release contract.

## What was actually obtained

- Downloaded the public IMD surface and autographic station catalogues and the
  Surface Table-III data description.
- Saved the northern subset as `northern_surface_stations.csv`, including Mandi
  (42078), Sundernagar (42079), Bhuntar (42081), Shimla (42083), Chandigarh (42105),
  Dehradun (42111) and Patiala (42101).
- Saved URL, query, HTTP status, byte count and SHA-256 receipts in
  `access_report.json`; original responses are local and Git-ignored.
- Checked current official `aws_data?sid=3` and `current_wx` APIs. Both returned
  **HTTP 401 with `{"error":"API key missing"}`**. No authentication bypass was attempted.
- Checked the historical portal's public free-data page: it links monthly/seasonal
  temperature/rainfall series and cyclone information, not the required aligned
  hourly station observations. The historical procurement route describes account
  enrolment/login. An API key for current observations alone does not supply years
  of historical training data.

**Downloaded weather observation rows: 0. Complete new six-input rows: 0.**
The catalogue is station metadata, not a training dataset. Training and testing
on an official northern six-input dataset remain blocked on acquiring observations.

## Why pressure and timing need care

Surface Table-III lists station-level pressure, mean-sea-level pressure, dry-bulb
temperature, humidity and wind. Station-level pressure is the appropriate input
for a BME280 pressure reading. The current-weather API documents MSLP; it cannot
be relabelled as station pressure, especially for Himalayan sites. Wind units
also require explicit conversion rather than assumptions.

The surface catalogue lists Mandi hours `03 12`, and Sundernagar every three
hours. These are not automatically hourly datasets. Do not fabricate hourly
observations or six-hour targets where the observed schedule does not support them.
Hourly AWS availability must be obtained from IMD. Matching PM2.5 and PM10 data
must also have verified concentration units, timestamps and station locations;
weather-only records do not complete the six-input contract.

## Concrete next step

Use [IMD_DATA_REQUEST.md](IMD_DATA_REQUEST.md) for the exact variables, station
codes, date ranges and metadata required. It is a draft and has not been sent.
Once official exports are available, verify units/cadence, join measured PM data
using a documented spatial/time policy, keep all six current inputs mandatory,
and train/test on station and future-time holdouts. Do not replace unavailable
pressure with a constant, reanalysis field or a reduced-input model without an
explicitly revised research design.

The existing trainer defaults to all six inputs; the default ESP32 environment
has been restored to the original six-input model. Reduced-input research builds
remain available only when explicitly selected by name.

## Official sources checked

- [IMD Data Service Portal](https://dsp.imdpune.gov.in/)
- [Station catalogue](https://dsp.imdpune.gov.in/home_station_list.php), public form selections SURFACE and AUTOGRAPHIC.
- [Data formats](https://dsp.imdpune.gov.in/home_sampledata_costestimate.php), public form selection SURFACE.
- [Free-data page](https://dsp.imdpune.gov.in/home_freedataaccess.php)
- [Current IMD API reference](https://api.imd.gov.in/public/api_reference.html)

`training_readiness.json` records the outstanding dependencies. No scores or
six-input Indian training artifacts were generated from missing observations.
