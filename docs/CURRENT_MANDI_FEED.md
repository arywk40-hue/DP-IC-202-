# Current Mandi API feed and delayed testing

Fetched 21 October 2026 for 31.71° N, 76.93° E. One query location is displayed;
it is not a physical mesh node. All six channels are present, with timestamps.

## Sources found and fetched

- Weather: Open-Meteo, explicitly pinned `models=ecmwf_ifs` — temperature,
  humidity, grid-surface pressure and wind in m/s.
- Particulates: Open-Meteo `domains=cams_global` — PM2.5 and PM10 in µg/m³.
- [ECMWF API documentation](https://open-meteo.com/en/docs/ecmwf-api) and
  [CAMS API documentation](https://open-meteo.com/en/docs/air-quality-api).

These are modeled estimates. CAMS global is approximately 45 km and three-hourly
underneath its hourly API output. The two providers return different grid cells;
their exact coordinates are saved. No six-channel co-located Mandi station stream
was verified. The reviewed [CPCB station-list snapshot](https://app.cpcbccr.com/ccr_docs/caaqms_list_All_India.pdf)
does not establish such a Mandi stream; its inventory may lag the live portal.

The initial current download has 89 past/current hourly positions through
21 October 16:00 UTC (21:30 IST), with all six channels. Seven future-valid hours
returned by the providers were excluded before inference. The latest frozen
forecast targets 22:00 UTC (03:30 IST on 22 October).

## How to run

Fetch once, update the local dashboard and record delayed shadow forecasts:

```sh
.venv/bin/python scripts/fetch_mandi_live.py --db data/himachal/mandi_dashboard.sqlite --online-state data/himachal/mandi_v2_online_live.sqlite
```

Collect every 15 minutes while the terminal/computer remains running:

```sh
.venv/bin/python scripts/fetch_mandi_live.py --db data/himachal/mandi_dashboard.sqlite --online-state data/himachal/mandi_v2_online_live.sqlite --watch-seconds 900
```

Only one collector may use the same output directory at a time. This job also
updates the shadow learner; a second online worker is not required. It is a local
process, not a hosted service or operating-system startup job. Ctrl+C stops it.
Interrupted downloads keep the previous dashboard data. Source identity changes
require a separate directory rather than silently mixing grids.

The existing backend serves http://127.0.0.1:8080. To start it after a restart:

```sh
.venv/bin/python -m server.dashboard --observations data/himachal/mandi_current_api_v1/history.json --db data/himachal/mandi_dashboard.sqlite --online-state data/himachal/mandi_v2_online_live.sqlite --ui apps/indra-himachal-ui/dist --port 8080
```

Raw receipts/history are under `data/himachal/mandi_current_api_v1/`, ignored by
Git. `history.json` preserves first-seen values and actual availability times.
Provider revisions are counted and retained in raw responses, not substituted
into existing predictions or truth. Missing values remain missing.

## What is being tested

The published numerical forecast remains the frozen v2 ensemble. The separate
shadow learner saves forecasts before any updates, waits for exact target-time
values acquired on later polls, then records errors and learns corrections.
The initial run has six pending eligible forecasts and zero updates. Earlier
historical positions initialize feature history; they cannot generate live
scores when their target time has already passed.

The nominal task is +6h from the input valid time. Actual issue/availability is
later than that valid time; report the actual remaining lead, not a full six
hours from retrieval. During bootstrap, eligible forecasts for several recent
hours may have substantially shorter remaining lead. No future API row is used
as an input or as early truth, even though provider forecasts are downloadable.

Later labels remain **model-grid values**, not measured weather. This can test
pipeline stability and adaptation to the API source; it cannot establish sensor
accuracy, improve the model by assumption, or validate cloudburst/flood/landslide
probabilities. Live-grid source state is namespaced separately from historical
replay and physical sensors. Online corrections remain in shadow mode.

## Archive test completed

The separate 30-day download covers 21 September–20 October: 720 complete hours,
690 eligible +6h pairs, including 24 target hours beyond the previous archive.
All six targets beat persistence MAE in both cohorts. The full period reuses
examined test dates, and 24 new target hours are a small sample. No weights were
retrained or selected on either cohort.

[Results and numerical errors](../reports/mandi_current_api_v1/REPORT.md).

Reproduce the download and evaluation:

```sh
.venv/bin/python scripts/fetch_mandi_data.py --start 2026-09-21 --end 2026-10-20
.venv/bin/python scripts/evaluate_mandi_snapshot.py --input data/himachal/mandi_api/2026-09-21_2026-10-20 --output reports/mandi_current_api_v1
```

Attribution: Open-Meteo, ECMWF IFS, Copernicus Atmosphere Monitoring Service (CAMS).
