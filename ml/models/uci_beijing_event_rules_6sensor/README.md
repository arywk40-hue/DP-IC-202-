# UCI Beijing six-sensor event-rule experiment

Training source: UCI Beijing Multi-Site Air Quality (501), 420,768 hourly
station rows from March 2013 to February 2017. See
`event_training_report.json` for the source checksum, dates, complete feature
and label order, fitted rows, class counts, and split metrics.

This model reproduces twelve deterministic sensor rules. The dataset contains
no independent observations confirming those weather events, so the metrics
are **rule-imitation metrics**, not weather-event detection accuracy. The model
has not been validated in Himachal Pradesh or on physical ESP32 hardware.

The six physical channels are temperature, relative humidity, pressure,
PM2.5, PM10, and wind. Eleven additional inputs are derived from these
channels and up to six hours of history. Ten event heads were fitted. The
severe-rainstorm and snowstorm rules had zero positive training rows and were
skipped; their C outputs are constant zero and must not be used as detectors.

`esp32_student/` holds the trained XGBoost heads.
`esp32_student/export/indra_event_classifier.h` is a separate C99 export,
checked on 2,048 complete rows against the Python model. It is not part of
the default six-hour forecast firmware.
