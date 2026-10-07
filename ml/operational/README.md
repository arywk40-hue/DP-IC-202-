# Operational prototype components

This directory adds versioned sensor records, guarded spatial map snapshots,
experimental event-rule diagnostics, an authenticated local ingestion service,
and driver parsing helpers. It does not train or replace the saved India forecast
model. The ESP32 preparation harness in `esp32/operational_node/` compiles with
physical mode disabled by default; it has not been flashed or sensor-calibrated.

From the repository root, run the synthetic, read-only two-node map demo:

```sh
python3 -m ml.operational.demo --output /tmp/indra-operational-demo --nodes 2
```

The output includes `index.html`, `map.json`, `observations.json`, and
`contracts.json`. Use a new empty output directory for each run. With no
terrain cache, the demo cannot produce pressure estimates between nodes;
unavailable values remain null. The map is not a measured forecast-accuracy
test, and the fixture is synthetic. The three-node option uses `--nodes 3`.

The saved India forecast can be exercised separately with the commands in
[`ml/india_sensor/README.md`](../india_sensor/README.md). Held-out archive
results from 7 October 2026 are in
[`reports/operational_phase/ML_TEST_2026-10-07.md`](../../reports/operational_phase/ML_TEST_2026-10-07.md).
Real Mandi accuracy requires synchronized sensor measurements and observed
six-hour outcomes; no connected ESP32 port was available for this test.
