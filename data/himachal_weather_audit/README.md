# Himachal four-weather-input file audit

Audited the four user-provided CSV files in `himachal 4-sensor dataset/`.
Run `python3 data/himachal_weather_audit/audit.py` from the repository root to reproduce
`audit_report.json`. Original files are unchanged. No model was trained or tested.

| Measurement | Rows | Station/coordinate identities | Observed date span |
|---|---:|---:|---|
| Air temperature | 611,048 | 30 | Jan 2022–Dec 2025 |
| Relative humidity | 609,428 | 30 | Jan 2022–Dec 2025 |
| Atmospheric pressure | 113,594 | 12 | Oct 2023–Dec 2025 |
| Wind speed | 237,225 | 13 | Jan 2007–Dec 2025 |

These are observed timestamp extrema, not continuous coverage. Wind timestamps before
2021 warrant checking against source metadata. Temperature header explicitly identifies
AIR temperature, resolving the ambiguous catalogue description; its `AoC` unit text
still warrants checking. Pressure is labelled mb, numerically equivalent to hPa;
station-level versus sea-level reference remains unverified. Wind is labelled km/h
and converted to m/s for range checks. Timezone is not specified in the CSV columns.

## Overlap and limitations

All four share 112,799 exact station/coordinate/timestamp keys across 12 stations,
including AWS IIT Mandi. A conservative screen excludes every duplicated key in
any input and values outside the project's broad physical ranges, leaving 43,909
four-input rows, including 2,047 at AWS IIT Mandi. There are 32,281 exact six-hour
pairs in this screened subset. These are NOT quality-approved training samples:
duplicate values have not yet been reconciled, pressure artifacts have not been
removed, and sensor freezing and spikes have not been screened.

Temperature has 19,387 out-of-range or missing rows; humidity has 14,146.
Pressure passes broad range checks, yet exactly 925 hPa appears in 49,130 of
113,594 rows (43.25%). At AWS IIT Mandi it appears in 6,763 of 10,817 pressure rows;
at Jogindernagar, 11,057 of 11,307. These repeated values require investigation
before being accepted as observations; the audit does not infer a missing-value code.

PM2.5 and PM10 are absent. The daily AQI file cannot supply these concentrations.
Six-input Indian training requires matching measured particulate records as well as
verified weather units, pressure reference, timezone, and quality controls.
