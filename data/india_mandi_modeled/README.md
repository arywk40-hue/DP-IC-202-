# Mandi modeled-grid dataset

24,336 hourly API positions, 1 January 2024–10 October 2026, at requested
31.71 N / 76.93 E. All six numeric variables are present. This is a retrospective
model-grid corpus, **not 24,336 physical station observations or independent events**.

`dataset_manifest.json` records query URLs, immutable hashes, units and returned
weather/air grid coordinates for every monthly response. Original responses,
`observations.csv` and `context.csv` remain local and Git-ignored. No source CSVs
are pushed. Recreate with `python3 scripts/test_india_mandi.py --prepare`.

Weather: ECMWF IFS through Open-Meteo; PM: CAMS global. The PM product is
approximately 45 km and 3-hourly beneath the hourly API output; no new interpolation
is performed by this adapter. Grid surface pressure is not verified station
pressure. The separate grids are not declared physically colocated. Original
issue-time data availability is unverified.

The six learned channels are T/RH/P/PM2.5/PM10/wind. Rain, snow and gust data in
`context.csv` are separate modeled context, not additional predictors or confirmed
hazard labels. This source is not admitted to the independent hazard pipeline.

Attribution: Open-Meteo, ECMWF IFS, Copernicus Atmosphere Monitoring Service (CAMS).
Source methods: [weather](https://open-meteo.com/en/docs/historical-weather-api),
[air quality](https://open-meteo.com/en/docs/air-quality-api).
