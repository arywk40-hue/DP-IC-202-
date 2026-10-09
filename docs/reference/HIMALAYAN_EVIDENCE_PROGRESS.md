# Six-channel Himalayan research: evidence progress — 9 October 2026

The six deployed channels are temperature, humidity, station pressure, PM2.5,
PM10 and wind. They are a fixed experimental predictor set. Whether they supply
useful event-warning skill must be measured on independent events and sites;
neither a new architecture nor artificial training examples can establish it.

## Response to the supplied scope audit

The missing `snowstorm` and CLI `--targets` changes were local at the time of
the connected-repository audit. They are now pushed to `main` in commit
`295e292`, with a regression test preventing rainfall-only snowstorm admission.
No trained disaster head or ESP32 disaster warning was enabled.

The audit correctly distinguishes exact +6h measurement forecasts from events
occurring anywhere within the next six hours. The current independent-event
trainer still associates exact future observed windows. A warning-window model
requires an explicit target change and fresh evaluation. No six-hour achieved
cloudburst lead time is claimed.

A subsequent [warning protocol update](../HIMALAYAN_WARNING_PROTOCOL.md) adds
explicit next-H-hour onset labels and keeps this exact-window benchmark. Real
data admission, training and measured warning skill remain pending.

## Acquired evidence and remaining gaps

| Target | Available now | Remaining before model fitting |
| --- | --- | --- |
| Cloudburst | Registered IMD/MAUSAM discovery leads and prepared institutional data request | Verified local one-hour rainfall criterion, exact intervals, locations/uncertainty, matched inputs and monitored negatives |
| Flash flood | Locally acquired HiFlo-DAT historical compilation: 128 records, 1846–2020; remains candidate-only | Adjudicated flood episodes/definitions and time/location uncertainties, contemporaneous six-channel observations, monitored negatives |
| Landslide | New NASA report download and two reviewed 2023 GSI leads, described below | Original-source/clock/group review, matched causal inputs and monitored negatives |

### NASA report acquisition

The live [NASA COOLR report layer](https://gis.earthdata.nasa.gov/portal/rest/services/Landslides/COOLR_Reports_Points/FeatureServer/0)
returned **731** reports in the declared Indian bounding box, of which **208**
are listed in Himachal Pradesh. **46** reported coordinates are within 50 km of
Mandi; distance to a reported point does not prove that a sensor measured the
event location. The box also includes other Indian states; it is not a state
boundary or a complete Himalayan inventory.

Dates in this snapshot span 1990–2020; **none overlap the current 2023/2024
India weather archive**. Most reports have kilometre-scale or unknown location
accuracy. They are discovery candidates, not a new gold-standard label set.
NASA describes COOLR as a mixture of catalog, volunteer and research reports
in its [source overview](https://gpm.nasa.gov/applications/landslides/coolr).

The downloader verifies the complete object-ID inventory and page hashes.
Originals, source links, reported clocks and canonical candidate rows are kept
locally in `results/field_sources/coolr_north_2026-10-09/` and are Git-ignored.
Serialized ArcGIS dates do not automatically become verified UTC event onset.
The committed audit is `reports/hazard_context_phase/coolr_north_audit.json`.

### GSI leads overlapping 2023

The official [Kullu assessment report](https://bhusanket.gsi.gov.in/Output/LS_Incidence_Report/2023/Landslides%20in%20Kullu%20District,%20Himachal%20Pradesh%20on%20July%20and%20August%202023.pdf)
provides a Nigloodhar occurrence on 14 August 2023, described as early morning
(PDF page 40), and Gungi reactivation on 18 July 2023 at a reported 3:30 pm
(page 42). Two candidate rows preserve published coordinates and these clocks.
Unknown UTC interpretation, time/position uncertainty and physical groups stay
null. Calendar overlap alone does not establish matching sensor observations.

The locally retained original PDF is hashed; its publication/use rights remain
unresolved, and its content is not redistributed in Git. The review summary is
`reports/hazard_context_phase/gsi_kullu_review.json`; candidate rows are in the
ignored `results/field_sources/gsi_kullu_2023/` directory.

**New admitted training labels: 0. New model weights: 0.**

## Experiment that preserves the six-channel contract

1. Obtain continuous, synchronized observations of all six channels around
   independently monitored event and non-event periods. Existing NOAA weather
   records do not supply the missing particulate measurements. Do not join
   distant/elevation-mismatched stations or replace missing measurements with
   artificial values to declare a complete six-channel corpus.
2. Freeze a target definition, covered area and warning window separately for
   each event. Request rain gauges for cloudburst labels and occurrence logs for
   flash floods/landslides. These offline labels do not add a runtime sensor.
3. Compare persistence/simple baselines and a compact temporal model using
   causal histories. Split entire event groups and sites; keep calibration and
   final testing separate. Report event recall, false alerts per monitored day
   and achieved lead time, including uncertainty.
4. Study terrain/catchment context only as a separately named experiment if
   useful. Its physical role in flood/slope failure cannot be replaced by
   relabelling temperature/humidity patterns. The six-channel experiment may
   show limited skill; report that result rather than hide it.
5. Export a successfully tested model and verify host/ESP32 parity and physical
   board performance before any operational warning claim.

The institutional [IMD/Himachal request package](IMD_HIMACHAL_DATA_REQUEST_PACKAGE.md)
has also been updated with the [IMD student-category page](https://dsp.imdpune.gov.in/home_categories.php):
eligible students up to postgraduate level have a listed data-charge waiver,
subject to identity and authorized institutional undertaking requirements.
Availability and permitted use still need provider confirmation. No email,
enrolment or order has been submitted by the assistant.
