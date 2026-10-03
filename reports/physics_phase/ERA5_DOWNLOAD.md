# ERA5-Land prerequisite (not acquired or evaluated)

No `.nc`, `.nc4`, `.grib`, `.grib2` or `.zarr` files were found under `data/` in this phase. The four named `era5_*` feature slots are missing and excluded from fitted active features. There is **no measured ERA5 contribution**.

Download [ERA5-Land hourly data](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=download) through your own CDS account after accepting its terms. Use your CDS API token locally, or the website's manual download. This work neither reads credentials nor bypasses authentication.

Exact 24 monthly requests: `data/registry/cds_physics_requests.json`.

- Years: 2023 and 2024; all 12 months, every valid day, all 24 UTC hours.
- Product type: `reanalysis`. These JSON requests are locally checked but **not submitted to the authenticated API**; confirm the current CDS form's “Show API request code” before submission.
- Area `[north, west, south, east]`: `[38, 68, 6, 98.5]` (India and an interpolation margin).
- Variables: `2m_temperature`, `2m_dewpoint_temperature`, `surface_pressure`, `10m_u_component_of_wind`, `10m_v_component_of_wind`.
- Request NetCDF, unarchived; if CDS returns a ZIP, manually extract the NetCDF files. Retain the download receipt and original metadata. Place files under `data/backgrounds/raw/era5_land/`, named `era5_land_2023_01.nc`, etc. Multiple variable files per month are acceptable but require merging coordinates before the current adapter call.
- Optionally download ERA5-Land static geopotential/orography through the dataset documentation's invariant-field route to establish **grid** surface elevation. Do not label surface pressure as station or sea-level pressure.

The [CDS catalogue](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview) describes hourly 0.1° fields (native approximately 9 km). `ml/datasets/era5_land.py:background` checks K/Pa/m s**-1 units, converts to °C/hPa/m/s, derives RH from dewpoint, interpolates space at an **exact UTC timestamp**, and preserves grid-surface pressure reference. Station targets are completed-hour means; for an hour-end H, aggregate background samples from the completed window [H−1h,H), rather than casually mixing instantaneous H with the station mean. The current full-hour builder does **not** perform that join yet; it must be added and tested once real files are supplied.

Use `era5_temperature_c`, `era5_relative_humidity_pct`, `era5_surface_pressure_hpa`, `era5_wind_speed_mps` as background covariates, never independent station labels. Keep archive publication availability separate from observation time. Reanalysis is hindcast-only unless availability at prediction time is verified; its atmospheric forcing can contain information from held-out station observations. Report that dependence and evaluate against a station-only model on identical rows.

Not obtained: CDS ERA5-Land, IMD station downloads requiring permission, and OpenAQ API observations requiring a key. None are needed for the NOAA-only runs here; no PM heads were trained. NWIC remains quarantined for unresolved clock/reference/licensing issues, including suspect Kala Amb coordinates/elevation.
