# IMD and Himachal data request package — draft, not sent

Prepared 8 October 2026. Fill the bracketed fields, confirm the intended use with
your supervisor, and arrange the institute's endorsement and authorized
signatures. Request availability and an estimate first; this draft is not an
order, payment, undertaking or permission to release supplied data.

## Where to email — checked 9 October 2026

Send separate requests, with your supervisor copied and the applicable letter
attached. Use your IIT Mandi email account. These are publicly listed enquiry
addresses; approval and the final enrolment/order route remain with the provider.

| Request | To | Suggested CC | Attach |
| --- | --- | --- | --- |
| IMD station weather/rainfall | `data.service@imd.gov.in` | `awslabpune@gmail.com`, `rameshchand66@imd.gov.in`, supervisor | IMD letter and Annexes A/B |
| HPSDMA event logs | `sdma-hp@nic.in` | Supervisor | Section 2 request |
| NWIC rainfall export/metadata | `helpdesk-nwic@gov.in` | Supervisor | Section 3 request and source dataset URLs |

The [current IMD portal contact listing](https://dsp.imdpune.gov.in/data_request_form_auto.php)
lists the observation-data and AWS/ARG addresses above.
[IMD Shimla's directory](https://mausam.imd.gov.in/shimla/contactus.php) lists
Ramesh Chand for Data Supply/Training at `rameshchand66@imd.gov.in`; its general
centre mailbox is `metcentresml@gmail.com` if local routing is needed.
[HPSDMA](https://hpsdma.nic.in/index1.aspx?langid=1&lev=2&lid=41&lsid=44)
lists the state authority address; [NWIC's portal](https://nwdp.nwic.gov.in/)
lists its helpdesk address. Start with an inventory/availability and quotation
enquiry. No email has been sent by the assistant.

## 1. IMD letter

**To:** National Data Centre / appropriate AWS–ARG data authority, IMD

**Subject:** Station inventory, pilot data availability and cost estimate for
academic Himalayan extreme-weather forecasting research at IIT Mandi

Dear Sir/Madam,

I am [full name], [programme and roll number] at Indian Institute of Technology
Mandi, working under [supervisor name, designation and department]. We request
guidance and a data-availability statement for an academic study of extreme
rainfall and related Himalayan weather events, initially focused on Mandi and
the Kullu–Manali region.

Our prototype's deployed environmental inputs are temperature, relative
humidity, station pressure, PM2.5, PM10 and wind speed. Requested rainfall and
event records will provide independent targets and validation. Meteorological
inputs and event labels will be kept separate. Missing particulate measurements
will not be fabricated; any reduced-input experiment will be separately named.

As a first stage, please provide:

1. The AWS/ARG/SRRG and relevant synoptic station inventory for Himachal Pradesh,
   including coordinates, elevation, operation dates, native sampling intervals,
   available variables and missing-period coverage.
2. Availability and a cost estimate for the pilot in Annex A, before any wider
   order. Please identify the custodian of Bahang/DGRE measurements where these
   are outside IMD's holdings.
3. Available independent event evidence and radar products in Annex B.
4. Written product-specific terms for institutional processing, derived model
   weights, academic publication, patent-related research, redistribution and
   possible future commercial use. The present study is proposed as
   [confirm non-commercial academic scope with supervisor]. Potential patent
   review or later commercialization must be disclosed and cleared separately;
   we do not seek to use an academic permission as commercial authorization.

We will complete the relevant enrolment and official undertaking through the
authorized institutional signatory after receiving your guidance. Please advise
on required endorsement, applicable academic concessions, charges and the
correct submission route.

Yours faithfully,

[Full name]  
[Programme / roll number]  
[Institutional email and phone]  
Indian Institute of Technology Mandi

**Supervisor endorsement:** [Name, designation, department, signature/date]  
**Authorized institutional signatory, if required:** [Name, office, seal]

### Annex A — observations and metadata

**Pilot:** complete July–August 2023 and July–August 2024 at available stations
in Mandi, Sundernagar, Bhuntar/Kullu, Manali/Bahang, Padhar and Shimla. Include
all records, not only rain days or disaster hours. These months provide event
context, not an assumption that all remaining hours are disaster-free.

**Extended availability enquiry:** 2018–2025, year-round where available.
The surface catalogue's identifiers Mandi 42078, Sundernagar 42079, Bhuntar
42081 and Shimla 42083 are enquiry references, not proof of hourly AWS coverage.
Please confirm current identifiers and station continuity.

| Field | Requested interpretation |
| --- | --- |
| Air temperature | Native observations and documented unit/exposure |
| Relative humidity | Percentage with QC and missing-value codes |
| Pressure | Station pressure with units/reference; keep MSL pressure separately identified |
| Wind speed | Native averaging interval, units, anemometer height; gusts separately identified if measured |
| Rainfall | Native timestamped increments or rate; 5–15-minute records preferred when available; hourly/3-hour/daily totals distinguished |
| Time | Timezone, interval start/end convention, clock changes and data availability/receipt information |
| Site | Identifier, coordinates, coordinate accuracy, elevation and datum, relocation/instrument history |
| Coverage/QC | Original flags, calibration metadata, outages, whether zero means observed dry or missing |

CSV is preferred for station tables; documented native formats are acceptable.
Please preserve actual cadence and avoid interpolating hourly values from
synoptic or daily records. Identify particulate measurements only if actually
colocated and available; otherwise indicate their absence and any known separate
data custodian.

### Annex B — event and radar evidence

Please identify available dated and located observations of localized extreme
rainfall/cloudbursts, storms, snowfall/freezing episodes, visibility/fog and
heat/cold episodes. For each record, please include its definition, original
date/time text and timezone, location/footprint, uncertainty, reporting and
measurement source, revision/QC status and stable event identifier.

For a cloudburst label, we need the underlying rain-rate or rolling one-hour
measurement, instrument/site and exact accumulation window; a daily total or
the event name alone cannot establish the intensity criterion. Please distinguish
gauged events from media reports, impacts, warnings and modeled estimates.

Please state which sites/periods were monitored and how non-occurrence is
established. Missing incident reports or observation outages are not verified
negative labels.

For the July 2023 Manali episode, the referenced case study is
[MAUSAM 6447](https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/6447).
Please advise on underlying DGRE/IMD subhourly station records. If archived
Doppler radar coverage exists for these locations and event periods, please
provide its inventory, available reflectivity/rainfall products, spatial/time
resolution, QC, permitted use and a separate cost estimate. Do not substitute
forecast alerts for observed event truth.

## 2. HPSDMA / district disaster authority request

**Subject:** Located and timed incident records for academic research at IIT Mandi

Dear Sir/Madam,

For the research described above, please provide available machine-readable
incident logs for Mandi and Kullu districts (2018–2025), with state-wide coverage
listed separately if available. We seek reported cloudbursts, flash floods and
rainfall-associated landslides, with stable record IDs, original times, locations,
coordinates/footprints and uncertainty, report revisions, supporting evidence
and the source of any rainfall intensity measurement.

Please identify separately whether an incident's cloudburst classification was
gauge-verified, inferred from damage or obtained from media. Please describe the
reporting/monitoring coverage and provide the conditions for research use and
publication. District incident counts alone do not provide hourly training labels.

[Requester and supervisor details/signatures as above]

## 3. NWIC / Himachal water department request

**Subject:** Complete weather/rainfall export and measurement metadata

Dear Sir/Madam,

Please provide available Himachal telemetry rainfall and weather records for
the pilot periods above, including observed zero-rainfall hours, missing values,
quality flags and station inventory. Please clarify whether the rainfall export
contains only wet records, whether rainfall is an increment or cumulative
counter, reset conventions, native interval and timestamp timezone.

For the supplied temperature/humidity/pressure/wind files, please confirm units,
station-pressure reference, station elevation/datum and interpretation of
repeated values. Please specify access, retention, institutional research,
derivative/publication and redistribution permissions independently.

[Requester and supervisor details/signatures as above]

## 4. IIT Mandi internal enquiry

Ask the supervisor or relevant campus lab for weather-station inventory,
calibrated T/RH/station pressure/wind records, rain-gauge records, colocated PM
coverage, explicit timestamps and QC. Confirm campus and external data permissions
and whether historical event-period measurements exist before arranging a new
sensor campaign.

## Checked routes and terms

- The [IMD Data Service Portal](https://dsp.imdpune.gov.in/index.php?error_code=E1)
  advertises historical data procurement, enrolment, availability and cost
  enquiries. Its listed correspondence address is **data.service@imd.gov.in**;
  ask it to confirm the current AWS/ARG route.
- A [3 October 2025 AWS RTI reply](https://internal.imd.gov.in/section/rti/rticases/20260112_rti_212.pdf)
  lists **sankar.nath@imd.gov.in** for purpose-specific organizational requests
  and says commercial AWS use is prohibited. This is a dated reference, not a
  guarantee of the current contact or a universal rule for every IMD product.
- The [official undertaking](https://dsp.imdpune.gov.in/documents/COU-1.pdf)
  requires purpose-limited use, permission before passing supplied data to others,
  acknowledgement and an institutional signature. It does not state a requirement
  to publish openly. Confirm applicable product terms before signing.
- The asserted 2025 public-portal closure date, present AWS station counts,
  proposed-station counts and delivery times were not verified in this check and
  are not used as facts in these letters. No letter, form, account, order,
  undertaking, payment or external message has been submitted.

The repository's 50-independent-event floor is a predeclared research screening
policy, not an IMD eligibility rule or proof that 50 events ensure model skill.
The initial availability request need not wait until that floor can be met.
HiFlo-DAT's public spreadsheets have now been acquired separately; see
[their data review](HIFLO_DATA_REVIEW.md). They provide historical flood leads,
not verified hourly cloudburst labels or current sensor observations.
