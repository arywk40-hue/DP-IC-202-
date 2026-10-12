# Low-cost data routes for Mandi — checked 12 October 2026

Scope: six fixed measurement channels plus causal features; next-six-hour
cloudburst, storm, flash-flood, landslide and snowstorm research. Pilot event
periods remain July–August 2023 and 2024. Numerical modeled-data testing already
covers 2024-01-01 through 2026-10-10.

This review checked public documentation and published location metadata. It
did not download a new observational corpus, confirm complete coverage, admit
new hazard labels, fit new models or send requests. Web search failing to find
a station is not evidence that no such station exists.

## Which routes help

| Source | Role for this project | What still needs checking |
| --- | --- | --- |
| ERA5 / Open-Meteo archive | Gridded weather context and numerical research benchmarks | Product, grid/elevation, surface-pressure reference, revisions and issue-time availability; not IMD station observations |
| NASA GPM IMERG | Satellite precipitation context around candidate events | Retrieval uncertainty, rain-rate versus accumulation units, run/version and latency; not a local cloudburst gauge |
| NOAA GHCNh / SYNOP / METAR | Observed weather and present-weather reports | Station identity, reporting gaps, pressure type, report time versus event onset, and matched PM |
| OpenAQ / CPCB / HPSPCB | Candidate measured PM2.5 and PM10 plus station metadata | Exact location, original provider, dates, cadence, units, QC and source-specific use terms |
| HPSDMA / IMD realized-event records | Candidate local event identity, timing and locations | Occurrence versus warning, onset uncertainty, duplicate episodes and monitored non-event coverage |
| DesInventar / EM-DAT | Disaster discovery and historical context where covered | Actual Himachal coverage and timing detail; cannot infer non-events from an absent record |

The [Open-Meteo archive documentation](https://open-meteo.com/en/docs/historical-weather-api)
describes several reanalysis/model products. The existing Mandi benchmark
explicitly uses ECMWF IFS weather and CAMS global PM, not measured six-channel
station data. Downloading another modeled source alone does not resolve that
validation limitation.

[NASA's IMERG documentation](https://gpm.nasa.gov/resources/documents/imerg-v07-technical-documentation)
describes half-hourly 0.1-degree precipitation estimates. Use these as satellite
context or explicitly satellite-defined targets. They do not establish the
project's independently verified local one-hour cloudburst label.

## Concrete particulate lead

OpenAQ lists [HIMUDA Complex Phase-1, Baddi — HPPCB, location 301389](https://explore.openaq.org/locations/301389)
as a stationary reference-grade CPCB-provider location, reporting since
24 March 2022. Published channels include PM2.5, PM10, temperature, humidity and
wind speed. Pressure is not listed. This metadata is a discovery lead, not proof
of complete valid pilot-period measurements. Baddi observations cannot be
relabeled as Mandi observations or joined to Mandi weather solely by timestamp.

No hourly measured PM archive near Mandi has been verified in this review.
Also, [New Mandi, Muzaffarnagar — UPPCB, location 6923](https://explore.openaq.org/locations/6923)
is in Uttar Pradesh, not Mandi in Himachal Pradesh; name matching is insufficient.

The [OpenAQ v3 API requires an API key](https://docs.openaq.org/using-the-api/api-key).
Its [location query](https://docs.openaq.org/api/operations/locations_get_v3_locations_get)
uses latitude,longitude and supports a maximum radius of 25 km. For Mandi,
start with `coordinates=31.7100,76.9300&radius=25000&iso=IN`; review both PM
parameters and original station metadata. Wider searches require a bounding
box or multiple queries, not silently increasing the radius beyond its limit.
Keep any key in a local environment variable, never a committed file or report.

OpenAQ also documents a [public S3 measurement archive](https://docs.openaq.org/aws/about),
organized by location ID, year, month and day. Known location IDs provide an
alternative route to historical files. Confirm actual objects before relying
on coverage; files can be patched. API availability, archive availability,
source rights and measurement quality are separate checks. AWS Athena is not
required for direct file downloads and can incur charges if used.

## Disaster-record corrections

The [DesInventar database selector](https://www.desinventar.net/DesInventar/)
lists Orissa (India), 1970–2014. This review did not verify a Himachal database
there; do not assume nationwide local-event coverage from the platform name.

[EM-DAT access documentation](https://doc.emdat.be/docs/data-accessibility/)
provides registered non-commercial public access and a separate archive.
Its [FAQ](https://doc.emdat.be/docs/additional-resources-and-tutorials/faq/)
describes entry thresholds and country-level impact reporting, with some
subnational location information. It is a discovery source, not an exhaustive
hourly Mandi event/non-event monitoring log. Product terms must be checked
before use or redistribution, including patent-related or commercial plans.

HPSDMA advisories and IMD warnings can identify leads; a forecast warning is
not evidence that the event occurred. Seek realized-event records and review
their timing and locations against the existing admission protocol.

## Acquisition order

1. Verify measured PM station inventory near Mandi and pilot-date availability
   through OpenAQ/CPCB and the HPSPCB Mandi office. If no suitable archive
   exists, arrange co-located six-channel field recording; do not fill the
   observational gap with distant stations or modeled PM without naming a
   separate experiment.
2. Review the existing NOAA storm candidates: 869 station/report timestamps,
   including 26 at Mandi, across six station IDs in 2023/2024. These are not
   independent episodes or known onsets. See the
   [storm evidence audit](../../reports/hazard_context_phase/storm_observation_audit.json).
3. Obtain gauge rain intensity, realized-event onsets and independently reviewed
   monitoring intervals using the already drafted
   [institutional request package](IMD_HIMACHAL_DATA_REQUEST_PACKAGE.md).
4. Add IMERG as separately identified satellite context if useful. Keep original
   downloads local and ignored, with URL, retrieval time, hashes and metadata.
5. Admit evidence, construct complete causal six-channel histories, then fit and
   evaluate held-out event episodes. Until then, real hazard accuracy remains
   undefined. Synthetic data can test software behavior, not establish it.
