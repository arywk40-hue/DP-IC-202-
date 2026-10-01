# Independent Himachal observations: access and screening

Checked 28–29 September 2026. This folder records downloaded source evidence,
not a new trained or validated model.

The official [NWIC Himachal climate catalogue](https://www.nwdp.nwic.gov.in/dataset/?groups=climate&organization=himachal-pradesh)
lists hourly rainfall in addition to the four weather channels already supplied.
The [rainfall dataset](https://nwdp.nwic.gov.in/dataset/rainfall-telemetry-hourly-himachal-pradesh-department)
has a [2021–2025 CSV resource](https://nwdp.nwic.gov.in/dataset/30da9f29-3aab-408b-8b03-01d66a9a449e/resource/42966187-af6f-46aa-815f-81acbe4a284b/download/rainfall_tel_hr_himachal_pradesh_hp_2021_2025.csv).
`rainfall_catalogue.json` preserves its metadata and license fields.

## What was actually downloaded

- 21,007,727 bytes; 166,355 rows at 110 stations.
- Actual timestamps: 8 May 2021–22 December 2025.
- 42,634 rows belong to duplicated station/coordinate/time keys; all were
  excluded from the conservative matching screen.
- 98 negative rainfall values were excluded. The maximum reported value is
  938 mm; gauge interval and quality need confirmation before interpreting it.
- **Zero records report 0 mm.** There are no dry-hour negatives in this file.
  This could reflect reporting/export behavior; its cause is not established.
  Missing hours must remain unknown, not be filled as dry conditions.

Exact matching with the screened four-channel files produced 1,431 rows,
including 45 at AWS IIT Mandi. All 1,431 are positive rainfall reports.
There are 269 exact six-hour future matches, also all positive. Neither set
can establish binary rain-detection performance, calibrate rain probability,
or train a defensible future-rain classifier without observed negatives.

`reports/deployment/rainfall_overlap.json` includes hashes and per-station
coverage. `raw/screened_weather_rain_candidates.csv` is a local exploratory
join, explicitly using source time strings without claiming verified UTC.
It still lacks both particulate channels and verified pressure quality.
A positive rainfall record is not automatically a light/moderate-rain,
squall, snowstorm, or any of the other model event labels.

Reproduce after downloading the resource into `raw/`:

```sh
python3 -m ml.deployment.audit_himachal
python3 -m ml.deployment.audit_rainfall
```

## Particulate sources checked

The [Himachal Pollution Control Board annual report](https://hppcb.nic.in/Publications/AR-2021-22.pdf)
documents the Baddi continuous air-quality station. This is a candidate source
for PM observations at Baddi, not proof of a colocated IIT Mandi PM dataset.
The [CPCB air-quality portals](https://cpcb.gov.in/air-quality-management-portals/)
are the official access route for further station/time exports.
No new hourly, colocated Mandi PM2.5/PM10 download was obtained in this run.
Annual air-quality summaries and city AQI values cannot replace these channels.

## Required next source evidence

Obtain a continuous gauge export including explicit zero/dry periods and quality
flags, timezone and accumulation-interval definitions, and station-matched
PM2.5/PM10 histories. Keep source measurements and independently observed labels
separate from the model's threshold-generated targets.
