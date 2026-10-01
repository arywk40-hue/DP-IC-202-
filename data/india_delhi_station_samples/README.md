# Delhi CPCB station samples (2024–2025)

Two original 15-minute station exports supplied by the project owner are kept
locally in `raw/` and excluded from Git. Their source and SHA-256 hashes are
recorded in `audit_report.json`. The source is the
[OpenCity Delhi air-quality collection](https://data.opencity.in/dataset/delhi-hourly-air-quality-reports),
which attributes the measurements to the CPCB data repository and marks these
resources as “Other (Public Domain)”. The resources are
[Jahangirpuri DPCC](https://data.opencity.in/dataset/delhi-hourly-air-quality-reports/resource/734c459f-3e47-44c7-b0b8-8270090cecf0)
and [CRRI Mathura Road IMD](https://data.opencity.in/dataset/delhi-hourly-air-quality-reports/resource/c4ec16f3-edfc-465e-8fb8-5bfaa14f8baa).
`audit_report.json` records hashes, source URLs and per-channel coverage.
To rerun the audit, place the original downloaded files at the two `raw/`
paths listed there; the script checks their columns and regenerates the report.

| Source | Timestamped station rows | Rows with all six listed values | Hours with four complete 15-minute readings |
| --- | ---: | ---: | ---: |
| Jahangirpuri DPCC | 70,176 | 55,309 | 7,191 |
| CRRI Mathura Road IMD | 70,176 | 0 | 0 |

Each CSV has one malformed separator row between years. The audit excludes it
from counts; it does not edit the original file. CRRI has particulate readings
but no temperature, humidity, pressure or wind in this export, so it cannot
train or evaluate the required six-input model by itself.

The six listed columns are `AT (degC)`, `RH (%)`, `BP (mmHg)`, `PM2.5 (ug/m3)`,
`PM10 (ug/m3)` and `WS (m/s)`. **Listed values are not yet approved six-channel
training records.** Jahangirpuri's pressure median is near 976 under a header
that claims mmHg. Its true units and whether it is station or sea-level
pressure must be confirmed with the provider before converting it to the
model's station-pressure hPa input. CSV timestamps have no UTC offset and the
resource page does not establish their timezone. The local solar-radiation
pattern suggests the timestamps are in India Standard Time, but this remains
an inference. See [source verification](SOURCE_VERIFICATION.md) for evidence
and the exact questions still open. Missing values, outliers and
15-minute-to-hourly aggregation need a documented quality review. These Delhi
stations cannot validate Mandi
performance and contain no independent hazard event labels.

Reproduce the source audit from the repository root:

```sh
python3 data/india_delhi_station_samples/audit.py
```

Do not fill missing channels with values from a different station or silently
reinterpret the pressure column. After source verification, a preparation step
can generate hourly records and evaluate the saved six-input Beijing model on a
held-out Delhi period before trying Indian retraining.
