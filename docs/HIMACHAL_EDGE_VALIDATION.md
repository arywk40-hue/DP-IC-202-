# Himachal local research node — Phase E

`esp32/himachal_node` is a separate application. It uses the existing operational
sensor abstractions and new generated local diagnostics/rules. It does not select
Beijing weights, invent an empirical hazard head or transmit external alerts.

## Diagnostics and generated identity

`configs/himachal_anomaly_v1.json` holds initial research settings: a fixed
16-reading ring per channel, eight valid samples of warm-up, median/MAD residuals
with explicit scale floors and an EWMA diagnostic. These settings have not been
fitted to independent local development observations. They are not sensor
accuracy or event-detection claims.

Python and generated C share configuration/hash, state meanings, float32
telemetry and double intermediate arithmetic. Range/Inf/self-test failures are
sensor faults; missing NaN is unavailable. CRC/time/clock rejection does not
advance the baseline. Long gaps rewarm the state. A valid fast weather change
is an environmental anomaly and remains valid input. Calm zero wind and a
constant reading alone are not diagnosed as failed sensors.

```sh
python -m ml.himachal.anomaly_codegen \
  --config configs/himachal_anomaly_v1.json \
  --output esp32/himachal_node/include/indra_anomaly.h --verify
python -m pytest -q tests/test_himachal_anomaly.py tests/test_himachal_anomaly_c.py
pio run -d esp32/himachal_node
```

The generator verifies the temporary header before publishing it and writes a
parity manifest. The local rule header is generated from the same feature/rule
configurations as Python. CI checks committed bytes and compiled stateful parity.
Tests include warm-up, boundary/adjacent values, gaps/replay/CRC/clock failures,
missing/range failures, reboot, slow drift, constant calm wind and abrupt weather.

## Local rule capabilities and missing states

The bounded local collector supports two explicit modes:

| Native interval | Supported local evidence | Unavailable evidence |
| --- | --- | --- |
| 60 seconds | Native 15-minute cloudburst-risk pattern after sufficient genuine history; preceding-hour PM baseline needs 75 minutes | Six-hour rain/snow pressure history: buffer intentionally spans only 75 minutes |
| 3600 seconds | Rain/snowstorm condition-risk rules after complete six-hour history and distinct hourly cloudburst companion | Native 15-minute pressure, temperature or wind changes |

The collector never expands hourly readings into minute samples. Missing
intervals restart collector history; missing channels remain null per channel.
The compact collector uses the initial PM floor/relative-decline proxy; it does
not accept independent calibrated PM noise sigmas. Use the server feature engine
when three-sigma noise adjustment or a longer native history is required.

Native mode must not be presented as a working local six-hour rain/snow detector.
The server can process longer complete native histories through the full feature
engine. Local probabilities remain null, trained-event-model mask is zero,
lead time is null and indication stays `LOCAL_ONLY` with dispatch `DISABLED`.
Local candidates are neither quorum decisions nor confirmed hazards.

## Serial synthetic demonstration

Default mode performs no physical IO. Supply one record per exact 60-second step:

```text
unix_seconds,T_C,RH_percent,station_P_hPa,PM25_ug_m3,PM10_ug_m3,wind_mps,crc_ok,clock_uncertainty_seconds
1767225600,20,60,900,25,50,0,1,2
```

`crc_ok` and clock uncertainty here are explicit test metadata supplied by the
host, not a verified physical link/clock. Serial records are always tagged
`synthetic_demo`; wind calibration in this path is a synthetic contract assumption.
They cannot become field evidence merely by passing the parser. Inputs are
bounded; malformed/extra fields refuse. `INFO` reports identities/capabilities;
`RESET` clears local state. Array order is always the six channels shown above.

JSON includes measured input array, diagnostic states/masks, rule scores/coverage,
abstention and local-candidate masks, source/profile/version, null probabilities
and disabled dispatch. `inference_latency_us` is instrumented around actual
on-board computation if the firmware is later run. No latency value has been
measured on a physical board in this phase.

## Physical enablement

Copy the example into ignored `include/device_config.h` only after the actual
board, pins, wind curve, surveyed EGM96 elevation, sensor calibration, native
cadence and clock uncertainty are known. Default pins are −1 and physical mode
is false. Enabling requires explicit cadence/calibration/site verification plus
valid clock uncertainty and wind/survey configuration. SensorHub additionally
checks pin validity/uniqueness and calibration inputs before acquiring.

The GPIO/RTC/GNSS/PMS drivers are prepared interfaces, not validated installation
claims. PMS CRC/staleness gates preserve missing PM. Physical wind averages the
actual encoder-derived readings over a complete native interval, with a small
sampling-boundary tolerance; incomplete/first intervals are unavailable. Actual
sampling/exposure/calibration must still be checked on the installed device.
No radio is enabled by this firmware. Actual peer protocol/RF readiness belongs
to later stages and cannot be inferred from successful compilation.

The configured compile target is the existing ESP32-S3 DevKitC-1 N8/no-PSRAM
profile. The actual board has not been identified or connected for this work.

## Measured software receipts and remaining hardware work

- [Generated host parity receipt](../esp32/himachal_node/include/indra_anomaly.parity.json):
  220 stateful synthetic rows; 424-byte anomaly state. No heap in inference.
- [Xtensa object/static stack analysis](../reports/himachal/anomaly_cross_object.json):
  5,252-byte object; 1,084-byte text, 80-byte literals, 144-byte read-only data,
  424-byte BSS. Static frames: 480-byte push, 176-byte median, 32-byte caller.
  This supports the proposed module budgets under static analysis; linked
  floating-point/libm helpers and real peak stack must not be silently omitted
  from a physical resource claim.
- [Four cross-build receipts](../reports/himachal/edge_cross_builds.json):
  full firmware RAM/flash and ELF/bin identities. These include the framework
  and drivers; the 32 KiB proposal applies to the anomaly module, not the whole
  Arduino application. The history buffer is a separate bounded allocation.

All of the above are software/synthetic engineering evidence. Board execution,
installed pin/driver behavior, physical inference latency/peak stack, power,
calibration, cold/condensation performance, soak stability and radio operation
remain **NOT_TESTED**. No cloudburst accuracy follows from these receipts.
