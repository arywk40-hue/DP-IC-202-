# INDRA showcase — five-minute walkthrough

Prepared 22 October 2026, IST. The software demonstration does not require waiting
for the IMD data request. Field-accuracy and hardware claims remain separate.

## Before the examiner arrives

Open these two tabs and confirm the Connected indicator:

- **http://127.0.0.1:8082** — twelve simulated locations; demonstrates area maps,
  category matching and synthetic hazard scenarios.
- **http://127.0.0.1:8080** — one Mandi model-grid location; demonstrates the
  current API feed, numerical forecast and delayed shadow learning.

Keep the computer awake and connected for new Mandi fetches. Have a charger and
the supplied screenshots/reports available if the network or local process stops.
Use the built interface served on these ports; a Vite development server is not
required. Do not install dependencies, retrain or download years of data on stage.

If the local processes have stopped, use three separate terminals:

```sh
# Terminal 1: current Mandi feed dashboard
MPLCONFIGDIR=/private/tmp/indra-v2-mpl .venv/bin/python -m server.dashboard --observations data/himachal/mandi_current_api_v1/history.json --ui apps/indra-himachal-ui/dist --db data/himachal/mandi_dashboard.sqlite --online-state data/himachal/mandi_v2_online_live.sqlite --port 8080

# Terminal 2: separate simulated network
MPLCONFIGDIR=/private/tmp/indra-v2-mpl .venv/bin/python -m server.dashboard --weather-demo --ui apps/indra-himachal-ui/dist --db data/himachal/weather_demo.sqlite --port 8082

# Terminal 3: future API collection and shadow scoring
MPLCONFIGDIR=/private/tmp/indra-v2-mpl .venv/bin/python scripts/fetch_mandi_live.py --db data/himachal/mandi_dashboard.sqlite --online-state data/himachal/mandi_v2_online_live.sqlite --watch-seconds 900
```

Start each only once. The collector lock prevents two copies using the same data.
The dashboard imports a snapshot at startup; the collector subsequently refreshes
its database. A stopped collector means old values stay visible with their times.

## Presentation order

| Time | Action | Explain |
| --- | --- | --- |
| 0:00–0:40 | Open :8082, Observations | Each location has six channels: temperature, RH, pressure, PM2.5, PM10 and wind. The twelve locations are simulated. |
| 0:40–1:40 | Open Parameters; select each of the six maps | Known points are interpolated within supported geometry. Outside coverage is masked. Two points support a line; three noncollinear points support an area. |
| 1:40–2:30 | Return to Observations; select Location 05, then 08 and 12 | Show heat stress, dust and wet/storm-like patterns. Scores are learned synthetic pattern matches. Hazard scenarios separately sample future rainfall and ground conditions. |
| 2:30–3:15 | Open :8080 | Show the Mandi source label, timestamp, six inputs and six-hour numerical outputs. This is one API/model location, not twelve real stations. |
| 3:15–4:15 | Open System and the model workspace | Show the active LightGBM/neural/hybrid blend, history and persistence fallback, frozen weights, comparison table, pending outcomes and shadow updates. Read the live count rather than memorizing it. |
| 4:15–5:00 | Open the test/progress reports | Show MAE against persistence, actual issue/target times and one saved prediction versus its later API value. State exactly what the evidence supports. |

Use the incomplete-history location if asked about failures: unavailable/warm-up
is intentional. Do not change missing inputs into zeros or hide their status.

## Explain the three different outputs

1. **Numerical forecast:** six estimated measurements at input time +6 hours.
2. **Weather patterns:** current categories from the same six channels and history.
3. **Hazard scenarios:** fractions of simulated rainfall/runoff/landslide-trigger
   outcomes under explicit assumptions. These are not calibrated event probabilities.

The online learner saves predictions, waits for later target-time values and then
updates separate residual corrections. Published offline predictions stay frozen.
Startup forecasts can have short remaining lead; show the timing breakdown before
calling any result a six-hour prospective test. A few updates do not show that
learning has improved errors.

## Evidence to keep open

- [Current API test: 720 complete hours and baseline comparisons](../reports/mandi_current_api_v1/REPORT.md).
- [Latest showcase-time prospective audit](../reports/showcase_2026_10_22/prospective/REPORT.md).
- [Active model architecture and results](../reports/mandi_pipeline_v2/REPORT.md).
- [Synthetic hazard source/assumption specification](SYNTHETIC_HAZARD_SCENARIOS.md).
- [Input/output and feature inventory](FEATURES.md).
- [Current-feed restart and audit instructions](CURRENT_MANDI_FEED.md).

Fresh desktop/mobile checks and fallback screenshots are saved under
`reports/showcase_2026_10_22/`.

## What remains outside this software showcase

- Actual ESP32/sensors/radio demonstration, if included in the presentation scope.
- Co-located physical Mandi outcomes and independent event/non-event records for
  real accuracy and calibrated hazard-probability claims.
- More prospective outcomes to assess shadow improvement and actual forecast lead.
- Public hosting, only if an external URL is required. Local demonstration works
  without a deployment account.

Before presenting, rehearse this sequence once on the actual display and check
text size. A short backup recording is useful but is not required by the app.
