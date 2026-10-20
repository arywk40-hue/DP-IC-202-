# Mandi API refresh — 21 October 2026 (Asia/Kolkata)

Downloaded the last 30 completed UTC days, **20 September–19 October 2026**,
for requested latitude 31.71, longitude 76.93. All **720 hourly positions** contain
all six channels; no values were filled. Rainfall, snowfall and wind-gust context
was also retained. The partial current UTC day was excluded.

Sources: [Open-Meteo Historical Weather / ECMWF IFS](https://open-meteo.com/en/docs/historical-weather-api)
and [Open-Meteo Air Quality / CAMS global](https://open-meteo.com/en/docs/air-quality-api).
These are modeled grid values, not IMD station observations or independent event labels.
Weather and air use different grids, recorded in the local manifest.

## Local dataset

`data/himachal/mandi_api/2026-09-20_2026-10-19/` contains:

- `observations.csv`: timestamp, location and the six model channels.
- `context.csv`: downloaded weather/PM values and auxiliary context.
- `raw/`: original provider responses with hashes in `dataset_manifest.json`.
- `dataset_manifest.json`, `download_request.json`, `download_summary.json`.
- `replay.json`: latest 25 hourly snapshots, preserving dates and actual retrieval time.

Raw files remain ignored; only code, summary and verification evidence are committed.
The frozen training CSV, original model weights and earlier submission report remain unchanged.
No retraining or fresh error/accuracy evaluation was performed by this download.

## Reproduce and display

```sh
.venv/bin/python scripts/fetch_mandi_data.py --start 2026-09-20 --end 2026-10-19
# Cached-only check, no network:
.venv/bin/python scripts/fetch_mandi_data.py --start 2026-09-20 --end 2026-10-19 --offline
# Publish to the running local Mandi store:
.venv/bin/python scripts/import_dashboard_observations.py --input data/himachal/mandi_api/2026-09-20_2026-10-19/replay.json --db data/himachal/mandi_dashboard.sqlite
```

The existing dashboard at http://127.0.0.1:5173 was refreshed. Desktop/mobile
checks confirm the active hybrid, 25/25 history, modeled/historical labels, stale
state and unavailable hazard probabilities. See `local_browser_verification.json`
and screenshots. These are workflow checks, not weather-skill measurements.
