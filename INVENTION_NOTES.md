**Confidential: do not publish before IP review.**

# Evidence and prior-art notes

This is a research prototype, not a demonstrated new meteorological interpolation invention. Current two-node evidence and losses are in [the two-node report](reports/two_node_phase/REPORT.md); earlier protocols remain in [the archived physics report](docs/archive/reports/physics_phase/REPORT.md) and [practicum results](reports/practicum/RESULTS.md). Claims below describe implemented behavior, not patent novelty.

| Claim | Evidence / distinction from bare IDW | Relationship to kriging / prior art |
|---|---|---|
| Source-aware QC and quarantine | Source quality flags, coordinate agreement, prior-period SRTM/catalogue height comparison and pressure plausibility masks precede interpolation (`ml/datasets/hourly_noaa.py`). Suspect pressures do not become labels or predictors. | Operational preprocessing, usable with IDW **or** kriging; not established as novel. Thresholds are heuristics and can exclude valid mountain observations. |
| Channel-specific fallback | A failed learned residual or fitted-envelope violation returns the same physics baseline; missing PM does not block T/RH/P/wind (`physics_residual.py`). | Control flow beyond bare interpolation, but fallbacks and hybrid models have broad prior art. Failure tests establish behavior, not operational reliability. |
| Refusal outside the network | Snapshot serving checks current contributors, the two-node corridor (or convex hull for larger networks), the 20 km limit, and withholds missing-elevation pressure (`physics_serving.py`). | An explicit abstention policy rather than unrestricted IDW prediction. Kriging has uncertainty/domain controls too; no unique algorithmic claim. No outage-field validation. |
| Elevation-aware pressure reduction | Reversible hydrostatic ideal-gas reduction to 0 m EGM96 with fixed lapse and optional virtual-temperature correction, log-space IDW, then query-height restoration (`physics.py`). | Established barometric/hypsometric physics, not a novel pressure equation. Kriging could interpolate the same transformed field. This is modeled reference pressure, **not** certified sea-level pressure. |
| Elevation-aware T and dewpoint RH | Fixed 6.5 K/km temperature adjustment, dewpoint interpolation and RH recovery at query T. | Terrain correction, moisture transforms and residual interpolation have established literature. This implementation's humidity baseline loses to raw RH IDW in the national evaluation. |
| Physics-residual boosting + NN | Learned corrections, selection-only shrinkage gate, OOD fallback. | Different fit from ordinary IDW and ordinary kriging; regression/residual kriging also separates trend and residual. No guarantee of smaller future or pointwise error. Test losses remain visible. |
| Checked block error bands | Global 72 h block-max scores; separate calibration, independent checking, and target/distance-specific withholding (`episodes.py`). | Split conformal/block methods have prior art. Calendar blocks are weather-episode proxies; exchangeability and nominal future coverage are unverified. |
| ESP32/server split | Heavy model training/inference stays in Python; the existing firmware provides mesh/sensor work. | A deployment partition, not an ESP32 ensemble implementation. No distillation, quantization, artifact export, RAM/flash timing or watchdog evidence for the new model. Embedded/server division has extensive prior art. |

Scientific references establish that constituent ideas predate this prototype:

- [ICAMS Federal Meteorological Handbook 3](https://www.icams-portal.gov/resources/ofcm/fmh/FMH3/00-entire-FMH3.pdf): hypsometric/virtual-temperature pressure reduction.
- [Pressure reduction uncertainty, Pauley (1998)](https://journals.ametsoc.org/view/journals/wefo/13/3/1520-0434_1998_013_0833_aeouis_2_0_co_2.xml): terrain and temperature assumptions matter.
- [Stahl et al. (2006), air-temperature interpolation in complex topography](https://www.sciencedirect.com/science/article/abs/pii/S0168192306001638): lapse/elevation correction and interpolation comparisons. Publisher abstract/search evidence consulted; full paper not obtained.
- [KrigR (2021)](https://arxiv.org/abs/2106.12046): terrain covariates with kriging of climate reanalysis.
- [Chernozhukov, Wüthrich and Zhu (2018)](https://arxiv.org/abs/1802.06300): conformal inference for dependent data with block structures.
- [CDS ERA5-Land documentation](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview): altitude correction of atmospheric forcing already exists in reanalysis.

A systematic prior-art search remains necessary for **each** combination claim: authenticated/QC mesh interpolation; contributor-specific refusal with fallback; pressure-reference reduction plus learned residual stacking; distance/terrain-dependent conformal abstention; and distilled weather models with server/device failover. Search patent families as well as scientific and deployed systems, with dates and claim charts. This phase checked selected scientific sources, not patents, freedom to operate, or legal novelty. Do not claim “first”, “never worse”, “calibrated 90% everywhere”, “all-India mesh validated”, or “ESP32 deployed”.
