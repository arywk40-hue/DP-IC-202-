# INDRA — six-channel India/Mandi forecasting research

[Project overview](docs/PROJECT_OVERVIEW.md) · [Architecture](docs/ARCHITECTURE.md) ·
[Model catalog](configs/model_catalog.json) · [Documentation index](docs/README.md)

Six channels: **temperature, humidity, station pressure, PM2.5, PM10 and wind**,
plus causal history/derived features. Himalayan targets: cloudburst, flash flood,
landslide and snowstorm, pending independent event and monitoring evidence.

The latest numerical benchmark fits/test weights using **Mandi, India API model
grids**, with no Chinese data or weights. It contains 24,336 hourly modeled
positions and a 954-pair temporal holdout. This is not measured Mandi field
accuracy. The API pressure is grid-surface pressure; independent hazard heads
remain unfitted.

```sh
python3 scripts/test_india_mandi.py --offline   # local cached data; no retraining
python3 scripts/test_india_mandi.py --prepare   # download ignored source on a fresh checkout
```

[Executed six-channel results](reports/india_mandi_phase/REPORT.md) ·
[Source provenance](data/india_mandi_modeled/README.md) ·
[Himalayan warning protocol](docs/HIMALAYAN_WARNING_PROTOCOL.md) ·
[Data request package](docs/reference/IMD_HIMACHAL_DATA_REQUEST_PACKAGE.md)

Raw datasets stay local. Country/source/model roles are explicit in the catalog.
Historical Beijing comparisons and spatial experiments are retained separately
for reproducibility. No physical ESP32 field validation or operational disaster
warning is claimed.
