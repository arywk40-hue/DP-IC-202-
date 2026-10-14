# Himachal sources and independent label pipeline

The new source registry and adapters add to the existing `ml/hazard_context`
admission/matching engine. They do not weaken its gates or overwrite the v1/v2
warning experiments. The only shared target-set extension is independent `rain`;
the existing event schema already accepts text event types. The separate profile
is `configs/himachal_labels_v1.json`.

## Source access and immutable cache

`configs/himachal_sources_v1.json` records official provider documentation,
native cadence/resolution, source kind and unresolved reuse terms. Public JSON
adapters cover explicit ERA5 weather, global CAMS PM via Open-Meteo, and hourly
NASA POWER. They request UTC and explicit units/model selection. Context is
cached as modeled data, never an independent local gauge or six-channel station.

The [Open-Meteo historical API](https://open-meteo.com/en/docs/historical-weather-api),
[air-quality API](https://open-meteo.com/en/docs/air-quality-api) and
[NASA POWER hourly documentation](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/)
are the request references. Native CAMS cadence remains three hours despite hourly
API positions. POWER must explicitly declare UTC; an LST response is rejected.

```sh
python -m ml.himachal.data.download \
  --config configs/himachal_sources_v1.json --source open_meteo_weather \
  --start 2024-01-01 --end 2024-01-31 --output data/himachal/context
# Repeat with --offline to require verified cache and prohibit network.
```

Dates split into bounded calendar-month chunks; responses have a 64 MiB cap,
three attempts, rate-limit backoff, fixed-ETag range resume, and provider-host
redirect checks. A changed/missing ETag cannot append bytes to a different file.
Raw response hashes, requests, provider role/version, units, returned coordinates,
retrieval clocks and source-resolution metadata are retained. Same requests reuse
the exact verified receipt; changed bytes fail. Station/cell IDs and original
issue-time availability remain **unverified** when the provider has not supplied
them. The adapter does not invent a grid ID from the requested coordinates.

CDS/IMERG, IMD, CPCB, OpenAQ and HPSDMA use audited manual imports in this adapter.
Existing authorized CDS download tooling remains available separately. No IMD/CPCB
bulk scraping route, private collection URL or rights grant is assumed.

```sh
python -m ml.himachal.data.download --source imerg_final_v07 \
  --start 2016-01-01 --end 2025-12-31 --output data/himachal/imerg \
  --input /path/to/legitimate-export.nc --metadata /path/to/reviewed-metadata.json
```

The metadata requires actual provider version, station/cell ID, native interval,
source units, retrieval time, rights evidence/reviewer and original request.
No metadata/export returns `NOT_READY`. Credentials and signed-token URLs are
rejected from provenance. Imports preserve immutable original bytes and filename;
they are cached, **not automatically admitted**. Source-specific terms still need
review. Raw/working data stays local under ignored `data/himachal/`.

## Normalization and virtual identity

`imerg_hourly` requires explicit half-hour start/end, mm/h rate, cell ID, quality,
random-error and fill metadata. Each rate contributes `rate × 0.5 h` accumulation;
two valid intervals are required for an hourly total. Gaps, rejected/fill values
and zero-as-fill ambiguity stay unavailable. Quality/error evidence is retained.
Satellite cell precipitation is not local gauge evidence for cloudburst admission.

`power_hourly` verifies UTC, declared units/fill values and kPa-to-hPa conversion.
Missing PM stays null. Source grid pressure remains grid-surface pressure. Neither
adapter declares original operational availability that the archive cannot prove.

`sensor_frame` accepts simultaneous six-channel snapshots through the canonical
adapter and separates physical-site/registration histories. A reviewed site table
must establish Indian/Himachal identity, coordinates, source and co-location;
country/state is never guessed from a rectangular bounding box. Grid/synthetic
records cannot become a measured six-channel Indian corpus.

Virtual-node ancestry deduplicates the true upstream station/cell and valid time,
so OpenAQ/CPCB copies and repeated model-cell queries do not manufacture stations.
Conflicting duplicates are rejected rather than silently fused. Variables/units,
elevation/datum, pressure reference, publication time, resolution, uncertainty,
ancestry, version and licence remain visible. All virtual nodes are excluded from
the minimum physical quorum, including external observed stations by default.

## Independent outcome profile

The offline JSONL envelope has `record` (existing nullable event schema),
`measurement` and `evidence_category`. Measurement intervals preserve amount,
unit, accumulation statistic, actual instrument and local-gauge review. Original
records keep time/location uncertainty, reviewed physical event groups, source
hashes, rights and reported-time text. Never create precise onset time from an
approximate incident date or hourly accumulation endpoint.

- Rain: gauge-sensitive initial research definition ≥0.2 mm liquid accumulation
  in one explicitly timed hour. It is not an official universal hazard definition.
- Snowstorm: independently confirmed occurrence under a reviewed definition;
  snowfall amount or cold/humid measurements alone are insufficient.
- Observed cloudburst: reviewed local gauge ≥100 mm over a verified hour, with
  independently reviewed event identity/onset. Public output remains
  `cloudburst_risk`; model/satellite/media candidates cannot supply this truth.

Rain/cloudburst structural intervals must agree with the legacy scalar measurement
and units. Daily totals cannot pass the hourly check. Unsupported definitions,
missing rights/identity/clocks/uncertainties and unapproved source roles remain
unadmitted. Possible cloudburst records block conflicting negative rain windows,
without creating positive rain labels. Candidates with unknown time/location stay
unknown and can conservatively exclude negatives.

```sh
python -m ml.himachal.data.labels --events /path/to/events.jsonl \
  --observations /path/to/native-snapshots.jsonl --monitoring /path/to/monitoring.json \
  --config /path/to/reviewed-himachal-label-profile.json \
  --output data/himachal/labels-v1 --offline
```

The reviewed profile adds `approved_sources` and `approved_sites` to the supplied
definitions. The existing source-admission fields remain mandatory. Monitoring
must match those sources, rights and exact outcome definition, cover the whole
six-hour future window and declared spatial radius, and have no candidate/event
overlap. Missing reports are not negatives. The adapter requires 24-hour complete
six-channel hourly history, preserves whole physical groups and never treats
ongoing/post-onset observations as new six-hour precursor positives.

Outputs are deterministic `labels.csv` plus a hash/config/input manifest, target
counts, rejected reasons, monitoring coverage and detailed `NOT_READY` branches.
Existing differing outputs refuse overwrite. Initial ≥50 groups/≥10 positive
sites are only a cohort-review screen, not final evaluation/deployment approval.
Further train/dev/calibration/test and season/valley gates remain mandatory.

The committed event/monitoring fixtures are **synthetic software contracts** and
never admit empirical training. Tests have an explicit internal contract mode to
exercise matching; it tags every row inadmissible and still returns `NOT_READY`.
The public CLI does not expose that override. Rules, simulations and satellite
rainfall cannot supply independent labels merely to make fitting succeed.
