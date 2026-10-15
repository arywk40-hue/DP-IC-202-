# Himachal neighbour and network research phase

This phase supplies tested Python registration, health, neighbour selection and
authenticated consensus components, a portable C frame codec/policy, and a
synthetic radio scheduler. It is not connected to the active dashboard or to a
physical radio. It does not change the active forecast model or event rules.

## Runtime contract

- Keep exactly six measurement channels. Three ordered event bits represent
  rain, snowstorm and cloudburst risk; these are current rule indications.
- An operator provisions reviewed registrations and distinct per-node keys.
  Provisioning files containing keys belong in ignored private storage with
  owner-only permissions, never in Git or an API response. Registration changes
  require new registration IDs and rotated keys; retired IDs remain reserved.
- Registration batch validation is atomic, including retired identity history.
- Health excludes missing/faulty channels, stale observations, uncertain clocks
  and critical batteries. Three good observations are required for recovery;
  confirmed persistent faults require a maintenance review. A regional change
  alone is not evidence of a sensor fault.
- Neighbours are selected within the configured 5 km / 750 m elevation limits,
  from at most 64 candidates, with at most six peers. A bounded scan reports
  unknown total coverage rather than claiming every eligible node was found.
- Requests and votes use an 82-byte application frame: a 64-byte body,
  16-byte truncated HMAC-SHA256 tag and 2-byte CRC. The host C codec is tested
  against Python, including tampering and quantization. The configured LoRa
  airtime is 0.472064 seconds per frame, before any additional MAC overhead.
- Queries lock the origin, observed time, registration, boot, profile and peer
  membership. Replays, changed duplicates, wrong-window and unsolicited votes
  are rejected. At least three agreeing independent physical nodes including
  the origin, two known failure domains, and two-thirds weighted agreement are
  required. Timeout means unavailable corroboration, not safe conditions.
- Outputs are risk-only, with probability unavailable and public dispatch off.

The C headers are included in the isolated ESP32 firmware build, but a live
packet receive/send loop and radio driver are not implemented. Compilation does
not establish on-board crypto execution, end-to-end mesh delivery or latency.

## Reproduce the engineering checks

Use the repository's Python dependency files and an activated environment:

```sh
python -m pytest tests/test_himachal_registration.py tests/test_himachal_health.py tests/test_himachal_consensus.py tests/test_himachal_radio.py -q
pio run -d esp32/himachal_node
python -m simulator.run_network --nodes 3 10 50 200 --scenarios nominal combined --seeds 1 --rounds 3 --output /tmp/indra_network_smoke.json
```

The retained stress receipt uses the default 30 seeds, 60 rounds, four node
counts and all six scenarios:

```sh
python -m simulator.run_network --output /tmp/indra_network_scale.json
```

This simulator calls the real registration/health/coordinator/codec/scheduler.
Local event flags and physical-role actors are explicitly synthetic fixtures.
It models a direct single-channel star, not a completed multihop mesh, terrain
propagation, measured RF losses, or trained weather inference.

## Results and remaining work

The retained scale receipt is `reports/himachal/network_scale.json`. Across
24 groups (four sizes, six scenarios), each with 30 seeds, no false
corroboration was observed. This must be read together with missed queries:
nominal missed-positive fractions are approximately 38.5% at three nodes,
89.6% at ten nodes, and 100% at 50 and 200 nodes. These fractions describe
injected protocol scenarios, not weather accuracy. The one-channel heartbeat
and query load is unsuitable at the larger scales under these assumptions.

Phase F therefore remains in progress. Remaining integration includes a real
transport/driver and verified provisioning, congestion-aware scheduling,
state recovery after gateway restart, dashboard corroboration displays, and
physical board/radio measurements. Full history-driven model/rule simulations
are a separate step; injected flags do not validate that pipeline.

The configured RF profile is disabled and conditional. Its power, equipment,
antenna and regulatory assumptions require verification for the actual setup.
No hardware configuration is inferred from this simulator.
