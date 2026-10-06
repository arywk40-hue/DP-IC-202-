# ERA5-Land access — real download blocked

**ERA5_DOWNLOAD_STATUS = BLOCKED_BY_ACCESS.** No personal credential file/environment key or real NetCDF files were found. Credentials were not read; no authenticated API request was made.

1. Register/login to your own [CDS account and API setup](https://cds.climate.copernicus.eu/how-to-api). Manually accept the ERA5-Land product terms. Keep your personal token in your own `.cdsapirc` outside the repository; do not paste it into reports or Git.
2. On [ERA5-Land hourly download](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=download), reproduce each of the unchanged 24 jobs from `data/registry/cds_physics_requests.json`. Confirm current “Show API request code”; local structural validation is not authenticated acceptance.
3. Select each month of 2023/2024, every valid date and all 24 hours UTC; India-margin area N38/W68/S6/E98.5. Variables: 2m temperature, 2m dewpoint, surface pressure, 10m u/v wind. Request NetCDF/unarchived. Do not substitute precipitation or undisclosed variables.
4. Save `data/backgrounds/raw/era5_land/era5_land_2023_01.nc` through `era5_land_2024_12.nc`. If delivered as ZIP, manually extract; retain original source bytes/receipt. Separate variable files can be merged only with identical coordinates/times. Preserve units, CF times, experiment/version dimensions and hashes.
5. Optional normal API client: install `cdsapi>=0.7.7` in the isolated environment, then `python -m ml.hazard_context.cli download-era5 --execute --accepted-terms`. This uses normal personal authentication; no bypass or automatic terms acceptance. Only dry-run/mock behavior has been tested.
6. Supply reviewed metadata JSON (provider, dataset/version, retrieval UTC, license, rights status/evidence URI, country scope) before normalization. Publication/availability timestamps remain unknown until backed by provider evidence; original reanalysis retrieval date cannot establish availability during 2023/24.

Normalizers and causal matching are tested against synthetic NetCDF files. Real ingestion, coverage, ERA5 contribution and S/SB accuracy remain unverified. Reanalysis is context, not independent disaster labels; atmospheric forcing may indirectly contain held-out observations. [CDS product description](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview).
