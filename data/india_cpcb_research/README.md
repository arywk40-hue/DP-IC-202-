# Indian CPCB-derived research observations

Prepared from the seven raw station samples in `data/india_station_audit/`.
All 368,462 hourly rows are retained; physically invalid readings become NaN.
No missing sensor values are invented. The source is a secondary compilation
published under CC BY-NC-SA 4.0, distinct from the Beijing dataset license.

- Pressure: excluded everywhere because units/reference remain unresolved.
- Temperature: accept only explicit Celsius headers; Dehradun's ambiguous
  `AT (degree)` is excluded.
- Time: assumed local Asia/Kolkata, converted to UTC at interval END to avoid
  using a completed hourly mean before it could have been observed. UTC hours
  fall at :30. Timezone is an explicit research assumption, not provider verification.
- Inputs/targets: observed temperature, humidity, PM2.5, PM10 and wind when
  available. Targets are hourly measurements ending exactly six hours later.
- Coverage: seven sample stations, no Mandi. Complete five-channel observations
  occur at Guwahati, Srinagar, Jodhpur and Baddi only.
- Baddi is entirely held out of Indian fitting/validation.

`dataset_manifest.json` contains source hashes, accepted column mappings,
per-station finite counts, exclusions and assumptions. `observations.csv` is
local and Git-ignored. Regenerate with `python3 -m ml.six_sensor_forecast.prepare_india`.

[Training and paired test results](../../ml/evaluation/INDIA_RESULTS.md)
