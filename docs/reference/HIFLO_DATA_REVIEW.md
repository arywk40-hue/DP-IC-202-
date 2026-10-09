# HiFlo-DAT acquisition and model suitability — 8 October 2026

The database has been released. Its [public collection](https://doi.org/10.17870/bathspa.c.7589948)
contains the [event spreadsheets](https://data.bathspa.ac.uk/articles/dataset/_HiFlo-DAT_Database/28053218)
and [geospatial file](https://data.bathspa.ac.uk/articles/dataset/_HiFlo-DAT_Database_Geospatial_Data/28053254).
Both repository items specify **CC BY 4.0**. Their originals were downloaded
into `results/field_sources/hiflo/`, which is Git-ignored. Published file sizes
and MD5 checksums matched; SHA-256 receipts are recorded in
`reports/hazard_context_phase/hiflo_audit.json`. No raw spreadsheets were added
to Git or modified.

Read-only workbook inspection found 128 merged event records spanning
1846–2020 and 59 geospatial placemarks. There are 71 complete start calendar
dates. Nineteen records give start-time information: twelve Excel time-of-day
values and seven qualified text entries. Unknown or approximate times were not
converted to invented midnight UTC timestamps. Coordinates are degree-labelled
text, with source precision categories retained.

The records include river floods, flash floods and other processes. They are
not 128 verified cloudbursts. No monitored non-event periods or aligned
deployment weather channels are supplied. The database ends before our current
2023–2024 weather archive, so there is no temporal overlap for fitting against
that archive. Earlier matched observations and record-specific time/location
validation are required.

One consistency flag requires source clarification: event 94 lists 62.6 mm
over three hours alongside a 25 mm/h mean intensity. The ratio is about
20.87 mm/h. The published fields were preserved; none was accepted as a
verified one-hour cloudburst measurement.

The source is registered as `hiflo_dat_kullu_v1`, with open-license metadata
verified and event admission still **candidate**. Training labels created: 0.
Model weights fitted from this source: 0. The updated
[request package](IMD_HIMACHAL_DATA_REQUEST_PACKAGE.md) addresses the weather,
event and negative-monitoring exports still needed.
