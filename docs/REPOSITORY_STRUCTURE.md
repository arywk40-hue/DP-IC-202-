# Repository Structure

The repository is divided by execution environment rather than by experiment.

```text
.
|-- ml/                 Offline Python pipelines and model artifacts
|   |-- docs/           ML design and experiment reports
|   |-- generated/      Exported C model headers
|   |-- real_india_data India ingestion, training, and parity tools
|   `-- model_*/        Versioned experiment outputs
|-- firmware/           PlatformIO ESP32-S3 application and tests
|   |-- lib/HazardModel Stable C++ model wrapper
|   |-- src/            Board smoke-test application
|   `-- test/           Native and on-device Unity tests
|-- tests/model/        Compiler-level tests for exported C headers
`-- .github/workflows/  Automated quality and build gates
```

## Ownership Boundaries

### ML

The ML workspace owns feature ordering, training statistics, model selection,
distillation, and C export. The exporter is the only supported way to change a
generated model header.

### Firmware

Firmware owns input validation, alert thresholds, board integration, sensor
adapters, timing, and transport. It consumes the generated model through
`xgb_model_inference()` and does not parse Python model files.

### Tests

The root C smoke test catches malformed or non-compiling model exports. The
PlatformIO native test validates the firmware wrapper on every pull request.
The ESP build proves compatibility with the selected board toolchain. A real
board is still required for on-device tests and resource measurements.

## Promotion Gate

A model is eligible for the firmware path only when all of these pass:

1. Python versus C probability parity.
2. Exported C model smoke test.
3. Native firmware wrapper tests.
4. ESP32-S3 firmware compilation.
5. On-device Unity test on the physical board.
6. Recorded latency, flash, and RAM measurements.

Passing the build gates proves integration correctness. It does not by itself
prove hazard accuracy or field readiness.

