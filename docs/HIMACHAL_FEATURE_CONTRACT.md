# Himachal native feature contract v1

`ml.himachal.features.build_packet(records, issue_time_utc)` produces deterministic
JSON input features. It does not train a model or supply independent event labels.
Definitions are frozen in `configs/himachal_features_v1.json`; the packet carries
its hash and a hash of the input snapshots actually available by issue time.

## Inputs and provenance

`ml.himachal.contracts.snapshot` accepts exactly the six named measurements and
their explicit units. It reuses the existing operational unit/range/QC adapters.
Kelvin/Celsius, Pa/hPa and km/h/m/s conversions are supported. Missing/rejected
channels remain null; original values/units are retained separately. NaN/Inf raw
values have a string representation; learned numerical inputs never contain them.

Required metadata includes node, physical-site and registration identities,
WGS84 position, elevation/datum, instrument and wind heights, native cadence,
source class/ID/cell, pressure reference, sensor model and per-channel calibration
IDs (null when unknown). Elevation/heights can explicitly be unknown. Model grids
must name the real provider cell. These fields are not extra physical sensors or
client-granted authentication privileges. They remain separate from six inputs.

Observation and valid time must agree. All timestamps require a timezone and are
converted to UTC; `available_at_utc` is mandatory and cannot precede observation.
For display use `Asia/Kolkata`, without changing calculation clocks. Native samples
must lie on their declared exact UTC grid; the cadence must divide an hour.

One feature history has one fixed site, registration, position, height, pressure
reference, source and calibration segment. Changes require a new segment rather
than mixing histories. Duplicate/reordered/off-grid input is rejected. Gaps are
not filled. A late packet can inform later issues only after its actual arrival.

Station and grid-surface pressure can produce separately tagged same-source
tendencies. Sea-level/unknown pressure stays unavailable. Grid context never
becomes a measured station pressure. Event-rule deployment separately requires
station pressure and observed/physical or explicitly synthetic-demo provenance.

## Features and units

Current values retain canonical units: degC, %, hPa, ug/m3, ug/m3, m/s. Each
channel has exact 15-minute, one-hour and six-hour changes and normalized rates
per elapsed hour, plus six-hour native-sample mean/population standard deviation.
Windows require every actual native sample from start through issue, inclusive.
RH changes use **percentage points**, with rates in percentage points/hour.
No hourly record can establish a quarter-hour change or a true instantaneous gust.
The storm-sequence pre-drop window is separately named: six hours ending at
issue−15 minutes, followed by a disjoint final 15-minute pressure-rebound window.
The feature packet does not infer a rebound from a six-hour total change.

Seven complete hourly snapshots span six hours; optional teacher history spans
24 hours. Their availability flags are distinct. At finer native cadence these
flags conservatively require complete native support throughout the window.

The PM ratio is PM2.5/PM10 and is null at zero/missing denominator. PM2.5 greater
than PM10 is flagged for review; the ratio is not silently clipped.

Hourly PM-decline baseline: median of the three preceding complete hourly values.
For finer native data, those hourly values are complete arithmetic means over
the three preceding completed hour windows. Native washout uses its separately
named preceding-hour median on `[issue−75 min, issue−15 min)` and current PM.
The baseline excludes the current decline interval. Both channels must decline:
PM2.5 by at least max(5 ug/m3, 20% baseline), PM10 by max(10 ug/m3, 20% baseline).
Baselines below 10/20 respectively make the proxy unavailable. An identified,
already available co-location noise calibration can additionally require a
three-sigma decline. Neither PM decline nor non-decline proves rainfall status.

Sharp hourly RH change starts at absolute 10 percentage points. The wind-increase
proxy starts at a genuine 15-minute increase of 3 m/s and current wind 8 m/s;
an explicit wind calibration ID is required. Calibration metadata is a source
claim until independently checked by the ingestion/registration layer. No gust
observation is inferred. June–September uses the Indian local calendar only.
The separate hourly companion applies that wind increase/current-wind setting
over a genuine full hour and retains a distinct name; it is not a 15-minute proxy.

## Meteorological estimates

The new helper uses [NPL water/ice Magnus equations](https://www.npl.co.uk/resources/q-a/dew-point-and-relative-humidity).
RH means saturation over liquid water. Water-domain computation is restricted
to −45…60 C, with result-domain checks. Zero RH has unavailable dew/frost point.
Below freezing, water dew point is explicitly labelled supercooled-water; frost
point is calculated from the same vapour pressure using ice coefficients and
returned only within −65…0 C. VPD uses liquid saturation, in kPa. No pressure
enhancement correction or instrument accuracy guarantee is claimed.

Heat index follows the [complete NWS calculation](https://www.weather.gov/tbw/heatindex):
preliminary simple index averaged with air temperature, then Rothfusz and the
low/high humidity adjustments where applicable. Fahrenheit intermediates convert
back to Celsius. A conservative implemented air-temperature screen of 40…112 F
returns null outside it; this screen is a research guard, not an NWS certification
of the entire temperature/humidity rectangle. Branch/status is always present.

## Packet and evidence

The packet has `schema_version`, issue/observation times, site/source metadata,
`features`, history flags and provenance/configuration hashes. Each feature has
a stable evidence ID, numerical/boolean value or null, unit, status and relevant
window/baseline detail. `training_label_admissible` is always false. Confidence,
rainfall measurements, event probabilities and forecast lead times are not
manufactured by the feature engine. Frozen existing model features/headers were
not changed; they require their original preprocessing.

The committed native CSV is a **synthetic software fixture**. It is not Indian
weather data and must not enter an empirical training or accuracy table.
