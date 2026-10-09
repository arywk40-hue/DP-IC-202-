# Draft IMD historical observation request — not sent

For the current Himalayan event study, use the expanded
[IMD/Himachal request package](../../docs/reference/IMD_HIMACHAL_DATA_REQUEST_PACKAGE.md),
checked on 8 October 2026. It adds rainfall/event evidence, staged availability
and cost enquiries, HPSDMA/NWIC requests and product-specific publication/IP
questions. This older specification is retained as historical source context.

Purpose: academic evaluation and training of an ESP32-S3 environmental forecasting
model using six measured channels. Research location: Mandi, Himachal Pradesh;
initial evaluation scope: northern India. Please confirm data-use, research
publication, redistribution and any commercial-use conditions separately.

Please provide machine-readable historical observations (CSV preferred) for
2018–2025 where available, with a station-by-station availability statement.
For the initial join to existing Baddi air-quality data, March 2022–March 2023
is the minimum overlapping period of interest; overlap at a valid nearby weather
station must be checked rather than assumed.

Priority IMD catalogue stations:

| Station | IMD code | Catalogue surface observation hours |
|---|---|---|
| Mandi | 42078 | 03, 12 |
| Sundernagar | 42079 | 00, 03, 06, 09, 12, 15, 18, 21 |
| Bhuntar | 42081 | 03, 06, 09, 12 |
| Shimla | 42083 | 03, 06, 09, 12 |
| Chandigarh | 42105 | 00, 03, 06, 09, 12, 15, 18, 21 |
| Dehradun | 42111 | 00, 03, 06, 09, 12, 15, 18, 21 |
| Patiala | 42101 | 00, 03, 06, 09, 12, 15, 18, 21 |

These codes and schedules come from the public surface station catalogue;
they do not prove record availability in the requested years. Please confirm
the schedule time standard. In particular, the listed Mandi schedule alone
does not provide exact six-hour target pairs. Please identify hourly AWS
stations near Mandi/Baddi and other northern air-quality monitoring sites.

Required meteorological variables:

1. Dry-bulb air temperature, degrees Celsius.
2. Relative humidity, percent.
3. **Station-level atmospheric pressure, hPa**, clearly distinguished from
   mean-sea-level pressure or pressure reduced to a standard altitude.
4. Wind speed, with its unit and anemometer height specified.

Prefer hourly AWS observations. If only Surface Table-III synoptic records
are available, supply their actual cadence; do not interpolate records to hourly.
Please include timestamp/timezone, averaging interval and start/end convention,
station identifier, latitude, longitude, elevation, instrument/relocation dates,
missing-value codes and quality-control flags.

PM2.5 and PM10 will require matching measured concentrations from an appropriate
air-quality provider unless equivalent co-located IMD observations are available.
Please identify any co-located air-quality stations. A join will not assume that
stations in the same city have equivalent altitude or meteorology.

Access route: https://dsp.imdpune.gov.in/
Data-format query: Surface -> SYNOPTIC HOUR (TABLE-III).
This is a draft specification only; no account registration, order, payment or
message to IMD has been submitted by the assistant.
