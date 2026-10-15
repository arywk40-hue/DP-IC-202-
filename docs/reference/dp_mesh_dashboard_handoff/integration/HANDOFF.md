# Handoff notes from High Level Systems

Give this page to the other 1.x owners. HLS does not own firmware, RF, or sensors — only Zone 1 (admin PWA) and the JSON contract.

## Communications (Abhinav)

- Dashboard never speaks LoRa. All mesh timing is hidden behind the Master.
- Please confirm after bench: typical `POST /api/rpc/{id}` round-trip including AODV rediscovery.
- HLS timeout is **2000 ms**. If multi-hop ToA + 500 ms rediscovery exceeds that, tell Mannan to raise `RPC_TIMEOUT_MS`.
- Poll window is 2 s at the top of the hour. The UI does not try to aim at that window; the Master scheduler must.

## Machine Learning (Ariyan)

- Dashboard displays **anomalyIndex 0–4** and human labels from the overview, plus engineering-unit sensors — not the 22-float TinyML tensor.
- If you add a class, bump `appVersion` and send the new `anomalyLabel` string on telemetry.
- Radiation alerts should still be class `4`; plume geometry is a **Master** GeoJSON layer later, not an HLS invention.

## Electronics & Power (Aditi)

- Send **volts**, not percent. Thresholds: warn &lt; 3.10 V, critical &lt; 3.00 V (LiFePO4 + XC6220).
- `CMD_GET_BATTERY` should come back through the same telemetry/status voltage field so the UI does not invent a second unit system.

## Cryptography (Anushka)

- Silent MIC/nonce reject is assumed **end-to-end**. Do not add a “crypto error” JSON field unless you also version the API.
- Until then the admin will only ever see **Not confirmed** on timeout.

## Physical Structure (Vishal)

- Markers use `lat`/`lng` from `/api/nodes` (NEO-6M at deploy).
- OSM tiles need WAN or a tile cache. Field demo without internet still shows nodes + heatmap on a dark basemap.

## Master firmware (pipeline Phase 3)

- Implement the five endpoints exactly as `integration/example_payloads.json`.
- Do **not** serve the React `dist/` from SPIFFS (Design 02 — rejected).
- `appVersion` must stay aligned with `DASHBOARD_API_VERSION` (`0.1.0`).

## Business (Jenish)

- Operator story: install PWA once, join Master AP, zero rupees/month — consistent with no-SIM positioning.
