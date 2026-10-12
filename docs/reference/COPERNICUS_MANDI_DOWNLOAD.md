# Copernicus Mandi download — 2016–2025

Prepared 12 October 2026. Ten complete years, every season and all UTC hours.
The two-year monsoon pilot is optional, not the requested final dataset.
The user selected manual browser downloads; the API route below is optional.

## Browser selection

Use [ERA5 hourly data on single levels](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=download):

- Product: **Reanalysis**.
- Variables: **2m temperature**, **2m dewpoint temperature**, **surface pressure**,
  **10m u-component of wind**, **10m v-component of wind**, **total precipitation**,
  **snowfall**. Humidity and wind speed derive from these fields.
- Full period: **2016–2025**, all months, valid days and 00:00–23:00 UTC.
- Area selection: **north 32.5, south 31.0, west 76.0, east 78.0**.
  This is a Mandi/Kullu regional grid, not all Himachal or India.
- Format: **NetCDF4 (Experimental)**; unarchived download. Multiple resulting
  files may still arrive in a ZIP, which must be retained and inspected.

These seven archive fields do not change the six physical deployed channels.
Weather supplies four modeled channels after derivation; PM2.5 and PM10 are
absent. Precipitation and snowfall are offline context, not verified cloudburst
or snowstorm occurrence labels. Surface pressure refers to grid elevation,
not a verified local station. The product's [overview](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview)
describes hourly reanalysis at a 0.25-degree grid; it is retrospective and is
not a live input available at each historical prediction time.

## Request-size limit

Safari was filled and the user accepted the product licence. The ten-year form
then displayed **“Request too large. Cost 3682224 over 121000 limit.”** This is a
request-size constraint, not a quoted monetary charge. No request was submitted
or downloaded during this setup. Further browser batching attempts encountered
stale-control errors; no smaller batch is claimed to have been submitted.

The script instead makes **120 monthly requests**, preserving all ten years.
There are **87,672 hourly time positions per grid cell** in that period before
checking actual provider coverage. This is planned coverage, not an acquired
row count. Small batches avoid the oversized combined request and allow resume
using original file hashes and matching receipts. A successful real request
still has to confirm the provider accepts the current API fields.

For manual downloads, keep the variables/area/hours above, but select one year
and a small group of months at a time. Check the form's size validation before
submitting. Repeat until the full 2016–2025 period is covered.

Start with **2016, January–March**. Use four quarter batches for each year:
January–March, April–June, July–September and October–December. Repeat for
2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024 and 2025: **40 batches**.
If the portal's validation changes or rejects a quarter, use individual months.
Retain all days and hours in each batch. Record year/quarter in the local file
name and preserve provider metadata/receipts. Do not claim all ten years are
downloaded until the files have been checked for full timestamp coverage.

At handoff the form still retained the oversized full-period selection.
Safari automation could not reduce it reliably (`elementHasNoFrame` / stale
element errors), even after reconnection. The required variables, bounds and
format had been verified, and licence acceptance was verified; submission and
acquisition had not completed. The user must clear/select the year and month
boxes for the first batch in the visible form.

## API setup and commands

Follow the [official CDS setup](https://cds.climate.copernicus.eu/how-to-api).
Sign in and save the displayed configuration in
`/Users/ariyanbhakat/.cdsapirc`, outside the repository:

```yaml
url: https://cds.climate.copernicus.eu/api
key: YOUR_PERSONAL_ACCESS_TOKEN
```

Replace the placeholder locally. Never send the token in chat or commit it.
The official `cdsapi==0.7.7` client was installed in an isolated local environment
at `/private/tmp/indra-cds-venv`; this temporary environment may need recreation
after cleanup. To recreate it:

```sh
python3 -m venv /private/tmp/indra-cds-venv
/private/tmp/indra-cds-venv/bin/python -m pip install 'cdsapi>=0.7.7'
```

From the repository root, inspect requests without authentication:

```sh
python3 scripts/download_copernicus_mandi.py --stage full
```

After manually accepting this product's licence and configuring the token,
start with a three-day format/access check, then the ten-year download:

```sh
/private/tmp/indra-cds-venv/bin/python scripts/download_copernicus_mandi.py \
  --stage smoke --execute --accepted-terms reanalysis-era5-single-levels
/private/tmp/indra-cds-venv/bin/python scripts/download_copernicus_mandi.py \
  --stage full --execute --accepted-terms reanalysis-era5-single-levels
```

Source bytes and receipts stay in the ignored
`data/backgrounds/raw/copernicus_mandi_v1/`. A `.download` suffix deliberately
does not assume the returned container. NetCDF/HDF5 or ZIP magic is screened;
this alone does not validate variables, units, coordinates, timestamps or rain
accumulation semantics. Interrupted `.part` files are preserved for inspection.
Originals are never overwritten; completed files resume only when request and
hash match the receipt. No model fitting, label admission or firmware change
occurs in this downloader.

The new single-level requests are separate from the frozen earlier ERA5-Land
physics requests. Do not pass single-level files to the existing Land normalizer
with fabricated `era5_land` provenance. Real content inspection and the proper
product-specific normalization must follow acquisition.

## Other useful access

- **Measured PM:** OpenAQ/CPCB/HPSPCB exports matching weather locations and
  dates remain the priority. OpenAQ's [API setup](https://docs.openaq.org/using-the-api/api-key)
  uses its own key; its public S3 archive is an alternative for known locations.
  A usable Mandi hourly archive has not been verified.
- **Optional modeled PM:** [CAMS EAC4 on the Atmosphere Data Store](https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4?tab=overview)
  lists PM2.5/PM10, but at a 0.75-degree grid and three-hour cadence. ADS has its
  own [API setup](https://ads.atmosphere.copernicus.eu/how-to-api). It cannot
  replace measured Mandi PM or create independent hourly station truth.
- **Actual hazards:** IMD gauge rain and realized-event records plus HPSDMA
  incident/monitoring records still require reviewed evidence. The prepared
  [request package](IMD_HIMACHAL_DATA_REQUEST_PACKAGE.md) gives contacts/specs.

No API account permission alone establishes cloudburst, flood or landslide
accuracy. Keep archive-context experiments separate from the independent-event
admission and held-out episode evaluation.
