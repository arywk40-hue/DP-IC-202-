# Limits of the event-rule experiment

The twelve targets in this package are deterministic threshold rules applied
to temperature, relative humidity, pressure, PM2.5, PM10, wind speed, and
quantities derived from their recent history. They are not observations of
rain, fog, smoke, frost, or other weather events. A high F1 or AUC against
these targets only means the model has learned to reproduce the rules.

Rules for rain, snow, fog, smoke, dust, and inversion use sensor patterns as
proxies. The source dataset does not supply independent ground-truth labels
for those events. Rare rule matches can produce unstable validation metrics;
inspect each event's positive count and confusion matrix in
`event_training_report.json`. A rule with no positive training examples is
skipped and must not be interpreted as a negative detector.

Hourly data support one-hour and six-hour changes. They do not support a
measured fifteen-minute pressure trend, so no fifteen-minute feature or
threshold is used. Derived history features are unavailable from a single
sensor snapshot. The heatmap now requires seven consecutive hourly readings per node.
Unavailable history or untrained heads return missing scores, never zero-filled
features. Both spatial strategies remain unvalidated against field observations.

Before any alerting claim, collect independently labeled events in the
deployment region, evaluate each class across time and stations, calibrate
probabilities, and test the complete sensor-to-ESP32 pipeline on hardware.
