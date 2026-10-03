> Scope: historical source/experiment reference. Statements about mandatory six inputs apply to the older forecast, not the current four-core-channel spatial task. See [current overview](../../docs/PROJECT_OVERVIEW.md). This file does not establish two-node deployment skill.

# Indian six-sensor source audit — downloaded samples, not training data

**Outcome:** retrieved the complete file inventory and seven station samples
from [Time Series Air Quality Data of India (2010–2023)](https://www.kaggle.com/datasets/abhisheksjha/time-series-air-quality-data-of-india-2010-2023),
version 2, published by Abhishek S. Jha as a secondary CPCB compilation.
Publisher metadata declares **CC BY-NC-SA 4.0**; this is not the CC BY license
of the existing Beijing data. Keep that distinction in research attribution
and assess permissions separately for any intended commercial use.

The station metadata actually contains **453 stations, 241 distinct city names,
and 31 state/UT names**. The full inventory contains 454 files, approximately
1.70 GB uncompressed. We downloaded only the seven samples below and the
station metadata: **368,462 station-hour rows**, not the complete archive.
A station list is not evidence of complete national six-sensor coverage.

| Station | City | Sample rows | Rows with six finite raw values | Main issue |
|---|---|---:|---:|---|
| HP001 | Baddi, Himachal Pradesh | 9,247 | 0 | Pressure column absent |
| UK001 | Dehradun | 8,240 | 5,456 | Temperature unit ambiguous; pressure metadata needs verification |
| JK001 | Srinagar | 18,733 | 0 | Pressure column absent |
| DL001 | ITO, Delhi | 116,112 | 0 | Sample has particulate fields but no four required weather channels |
| RJ001 | Jodhpur | 64,272 | 48,486 | Pressure reference/units and time semantics need verification |
| KA001 | Bengaluru | 116,050 | 0 | No overlap of all six finite fields; pressure units suspicious |
| AS001 | Guwahati | 35,808 | 22,633 | Pressure header conflicts with many numeric values |

Finite raw values do **not** imply valid physical readings, verified units,
or suitability for model testing. No sample has been approved for evaluation.
For example, Guwahati pressure is labelled `BP (mmHg)` but its median is 994.16;
converting every finite value according to that label places 24,060 observations
outside the model's 300–1100 hPa range. We do not silently reinterpret the units.
Bengaluru has the same kind of issue. Source times are interval starts/ends;
verify timezone and label availability before constructing causal forecasts.

## Mandi / Himachal findings

There is **no city listed as Mandi in Himachal Pradesh in this archive**. The
Himachal entry is Baddi. Mandi Gobindgarh in Punjab and New Mandi in Uttar
Pradesh must not be confused with Mandi, Himachal Pradesh. Baddi is not a local
Mandi validation set, and its missing pressure cannot be filled with a constant.

Additional first-party sources identified online:

- [National Water Data Portal: Himachal climate datasets](https://www.nwdp.nwic.gov.in/dataset/?groups=climate&organization=himachal-pradesh)
  lists hourly telemetry temperature, relative humidity, pressure and wind.
  Individual station locations, overlapping timestamps and download access
  still require inspection. These data were **not downloaded in this audit**.
- [Himachal PCB Annual Report 2022–23](https://hppcb.nic.in/Publications/AR-2022-23.pdf)
  records monitoring in Sunder Nagar and other Himachal towns. Annual/report
  summaries are not a substitute for aligned hourly six-input observations.
- [CPCB air-quality portal](https://airquality.cpcb.gov.in/AQI_India/)
  is a primary-provider route for particulate data. Its web page presents
  CAPTCHA verification; this audit did not bypass it or obtain a direct bulk export.

## Files and reproduction

- `file_inventory.json`: complete published filename/byte inventory.
- `source_metadata.json`: publisher description, version and license evidence.
- `coverage_report.json`: reproducible per-station counts, units, hashes and blockers.
- `raw/`: downloaded original responses, Git-ignored. Some `.csv` download
  responses are actually ZIP containers; the reader detects this by content.

From the repository root:

```bash
python3 -m ml.six_sensor_forecast.audit_india --download
# Re-audit downloaded files without network access:
python3 -m ml.six_sensor_forecast.audit_india
```

Next steps are to verify the candidate station units/time metadata, obtain
aligned missing measurements from a documented primary source or separately
labelled reanalysis join, and build a frozen Indian evaluation dataset. Then
score the unchanged Beijing teacher/student before Indian retraining. Station
and region holdouts must remain untouched by fitting and model selection.

**The existing model remains trained on Beijing data. No Indian accuracy result,
retraining, Mandi validation or nationwide applicability is claimed by this audit.**


Subsequent work: [Indian profile training](../../docs/archive/ml/evaluation/INDIA_RESULTS.md)
uses only explicit-unit channels, excluding pressure and ambiguous temperature,
under documented interval/timezone assumptions. This original audit remains
the record of why complete six-input evaluation is unavailable.
