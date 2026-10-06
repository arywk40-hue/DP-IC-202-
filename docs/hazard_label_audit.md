# Independent Indian hazard-label audit

**Confidential: do not publish before IP review.** Audited 6 October 2026 before any new fit. Original locally verified baseline: `bc1d8be`; GitHub CI exposed one GCC portability issue in a test harness, repaired separately in `1e67bd9`. Frozen scores/model/export remain unchanged; remote status is recorded in the new phase receipt.

| Target | Existing source | Label type | Independent? | Suitable for training? | Main limitation |
|---|---|---|---|---|---|
| High wind, hot T, near saturation | NOAA future exact t+6h hourly measurements, `ml/india_sensor/labels.py` | Observed future measurement thresholds | Yes relative to issue-time inputs | Existing measurement research only | Hourly mean, rare positives; not gust/storm/heatwave/fog/disaster truth |
| Thunderstorm/storm-like conditions | `ml/event_classifier/features.py` Beijing sensor rules | Weak input-generated heuristic | No | No independent India event training | Matches its own rules, not storm records; China remains separate |
| Heatwave/cold-wave/heat-index patterns | Event classifier rules and fixed hot-T threshold | Weak heuristic / measurement threshold | Not independent official declaration | No official event head | Regional/duration criteria and independent declarations absent |
| Wildfire evaporative risk, fog, smoke/dust/AQI patterns | Beijing rule labels and optional PM fields | Weak patterns / optical PM measurements | No event independence | No wildfire/smoke-source/disaster head | PM source/clock/rights unresolved; no attribution |
| Rainfall | NWIC wet-only local files, existing registry/source receipts | Reported rainfall measurements, incomplete coverage | Potentially, once interpretation verified | No current hazard fit | Wet-only records cannot supply negatives; clock/unit/rights gates |
| Heavy/extreme rain | [IMD data supply](https://dsp.imdpune.gov.in/data_request_form_dsp.php), [daily gridded archive](https://imdpune.gov.in/lrfindex.php) | Gauge vs daily gridded analysis | Gauge can be independent; gridded analysis is distinct | Candidate, requires authorized export/definitions/coverage | Daily rain cannot establish hourly localized extremes; rights/access unresolved |
| Satellite rain | [NASA IMERG documentation](https://gpm.nasa.gov/resources/documents/imerg-v07-technical-documentation) | Satellite/gauge-adjusted estimate | External, but not direct local gauge truth | Research context/qualified estimated-rain target only | Product latency, grid smoothing and gauge dependence; no independent cloudburst label |
| Cloudburst | [IMD MAUSAM 2017 case study](https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/5084) | Five reported gauge/AWS-observed cases, outside 2023/24 | Potential observed evidence | Candidate only; training DISABLED | No complete machine-readable records/monitored negatives here; event time/location detail needs full text; article CC-BY-NC notice conflicts with generic CC-BY text |
| Flood / flash flood | [CWC observation portal](https://cwc.gov.in/hydro-meteorological-observation), authorized state disaster reports | River gauge data vs occurrence reports | Potential independent occurrence evidence | Candidate; none admitted | River levels/forecast warnings/rain are not proof of local flash flood. CWC policy PDF returned 401; no access bypass |
| Landslide occurrence | [GSI field-validated inventory](https://bhusanket.gsi.gov.in/index.html) | Mapped occurrence vs susceptibility/forecast | Inventory potentially independent | Candidate; no admitted export | Source advertises public downloads; actual dated records/rights/negative survey coverage not verified. Static susceptibility is not an event |
| Landslide weather risk | No independent current target | Proposed environmental-risk model | No labels | DISABLED | Keep separate from actual landslide occurrence |
| Wildfire / fire | [NASA FIRMS API](https://firms.modaps.eosdis.nasa.gov/api/) | Thermal anomaly / active-fire detection | Satellite observation, not necessarily confirmed vegetation wildfire | Qualified thermal-anomaly research candidate only | [API requires MAP_KEY](https://firms.modaps.eosdis.nasa.gov/api/map_key/); coverage/non-detections and attribution need validation; FAQ fetch returned 403 |
| ERA5 atmospheric background | Existing `ml/datasets/era5_land.py`, 24 frozen CDS requests | Model-based retrospective reanalysis | Not independent event truth | SB context only, never hazard proof | No files/token; indirect observation assimilation; publication semantics required |

NASA describes IMERG as combined precipitation estimates with successive product runs; gauge-adjusted estimates retain satellite/model uncertainty. [NASA product directory](https://gpm.nasa.gov/data/directory). The MAUSAM paper describes localized hourly extreme rain observed using gauges/AWS, not detection from RH/pressure alone. Its license conflict is intentionally unresolved.

## Existing infrastructure and gaps

- `ml/india_sensor/labels.py` already validates independent observed exports, monitored negatives, source hashes and disjoint event IDs; it has no provider adapters, station-event association or independent occurrence corpus. Reuse its principles without refactoring stable code.
- `ml/datasets/schema.sql`, adapters and source registry preserve observation provenance, source clock/pressure interpretation and separate open/restricted views. Those views are not automatic event admission.
- `ml/spatial_ensemble/episodes.py` supplies fixed 72h time proxies; they are not physical storm identities. New grouping must keep duplicate/nearby multi-station reports together and purge intervals across split boundaries.
- Current inference returns null for every independent disaster head. Existing China sensor-rule scores remain explicitly separate diagnostics; no new model can relabel them as observed events.
- Coordinates, UTC times, measured intensity, confidence and monitored coverage must remain null if the provider does not supply evidence. No state/district centroid or guessed midnight event is inserted.

## Admission order

Prioritize gauge heavy/extreme rainfall, specifically evidenced cloudbursts, independent flood/flash-flood records, dated landslide occurrences, then qualified fire detections. Candidate discovery is not admission. Rights, independent definitions, uncertainty, adequate distinct events/sites/years, defensible negatives and event-disjoint split support are required. Minimum research support is a screening floor, never proof of scientific sufficiency or deployment approval.

## ERA5 availability audit

No `.nc/.nc4/.grib/.grib2/.zarr` ERA5 files were found under data. Neither `.cdsapirc` nor a CDSAPI_KEY was present; only existence was checked, no secrets read. **ERA5_DOWNLOAD_STATUS = BLOCKED_BY_ACCESS.** Validate the unchanged 24 2023/2024 monthly requests; download only after personal [CDS setup and manual terms acceptance](https://cds.climate.copernicus.eu/how-to-api). ERA5 is model-based, with indirect observation influence through atmospheric forcing; retain that dependence in any station holdout. [CDS dataset description](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview).

## PM admission update

| Source | Clock/interval | Units and PM identity | Country/station/QC/rights | Outcome |
|---|---|---|---|---|
| Existing CPCB-derived compilation | Assumed IST; interval unverified | Legacy canonical PM2.5/PM10 fields; provider metadata still needed | Restricted NC terms; legacy assumptions retained | No new clean admission/model |
| Delhi/OpenCity samples | Unresolved source convention | Source units/QC still need verification | Identity/rights incomplete | Candidate, no new fit |
| OpenAQ | API documents time handling; AWS archive has explicit ISO-offset datetimes, averaging interval still provider-specific | Archive documents pollutant/unit/sensor IDs | Provider license, country and QC metadata still required | Candidate; no acquired/admitted PM rows |
| Sensor.Community | Provider/native cadence/clock metadata unresolved locally | Optical PM fields require verified units/channel/QC | Provider rights and identity incomplete | Candidate, no new fit |

OpenAQ API authentication is key-based, but a **documented public S3 archive** is also a legitimate route—not an authentication bypass. Its rows include timestamps/coordinates, PM parameters/units and location/sensor IDs, but the documented narrow schema does not itself establish provider rights, country or complete QC/averaging semantics. [OpenAQ archive documentation](https://docs.openaq.org/aws/about), [API key documentation](https://docs.openaq.org/using-the-api/api-key). No raw PM export was acquired/admitted in this phase.

NASA fire products distinguish fire, no-fire and no-observation states. A missing detection CSV row is therefore not automatically a monitored negative; retain quality/coverage/attribution before a qualified fire target. [NASA LAADS product description](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/science-domain/thermal-anomalies-fire/).
