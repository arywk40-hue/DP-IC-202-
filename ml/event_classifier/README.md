# Six-sensor event-rule experiment

This is a separate research experiment. It learns twelve deterministic rules
computed from the six measured channels: temperature, relative humidity,
pressure, PM2.5, PM10, and wind speed. The classifier uses those readings and
eleven derived features, including changes that require up to six hours of
history. No seventh physical sensor is required.

The targets are **rule matches, not observed weather events**. A model score
against these targets measures rule imitation; it does not establish accuracy
for rain, fog, fire, or other real hazards. No Indian field validation or
physical ESP32 timing has been performed for this classifier. The six-hour
measurement forecast remains in `ml/six_sensor_forecast/`.

Model files and provenance belong in
`ml/models/uci_beijing_event_rules_6sensor/`. The report
`event_training_report.json` records the source checksum, split, feature and
label order, class counts, and validation/test metrics. Skipped rules have no
trained model and export a zero probability. The C export is
`esp32_student/export/indra_event_classifier.h`; its 17 inputs comprise six
sensor values and eleven derived quantities, so an ESP32 caller must compute
the derived quantities in the same order and from the same history.

From the repository root:

```bash
python3 -m ml.event_classifier.train
python3 -m ml.event_classifier.export
```

The export command compiles a C runner and compares it with XGBoost before
writing the header. For now, the header is an offline experiment and is not
part of the default ESP32 forecast build.
