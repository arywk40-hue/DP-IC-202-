# Data licenses and training-view admission

License evidence consolidated on 3 October 2026 from [the source registry](../data/registry/sources.json), [the original dataset review](archive/reports/review/DATASETS_AND_PIPELINE.md) and retained source manifests. This is recorded evidence, not fresh provider confirmation or legal approval. Check and freeze the actual product/export terms before new use.

`training_open` is the clean, open-license observed-target view; `training_restricted` admits resolved restricted-license rows separately. Unresolved licenses, UTC/interval conventions, units, QC or pressure references block admission to both. Modeled products belong in separate background fields, not measured targets. Legacy CPCB research artifacts predate these gates and retain their explicitly assumed timezone.

## Every registered source

| Source ID / evidence | Recorded license | Commercial-use status | Present use / view |
|---|---|---|---|
| [uci_beijing_501](https://doi.org/10.24432/C5RK5G) | CC-BY-4.0 | Allowed under recorded terms; retain attribution/terms | Legacy forecast/event training; new view contracts incomplete |
| [india_cpcb_kaggle_v2](https://www.kaggle.com/datasets/abhisheksjha/time-series-air-quality-data-of-india-2010-2023) | CC-BY-NC-SA-4.0 | Non-commercial only; additional permission for commercial use | Legacy restricted research; new restricted admission awaits contracts |
| [delhi_opencity](https://data.opencity.in/dataset/delhi-hourly-air-quality-reports) | Other (Public Domain) | Unresolved; no commercial clearance | Quarantine; neither target view |
| [nwic_hp_temperature](https://www.nwdp.nwic.gov.in/dataset/temperature-telemetry-hourly-himachal-pradesh-water-department) | other-open | Unresolved; no commercial clearance | Quarantine; neither target view |
| [nwic_hp_humidity](https://www.nwdp.nwic.gov.in/dataset/relative-humidity-telemetry-hourly-himachal-pradesh) | other-open | Unresolved; no commercial clearance | Quarantine; neither target view |
| [nwic_hp_pressure](https://www.nwdp.nwic.gov.in/dataset/atmospheric-pressure-telemetry-hourly-himachal-pradesh) | other-open | Unresolved; no commercial clearance | Quarantine; neither target view |
| [nwic_hp_wind](https://www.nwdp.nwic.gov.in/dataset/wind-speed-telemetry-hourly-himachal-pradesh-department) | other-open | Unresolved; no commercial clearance | Quarantine; neither target view |
| [nwic_hp_rainfall](https://nwdp.nwic.gov.in/dataset/rainfall-telemetry-hourly-himachal-pradesh-department) | Other (Open) | Unresolved; no commercial clearance | Quarantine; neither target view |
| [nwic_hp_temperature_legacy](https://nwdp.nwic.gov.in/dataset/temperature-telemetry-hourly-himachal-pradesh-water-department) | UNVERIFIED | Unresolved; no commercial clearance | Quarantine; neither target view |
| [imd_station_catalogue](https://dsp.imdpune.gov.in/) | UNVERIFIED | Unresolved; no commercial clearance | No approved observation training rows |
| [srtm_gl1](https://portal.opentopography.org/raster?opentopoID=OTSRTM.082015.4326.1) | USGS public-domain product; mirror attribution | Allowed under recorded terms; retain attribution/terms | Static features/grouping; not weather targets |
| [era5_land](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land) | CC-BY | Allowed under recorded terms; retain attribution/terms | Not acquired; planned background only |
| [era5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels) | CC-BY | Allowed under recorded terms; retain attribution/terms | Not acquired; planned background only |
| [nasa_power](https://power.larc.nasa.gov/) | Free NASA data; attribution | Allowed under recorded terms; retain attribution/terms | Mandi diagnostic/background; not observed targets |
| [noaa_ghcnh](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly) | CC0-1.0 | Allowed under recorded terms; retain attribution/terms | Clean observed targets after QC |
| [openaq](https://docs.openaq.org/resources/licenses) | Provider-specific | Unresolved; no commercial clearance | No approved observation training rows |
| [sensor_community](https://sensor.community/en/) | Database Contents License 1.0; database terms unresolved | Unresolved; no commercial clearance | No approved observation training rows |
| [cams_eac4](https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4) | CC-BY | Allowed under recorded terms; retain attribution/terms | Not acquired; planned background only |
| [koppen_geiger_1991_2020](https://www.gloh2o.org/koppen/) | CC-BY-4.0 | Allowed under recorded terms; retain attribution/terms | Static features/grouping; not weather targets |

## Important unresolved evidence

- NWIC: catalogue `other-open` labels do not resolve exact rights; all four-channel rows remain quarantined. Rainfall rights/clock semantics are unresolved too. The legacy temperature export contains only four rows, not the advertised long history.
- Delhi/OpenCity: catalogue says “Other (Public Domain)”, but primary-provider terms, pressure unit/reference and time convention are unresolved. Do not infer admission from that catalog label.
- NOAA: use station-level pressure only; UTC/QC contracts and CC0 evidence are recorded. Repeated/aliased sites and suspect elevations still need scientific review.
- ERA5/ERA5-Land/CAMS: recorded CC-BY class is not evidence of acquisition or acceptance of current service terms. CDS/ADS account terms must be accepted through authorized access. ERA5 pressure is grid-surface background; the registry station-reference placeholder is not a valid target mapping.
- POWER: explicit UTC is required; grid pressure is not station truth. Default local solar time must not be silently converted.
- OpenAQ: a key alone does not establish rights to each provider dataset. IMD permission/export terms and Sensor.Community content/database terms remain unresolved.
- UCI derived RH and uncertain pressure/interval contract in the new registry prevent treating the older forecast training as automatic spatial-view approval.
- Derived SRTM slope and climate classifications are inputs/group labels, not extra independently measured weather targets. Keep terrain product/datum/hash provenance.

No source terms were changed and no authenticated download was attempted in this documentation pass.
