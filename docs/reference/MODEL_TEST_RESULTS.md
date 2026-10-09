# XGBoost model test results

Run date: 2026-10-07. No model or training code was changed.

## Scope and interpretation

The requested 14-feature pipeline is absent from the current tree. Its exact source, weatherHistory.csv and compatible weights were recovered into an ignored cache from Git history. Current models were evaluated on their own feature/target contracts and native held-out splits. A single accuracy ranking across regression, rule classification and future-threshold classification would be invalid.

The archived training labels are computed from the same features, with synthetic PM2.5, CO2 and lightning. High weatherHistory accuracy measures rule reproduction and is not independently observed hazard accuracy. Random row splitting and full-series pressure interpolation also weaken the independence of that test.

Mandi scores below are agreement with explicitly defined research proxies on Open-Meteo/CAMS modeled data, not real hazard labels or sensor validation. CO2, lightning distance and lightning threat remain NaN. VOC is not one of the 14 features. CO and NO2 are not CO2; they are downloaded but never substituted. The historical dewpoint approximation is reused despite downloading source dewpoint.

[Open-Meteo weather documentation](https://open-meteo.com/en/docs/historical-weather-api) · [Open-Meteo air-quality documentation](https://open-meteo.com/en/docs/air-quality-api)

## Run contract

```json
{
  "commit": "bd862890dfce48f810fc9efc02748a407b6a3b37",
  "dataset": "ml/dataset/weatherHistory.csv",
  "dataset_sha256": "22c028ceb97c6ad405831dfda61f0235532d9ab873229ff57ce4240853ef0a1f",
  "source_sha256": {
    "prepare_dataset.py": "6102fe03d4e81f995686fe58952a3dc8867eb65f059108cebd0de22f0df5ab6e",
    "train_model.py": "0050f9cc32a5f582625ba0dcc52fbbb4794675ccbeae4df167670b3dea295dae",
    "convert_to_c.py": "67c8cc734583599ddd00a2ed407dbdf132b2abfe493cc19690f3dec6a59cdb33"
  },
  "features": [
    "temp_current",
    "humidity_current",
    "pressure_current",
    "wind_speed_current",
    "pm25_current",
    "co2_current",
    "lightning_dist_current",
    "temp_humidity_ratio",
    "pressure_trend",
    "heat_index",
    "dew_point",
    "fire_risk_index",
    "flood_risk_index",
    "lightning_threat"
  ],
  "class_order": [
    "wildfire",
    "flood",
    "storm",
    "air_quality"
  ],
  "split": "random seed 42; test 20%; validation 12.5% of remaining 80%",
  "evidence": "Input-derived rule labels; synthetic PM2.5/CO2/lightning; random split is not temporal or site validation",
  "rows": 96453,
  "train": 67516,
  "validation": 9646,
  "test": 19291,
  "generated_feature_sha256": "4c74b9ad74edb1b246a5e5b1ace38c5ed6de58a05abdb9d905a36d4956cfc970",
  "generated_label_sha256": "3f6ee0342e8c0e7facde886bec30ed1a0c816f03a06307a2426417decf2365c5",
  "missing_mandi_features": [
    "co2_current",
    "lightning_dist_current",
    "lightning_threat"
  ],
  "no_voc_feature": true,
  "unused_downloaded_variables": [
    "pm10",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "cloud_cover",
    "dew_point_2m"
  ],
  "proxy_rule": "flood: preceding 3h rain >= 30.0 mm; storm: wind >40 km/h; wildfire: T>30C, RH<35%, wind>20 km/h; air_quality: PM2.5>60 ug/m3; else normal",
  "proxy_priority": [
    "flood",
    "storm",
    "wildfire",
    "air_quality"
  ],
  "usable_proxy_hours": 718,
  "derivation_notes": "Historical compute_derived_features reused exactly. RH fraction; wind km/h. API dewpoint retained but historical approximation used. Surface pressure preserved; no sea-level substitution or >900hPa imputation."
}
```

## Mandi source and missing-data audit

```json
{
  "start_date": "2026-09-07",
  "end_date": "2026-10-06",
  "expected_hours": 720,
  "weather": {
    "url": "https://archive-api.open-meteo.com/v1/archive?latitude=31.71&longitude=76.93&start_date=2026-09-07&end_date=2026-10-06&timezone=UTC&hourly=temperature_2m%2Crelative_humidity_2m%2Cdew_point_2m%2Csurface_pressure%2Cwind_speed_10m%2Ccloud_cover%2Cprecipitation",
    "sha256": "4ab4cab1afb5c5972f61db7d8a3236e0f323d41b6b4d4630ec91a4ff647e3cf6",
    "cache": "results/model_tests/cache/weather_8023cc058ceef603.json",
    "returned_latitude": 31.669594,
    "returned_longitude": 76.942444,
    "elevation": 770.0,
    "units": {
      "time": "iso8601",
      "temperature_2m": "\u00b0C",
      "relative_humidity_2m": "%",
      "dew_point_2m": "\u00b0C",
      "surface_pressure": "hPa",
      "wind_speed_10m": "km/h",
      "cloud_cover": "%",
      "precipitation": "mm"
    }
  },
  "air": {
    "url": "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=31.71&longitude=76.93&start_date=2026-09-07&end_date=2026-10-06&timezone=UTC&hourly=pm10%2Cpm2_5%2Ccarbon_monoxide%2Cnitrogen_dioxide",
    "sha256": "8df5b6864da4063e5318f103a52618ecae4b37f5fe28def30378d2cfd5d0cf96",
    "cache": "results/model_tests/cache/air_dba581a002fa23ea.json",
    "returned_latitude": 31.700005,
    "returned_longitude": 76.899994,
    "elevation": 770.0,
    "units": {
      "time": "iso8601",
      "pm10": "\u03bcg/m\u00b3",
      "pm2_5": "\u03bcg/m\u00b3",
      "carbon_monoxide": "\u03bcg/m\u00b3",
      "nitrogen_dioxide": "\u03bcg/m\u00b3"
    }
  },
  "missing_per_variable": {
    "temperature_2m": 0,
    "relative_humidity_2m": 0,
    "dew_point_2m": 0,
    "surface_pressure": 0,
    "wind_speed_10m": 0,
    "cloud_cover": 0,
    "precipitation": 0,
    "pm10": 0,
    "pm2_5": 0,
    "carbon_monoxide": 0,
    "nitrogen_dioxide": 0
  },
  "evidence": "Open-Meteo gridded weather reanalysis and CAMS air-quality model data, not local sensor ground truth"
}
```

## Archived bundle ranking on the reconstructed native holdout

| Rank | Bundle | Exact four-label accuracy | Macro-F1 across four hazards | Mean binary accuracy |
| --- | --- | ---: | ---: | ---: |
| 1 | archive:ml/model | 0.996216 | 0.996063 | 0.999054 |
| 2 | archive:ml/model_baseline | 0.996216 | 0.996063 | 0.999054 |

Best comparable native legacy bundle(s): **archive:ml/model, archive:ml/model_baseline**. This names the best rule-reproduction score, not a field deployment winner.

## Archived bundles: Mandi exclusive proxy ranking

| Rank | Bundle | Proxy accuracy | Macro-F1 (all five classes) | Normal-only baseline accuracy | Predicted class shares |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | archive:ml/model_india_26_distilled | 0.993036 | 0.394000 | 0.945682 | normal 94.4%, wildfire 0.4%, flood 0.0%, storm 0.0%, air_quality 5.2% |
| 2 | archive:ml/model_india_26_distilled_context | 0.993036 | 0.394000 | 0.945682 | normal 94.4%, wildfire 0.4%, flood 0.0%, storm 0.0%, air_quality 5.2% |
| 3 | archive:ml/model_india_26_masked_distilled_edge | 0.993036 | 0.394000 | 0.945682 | normal 94.4%, wildfire 0.4%, flood 0.0%, storm 0.0%, air_quality 5.2% |
| 4 | archive:ml/model_india_26_verified_storm_candidate | 0.993036 | 0.394000 | 0.945682 | normal 94.4%, wildfire 0.4%, flood 0.0%, storm 0.0%, air_quality 5.2% |
| 5 | archive:ml/model_india_pilot | 0.809192 | 0.251144 | 0.945682 | normal 75.5%, wildfire 0.4%, flood 0.0%, storm 0.0%, air_quality 24.1% |
| 6 | archive:ml/model_india_26_baseline_repro | 0.548747 | 0.175041 | 0.945682 | normal 50.0%, wildfire 0.4%, flood 0.0%, storm 0.0%, air_quality 49.6% |
| 7 | archive:ml/model_india_26_geo_temporal | 0.548747 | 0.175041 | 0.945682 | normal 50.0%, wildfire 0.4%, flood 0.0%, storm 0.0%, air_quality 49.6% |
| 8 | archive:ml/model | 0.437326 | 0.149894 | 0.945682 | normal 38.3%, wildfire 4.3%, flood 0.0%, storm 0.0%, air_quality 57.4% |
| 9 | archive:ml/model_baseline | 0.437326 | 0.149894 | 0.945682 | normal 38.3%, wildfire 4.3%, flood 0.0%, storm 0.0%, air_quality 57.4% |
| 10 | archive:ml/model_india_26 | 0.306407 | 0.110733 | 0.945682 | normal 25.8%, wildfire 0.4%, flood 0.0%, storm 0.0%, air_quality 73.8% |

## All classifier accuracy results

Rank resets for each target, identical test-row key set, split and evidence category. Order: macro-F1, then accuracy; exact score ties receive equal ranks. Regression models are listed separately with their continuous errors.

| Rank within comparable task | Model | Target / split | Accuracy | Binary macro-F1 | Evidence |
| ---: | --- | --- | ---: | ---: | --- |
| 1 | archive:ml/model/air_quality | air_quality / weatherHistory_seed42_test20 | 0.998134 | 0.998105 | native_random_holdout |
| 1 | archive:ml/model_baseline/air_quality | air_quality / weatherHistory_seed42_test20 | 0.998134 | 0.998105 | native_random_holdout |
| 1 | archive:ml/model_india_26/air_quality | air_quality / weatherHistory_seed42_test20 | 0.439272 | 0.307463 | weatherHistory_transfer_diagnostic_not_original_test |
| 2 | archive:ml/model_india_pilot/air_quality | air_quality / weatherHistory_seed42_test20 | 0.438132 | 0.305200 | weatherHistory_transfer_diagnostic_not_original_test |
| 3 | archive:ml/model_india_26_baseline_repro/air_quality | air_quality / weatherHistory_seed42_test20 | 0.438028 | 0.304994 | weatherHistory_transfer_diagnostic_not_original_test |
| 3 | archive:ml/model_india_26_geo_temporal/air_quality | air_quality / weatherHistory_seed42_test20 | 0.438028 | 0.304994 | weatherHistory_transfer_diagnostic_not_original_test |
| 5 | archive:ml/model_india_26_distilled/air_quality | air_quality / weatherHistory_seed42_test20 | 0.437821 | 0.304581 | weatherHistory_transfer_diagnostic_not_original_test |
| 5 | archive:ml/model_india_26_distilled_context/air_quality | air_quality / weatherHistory_seed42_test20 | 0.437821 | 0.304581 | weatherHistory_transfer_diagnostic_not_original_test |
| 5 | archive:ml/model_india_26_masked_distilled_edge/air_quality | air_quality / weatherHistory_seed42_test20 | 0.437821 | 0.304581 | weatherHistory_transfer_diagnostic_not_original_test |
| 5 | archive:ml/model_india_26_verified_storm_candidate/air_quality | air_quality / weatherHistory_seed42_test20 | 0.437821 | 0.304581 | weatherHistory_transfer_diagnostic_not_original_test |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/cold_frontal_passage.ubj | cold_frontal_passage / future_test | 0.999980 | 0.961534 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/cold_frontal_passage.ubj | cold_frontal_passage / geographic_test | 1.000000 | 1.000000 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/dust_storm_haboob.ubj | dust_storm_haboob / future_test | 1.000000 | 0.500000 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/dust_storm_haboob.ubj | dust_storm_haboob / geographic_test | 1.000000 | 0.500000 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/extreme_heatwave.ubj | extreme_heatwave / future_test | 0.992213 | 0.833863 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/extreme_heatwave.ubj | extreme_heatwave / geographic_test | 0.991513 | 0.755487 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | archive:ml/model/flood | flood / weatherHistory_seed42_test20 | 0.999119 | 0.996713 | native_random_holdout |
| 1 | archive:ml/model_baseline/flood | flood / weatherHistory_seed42_test20 | 0.999119 | 0.996713 | native_random_holdout |
| 1 | archive:ml/model_india_26/flood | flood / weatherHistory_seed42_test20 | 0.952309 | 0.738828 | weatherHistory_transfer_diagnostic_not_original_test |
| 2 | archive:ml/model_india_pilot/flood | flood / weatherHistory_seed42_test20 | 0.952050 | 0.736733 | weatherHistory_transfer_diagnostic_not_original_test |
| 3 | archive:ml/model_india_26_baseline_repro/flood | flood / weatherHistory_seed42_test20 | 0.951635 | 0.733358 | weatherHistory_transfer_diagnostic_not_original_test |
| 3 | archive:ml/model_india_26_distilled/flood | flood / weatherHistory_seed42_test20 | 0.951635 | 0.733358 | weatherHistory_transfer_diagnostic_not_original_test |
| 3 | archive:ml/model_india_26_distilled_context/flood | flood / weatherHistory_seed42_test20 | 0.951635 | 0.733358 | weatherHistory_transfer_diagnostic_not_original_test |
| 3 | archive:ml/model_india_26_geo_temporal/flood | flood / weatherHistory_seed42_test20 | 0.951635 | 0.733358 | weatherHistory_transfer_diagnostic_not_original_test |
| 3 | archive:ml/model_india_26_verified_storm_candidate/flood | flood / weatherHistory_seed42_test20 | 0.951635 | 0.733358 | weatherHistory_transfer_diagnostic_not_original_test |
| 8 | archive:ml/model_india_26_masked_distilled_edge/flood | flood / weatherHistory_seed42_test20 | 0.949147 | 0.712493 | weatherHistory_transfer_diagnostic_not_original_test |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/freezing_rain_sleet.ubj | freezing_rain_sleet / future_test | 0.999822 | 0.981737 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/freezing_rain_sleet.ubj | freezing_rain_sleet / geographic_test | 0.999941 | 0.992943 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/ground_frost.ubj | ground_frost / future_test | 0.999704 | 0.999172 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/ground_frost.ubj | ground_frost / geographic_test | 0.999881 | 0.999708 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | data/india_sensor/models/himalaya_holdout_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj | high_wind_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/northern_plains_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_D_peninsula_proxy.ubj | high_wind_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/peninsula_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_D_western_arid_proxy.ubj | high_wind_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/western_arid_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/models/himalaya_holdout_high_wind_measurement_at_6h_A.ubj | high_wind_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/A | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/models/himalaya_holdout_high_wind_measurement_at_6h_B.ubj | high_wind_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/B | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_western_arid_proxy.ubj | high_wind_measurement_at_6h / india_sensor_phase/national/test/western_arid_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_peninsula_proxy.ubj | high_wind_measurement_at_6h / india_sensor_phase/national/test/peninsula_proxy | 0.999797 | 0.499949 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/models/national_high_wind_measurement_at_6h_A.ubj | high_wind_measurement_at_6h / india_sensor_phase/national/test/A | 0.999888 | 0.499972 | native_holdout_future_measured_threshold |
| 1 | ml/models/india_sensor_v1/national_high_wind_measurement_at_6h_B.ubj | high_wind_measurement_at_6h / india_sensor_phase/national/test/B | 0.999888 | 0.499972 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj | high_wind_measurement_at_6h / india_sensor_phase/national/test/northern_plains_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj | high_wind_measurement_at_6h / offline_phase/himalaya_holdout/test/northern_plains_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_D_peninsula_proxy.ubj | high_wind_measurement_at_6h / offline_phase/himalaya_holdout/test/peninsula_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_D_western_arid_proxy.ubj | high_wind_measurement_at_6h / offline_phase/himalaya_holdout/test/western_arid_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_A.ubj | high_wind_measurement_at_6h / offline_phase/himalaya_holdout/test/A | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_B.ubj | high_wind_measurement_at_6h / offline_phase/himalaya_holdout/test/B | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_western_arid_proxy.ubj | high_wind_measurement_at_6h / offline_phase/national/test/western_arid_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_peninsula_proxy.ubj | high_wind_measurement_at_6h / offline_phase/national/test/peninsula_proxy | 0.999797 | 0.499949 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_high_wind_measurement_at_6h_A.ubj | high_wind_measurement_at_6h / offline_phase/national/test/A | 0.999888 | 0.499972 | native_holdout_future_measured_threshold |
| 1 | ml/models/india_sensor_v1/national_high_wind_measurement_at_6h_B.ubj | high_wind_measurement_at_6h / offline_phase/national/test/B | 0.999888 | 0.499972 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj | high_wind_measurement_at_6h / offline_phase/national/test/northern_plains_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_A.ubj | high_wind_measurement_at_6h / offline_phase/temporal/test/A | 0.999762 | 0.499940 | native_holdout_future_measured_threshold |
| 2 | data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_B.ubj | high_wind_measurement_at_6h / offline_phase/temporal/test/B | 0.999750 | 0.499938 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_D_peninsula_proxy.ubj | high_wind_measurement_at_6h / offline_phase/temporal/test/peninsula_proxy | 0.999664 | 0.499916 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_D_western_arid_proxy.ubj | high_wind_measurement_at_6h / offline_phase/temporal/test/western_arid_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj | high_wind_measurement_at_6h / offline_phase/temporal/test/northern_plains_proxy | 0.999878 | 0.499969 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_D_northeast_proxy.ubj | hot_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/northeast_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_D_northern_plains_proxy.ubj | hot_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/northern_plains_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_D_peninsula_proxy.ubj | hot_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/peninsula_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_western_arid_proxy.ubj | hot_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/western_arid_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_A.ubj | hot_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/A | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_B.ubj | hot_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/B | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_hot_measurement_at_6h_D_northern_plains_proxy.ubj | hot_measurement_at_6h / india_sensor_phase/national/test/northern_plains_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/models/national_hot_measurement_at_6h_D_peninsula_proxy.ubj | hot_measurement_at_6h / india_sensor_phase/national/test/peninsula_proxy | 0.997974 | 0.499493 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_hot_measurement_at_6h_D_northeast_proxy.ubj | hot_measurement_at_6h / india_sensor_phase/national/test/northeast_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_hot_measurement_at_6h_D_mountain_proxy.ubj | hot_measurement_at_6h / india_sensor_phase/national/test/mountain_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | ml/models/india_sensor_v1/national_hot_measurement_at_6h_B.ubj | hot_measurement_at_6h / india_sensor_phase/national/test/B | 0.996345 | 0.499085 | native_holdout_future_measured_threshold |
| 2 | data/india_sensor/models/national_hot_measurement_at_6h_A.ubj | hot_measurement_at_6h / india_sensor_phase/national/test/A | 0.996177 | 0.499042 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/models/national_hot_measurement_at_6h_D_western_arid_proxy.ubj | hot_measurement_at_6h / india_sensor_phase/national/test/western_arid_proxy | 0.985036 | 0.496231 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_northeast_proxy.ubj | hot_measurement_at_6h / offline_phase/himalaya_holdout/test/northeast_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_northern_plains_proxy.ubj | hot_measurement_at_6h / offline_phase/himalaya_holdout/test/northern_plains_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_peninsula_proxy.ubj | hot_measurement_at_6h / offline_phase/himalaya_holdout/test/peninsula_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_western_arid_proxy.ubj | hot_measurement_at_6h / offline_phase/himalaya_holdout/test/western_arid_proxy | 1.000000 | 0.500000 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_A.ubj | hot_measurement_at_6h / offline_phase/himalaya_holdout/test/A | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_B.ubj | hot_measurement_at_6h / offline_phase/himalaya_holdout/test/B | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/himalaya_only_hot_measurement_at_6h_A.ubj | hot_measurement_at_6h / offline_phase/himalaya_only/test/A | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/himalaya_only_hot_measurement_at_6h_D_mountain_proxy.ubj | hot_measurement_at_6h / offline_phase/himalaya_only/test/B | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/himalaya_only_hot_measurement_at_6h_D_mountain_proxy.ubj | hot_measurement_at_6h / offline_phase/himalaya_only/test/mountain_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_hot_measurement_at_6h_D_northern_plains_proxy.ubj | hot_measurement_at_6h / offline_phase/national/test/northern_plains_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_hot_measurement_at_6h_D_peninsula_proxy.ubj | hot_measurement_at_6h / offline_phase/national/test/peninsula_proxy | 0.997974 | 0.499493 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_hot_measurement_at_6h_D_northeast_proxy.ubj | hot_measurement_at_6h / offline_phase/national/test/northeast_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_hot_measurement_at_6h_D_mountain_proxy.ubj | hot_measurement_at_6h / offline_phase/national/test/mountain_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | ml/models/india_sensor_v1/national_hot_measurement_at_6h_B.ubj | hot_measurement_at_6h / offline_phase/national/test/B | 0.996345 | 0.499085 | native_holdout_future_measured_threshold |
| 2 | data/india_sensor/offline/models/national_hot_measurement_at_6h_A.ubj | hot_measurement_at_6h / offline_phase/national/test/A | 0.996177 | 0.499042 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_hot_measurement_at_6h_D_western_arid_proxy.ubj | hot_measurement_at_6h / offline_phase/national/test/western_arid_proxy | 0.985401 | 0.520132 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_western_arid_proxy.ubj | hot_measurement_at_6h / offline_phase/temporal/test/western_arid_proxy | 0.993024 | 0.555392 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_northern_plains_proxy.ubj | hot_measurement_at_6h / offline_phase/temporal/test/northern_plains_proxy | 0.999816 | 0.499954 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_mountain_proxy.ubj | hot_measurement_at_6h / offline_phase/temporal/test/mountain_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_northeast_proxy.ubj | hot_measurement_at_6h / offline_phase/temporal/test/northeast_proxy | 1.000000 | 0.500000 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_hot_measurement_at_6h_B.ubj | hot_measurement_at_6h / offline_phase/temporal/test/B | 0.997892 | 0.499473 | native_holdout_future_measured_threshold |
| 2 | data/india_sensor/offline/models/temporal_hot_measurement_at_6h_A.ubj | hot_measurement_at_6h / offline_phase/temporal/test/A | 0.997870 | 0.499467 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_peninsula_proxy.ubj | hot_measurement_at_6h / offline_phase/temporal/test/peninsula_proxy | 0.998110 | 0.499527 | native_holdout_future_measured_threshold |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/light_moderate_rain.ubj | light_moderate_rain / future_test | 1.000000 | 1.000000 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/light_moderate_rain.ubj | light_moderate_rain / geographic_test | 1.000000 | 1.000000 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj | near_saturation_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/northern_plains_proxy | 0.884601 | 0.676395 | cross_region_transfer_no_native_routed_test_rows |
| 2 | data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj | near_saturation_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/western_arid_proxy | 0.868331 | 0.655715 | cross_region_transfer_no_native_routed_test_rows |
| 3 | data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj | near_saturation_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/peninsula_proxy | 0.894060 | 0.647084 | cross_region_transfer_no_native_routed_test_rows |
| 4 | data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_northeast_proxy.ubj | near_saturation_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/northeast_proxy | 0.894438 | 0.626975 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_B.ubj | near_saturation_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/B | 0.893303 | 0.688539 | native_holdout_future_measured_threshold |
| 2 | data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_A.ubj | near_saturation_measurement_at_6h / india_sensor_phase/himalaya_holdout/test/A | 0.890276 | 0.658758 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/models/national_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj | near_saturation_measurement_at_6h / india_sensor_phase/national/test/northern_plains_proxy | 0.906160 | 0.740396 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/models/national_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj | near_saturation_measurement_at_6h / india_sensor_phase/national/test/peninsula_proxy | 0.939204 | 0.660079 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_mountain_proxy.ubj | near_saturation_measurement_at_6h / india_sensor_phase/national/test/mountain_proxy | 0.991597 | 0.497890 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/models/national_near_saturation_measurement_at_6h_B.ubj | near_saturation_measurement_at_6h / india_sensor_phase/national/test/B | 0.941160 | 0.681876 | native_holdout_future_measured_threshold |
| 2 | data/india_sensor/models/national_near_saturation_measurement_at_6h_A.ubj | near_saturation_measurement_at_6h / india_sensor_phase/national/test/A | 0.941497 | 0.681250 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/models/national_near_saturation_measurement_at_6h_D_northeast_proxy.ubj | near_saturation_measurement_at_6h / india_sensor_phase/national/test/northeast_proxy | 0.933646 | 0.761231 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/models/national_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj | near_saturation_measurement_at_6h / india_sensor_phase/national/test/western_arid_proxy | 0.996713 | 0.499177 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/himalaya_holdout/test/northern_plains_proxy | 0.884222 | 0.675886 | cross_region_transfer_no_native_routed_test_rows |
| 2 | data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/himalaya_holdout/test/peninsula_proxy | 0.898222 | 0.663078 | cross_region_transfer_no_native_routed_test_rows |
| 3 | data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/himalaya_holdout/test/western_arid_proxy | 0.875899 | 0.662847 | cross_region_transfer_no_native_routed_test_rows |
| 4 | data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_northeast_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/himalaya_holdout/test/northeast_proxy | 0.894438 | 0.626975 | cross_region_transfer_no_native_routed_test_rows |
| 1 | data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_B.ubj | near_saturation_measurement_at_6h / offline_phase/himalaya_holdout/test/B | 0.891033 | 0.679615 | native_holdout_future_measured_threshold |
| 2 | data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_A.ubj | near_saturation_measurement_at_6h / offline_phase/himalaya_holdout/test/A | 0.889141 | 0.653210 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/himalaya_only_near_saturation_measurement_at_6h_A.ubj | near_saturation_measurement_at_6h / offline_phase/himalaya_only/test/A | 0.871688 | 0.561643 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/himalaya_only_near_saturation_measurement_at_6h_D_mountain_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/himalaya_only/test/B | 0.871688 | 0.561643 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/himalaya_only_near_saturation_measurement_at_6h_D_mountain_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/himalaya_only/test/mountain_proxy | 0.871688 | 0.561643 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/national/test/northern_plains_proxy | 0.902130 | 0.731297 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/national/test/peninsula_proxy | 0.935860 | 0.618176 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_mountain_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/national/test/mountain_proxy | 0.991597 | 0.497890 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_A.ubj | near_saturation_measurement_at_6h / offline_phase/national/test/A | 0.943973 | 0.702309 | native_holdout_future_measured_threshold |
| 2 | ml/models/india_sensor_v1/national_near_saturation_measurement_at_6h_B.ubj | near_saturation_measurement_at_6h / offline_phase/national/test/B | 0.943579 | 0.696785 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_northeast_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/national/test/northeast_proxy | 0.931768 | 0.746693 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/national/test/western_arid_proxy | 0.996713 | 0.499177 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/temporal/test/western_arid_proxy | 0.979209 | 0.763464 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_northeast_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/temporal/test/northeast_proxy | 0.930982 | 0.677022 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_B.ubj | near_saturation_measurement_at_6h / offline_phase/temporal/test/B | 0.953389 | 0.699533 | native_holdout_future_measured_threshold |
| 2 | data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_A.ubj | near_saturation_measurement_at_6h / offline_phase/temporal/test/A | 0.953777 | 0.698857 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/temporal/test/peninsula_proxy | 0.959111 | 0.702717 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_mountain_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/temporal/test/mountain_proxy | 0.890276 | 0.724177 | native_holdout_future_measured_threshold |
| 1 | data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj | near_saturation_measurement_at_6h / offline_phase/temporal/test/northern_plains_proxy | 0.945070 | 0.706668 | native_holdout_future_measured_threshold |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/radiation_fog.ubj | radiation_fog / future_test | 0.999209 | 0.985615 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/radiation_fog.ubj | radiation_fog / geographic_test | 0.999703 | 0.992507 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/smog_inversion_trap.ubj | smog_inversion_trap / future_test | 1.000000 | 1.000000 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/smog_inversion_trap.ubj | smog_inversion_trap / geographic_test | 1.000000 | 1.000000 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/smoke_plume.ubj | smoke_plume / future_test | 0.999881 | 0.998134 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/smoke_plume.ubj | smoke_plume / geographic_test | 0.999941 | 0.998713 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | archive:ml/model/storm | storm / weatherHistory_seed42_test20 | 0.999637 | 0.999263 | native_random_holdout |
| 1 | archive:ml/model_baseline/storm | storm / weatherHistory_seed42_test20 | 0.999637 | 0.999263 | native_random_holdout |
| 1 | archive:ml/model_india_26/storm | storm / weatherHistory_seed42_test20 | 0.920844 | 0.787751 | weatherHistory_transfer_diagnostic_not_original_test |
| 2 | archive:ml/model_india_26_baseline_repro/storm | storm / weatherHistory_seed42_test20 | 0.920637 | 0.787007 | weatherHistory_transfer_diagnostic_not_original_test |
| 2 | archive:ml/model_india_26_distilled/storm | storm / weatherHistory_seed42_test20 | 0.920637 | 0.787007 | weatherHistory_transfer_diagnostic_not_original_test |
| 2 | archive:ml/model_india_26_distilled_context/storm | storm / weatherHistory_seed42_test20 | 0.920637 | 0.787007 | weatherHistory_transfer_diagnostic_not_original_test |
| 2 | archive:ml/model_india_26_geo_temporal/storm | storm / weatherHistory_seed42_test20 | 0.920637 | 0.787007 | weatherHistory_transfer_diagnostic_not_original_test |
| 6 | archive:ml/model_india_pilot/storm | storm / weatherHistory_seed42_test20 | 0.920274 | 0.785702 | weatherHistory_transfer_diagnostic_not_original_test |
| 7 | archive:ml/model_india_26_masked_distilled_edge/storm | storm / weatherHistory_seed42_test20 | 0.856358 | 0.461311 | weatherHistory_transfer_diagnostic_not_original_test |
| 8 | archive:ml/model_india_26_verified_storm_candidate/storm | storm / weatherHistory_seed42_test20 | 0.855736 | 0.461130 | weatherHistory_transfer_diagnostic_not_original_test |
| 8 | archive:ml/model_india_storm_verified/storm | storm / weatherHistory_seed42_test20 | 0.855736 | 0.461130 | weatherHistory_transfer_diagnostic_not_original_test |
| 1 | archive:ml/model/wildfire | wildfire / weatherHistory_seed42_test20 | 0.999326 | 0.996460 | native_random_holdout |
| 1 | archive:ml/model_baseline/wildfire | wildfire / weatherHistory_seed42_test20 | 0.999326 | 0.996460 | native_random_holdout |
| 1 | archive:ml/model_india_26/wildfire | wildfire / weatherHistory_seed42_test20 | 0.950184 | 0.487228 | weatherHistory_transfer_diagnostic_not_original_test |
| 1 | archive:ml/model_india_26_baseline_repro/wildfire | wildfire / weatherHistory_seed42_test20 | 0.950184 | 0.487228 | weatherHistory_transfer_diagnostic_not_original_test |
| 1 | archive:ml/model_india_26_distilled/wildfire | wildfire / weatherHistory_seed42_test20 | 0.950184 | 0.487228 | weatherHistory_transfer_diagnostic_not_original_test |
| 1 | archive:ml/model_india_26_distilled_context/wildfire | wildfire / weatherHistory_seed42_test20 | 0.950184 | 0.487228 | weatherHistory_transfer_diagnostic_not_original_test |
| 1 | archive:ml/model_india_26_geo_temporal/wildfire | wildfire / weatherHistory_seed42_test20 | 0.950184 | 0.487228 | weatherHistory_transfer_diagnostic_not_original_test |
| 1 | archive:ml/model_india_26_masked_distilled_edge/wildfire | wildfire / weatherHistory_seed42_test20 | 0.950184 | 0.487228 | weatherHistory_transfer_diagnostic_not_original_test |
| 1 | archive:ml/model_india_26_verified_storm_candidate/wildfire | wildfire / weatherHistory_seed42_test20 | 0.950184 | 0.487228 | weatherHistory_transfer_diagnostic_not_original_test |
| 1 | archive:ml/model_india_pilot/wildfire | wildfire / weatherHistory_seed42_test20 | 0.950184 | 0.487228 | weatherHistory_transfer_diagnostic_not_original_test |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/wildfire_evaporative_risk.ubj | wildfire_evaporative_risk / future_test | 1.000000 | 1.000000 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |
| 1 | ml/models/uci_beijing_event_rules_6sensor/esp32_student/wildfire_evaporative_risk.ubj | wildfire_evaporative_risk / geographic_test | 1.000000 | 0.500000 | RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED |

## Regression results (classification accuracy is not applicable)

| Model | Split | Rows | MAE | RMSE | R² | Persistence MAE |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| ml/models/india_cpcb_5sensor_6h/teacher/temperature_c.ubj | future_test | 3592 | 1.981658 | 2.737575 | 0.764699 | 5.147608 |
| ml/models/india_cpcb_5sensor_6h/teacher/temperature_c.ubj | geographic_test | 1705 | 1.309136 | 1.649961 | 0.556182 | 1.727226 |
| ml/models/india_cpcb_5sensor_6h/teacher/temperature_c.ubj | Mandi_modeled_future_values | 714 | 2.287655 | 2.880535 | 0.549433 | 5.095938 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/temperature_c.ubj | future_test | 3592 | 4.335957 | 5.101009 | 0.183033 | 5.147608 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/temperature_c.ubj | geographic_test | 1705 | 1.672177 | 2.086537 | 0.290243 | 1.727226 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/temperature_c.ubj | Mandi_modeled_future_values | 714 | 4.616579 | 5.201662 | -0.469256 | 5.095938 |
| ml/models/india_cpcb_5sensor_6h/teacher/relative_humidity_pct.ubj | future_test | 3592 | 7.938032 | 10.990524 | 0.788654 | 16.520306 |
| ml/models/india_cpcb_5sensor_6h/teacher/relative_humidity_pct.ubj | geographic_test | 1597 | 10.017673 | 12.740023 | 0.353900 | 14.048429 |
| ml/models/india_cpcb_5sensor_6h/teacher/relative_humidity_pct.ubj | Mandi_modeled_future_values | 714 | 9.288037 | 12.214745 | 0.497496 | 19.560225 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/relative_humidity_pct.ubj | future_test | 3592 | 14.433320 | 17.441578 | 0.467734 | 16.520306 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/relative_humidity_pct.ubj | geographic_test | 1597 | 13.185810 | 15.976697 | -0.016092 | 14.048429 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/relative_humidity_pct.ubj | Mandi_modeled_future_values | 714 | 15.927847 | 18.031891 | -0.095099 | 19.560225 |
| ml/models/india_cpcb_5sensor_6h/teacher/pm25_ug_m3.ubj | future_test | 3468 | 31.147482 | 44.536021 | 0.591736 | 56.435699 |
| ml/models/india_cpcb_5sensor_6h/teacher/pm25_ug_m3.ubj | geographic_test | 1689 | 35.352367 | 53.353031 | 0.405033 | 46.659618 |
| ml/models/india_cpcb_5sensor_6h/teacher/pm25_ug_m3.ubj | Mandi_modeled_future_values | 714 | 10.797235 | 14.418850 | 0.201446 | 10.345098 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/pm25_ug_m3.ubj | future_test | 3468 | 45.609791 | 67.926510 | 0.050278 | 56.435699 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/pm25_ug_m3.ubj | geographic_test | 1689 | 40.503017 | 60.108201 | 0.244834 | 46.659618 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/pm25_ug_m3.ubj | Mandi_modeled_future_values | 714 | 10.330226 | 13.045453 | 0.346326 | 10.345098 |
| ml/models/india_cpcb_5sensor_6h/teacher/pm10_ug_m3.ubj | future_test | 3459 | 61.614597 | 89.750887 | 0.444280 | 109.125877 |
| ml/models/india_cpcb_5sensor_6h/teacher/pm10_ug_m3.ubj | geographic_test | 1684 | 58.745102 | 87.473235 | 0.285612 | 80.768517 |
| ml/models/india_cpcb_5sensor_6h/teacher/pm10_ug_m3.ubj | Mandi_modeled_future_values | 714 | 22.669132 | 32.441210 | -1.472309 | 12.168907 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/pm10_ug_m3.ubj | future_test | 3459 | 87.193176 | 126.164099 | -0.098120 | 109.125877 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/pm10_ug_m3.ubj | geographic_test | 1684 | 69.072189 | 99.311699 | 0.079160 | 80.768517 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/pm10_ug_m3.ubj | Mandi_modeled_future_values | 714 | 17.978313 | 22.578704 | -0.197586 | 12.168907 |
| ml/models/india_cpcb_5sensor_6h/teacher/wind_speed_mps.ubj | future_test | 3591 | 0.295423 | 0.432542 | 0.203813 | 0.418535 |
| ml/models/india_cpcb_5sensor_6h/teacher/wind_speed_mps.ubj | geographic_test | 1705 | 0.580134 | 0.786731 | 0.079974 | 0.834481 |
| ml/models/india_cpcb_5sensor_6h/teacher/wind_speed_mps.ubj | Mandi_modeled_future_values | 714 | 0.375689 | 0.465219 | 0.171402 | 0.607532 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/wind_speed_mps.ubj | future_test | 3591 | 0.349038 | 0.521262 | -0.156299 | 0.418535 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/wind_speed_mps.ubj | geographic_test | 1705 | 0.664565 | 0.883129 | -0.159299 | 0.834481 |
| ml/models/india_cpcb_5sensor_6h/esp32_student/wind_speed_mps.ubj | Mandi_modeled_future_values | 714 | 0.479916 | 0.608533 | -0.417741 | 0.607532 |
| ml/models/india_cpcb_pm_6h/teacher/pm25_ug_m3.ubj | future_test | 10157 | 27.986094 | 48.005572 | 0.673070 | 36.850834 |
| ml/models/india_cpcb_pm_6h/teacher/pm25_ug_m3.ubj | geographic_test | 1897 | 39.014366 | 57.387326 | 0.408070 | 48.820160 |
| ml/models/india_cpcb_pm_6h/teacher/pm25_ug_m3.ubj | Mandi_modeled_future_values | 714 | 9.780781 | 12.055710 | 0.441750 | 10.345098 |
| ml/models/india_cpcb_pm_6h/esp32_student/pm25_ug_m3.ubj | future_test | 10157 | 36.850834 | 65.300145 | 0.395078 | 36.850834 |
| ml/models/india_cpcb_pm_6h/esp32_student/pm25_ug_m3.ubj | geographic_test | 1897 | 48.820160 | 73.248930 | 0.035636 | 48.820160 |
| ml/models/india_cpcb_pm_6h/esp32_student/pm25_ug_m3.ubj | Mandi_modeled_future_values | 714 | 10.345098 | 13.104827 | 0.340362 | 10.345098 |
| ml/models/india_cpcb_pm_6h/teacher/pm10_ug_m3.ubj | future_test | 10159 | 50.199879 | 80.042216 | 0.568099 | 66.730232 |
| ml/models/india_cpcb_pm_6h/teacher/pm10_ug_m3.ubj | geographic_test | 1891 | 62.031693 | 88.460120 | 0.348878 | 82.545311 |
| ml/models/india_cpcb_pm_6h/teacher/pm10_ug_m3.ubj | Mandi_modeled_future_values | 714 | 14.310702 | 17.510634 | 0.279702 | 12.168907 |
| ml/models/india_cpcb_pm_6h/esp32_student/pm10_ug_m3.ubj | future_test | 10159 | 64.971741 | 107.203916 | 0.225241 | 66.730232 |
| ml/models/india_cpcb_pm_6h/esp32_student/pm10_ug_m3.ubj | geographic_test | 1891 | 79.695648 | 112.114491 | -0.045902 | 82.545311 |
| ml/models/india_cpcb_pm_6h/esp32_student/pm10_ug_m3.ubj | Mandi_modeled_future_values | 714 | 13.068712 | 16.625457 | 0.350684 | 12.168907 |
| ml/models/uci_beijing_5sensor_6h/teacher/temperature_c.ubj | future_test | 50964 | 1.864628 | 2.389007 | 0.961634 | 3.608204 |
| ml/models/uci_beijing_5sensor_6h/teacher/temperature_c.ubj | geographic_test | 16964 | 2.019476 | 2.609836 | 0.955061 | 3.868699 |
| ml/models/uci_beijing_5sensor_6h/teacher/temperature_c.ubj | Mandi_modeled_future_values | 714 | 2.630439 | 3.241900 | 0.429294 | 5.095938 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/temperature_c.ubj | future_test | 50964 | 3.195529 | 3.850549 | 0.900331 | 3.608204 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/temperature_c.ubj | geographic_test | 16964 | 3.513340 | 4.158574 | 0.885900 | 3.868699 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/temperature_c.ubj | Mandi_modeled_future_values | 714 | 4.781465 | 5.351039 | -0.554853 | 5.095938 |
| ml/models/uci_beijing_5sensor_6h/teacher/relative_humidity_pct.ubj | future_test | 50964 | 9.923376 | 13.117053 | 0.705387 | 15.927876 |
| ml/models/uci_beijing_5sensor_6h/teacher/relative_humidity_pct.ubj | geographic_test | 16964 | 9.580147 | 12.787230 | 0.718825 | 15.247670 |
| ml/models/uci_beijing_5sensor_6h/teacher/relative_humidity_pct.ubj | Mandi_modeled_future_values | 714 | 10.471743 | 13.597958 | 0.377244 | 19.560225 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/relative_humidity_pct.ubj | future_test | 50964 | 14.292105 | 17.739757 | 0.461141 | 15.927876 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/relative_humidity_pct.ubj | geographic_test | 16964 | 13.936581 | 16.920732 | 0.507663 | 15.247670 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/relative_humidity_pct.ubj | Mandi_modeled_future_values | 714 | 17.248194 | 19.513289 | -0.282424 | 19.560225 |
| ml/models/uci_beijing_5sensor_6h/teacher/pm25_ug_m3.ubj | future_test | 50479 | 32.719501 | 54.762970 | 0.656707 | 36.381683 |
| ml/models/uci_beijing_5sensor_6h/teacher/pm25_ug_m3.ubj | geographic_test | 16831 | 26.143990 | 44.354082 | 0.645128 | 26.886639 |
| ml/models/uci_beijing_5sensor_6h/teacher/pm25_ug_m3.ubj | Mandi_modeled_future_values | 714 | 11.467820 | 14.565305 | 0.185142 | 10.345098 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/pm25_ug_m3.ubj | future_test | 50479 | 34.993904 | 59.368990 | 0.596531 | 36.381683 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/pm25_ug_m3.ubj | geographic_test | 16831 | 26.144169 | 45.870692 | 0.620445 | 26.886639 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/pm25_ug_m3.ubj | Mandi_modeled_future_values | 714 | 10.869210 | 13.612113 | 0.288305 | 10.345098 |
| ml/models/uci_beijing_5sensor_6h/teacher/pm10_ug_m3.ubj | future_test | 50625 | 40.339012 | 63.759759 | 0.616606 | 45.850567 |
| ml/models/uci_beijing_5sensor_6h/teacher/pm10_ug_m3.ubj | geographic_test | 16868 | 33.674496 | 52.764929 | 0.584150 | 35.143528 |
| ml/models/uci_beijing_5sensor_6h/teacher/pm10_ug_m3.ubj | Mandi_modeled_future_values | 714 | 13.208736 | 17.144865 | 0.309479 | 12.168907 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/pm10_ug_m3.ubj | future_test | 50625 | 43.595249 | 68.363334 | 0.559244 | 45.850567 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/pm10_ug_m3.ubj | geographic_test | 16868 | 34.627460 | 54.210802 | 0.561048 | 35.143528 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/pm10_ug_m3.ubj | Mandi_modeled_future_values | 714 | 15.235689 | 18.830379 | 0.167035 | 12.168907 |
| ml/models/uci_beijing_5sensor_6h/teacher/wind_speed_mps.ubj | future_test | 51019 | 0.668380 | 0.938083 | 0.287291 | 0.892391 |
| ml/models/uci_beijing_5sensor_6h/teacher/wind_speed_mps.ubj | geographic_test | 16988 | 0.694632 | 0.999212 | 0.214567 | 0.923634 |
| ml/models/uci_beijing_5sensor_6h/teacher/wind_speed_mps.ubj | Mandi_modeled_future_values | 714 | 0.428306 | 0.536848 | -0.103395 | 0.607532 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/wind_speed_mps.ubj | future_test | 51019 | 0.730691 | 0.999322 | 0.191200 | 0.892391 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/wind_speed_mps.ubj | geographic_test | 16988 | 0.746537 | 1.060477 | 0.115300 | 0.923634 |
| ml/models/uci_beijing_5sensor_6h/esp32_student/wind_speed_mps.ubj | Mandi_modeled_future_values | 714 | 0.631073 | 0.751912 | -1.164521 | 0.607532 |
| ml/models/uci_beijing_6h/teacher/temperature_c.ubj | future_test | 50964 | 1.829963 | 2.353383 | 0.962770 | 3.608204 |
| ml/models/uci_beijing_6h/teacher/temperature_c.ubj | geographic_test | 16964 | 2.025021 | 2.604741 | 0.955236 | 3.868699 |
| ml/models/uci_beijing_6h/teacher/temperature_c.ubj | Mandi_modeled_future_values | 714 | 2.978722 | 3.666120 | 0.270162 | 5.095938 |
| ml/models/uci_beijing_6h/esp32_student/temperature_c.ubj | future_test | 50964 | 3.198492 | 3.849232 | 0.900399 | 3.608204 |
| ml/models/uci_beijing_6h/esp32_student/temperature_c.ubj | geographic_test | 16964 | 3.525070 | 4.154021 | 0.886150 | 3.868699 |
| ml/models/uci_beijing_6h/esp32_student/temperature_c.ubj | Mandi_modeled_future_values | 714 | 4.767087 | 5.292156 | -0.520822 | 5.095938 |
| ml/models/uci_beijing_6h/teacher/relative_humidity_pct.ubj | future_test | 50964 | 9.653330 | 12.807555 | 0.719126 | 15.927876 |
| ml/models/uci_beijing_6h/teacher/relative_humidity_pct.ubj | geographic_test | 16964 | 9.625280 | 12.797803 | 0.718359 | 15.247670 |
| ml/models/uci_beijing_6h/teacher/relative_humidity_pct.ubj | Mandi_modeled_future_values | 714 | 14.003953 | 17.255196 | -0.002791 | 19.560225 |
| ml/models/uci_beijing_6h/esp32_student/relative_humidity_pct.ubj | future_test | 50964 | 14.334477 | 17.755448 | 0.460188 | 15.927876 |
| ml/models/uci_beijing_6h/esp32_student/relative_humidity_pct.ubj | geographic_test | 16964 | 13.973976 | 16.905364 | 0.508557 | 15.247670 |
| ml/models/uci_beijing_6h/esp32_student/relative_humidity_pct.ubj | Mandi_modeled_future_values | 714 | 17.158398 | 19.162110 | -0.236680 | 19.560225 |
| ml/models/uci_beijing_6h/teacher/pressure_hpa.ubj | future_test | 50964 | 1.300574 | 1.756313 | 0.972026 | 1.839361 |
| ml/models/uci_beijing_6h/teacher/pressure_hpa.ubj | geographic_test | 16970 | 1.306415 | 1.737833 | 0.971283 | 1.843270 |
| ml/models/uci_beijing_6h/teacher/pressure_hpa.ubj | Mandi_modeled_future_values | 714 | 2.142903 | 2.476763 | 0.063984 | 1.696918 |
| ml/models/uci_beijing_6h/esp32_student/pressure_hpa.ubj | future_test | 50964 | 1.793230 | 2.302370 | 0.951927 | 1.839361 |
| ml/models/uci_beijing_6h/esp32_student/pressure_hpa.ubj | geographic_test | 16970 | 1.783909 | 2.297490 | 0.949808 | 1.843270 |
| ml/models/uci_beijing_6h/esp32_student/pressure_hpa.ubj | Mandi_modeled_future_values | 714 | 1.771123 | 2.131616 | 0.306682 | 1.696918 |
| ml/models/uci_beijing_6h/teacher/pm25_ug_m3.ubj | future_test | 50479 | 32.301071 | 54.311637 | 0.662342 | 36.381683 |
| ml/models/uci_beijing_6h/teacher/pm25_ug_m3.ubj | geographic_test | 16831 | 25.843815 | 44.128120 | 0.648735 | 26.886639 |
| ml/models/uci_beijing_6h/teacher/pm25_ug_m3.ubj | Mandi_modeled_future_values | 714 | 10.152187 | 13.764261 | 0.272306 | 10.345098 |
| ml/models/uci_beijing_6h/esp32_student/pm25_ug_m3.ubj | future_test | 50479 | 34.918980 | 58.743482 | 0.604988 | 36.381683 |
| ml/models/uci_beijing_6h/esp32_student/pm25_ug_m3.ubj | geographic_test | 16831 | 26.242636 | 45.357669 | 0.628888 | 26.886639 |
| ml/models/uci_beijing_6h/esp32_student/pm25_ug_m3.ubj | Mandi_modeled_future_values | 714 | 11.525719 | 14.305036 | 0.214003 | 10.345098 |
| ml/models/uci_beijing_6h/teacher/pm10_ug_m3.ubj | future_test | 50625 | 39.857838 | 63.368938 | 0.621292 | 45.850567 |
| ml/models/uci_beijing_6h/teacher/pm10_ug_m3.ubj | geographic_test | 16868 | 33.457298 | 52.749352 | 0.584396 | 35.143528 |
| ml/models/uci_beijing_6h/teacher/pm10_ug_m3.ubj | Mandi_modeled_future_values | 714 | 13.271233 | 17.278959 | 0.298635 | 12.168907 |
| ml/models/uci_beijing_6h/esp32_student/pm10_ug_m3.ubj | future_test | 50625 | 43.524796 | 68.728221 | 0.554527 | 45.850567 |
| ml/models/uci_beijing_6h/esp32_student/pm10_ug_m3.ubj | geographic_test | 16868 | 34.328148 | 54.435921 | 0.557395 | 35.143528 |
| ml/models/uci_beijing_6h/esp32_student/pm10_ug_m3.ubj | Mandi_modeled_future_values | 714 | 14.054061 | 17.626074 | 0.270173 | 12.168907 |
| ml/models/uci_beijing_6h/teacher/wind_speed_mps.ubj | future_test | 51019 | 0.657017 | 0.927486 | 0.303302 | 0.892391 |
| ml/models/uci_beijing_6h/teacher/wind_speed_mps.ubj | geographic_test | 16988 | 0.696781 | 0.989580 | 0.229636 | 0.923634 |
| ml/models/uci_beijing_6h/teacher/wind_speed_mps.ubj | Mandi_modeled_future_values | 714 | 0.518810 | 0.626601 | -0.503180 | 0.607532 |
| ml/models/uci_beijing_6h/esp32_student/wind_speed_mps.ubj | future_test | 51019 | 0.731567 | 1.000842 | 0.188738 | 0.892391 |
| ml/models/uci_beijing_6h/esp32_student/wind_speed_mps.ubj | geographic_test | 16988 | 0.745657 | 1.059038 | 0.117698 | 0.923634 |
| ml/models/uci_beijing_6h/esp32_student/wind_speed_mps.ubj | Mandi_modeled_future_values | 714 | 0.641030 | 0.762887 | -1.228174 | 0.607532 |
| ml/models/uci_beijing_pm_6h/teacher/pm25_ug_m3.ubj | future_test | 50639 | 35.038342 | 59.100197 | 0.599420 | 36.491142 |
| ml/models/uci_beijing_pm_6h/teacher/pm25_ug_m3.ubj | geographic_test | 16889 | 26.453533 | 45.826119 | 0.620504 | 27.013382 |
| ml/models/uci_beijing_pm_6h/teacher/pm25_ug_m3.ubj | Mandi_modeled_future_values | 714 | 11.390447 | 14.145485 | 0.231439 | 10.345098 |
| ml/models/uci_beijing_pm_6h/esp32_student/pm25_ug_m3.ubj | future_test | 50639 | 35.355247 | 59.627477 | 0.592240 | 36.491142 |
| ml/models/uci_beijing_pm_6h/esp32_student/pm25_ug_m3.ubj | geographic_test | 16889 | 26.478022 | 46.038532 | 0.616978 | 27.013382 |
| ml/models/uci_beijing_pm_6h/esp32_student/pm25_ug_m3.ubj | Mandi_modeled_future_values | 714 | 11.527678 | 14.280983 | 0.216644 | 10.345098 |
| ml/models/uci_beijing_pm_6h/teacher/pm10_ug_m3.ubj | future_test | 50785 | 43.833199 | 68.427689 | 0.557699 | 45.923325 |
| ml/models/uci_beijing_pm_6h/teacher/pm10_ug_m3.ubj | geographic_test | 16926 | 34.654583 | 54.180482 | 0.560854 | 35.248672 |
| ml/models/uci_beijing_pm_6h/teacher/pm10_ug_m3.ubj | Mandi_modeled_future_values | 714 | 15.401896 | 18.615920 | 0.185900 | 12.168907 |
| ml/models/uci_beijing_pm_6h/esp32_student/pm10_ug_m3.ubj | future_test | 50785 | 44.613991 | 70.680951 | 0.528091 | 45.923325 |
| ml/models/uci_beijing_pm_6h/esp32_student/pm10_ug_m3.ubj | geographic_test | 16926 | 34.614071 | 55.863308 | 0.533151 | 35.248672 |
| ml/models/uci_beijing_pm_6h/esp32_student/pm10_ug_m3.ubj | Mandi_modeled_future_values | 714 | 13.179580 | 16.632233 | 0.350155 | 12.168907 |

## Per-class reports and confusion matrices

Binary matrix order is [negative, positive], rows=true and columns=predicted. Zero-support classes have zero F1 by explicit convention.

### archive:ml/model/wildfire — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.999326; macro-F1 0.996460.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9992908188314876,
      "f1-score": 0.9996452836366613,
      "support": 18331.0
    },
    "positive": {
      "precision": 0.986639260020555,
      "recall": 1.0,
      "f1-score": 0.9932747025349198,
      "support": 960.0
    },
    "accuracy": 0.9993261106215333,
    "macro avg": {
      "precision": 0.9933196300102776,
      "recall": 0.9996454094157439,
      "f1-score": 0.9964599930857905,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9993351142822939,
      "recall": 0.9993261106215333,
      "f1-score": 0.9993282571550028,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      18318,
      13
    ],
    [
      0,
      960
    ]
  ],
  "true_share": {
    "negative": 0.9502358612824633,
    "positive": 0.049764138717536675
  },
  "predicted_share": {
    "negative": 0.9495619719039967,
    "positive": 0.05043802809600332
  }
}
```

### archive:ml/model/wildfire — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.956825; macro-F1 0.488968.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9568245125348189,
      "f1-score": 0.9779359430604982,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 0.9568245125348189,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.47841225626740946,
      "f1-score": 0.4889679715302491,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 0.9568245125348189,
      "f1-score": 0.9779359430604982,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      687,
      31
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 0.9568245125348189,
    "positive": 0.04317548746518106
  }
}
```

### archive:ml/model/flood — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.999119; macro-F1 0.996713.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.999050597565062,
      "f1-score": 0.9995250733342645,
      "support": 17906.0
    },
    "positive": {
      "precision": 0.9878744650499287,
      "recall": 1.0,
      "f1-score": 0.9939002511661285,
      "support": 1385.0
    },
    "accuracy": 0.9991187600435436,
    "macro avg": {
      "precision": 0.9939372325249644,
      "recall": 0.9995252987825309,
      "f1-score": 0.9967126622501965,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9991294455494351,
      "recall": 0.9991187600435436,
      "f1-score": 0.9991212384525648,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      17889,
      17
    ],
    [
      0,
      1385
    ]
  ],
  "true_share": {
    "negative": 0.9282048623710538,
    "positive": 0.07179513762894614
  },
  "predicted_share": {
    "negative": 0.9273236224145974,
    "positive": 0.07267637758540252
  }
}
```

### archive:ml/model/flood — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model/storm — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.999637; macro-F1 0.999263.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9995762711864407,
      "f1-score": 0.9997880906971816,
      "support": 16520.0
    },
    "positive": {
      "precision": 0.9974802015838733,
      "recall": 1.0,
      "f1-score": 0.9987385114435033,
      "support": 2771.0
    },
    "accuracy": 0.9996371364885179,
    "macro avg": {
      "precision": 0.9987401007919366,
      "recall": 0.9997881355932203,
      "f1-score": 0.9992633010703424,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9996380508314195,
      "recall": 0.9996371364885179,
      "f1-score": 0.9996373269155246,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      16513,
      7
    ],
    [
      0,
      2771
    ]
  ],
  "true_share": {
    "negative": 0.8563578870976103,
    "positive": 0.1436421129023897
  },
  "predicted_share": {
    "negative": 0.8559950235861282,
    "positive": 0.14400497641387175
  }
}
```

### archive:ml/model/storm — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model/air_quality — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.998134; macro-F1 0.998105.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9957552175451008,
      "recall": 1.0,
      "f1-score": 0.9978730946472882,
      "support": 8445.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.9966808039830353,
      "f1-score": 0.9983376431473956,
      "support": 10846.0
    },
    "accuracy": 0.9981338447980924,
    "macro avg": {
      "precision": 0.9978776087725504,
      "recall": 0.9983404019915176,
      "f1-score": 0.9981053688973419,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9981417662209515,
      "recall": 0.9981338447980924,
      "f1-score": 0.9981342782578924,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      8445,
      0
    ],
    [
      36,
      10810
    ]
  ],
  "true_share": {
    "negative": 0.43776890778083044,
    "positive": 0.5622310922191696
  },
  "predicted_share": {
    "negative": 0.4396350629827381,
    "positive": 0.560364937017262
  }
}
```

### archive:ml/model/air_quality — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.456825; macro-F1 0.381887.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.4256259204712813,
      "f1-score": 0.5971074380165289,
      "support": 679.0
    },
    "positive": {
      "precision": 0.09090909090909091,
      "recall": 1.0,
      "f1-score": 0.16666666666666666,
      "support": 39.0
    },
    "accuracy": 0.4568245125348189,
    "macro avg": {
      "precision": 0.5454545454545454,
      "recall": 0.7128129602356407,
      "f1-score": 0.38188705234159775,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.950620410230438,
      "recall": 0.4568245125348189,
      "f1-score": 0.5737269504362439,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      289,
      390
    ],
    [
      0,
      39
    ]
  ],
  "true_share": {
    "negative": 0.9456824512534819,
    "positive": 0.054317548746518104
  },
  "predicted_share": {
    "negative": 0.4025069637883008,
    "positive": 0.5974930362116991
  }
}
```

### archive:ml/model_baseline/wildfire — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.999326; macro-F1 0.996460.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9992908188314876,
      "f1-score": 0.9996452836366613,
      "support": 18331.0
    },
    "positive": {
      "precision": 0.986639260020555,
      "recall": 1.0,
      "f1-score": 0.9932747025349198,
      "support": 960.0
    },
    "accuracy": 0.9993261106215333,
    "macro avg": {
      "precision": 0.9933196300102776,
      "recall": 0.9996454094157439,
      "f1-score": 0.9964599930857905,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9993351142822939,
      "recall": 0.9993261106215333,
      "f1-score": 0.9993282571550028,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      18318,
      13
    ],
    [
      0,
      960
    ]
  ],
  "true_share": {
    "negative": 0.9502358612824633,
    "positive": 0.049764138717536675
  },
  "predicted_share": {
    "negative": 0.9495619719039967,
    "positive": 0.05043802809600332
  }
}
```

### archive:ml/model_baseline/wildfire — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.956825; macro-F1 0.488968.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9568245125348189,
      "f1-score": 0.9779359430604982,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 0.9568245125348189,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.47841225626740946,
      "f1-score": 0.4889679715302491,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 0.9568245125348189,
      "f1-score": 0.9779359430604982,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      687,
      31
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 0.9568245125348189,
    "positive": 0.04317548746518106
  }
}
```

### archive:ml/model_baseline/flood — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.999119; macro-F1 0.996713.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.999050597565062,
      "f1-score": 0.9995250733342645,
      "support": 17906.0
    },
    "positive": {
      "precision": 0.9878744650499287,
      "recall": 1.0,
      "f1-score": 0.9939002511661285,
      "support": 1385.0
    },
    "accuracy": 0.9991187600435436,
    "macro avg": {
      "precision": 0.9939372325249644,
      "recall": 0.9995252987825309,
      "f1-score": 0.9967126622501965,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9991294455494351,
      "recall": 0.9991187600435436,
      "f1-score": 0.9991212384525648,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      17889,
      17
    ],
    [
      0,
      1385
    ]
  ],
  "true_share": {
    "negative": 0.9282048623710538,
    "positive": 0.07179513762894614
  },
  "predicted_share": {
    "negative": 0.9273236224145974,
    "positive": 0.07267637758540252
  }
}
```

### archive:ml/model_baseline/flood — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_baseline/storm — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.999637; macro-F1 0.999263.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9995762711864407,
      "f1-score": 0.9997880906971816,
      "support": 16520.0
    },
    "positive": {
      "precision": 0.9974802015838733,
      "recall": 1.0,
      "f1-score": 0.9987385114435033,
      "support": 2771.0
    },
    "accuracy": 0.9996371364885179,
    "macro avg": {
      "precision": 0.9987401007919366,
      "recall": 0.9997881355932203,
      "f1-score": 0.9992633010703424,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9996380508314195,
      "recall": 0.9996371364885179,
      "f1-score": 0.9996373269155246,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      16513,
      7
    ],
    [
      0,
      2771
    ]
  ],
  "true_share": {
    "negative": 0.8563578870976103,
    "positive": 0.1436421129023897
  },
  "predicted_share": {
    "negative": 0.8559950235861282,
    "positive": 0.14400497641387175
  }
}
```

### archive:ml/model_baseline/storm — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_baseline/air_quality — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.998134; macro-F1 0.998105.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9957552175451008,
      "recall": 1.0,
      "f1-score": 0.9978730946472882,
      "support": 8445.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.9966808039830353,
      "f1-score": 0.9983376431473956,
      "support": 10846.0
    },
    "accuracy": 0.9981338447980924,
    "macro avg": {
      "precision": 0.9978776087725504,
      "recall": 0.9983404019915176,
      "f1-score": 0.9981053688973419,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9981417662209515,
      "recall": 0.9981338447980924,
      "f1-score": 0.9981342782578924,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      8445,
      0
    ],
    [
      36,
      10810
    ]
  ],
  "true_share": {
    "negative": 0.43776890778083044,
    "positive": 0.5622310922191696
  },
  "predicted_share": {
    "negative": 0.4396350629827381,
    "positive": 0.560364937017262
  }
}
```

### archive:ml/model_baseline/air_quality — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.456825; macro-F1 0.381887.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.4256259204712813,
      "f1-score": 0.5971074380165289,
      "support": 679.0
    },
    "positive": {
      "precision": 0.09090909090909091,
      "recall": 1.0,
      "f1-score": 0.16666666666666666,
      "support": 39.0
    },
    "accuracy": 0.4568245125348189,
    "macro avg": {
      "precision": 0.5454545454545454,
      "recall": 0.7128129602356407,
      "f1-score": 0.38188705234159775,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.950620410230438,
      "recall": 0.4568245125348189,
      "f1-score": 0.5737269504362439,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      289,
      390
    ],
    [
      0,
      39
    ]
  ],
  "true_share": {
    "negative": 0.9456824512534819,
    "positive": 0.054317548746518104
  },
  "predicted_share": {
    "negative": 0.4025069637883008,
    "positive": 0.5974930362116991
  }
}
```

### archive:ml/model_india_26/wildfire — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.950184; macro-F1 0.487228.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9502332814930016,
      "recall": 0.9999454476024221,
      "f1-score": 0.9744557560936711,
      "support": 18331.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 960.0
    },
    "accuracy": 0.9501840236379658,
    "macro avg": {
      "precision": 0.4751166407465008,
      "recall": 0.49997272380121105,
      "f1-score": 0.48722787804683554,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9029457406587637,
      "recall": 0.9501840236379658,
      "f1-score": 0.9259628046733236,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      18330,
      1
    ],
    [
      960,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9502358612824633,
    "positive": 0.049764138717536675
  },
  "predicted_share": {
    "negative": 0.9999481623555025,
    "positive": 5.183764449743404e-05
  }
}
```

### archive:ml/model_india_26/wildfire — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.995822; macro-F1 0.498953.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813678,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 0.9958217270194986,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.4979108635097493,
      "f1-score": 0.4989532449406839,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813677,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      715,
      3
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 0.9958217270194986,
    "positive": 0.004178272980501393
  }
}
```

### archive:ml/model_india_26/flood — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.952309; macro-F1 0.738828.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9511314140019123,
      "recall": 1.0,
      "f1-score": 0.9749537188282696,
      "support": 17906.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.33574007220216606,
      "f1-score": 0.5027027027027027,
      "support": 1385.0
    },
    "accuracy": 0.9523093670623607,
    "macro avg": {
      "precision": 0.9755657070009561,
      "recall": 0.667870036101083,
      "f1-score": 0.7388282107654862,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.954639940859377,
      "recall": 0.9523093670623607,
      "f1-score": 0.941048392130125,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      17906,
      0
    ],
    [
      920,
      465
    ]
  ],
  "true_share": {
    "negative": 0.9282048623710538,
    "positive": 0.07179513762894614
  },
  "predicted_share": {
    "negative": 0.9758954953086931,
    "positive": 0.024104504691306827
  }
}
```

### archive:ml/model_india_26/flood — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26/storm — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.920844; macro-F1 0.787751.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.915387599046933,
      "recall": 1.0,
      "f1-score": 0.9558249197211213,
      "support": 16520.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.4489354023818116,
      "f1-score": 0.6196762141967621,
      "support": 2771.0
    },
    "accuracy": 0.9208439168524182,
    "macro avg": {
      "precision": 0.9576937995234664,
      "recall": 0.7244677011909058,
      "f1-score": 0.7877505669589417,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9275415030975757,
      "recall": 0.9208439168524182,
      "f1-score": 0.9075398094101993,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      16520,
      0
    ],
    [
      1527,
      1244
    ]
  ],
  "true_share": {
    "negative": 0.8563578870976103,
    "positive": 0.1436421129023897
  },
  "predicted_share": {
    "negative": 0.935513970245192,
    "positive": 0.06448602975480794
  }
}
```

### archive:ml/model_india_26/storm — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26/air_quality — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.439272; macro-F1 0.307463.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.4384279929394663,
      "recall": 1.0,
      "f1-score": 0.6095932435846537,
      "support": 8445.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.00267379679144385,
      "f1-score": 0.005333333333333333,
      "support": 10846.0
    },
    "accuracy": 0.439272199471256,
    "macro avg": {
      "precision": 0.7192139964697332,
      "recall": 0.5013368983957219,
      "f1-score": 0.3074632884589935,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.7541612358288214,
      "recall": 0.439272199471256,
      "f1-score": 0.26985953425979653,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      8445,
      0
    ],
    [
      10817,
      29
    ]
  ],
  "true_share": {
    "negative": 0.43776890778083044,
    "positive": 0.5622310922191696
  },
  "predicted_share": {
    "negative": 0.9984967083095744,
    "positive": 0.001503291690425587
  }
}
```

### archive:ml/model_india_26/air_quality — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.309192; macro-F1 0.278538.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9893048128342246,
      "recall": 0.27245949926362295,
      "f1-score": 0.42725173210161665,
      "support": 679.0
    },
    "positive": {
      "precision": 0.0696798493408663,
      "recall": 0.9487179487179487,
      "f1-score": 0.12982456140350876,
      "support": 39.0
    },
    "accuracy": 0.30919220055710306,
    "macro avg": {
      "precision": 0.5294923310875455,
      "recall": 0.6105887239907858,
      "f1-score": 0.2785381467525627,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9393530390511592,
      "recall": 0.309192200557103,
      "f1-score": 0.4110962172586832,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      185,
      494
    ],
    [
      2,
      37
    ]
  ],
  "true_share": {
    "negative": 0.9456824512534819,
    "positive": 0.054317548746518104
  },
  "predicted_share": {
    "negative": 0.2604456824512535,
    "positive": 0.7395543175487466
  }
}
```

### archive:ml/model_india_26_baseline_repro/wildfire — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.950184; macro-F1 0.487228.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9502332814930016,
      "recall": 0.9999454476024221,
      "f1-score": 0.9744557560936711,
      "support": 18331.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 960.0
    },
    "accuracy": 0.9501840236379658,
    "macro avg": {
      "precision": 0.4751166407465008,
      "recall": 0.49997272380121105,
      "f1-score": 0.48722787804683554,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9029457406587637,
      "recall": 0.9501840236379658,
      "f1-score": 0.9259628046733236,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      18330,
      1
    ],
    [
      960,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9502358612824633,
    "positive": 0.049764138717536675
  },
  "predicted_share": {
    "negative": 0.9999481623555025,
    "positive": 5.183764449743404e-05
  }
}
```

### archive:ml/model_india_26_baseline_repro/wildfire — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.995822; macro-F1 0.498953.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813678,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 0.9958217270194986,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.4979108635097493,
      "f1-score": 0.4989532449406839,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813677,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      715,
      3
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 0.9958217270194986,
    "positive": 0.004178272980501393
  }
}
```

### archive:ml/model_india_26_baseline_repro/flood — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.951635; macro-F1 0.733358.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9504750782950263,
      "recall": 1.0,
      "f1-score": 0.9746087903116071,
      "support": 17906.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.3263537906137184,
      "f1-score": 0.49210669569951004,
      "support": 1385.0
    },
    "accuracy": 0.951635477683894,
    "macro avg": {
      "precision": 0.9752375391475132,
      "recall": 0.6631768953068592,
      "f1-score": 0.7333577430055586,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9540307268648976,
      "recall": 0.951635477683894,
      "f1-score": 0.9399674860226769,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      17906,
      0
    ],
    [
      933,
      452
    ]
  ],
  "true_share": {
    "negative": 0.9282048623710538,
    "positive": 0.07179513762894614
  },
  "predicted_share": {
    "negative": 0.9765693846871598,
    "positive": 0.023430615312840186
  }
}
```

### archive:ml/model_india_26_baseline_repro/flood — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26_baseline_repro/storm — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.920637; macro-F1 0.787007.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9151847543072406,
      "recall": 1.0,
      "f1-score": 0.955714327037112,
      "support": 16520.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.4474918801876579,
      "f1-score": 0.618299675891299,
      "support": 2771.0
    },
    "accuracy": 0.9206365662744285,
    "macro avg": {
      "precision": 0.9575923771536203,
      "recall": 0.723745940093829,
      "f1-score": 0.7870070014642054,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9273677954048838,
      "recall": 0.9206365662744285,
      "f1-score": 0.9072473736223048,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      16520,
      0
    ],
    [
      1531,
      1240
    ]
  ],
  "true_share": {
    "negative": 0.8563578870976103,
    "positive": 0.1436421129023897
  },
  "predicted_share": {
    "negative": 0.9357213208231818,
    "positive": 0.0642786791768182
  }
}
```

### archive:ml/model_india_26_baseline_repro/storm — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26_baseline_repro/air_quality — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.438028; macro-F1 0.304994.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.4378824017421964,
      "recall": 1.0,
      "f1-score": 0.6090656665825249,
      "support": 8445.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.0004609994468006638,
      "f1-score": 0.0009215740484747949,
      "support": 10846.0
    },
    "accuracy": 0.4380280960033176,
    "macro avg": {
      "precision": 0.7189412008710983,
      "recall": 0.5002304997234003,
      "f1-score": 0.30499362031549987,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.7539223929662977,
      "recall": 0.4380280960033176,
      "f1-score": 0.26714814921047014,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      8445,
      0
    ],
    [
      10841,
      5
    ]
  ],
  "true_share": {
    "negative": 0.43776890778083044,
    "positive": 0.5622310922191696
  },
  "predicted_share": {
    "negative": 0.9997408117775128,
    "positive": 0.00025918822248717017
  }
}
```

### archive:ml/model_india_26_baseline_repro/air_quality — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.552925; macro-F1 0.439492.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.994475138121547,
      "recall": 0.5301914580265096,
      "f1-score": 0.69164265129683,
      "support": 679.0
    },
    "positive": {
      "precision": 0.10393258426966293,
      "recall": 0.9487179487179487,
      "f1-score": 0.18734177215189873,
      "support": 39.0
    },
    "accuracy": 0.552924791086351,
    "macro avg": {
      "precision": 0.5492038611956049,
      "recall": 0.7394547033722292,
      "f1-score": 0.43949221172436437,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9461030495418487,
      "recall": 0.552924791086351,
      "f1-score": 0.6642502637109633,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      360,
      319
    ],
    [
      2,
      37
    ]
  ],
  "true_share": {
    "negative": 0.9456824512534819,
    "positive": 0.054317548746518104
  },
  "predicted_share": {
    "negative": 0.5041782729805014,
    "positive": 0.4958217270194986
  }
}
```

### archive:ml/model_india_26_distilled/wildfire — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.950184; macro-F1 0.487228.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9502332814930016,
      "recall": 0.9999454476024221,
      "f1-score": 0.9744557560936711,
      "support": 18331.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 960.0
    },
    "accuracy": 0.9501840236379658,
    "macro avg": {
      "precision": 0.4751166407465008,
      "recall": 0.49997272380121105,
      "f1-score": 0.48722787804683554,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9029457406587637,
      "recall": 0.9501840236379658,
      "f1-score": 0.9259628046733236,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      18330,
      1
    ],
    [
      960,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9502358612824633,
    "positive": 0.049764138717536675
  },
  "predicted_share": {
    "negative": 0.9999481623555025,
    "positive": 5.183764449743404e-05
  }
}
```

### archive:ml/model_india_26_distilled/wildfire — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.995822; macro-F1 0.498953.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813678,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 0.9958217270194986,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.4979108635097493,
      "f1-score": 0.4989532449406839,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813677,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      715,
      3
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 0.9958217270194986,
    "positive": 0.004178272980501393
  }
}
```

### archive:ml/model_india_26_distilled/flood — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.951635; macro-F1 0.733358.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9504750782950263,
      "recall": 1.0,
      "f1-score": 0.9746087903116071,
      "support": 17906.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.3263537906137184,
      "f1-score": 0.49210669569951004,
      "support": 1385.0
    },
    "accuracy": 0.951635477683894,
    "macro avg": {
      "precision": 0.9752375391475132,
      "recall": 0.6631768953068592,
      "f1-score": 0.7333577430055586,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9540307268648976,
      "recall": 0.951635477683894,
      "f1-score": 0.9399674860226769,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      17906,
      0
    ],
    [
      933,
      452
    ]
  ],
  "true_share": {
    "negative": 0.9282048623710538,
    "positive": 0.07179513762894614
  },
  "predicted_share": {
    "negative": 0.9765693846871598,
    "positive": 0.023430615312840186
  }
}
```

### archive:ml/model_india_26_distilled/flood — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26_distilled/storm — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.920637; macro-F1 0.787007.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9151847543072406,
      "recall": 1.0,
      "f1-score": 0.955714327037112,
      "support": 16520.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.4474918801876579,
      "f1-score": 0.618299675891299,
      "support": 2771.0
    },
    "accuracy": 0.9206365662744285,
    "macro avg": {
      "precision": 0.9575923771536203,
      "recall": 0.723745940093829,
      "f1-score": 0.7870070014642054,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9273677954048838,
      "recall": 0.9206365662744285,
      "f1-score": 0.9072473736223048,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      16520,
      0
    ],
    [
      1531,
      1240
    ]
  ],
  "true_share": {
    "negative": 0.8563578870976103,
    "positive": 0.1436421129023897
  },
  "predicted_share": {
    "negative": 0.9357213208231818,
    "positive": 0.0642786791768182
  }
}
```

### archive:ml/model_india_26_distilled/storm — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26_distilled/air_quality — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.437821; macro-F1 0.304581.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.43779160186625193,
      "recall": 1.0,
      "f1-score": 0.6089778258518118,
      "support": 8445.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 9.219988936013277e-05,
      "f1-score": 0.00018438277864847423,
      "support": 10846.0
    },
    "accuracy": 0.4378207454253279,
    "macro avg": {
      "precision": 0.718895800933126,
      "recall": 0.5000460999446801,
      "f1-score": 0.30458110431523017,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.7538826436037789,
      "recall": 0.4378207454253279,
      "f1-score": 0.26669522341691837,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      8445,
      0
    ],
    [
      10845,
      1
    ]
  ],
  "true_share": {
    "negative": 0.43776890778083044,
    "positive": 0.5622310922191696
  },
  "predicted_share": {
    "negative": 0.9999481623555025,
    "positive": 5.183764449743404e-05
  }
}
```

### archive:ml/model_india_26_distilled/air_quality — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.997214; macro-F1 0.986107.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9970631424375918,
      "recall": 1.0,
      "f1-score": 0.9985294117647059,
      "support": 679.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.9487179487179487,
      "f1-score": 0.9736842105263158,
      "support": 39.0
    },
    "accuracy": 0.9972144846796658,
    "macro avg": {
      "precision": 0.9985315712187959,
      "recall": 0.9743589743589743,
      "f1-score": 0.9861068111455109,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9972226653413995,
      "recall": 0.9972144846796658,
      "f1-score": 0.9971798813353226,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      679,
      0
    ],
    [
      2,
      37
    ]
  ],
  "true_share": {
    "negative": 0.9456824512534819,
    "positive": 0.054317548746518104
  },
  "predicted_share": {
    "negative": 0.9484679665738162,
    "positive": 0.05153203342618384
  }
}
```

### archive:ml/model_india_26_distilled_context/wildfire — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.950184; macro-F1 0.487228.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9502332814930016,
      "recall": 0.9999454476024221,
      "f1-score": 0.9744557560936711,
      "support": 18331.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 960.0
    },
    "accuracy": 0.9501840236379658,
    "macro avg": {
      "precision": 0.4751166407465008,
      "recall": 0.49997272380121105,
      "f1-score": 0.48722787804683554,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9029457406587637,
      "recall": 0.9501840236379658,
      "f1-score": 0.9259628046733236,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      18330,
      1
    ],
    [
      960,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9502358612824633,
    "positive": 0.049764138717536675
  },
  "predicted_share": {
    "negative": 0.9999481623555025,
    "positive": 5.183764449743404e-05
  }
}
```

### archive:ml/model_india_26_distilled_context/wildfire — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.995822; macro-F1 0.498953.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813678,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 0.9958217270194986,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.4979108635097493,
      "f1-score": 0.4989532449406839,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813677,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      715,
      3
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 0.9958217270194986,
    "positive": 0.004178272980501393
  }
}
```

### archive:ml/model_india_26_distilled_context/flood — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.951635; macro-F1 0.733358.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9504750782950263,
      "recall": 1.0,
      "f1-score": 0.9746087903116071,
      "support": 17906.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.3263537906137184,
      "f1-score": 0.49210669569951004,
      "support": 1385.0
    },
    "accuracy": 0.951635477683894,
    "macro avg": {
      "precision": 0.9752375391475132,
      "recall": 0.6631768953068592,
      "f1-score": 0.7333577430055586,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9540307268648976,
      "recall": 0.951635477683894,
      "f1-score": 0.9399674860226769,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      17906,
      0
    ],
    [
      933,
      452
    ]
  ],
  "true_share": {
    "negative": 0.9282048623710538,
    "positive": 0.07179513762894614
  },
  "predicted_share": {
    "negative": 0.9765693846871598,
    "positive": 0.023430615312840186
  }
}
```

### archive:ml/model_india_26_distilled_context/flood — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26_distilled_context/storm — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.920637; macro-F1 0.787007.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9151847543072406,
      "recall": 1.0,
      "f1-score": 0.955714327037112,
      "support": 16520.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.4474918801876579,
      "f1-score": 0.618299675891299,
      "support": 2771.0
    },
    "accuracy": 0.9206365662744285,
    "macro avg": {
      "precision": 0.9575923771536203,
      "recall": 0.723745940093829,
      "f1-score": 0.7870070014642054,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9273677954048838,
      "recall": 0.9206365662744285,
      "f1-score": 0.9072473736223048,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      16520,
      0
    ],
    [
      1531,
      1240
    ]
  ],
  "true_share": {
    "negative": 0.8563578870976103,
    "positive": 0.1436421129023897
  },
  "predicted_share": {
    "negative": 0.9357213208231818,
    "positive": 0.0642786791768182
  }
}
```

### archive:ml/model_india_26_distilled_context/storm — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26_distilled_context/air_quality — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.437821; macro-F1 0.304581.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.43779160186625193,
      "recall": 1.0,
      "f1-score": 0.6089778258518118,
      "support": 8445.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 9.219988936013277e-05,
      "f1-score": 0.00018438277864847423,
      "support": 10846.0
    },
    "accuracy": 0.4378207454253279,
    "macro avg": {
      "precision": 0.718895800933126,
      "recall": 0.5000460999446801,
      "f1-score": 0.30458110431523017,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.7538826436037789,
      "recall": 0.4378207454253279,
      "f1-score": 0.26669522341691837,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      8445,
      0
    ],
    [
      10845,
      1
    ]
  ],
  "true_share": {
    "negative": 0.43776890778083044,
    "positive": 0.5622310922191696
  },
  "predicted_share": {
    "negative": 0.9999481623555025,
    "positive": 5.183764449743404e-05
  }
}
```

### archive:ml/model_india_26_distilled_context/air_quality — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.997214; macro-F1 0.986107.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9970631424375918,
      "recall": 1.0,
      "f1-score": 0.9985294117647059,
      "support": 679.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.9487179487179487,
      "f1-score": 0.9736842105263158,
      "support": 39.0
    },
    "accuracy": 0.9972144846796658,
    "macro avg": {
      "precision": 0.9985315712187959,
      "recall": 0.9743589743589743,
      "f1-score": 0.9861068111455109,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9972226653413995,
      "recall": 0.9972144846796658,
      "f1-score": 0.9971798813353226,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      679,
      0
    ],
    [
      2,
      37
    ]
  ],
  "true_share": {
    "negative": 0.9456824512534819,
    "positive": 0.054317548746518104
  },
  "predicted_share": {
    "negative": 0.9484679665738162,
    "positive": 0.05153203342618384
  }
}
```

### archive:ml/model_india_26_geo_temporal/wildfire — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.950184; macro-F1 0.487228.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9502332814930016,
      "recall": 0.9999454476024221,
      "f1-score": 0.9744557560936711,
      "support": 18331.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 960.0
    },
    "accuracy": 0.9501840236379658,
    "macro avg": {
      "precision": 0.4751166407465008,
      "recall": 0.49997272380121105,
      "f1-score": 0.48722787804683554,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9029457406587637,
      "recall": 0.9501840236379658,
      "f1-score": 0.9259628046733236,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      18330,
      1
    ],
    [
      960,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9502358612824633,
    "positive": 0.049764138717536675
  },
  "predicted_share": {
    "negative": 0.9999481623555025,
    "positive": 5.183764449743404e-05
  }
}
```

### archive:ml/model_india_26_geo_temporal/wildfire — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.995822; macro-F1 0.498953.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813678,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 0.9958217270194986,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.4979108635097493,
      "f1-score": 0.4989532449406839,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813677,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      715,
      3
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 0.9958217270194986,
    "positive": 0.004178272980501393
  }
}
```

### archive:ml/model_india_26_geo_temporal/flood — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.951635; macro-F1 0.733358.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9504750782950263,
      "recall": 1.0,
      "f1-score": 0.9746087903116071,
      "support": 17906.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.3263537906137184,
      "f1-score": 0.49210669569951004,
      "support": 1385.0
    },
    "accuracy": 0.951635477683894,
    "macro avg": {
      "precision": 0.9752375391475132,
      "recall": 0.6631768953068592,
      "f1-score": 0.7333577430055586,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9540307268648976,
      "recall": 0.951635477683894,
      "f1-score": 0.9399674860226769,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      17906,
      0
    ],
    [
      933,
      452
    ]
  ],
  "true_share": {
    "negative": 0.9282048623710538,
    "positive": 0.07179513762894614
  },
  "predicted_share": {
    "negative": 0.9765693846871598,
    "positive": 0.023430615312840186
  }
}
```

### archive:ml/model_india_26_geo_temporal/flood — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26_geo_temporal/storm — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.920637; macro-F1 0.787007.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9151847543072406,
      "recall": 1.0,
      "f1-score": 0.955714327037112,
      "support": 16520.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.4474918801876579,
      "f1-score": 0.618299675891299,
      "support": 2771.0
    },
    "accuracy": 0.9206365662744285,
    "macro avg": {
      "precision": 0.9575923771536203,
      "recall": 0.723745940093829,
      "f1-score": 0.7870070014642054,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9273677954048838,
      "recall": 0.9206365662744285,
      "f1-score": 0.9072473736223048,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      16520,
      0
    ],
    [
      1531,
      1240
    ]
  ],
  "true_share": {
    "negative": 0.8563578870976103,
    "positive": 0.1436421129023897
  },
  "predicted_share": {
    "negative": 0.9357213208231818,
    "positive": 0.0642786791768182
  }
}
```

### archive:ml/model_india_26_geo_temporal/storm — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26_geo_temporal/air_quality — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.438028; macro-F1 0.304994.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.4378824017421964,
      "recall": 1.0,
      "f1-score": 0.6090656665825249,
      "support": 8445.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.0004609994468006638,
      "f1-score": 0.0009215740484747949,
      "support": 10846.0
    },
    "accuracy": 0.4380280960033176,
    "macro avg": {
      "precision": 0.7189412008710983,
      "recall": 0.5002304997234003,
      "f1-score": 0.30499362031549987,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.7539223929662977,
      "recall": 0.4380280960033176,
      "f1-score": 0.26714814921047014,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      8445,
      0
    ],
    [
      10841,
      5
    ]
  ],
  "true_share": {
    "negative": 0.43776890778083044,
    "positive": 0.5622310922191696
  },
  "predicted_share": {
    "negative": 0.9997408117775128,
    "positive": 0.00025918822248717017
  }
}
```

### archive:ml/model_india_26_geo_temporal/air_quality — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.552925; macro-F1 0.439492.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.994475138121547,
      "recall": 0.5301914580265096,
      "f1-score": 0.69164265129683,
      "support": 679.0
    },
    "positive": {
      "precision": 0.10393258426966293,
      "recall": 0.9487179487179487,
      "f1-score": 0.18734177215189873,
      "support": 39.0
    },
    "accuracy": 0.552924791086351,
    "macro avg": {
      "precision": 0.5492038611956049,
      "recall": 0.7394547033722292,
      "f1-score": 0.43949221172436437,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9461030495418487,
      "recall": 0.552924791086351,
      "f1-score": 0.6642502637109633,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      360,
      319
    ],
    [
      2,
      37
    ]
  ],
  "true_share": {
    "negative": 0.9456824512534819,
    "positive": 0.054317548746518104
  },
  "predicted_share": {
    "negative": 0.5041782729805014,
    "positive": 0.4958217270194986
  }
}
```

### archive:ml/model_india_26_masked_distilled_edge/wildfire — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.950184; macro-F1 0.487228.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9502332814930016,
      "recall": 0.9999454476024221,
      "f1-score": 0.9744557560936711,
      "support": 18331.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 960.0
    },
    "accuracy": 0.9501840236379658,
    "macro avg": {
      "precision": 0.4751166407465008,
      "recall": 0.49997272380121105,
      "f1-score": 0.48722787804683554,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9029457406587637,
      "recall": 0.9501840236379658,
      "f1-score": 0.9259628046733236,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      18330,
      1
    ],
    [
      960,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9502358612824633,
    "positive": 0.049764138717536675
  },
  "predicted_share": {
    "negative": 0.9999481623555025,
    "positive": 5.183764449743404e-05
  }
}
```

### archive:ml/model_india_26_masked_distilled_edge/wildfire — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.995822; macro-F1 0.498953.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813678,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 0.9958217270194986,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.4979108635097493,
      "f1-score": 0.4989532449406839,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813677,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      715,
      3
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 0.9958217270194986,
    "positive": 0.004178272980501393
  }
}
```

### archive:ml/model_india_26_masked_distilled_edge/flood — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.949147; macro-F1 0.712493.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9480595118335363,
      "recall": 1.0,
      "f1-score": 0.9733373195988367,
      "support": 17906.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.29169675090252706,
      "f1-score": 0.45164896590273895,
      "support": 1385.0
    },
    "accuracy": 0.9491472707480172,
    "macro avg": {
      "precision": 0.9740297559167681,
      "recall": 0.6458483754512635,
      "f1-score": 0.7124931427507879,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9517885863299622,
      "recall": 0.9491472707480172,
      "f1-score": 0.9358826324458069,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      17906,
      0
    ],
    [
      981,
      404
    ]
  ],
  "true_share": {
    "negative": 0.9282048623710538,
    "positive": 0.07179513762894614
  },
  "predicted_share": {
    "negative": 0.9790575916230366,
    "positive": 0.020942408376963352
  }
}
```

### archive:ml/model_india_26_masked_distilled_edge/flood — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26_masked_distilled_edge/storm — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.856358; macro-F1 0.461311.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.8563578870976103,
      "recall": 1.0,
      "f1-score": 0.9226215408673313,
      "support": 16520.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 2771.0
    },
    "accuracy": 0.8563578870976103,
    "macro avg": {
      "precision": 0.42817894354880515,
      "recall": 0.5,
      "f1-score": 0.46131077043366564,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.7333488307942835,
      "recall": 0.8563578870976103,
      "f1-score": 0.7900942333278893,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      16520,
      0
    ],
    [
      2771,
      0
    ]
  ],
  "true_share": {
    "negative": 0.8563578870976103,
    "positive": 0.1436421129023897
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26_masked_distilled_edge/storm — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26_masked_distilled_edge/air_quality — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.437821; macro-F1 0.304581.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.43779160186625193,
      "recall": 1.0,
      "f1-score": 0.6089778258518118,
      "support": 8445.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 9.219988936013277e-05,
      "f1-score": 0.00018438277864847423,
      "support": 10846.0
    },
    "accuracy": 0.4378207454253279,
    "macro avg": {
      "precision": 0.718895800933126,
      "recall": 0.5000460999446801,
      "f1-score": 0.30458110431523017,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.7538826436037789,
      "recall": 0.4378207454253279,
      "f1-score": 0.26669522341691837,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      8445,
      0
    ],
    [
      10845,
      1
    ]
  ],
  "true_share": {
    "negative": 0.43776890778083044,
    "positive": 0.5622310922191696
  },
  "predicted_share": {
    "negative": 0.9999481623555025,
    "positive": 5.183764449743404e-05
  }
}
```

### archive:ml/model_india_26_masked_distilled_edge/air_quality — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.997214; macro-F1 0.986107.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9970631424375918,
      "recall": 1.0,
      "f1-score": 0.9985294117647059,
      "support": 679.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.9487179487179487,
      "f1-score": 0.9736842105263158,
      "support": 39.0
    },
    "accuracy": 0.9972144846796658,
    "macro avg": {
      "precision": 0.9985315712187959,
      "recall": 0.9743589743589743,
      "f1-score": 0.9861068111455109,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9972226653413995,
      "recall": 0.9972144846796658,
      "f1-score": 0.9971798813353226,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      679,
      0
    ],
    [
      2,
      37
    ]
  ],
  "true_share": {
    "negative": 0.9456824512534819,
    "positive": 0.054317548746518104
  },
  "predicted_share": {
    "negative": 0.9484679665738162,
    "positive": 0.05153203342618384
  }
}
```

### archive:ml/model_india_26_verified_storm_candidate/wildfire — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.950184; macro-F1 0.487228.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9502332814930016,
      "recall": 0.9999454476024221,
      "f1-score": 0.9744557560936711,
      "support": 18331.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 960.0
    },
    "accuracy": 0.9501840236379658,
    "macro avg": {
      "precision": 0.4751166407465008,
      "recall": 0.49997272380121105,
      "f1-score": 0.48722787804683554,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9029457406587637,
      "recall": 0.9501840236379658,
      "f1-score": 0.9259628046733236,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      18330,
      1
    ],
    [
      960,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9502358612824633,
    "positive": 0.049764138717536675
  },
  "predicted_share": {
    "negative": 0.9999481623555025,
    "positive": 5.183764449743404e-05
  }
}
```

### archive:ml/model_india_26_verified_storm_candidate/wildfire — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.995822; macro-F1 0.498953.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813678,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 0.9958217270194986,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.4979108635097493,
      "f1-score": 0.4989532449406839,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813677,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      715,
      3
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 0.9958217270194986,
    "positive": 0.004178272980501393
  }
}
```

### archive:ml/model_india_26_verified_storm_candidate/flood — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.951635; macro-F1 0.733358.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9504750782950263,
      "recall": 1.0,
      "f1-score": 0.9746087903116071,
      "support": 17906.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.3263537906137184,
      "f1-score": 0.49210669569951004,
      "support": 1385.0
    },
    "accuracy": 0.951635477683894,
    "macro avg": {
      "precision": 0.9752375391475132,
      "recall": 0.6631768953068592,
      "f1-score": 0.7333577430055586,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9540307268648976,
      "recall": 0.951635477683894,
      "f1-score": 0.9399674860226769,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      17906,
      0
    ],
    [
      933,
      452
    ]
  ],
  "true_share": {
    "negative": 0.9282048623710538,
    "positive": 0.07179513762894614
  },
  "predicted_share": {
    "negative": 0.9765693846871598,
    "positive": 0.023430615312840186
  }
}
```

### archive:ml/model_india_26_verified_storm_candidate/flood — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26_verified_storm_candidate/storm — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.855736; macro-F1 0.461130.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.8562684786555319,
      "recall": 0.999273607748184,
      "f1-score": 0.9222603983351491,
      "support": 16520.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 2771.0
    },
    "accuracy": 0.8557358353636411,
    "macro avg": {
      "precision": 0.42813423932776595,
      "recall": 0.499636803874092,
      "f1-score": 0.46113019916757453,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.7332722651697365,
      "recall": 0.8557358353636411,
      "f1-score": 0.7897849660720887,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      16508,
      12
    ],
    [
      2771,
      0
    ]
  ],
  "true_share": {
    "negative": 0.8563578870976103,
    "positive": 0.1436421129023897
  },
  "predicted_share": {
    "negative": 0.9993779482660308,
    "positive": 0.0006220517339692084
  }
}
```

### archive:ml/model_india_26_verified_storm_candidate/storm — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_26_verified_storm_candidate/air_quality — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.437821; macro-F1 0.304581.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.43779160186625193,
      "recall": 1.0,
      "f1-score": 0.6089778258518118,
      "support": 8445.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 9.219988936013277e-05,
      "f1-score": 0.00018438277864847423,
      "support": 10846.0
    },
    "accuracy": 0.4378207454253279,
    "macro avg": {
      "precision": 0.718895800933126,
      "recall": 0.5000460999446801,
      "f1-score": 0.30458110431523017,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.7538826436037789,
      "recall": 0.4378207454253279,
      "f1-score": 0.26669522341691837,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      8445,
      0
    ],
    [
      10845,
      1
    ]
  ],
  "true_share": {
    "negative": 0.43776890778083044,
    "positive": 0.5622310922191696
  },
  "predicted_share": {
    "negative": 0.9999481623555025,
    "positive": 5.183764449743404e-05
  }
}
```

### archive:ml/model_india_26_verified_storm_candidate/air_quality — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.997214; macro-F1 0.986107.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9970631424375918,
      "recall": 1.0,
      "f1-score": 0.9985294117647059,
      "support": 679.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.9487179487179487,
      "f1-score": 0.9736842105263158,
      "support": 39.0
    },
    "accuracy": 0.9972144846796658,
    "macro avg": {
      "precision": 0.9985315712187959,
      "recall": 0.9743589743589743,
      "f1-score": 0.9861068111455109,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9972226653413995,
      "recall": 0.9972144846796658,
      "f1-score": 0.9971798813353226,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      679,
      0
    ],
    [
      2,
      37
    ]
  ],
  "true_share": {
    "negative": 0.9456824512534819,
    "positive": 0.054317548746518104
  },
  "predicted_share": {
    "negative": 0.9484679665738162,
    "positive": 0.05153203342618384
  }
}
```

### archive:ml/model_india_pilot/wildfire — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.950184; macro-F1 0.487228.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9502332814930016,
      "recall": 0.9999454476024221,
      "f1-score": 0.9744557560936711,
      "support": 18331.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 960.0
    },
    "accuracy": 0.9501840236379658,
    "macro avg": {
      "precision": 0.4751166407465008,
      "recall": 0.49997272380121105,
      "f1-score": 0.48722787804683554,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9029457406587637,
      "recall": 0.9501840236379658,
      "f1-score": 0.9259628046733236,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      18330,
      1
    ],
    [
      960,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9502358612824633,
    "positive": 0.049764138717536675
  },
  "predicted_share": {
    "negative": 0.9999481623555025,
    "positive": 5.183764449743404e-05
  }
}
```

### archive:ml/model_india_pilot/wildfire — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.995822; macro-F1 0.498953.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813678,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 0.9958217270194986,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.4979108635097493,
      "f1-score": 0.4989532449406839,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 0.9958217270194986,
      "f1-score": 0.9979064898813677,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      715,
      3
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 0.9958217270194986,
    "positive": 0.004178272980501393
  }
}
```

### archive:ml/model_india_pilot/flood — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.952050; macro-F1 0.736733.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9508788699484892,
      "recall": 1.0,
      "f1-score": 0.9748210251245338,
      "support": 17906.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.33212996389891697,
      "f1-score": 0.4986449864498645,
      "support": 1385.0
    },
    "accuracy": 0.9520501788398735,
    "macro avg": {
      "precision": 0.9754394349742446,
      "recall": 0.6660649819494585,
      "f1-score": 0.7367330057871991,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9544055282410268,
      "recall": 0.9520501788398735,
      "f1-score": 0.9406339008922795,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      17906,
      0
    ],
    [
      925,
      460
    ]
  ],
  "true_share": {
    "negative": 0.9282048623710538,
    "positive": 0.07179513762894614
  },
  "predicted_share": {
    "negative": 0.9761546835311803,
    "positive": 0.02384531646881966
  }
}
```

### archive:ml/model_india_pilot/flood — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_pilot/storm — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.920274; macro-F1 0.785702.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9148299922472034,
      "recall": 1.0,
      "f1-score": 0.9555208514084099,
      "support": 16520.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.44496571634788884,
      "f1-score": 0.6158841158841158,
      "support": 2771.0
    },
    "accuracy": 0.9202737027629464,
    "macro avg": {
      "precision": 0.9574149961236017,
      "recall": 0.7224828581739444,
      "f1-score": 0.7857024836462629,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.9270639921167281,
      "recall": 0.9202737027629464,
      "f1-score": 0.9067347130984302,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      16520,
      0
    ],
    [
      1538,
      1233
    ]
  ],
  "true_share": {
    "negative": 0.8563578870976103,
    "positive": 0.1436421129023897
  },
  "predicted_share": {
    "negative": 0.9360841843346638,
    "positive": 0.06391581566533616
  }
}
```

### archive:ml/model_india_pilot/storm — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### archive:ml/model_india_pilot/air_quality — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.438132; macro-F1 0.305200.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.4379278158058494,
      "recall": 1.0,
      "f1-score": 0.6091095964513686,
      "support": 8445.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.0006453992255209294,
      "f1-score": 0.0012899659080438588,
      "support": 10846.0
    },
    "accuracy": 0.43813177129231246,
    "macro avg": {
      "precision": 0.7189639079029246,
      "recall": 0.5003226996127604,
      "f1-score": 0.30519978117970625,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.7539422738313409,
      "recall": 0.43813177129231246,
      "f1-score": 0.26737450169874305,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      8445,
      0
    ],
    [
      10839,
      7
    ]
  ],
  "true_share": {
    "negative": 0.43776890778083044,
    "positive": 0.5622310922191696
  },
  "predicted_share": {
    "negative": 0.9996371364885179,
    "positive": 0.00036286351148203825
  }
}
```

### archive:ml/model_india_pilot/air_quality — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 0.813370; macro-F1 0.629224.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.8026509572901326,
      "f1-score": 0.8905228758169934,
      "support": 679.0
    },
    "positive": {
      "precision": 0.2254335260115607,
      "recall": 1.0,
      "f1-score": 0.36792452830188677,
      "support": 39.0
    },
    "accuracy": 0.8133704735376045,
    "macro avg": {
      "precision": 0.6127167630057804,
      "recall": 0.9013254786450663,
      "f1-score": 0.6292237020594401,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9579274477917142,
      "recall": 0.8133704735376045,
      "f1-score": 0.8621366146009917,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      545,
      134
    ],
    [
      0,
      39
    ]
  ],
  "true_share": {
    "negative": 0.9456824512534819,
    "positive": 0.054317548746518104
  },
  "predicted_share": {
    "negative": 0.7590529247910863,
    "positive": 0.24094707520891365
  }
}
```

### archive:ml/model_india_storm_verified/storm — weatherHistory_seed42_test20 / heldout

Rows 19291; accuracy 0.855736; macro-F1 0.461130.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.8562684786555319,
      "recall": 0.999273607748184,
      "f1-score": 0.9222603983351491,
      "support": 16520.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 2771.0
    },
    "accuracy": 0.8557358353636411,
    "macro avg": {
      "precision": 0.42813423932776595,
      "recall": 0.499636803874092,
      "f1-score": 0.46113019916757453,
      "support": 19291.0
    },
    "weighted avg": {
      "precision": 0.7332722651697365,
      "recall": 0.8557358353636411,
      "f1-score": 0.7897849660720887,
      "support": 19291.0
    }
  },
  "confusion_matrix": [
    [
      16508,
      12
    ],
    [
      2771,
      0
    ]
  ],
  "true_share": {
    "negative": 0.8563578870976103,
    "positive": 0.1436421129023897
  },
  "predicted_share": {
    "negative": 0.9993779482660308,
    "positive": 0.0006220517339692084
  }
}
```

### archive:ml/model_india_storm_verified/storm — weatherHistory_seed42_test20 / mandi_proxy

Rows 718; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      718,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_high_wind_measurement_at_6h_A.ubj — offline_phase/national/test/A / heldout

Rows 17858; accuracy 0.999888; macro-F1 0.499972.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.999888005375742,
      "recall": 1.0,
      "f1-score": 0.9999439995519964,
      "support": 17856.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 2.0
    },
    "accuracy": 0.999888005375742,
    "macro avg": {
      "precision": 0.499944002687871,
      "recall": 0.5,
      "f1-score": 0.4999719997759982,
      "support": 17858.0
    },
    "weighted avg": {
      "precision": 0.9997760232942798,
      "recall": 0.999888005375742,
      "f1-score": 0.9998320111994875,
      "support": 17858.0
    }
  },
  "confusion_matrix": [
    [
      17856,
      0
    ],
    [
      2,
      0
    ]
  ],
  "true_share": {
    "negative": 0.999888005375742,
    "positive": 0.00011199462425803562
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### ml/models/india_sensor_v1/national_high_wind_measurement_at_6h_B.ubj — offline_phase/national/test/B / heldout

Rows 17858; accuracy 0.999888; macro-F1 0.499972.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.999888005375742,
      "recall": 1.0,
      "f1-score": 0.9999439995519964,
      "support": 17856.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 2.0
    },
    "accuracy": 0.999888005375742,
    "macro avg": {
      "precision": 0.499944002687871,
      "recall": 0.5,
      "f1-score": 0.4999719997759982,
      "support": 17858.0
    },
    "weighted avg": {
      "precision": 0.9997760232942798,
      "recall": 0.999888005375742,
      "f1-score": 0.9998320111994875,
      "support": 17858.0
    }
  },
  "confusion_matrix": [
    [
      17856,
      0
    ],
    [
      2,
      0
    ]
  ],
  "true_share": {
    "negative": 0.999888005375742,
    "positive": 0.00011199462425803562
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj — offline_phase/national/test/northern_plains_proxy / heldout

Rows 1761; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 1761.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 1761.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 1761.0
    }
  },
  "confusion_matrix": [
    [
      1761,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_peninsula_proxy.ubj — offline_phase/national/test/peninsula_proxy / heldout

Rows 9875; accuracy 0.999797; macro-F1 0.499949.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9997974683544304,
      "recall": 1.0,
      "f1-score": 0.9998987239214098,
      "support": 9873.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 2.0
    },
    "accuracy": 0.9997974683544304,
    "macro avg": {
      "precision": 0.4998987341772152,
      "recall": 0.5,
      "f1-score": 0.4999493619607049,
      "support": 9875.0
    },
    "weighted avg": {
      "precision": 0.9995949777279282,
      "recall": 0.9997974683544304,
      "f1-score": 0.999696212787451,
      "support": 9875.0
    }
  },
  "confusion_matrix": [
    [
      9873,
      0
    ],
    [
      2,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9997974683544304,
    "positive": 0.00020253164556962027
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_western_arid_proxy.ubj — offline_phase/national/test/western_arid_proxy / heldout

Rows 2787; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2787.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2787.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2787.0
    }
  },
  "confusion_matrix": [
    [
      2787,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_hot_measurement_at_6h_A.ubj — offline_phase/national/test/A / heldout

Rows 17785; accuracy 0.996177; macro-F1 0.499042.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9965687928900889,
      "recall": 0.9996050552922591,
      "f1-score": 0.9980846149512703,
      "support": 17724.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 61.0
    },
    "accuracy": 0.9961765532752319,
    "macro avg": {
      "precision": 0.49828439644504446,
      "recall": 0.49980252764612954,
      "f1-score": 0.49904230747563516,
      "support": 17785.0
    },
    "weighted avg": {
      "precision": 0.9931507048177641,
      "recall": 0.9961765532752319,
      "f1-score": 0.9946613278266132,
      "support": 17785.0
    }
  },
  "confusion_matrix": [
    [
      17717,
      7
    ],
    [
      61,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9965701433792522,
    "positive": 0.003429856620747821
  },
  "predicted_share": {
    "negative": 0.9996064098959797,
    "positive": 0.0003935901040202418
  }
}
```

### ml/models/india_sensor_v1/national_hot_measurement_at_6h_B.ubj — offline_phase/national/test/B / heldout

Rows 17785; accuracy 0.996345; macro-F1 0.499085.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.996569371801361,
      "recall": 0.9997743173098623,
      "f1-score": 0.9981692719335304,
      "support": 17724.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 61.0
    },
    "accuracy": 0.9963452347483834,
    "macro avg": {
      "precision": 0.4982846859006805,
      "recall": 0.49988715865493116,
      "f1-score": 0.4990846359667652,
      "support": 17785.0
    },
    "weighted avg": {
      "precision": 0.9931512817434535,
      "recall": 0.9963452347483834,
      "f1-score": 0.9947456944475622,
      "support": 17785.0
    }
  },
  "confusion_matrix": [
    [
      17720,
      4
    ],
    [
      61,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9965701433792522,
    "positive": 0.003429856620747821
  },
  "predicted_share": {
    "negative": 0.9997750913691313,
    "positive": 0.00022490863086870958
  }
}
```

### data/india_sensor/offline/models/national_hot_measurement_at_6h_D_mountain_proxy.ubj — offline_phase/national/test/mountain_proxy / heldout

Rows 238; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 238.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 238.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 238.0
    }
  },
  "confusion_matrix": [
    [
      238,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_hot_measurement_at_6h_D_northeast_proxy.ubj — offline_phase/national/test/northeast_proxy / heldout

Rows 3197; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 3197.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 3197.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 3197.0
    }
  },
  "confusion_matrix": [
    [
      3197,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_hot_measurement_at_6h_D_northern_plains_proxy.ubj — offline_phase/national/test/northern_plains_proxy / heldout

Rows 1737; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 1737.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 1737.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 1737.0
    }
  },
  "confusion_matrix": [
    [
      1737,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_hot_measurement_at_6h_D_peninsula_proxy.ubj — offline_phase/national/test/peninsula_proxy / heldout

Rows 9873; accuracy 0.997974; macro-F1 0.499493.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9979742732705358,
      "recall": 1.0,
      "f1-score": 0.9989861097029301,
      "support": 9853.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 20.0
    },
    "accuracy": 0.9979742732705358,
    "macro avg": {
      "precision": 0.4989871366352679,
      "recall": 0.5,
      "f1-score": 0.49949305485146506,
      "support": 9873.0
    },
    "weighted avg": {
      "precision": 0.995952650109854,
      "recall": 0.9979742732705358,
      "f1-score": 0.9969624368381413,
      "support": 9873.0
    }
  },
  "confusion_matrix": [
    [
      9853,
      0
    ],
    [
      20,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9979742732705358,
    "positive": 0.0020257267294641955
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_hot_measurement_at_6h_D_western_arid_proxy.ubj — offline_phase/national/test/western_arid_proxy / heldout

Rows 2740; accuracy 0.985401; macro-F1 0.520132.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9853961299744433,
      "recall": 1.0,
      "f1-score": 0.9926443545421111,
      "support": 2699.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 0.024390243902439025,
      "f1-score": 0.047619047619047616,
      "support": 41.0
    },
    "accuracy": 0.9854014598540146,
    "macro avg": {
      "precision": 0.9926980649872217,
      "recall": 0.5121951219512195,
      "f1-score": 0.5201317010805794,
      "support": 2740.0
    },
    "weighted avg": {
      "precision": 0.9856146550368695,
      "recall": 0.9854014598540146,
      "f1-score": 0.9785034649129702,
      "support": 2740.0
    }
  },
  "confusion_matrix": [
    [
      2699,
      0
    ],
    [
      40,
      1
    ]
  ],
  "true_share": {
    "negative": 0.9850364963503649,
    "positive": 0.014963503649635036
  },
  "predicted_share": {
    "negative": 0.9996350364963503,
    "positive": 0.000364963503649635
  }
}
```

### data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_A.ubj — offline_phase/national/test/A / heldout

Rows 17777; accuracy 0.943973; macro-F1 0.702309.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9482479472649474,
      "recall": 0.9938787878787879,
      "f1-score": 0.9705273125406877,
      "support": 16500.0
    },
    "positive": {
      "precision": 0.7908902691511387,
      "recall": 0.29913860610806575,
      "f1-score": 0.4340909090909091,
      "support": 1277.0
    },
    "accuracy": 0.9439725487990099,
    "macro avg": {
      "precision": 0.869569108208043,
      "recall": 0.6465086969934268,
      "f1-score": 0.7023091108157984,
      "support": 17777.0
    },
    "weighted avg": {
      "precision": 0.9369442540123551,
      "recall": 0.9439725487990099,
      "f1-score": 0.9319927292473665,
      "support": 17777.0
    }
  },
  "confusion_matrix": [
    [
      16399,
      101
    ],
    [
      895,
      382
    ]
  ],
  "true_share": {
    "negative": 0.9281656072453169,
    "positive": 0.07183439275468302
  },
  "predicted_share": {
    "negative": 0.9728300613151826,
    "positive": 0.02716993868481746
  }
}
```

### ml/models/india_sensor_v1/national_near_saturation_measurement_at_6h_B.ubj — offline_phase/national/test/B / heldout

Rows 17777; accuracy 0.943579; macro-F1 0.696785.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9475021657522379,
      "recall": 0.9943030303030304,
      "f1-score": 0.9703386071270146,
      "support": 16500.0
    },
    "positive": {
      "precision": 0.7965367965367965,
      "recall": 0.28817541111981204,
      "f1-score": 0.42323174238067857,
      "support": 1277.0
    },
    "accuracy": 0.9435787815716937,
    "macro avg": {
      "precision": 0.8720194811445172,
      "recall": 0.6412392207114213,
      "f1-score": 0.6967851747538466,
      "support": 17777.0
    },
    "weighted avg": {
      "precision": 0.93665766012766,
      "recall": 0.9435787815716937,
      "f1-score": 0.9310375177260432,
      "support": 17777.0
    }
  },
  "confusion_matrix": [
    [
      16406,
      94
    ],
    [
      909,
      368
    ]
  ],
  "true_share": {
    "negative": 0.9281656072453169,
    "positive": 0.07183439275468302
  },
  "predicted_share": {
    "negative": 0.9740113629971311,
    "positive": 0.025988637002868877
  }
}
```

### data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_mountain_proxy.ubj — offline_phase/national/test/mountain_proxy / heldout

Rows 238; accuracy 0.991597; macro-F1 0.497890.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9915966386554622,
      "recall": 1.0,
      "f1-score": 0.9957805907172996,
      "support": 236.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 2.0
    },
    "accuracy": 0.9915966386554622,
    "macro avg": {
      "precision": 0.4957983193277311,
      "recall": 0.5,
      "f1-score": 0.4978902953586498,
      "support": 238.0
    },
    "weighted avg": {
      "precision": 0.9832638937928112,
      "recall": 0.9915966386554622,
      "f1-score": 0.9874126865936248,
      "support": 238.0
    }
  },
  "confusion_matrix": [
    [
      236,
      0
    ],
    [
      2,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9915966386554622,
    "positive": 0.008403361344537815
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_northeast_proxy.ubj — offline_phase/national/test/northeast_proxy / heldout

Rows 3195; accuracy 0.931768; macro-F1 0.746693.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9372742200328408,
      "recall": 0.990628254078445,
      "f1-score": 0.963212959838002,
      "support": 2881.0
    },
    "positive": {
      "precision": 0.82,
      "recall": 0.39171974522292996,
      "f1-score": 0.5301724137931034,
      "support": 314.0
    },
    "accuracy": 0.9317683881064163,
    "macro avg": {
      "precision": 0.8786371100164203,
      "recall": 0.6911739996506875,
      "f1-score": 0.7466926868155528,
      "support": 3195.0
    },
    "weighted avg": {
      "precision": 0.9257486785335255,
      "recall": 0.9317683881064163,
      "f1-score": 0.9206543584426661,
      "support": 3195.0
    }
  },
  "confusion_matrix": [
    [
      2854,
      27
    ],
    [
      191,
      123
    ]
  ],
  "true_share": {
    "negative": 0.9017214397496087,
    "positive": 0.09827856025039124
  },
  "predicted_share": {
    "negative": 0.9530516431924883,
    "positive": 0.046948356807511735
  }
}
```

### data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj — offline_phase/national/test/northern_plains_proxy / heldout

Rows 1737; accuracy 0.902130; macro-F1 0.731297.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9066339066339066,
      "recall": 0.9879518072289156,
      "f1-score": 0.9455477258167841,
      "support": 1494.0
    },
    "positive": {
      "precision": 0.8348623853211009,
      "recall": 0.37448559670781895,
      "f1-score": 0.5170454545454546,
      "support": 243.0
    },
    "accuracy": 0.9021301093839954,
    "macro avg": {
      "precision": 0.8707481459775037,
      "recall": 0.6812187019683673,
      "f1-score": 0.7312965901811194,
      "support": 1737.0
    },
    "weighted avg": {
      "precision": 0.8965933311134623,
      "recall": 0.9021301093839954,
      "f1-score": 0.8856018122192407,
      "support": 1737.0
    }
  },
  "confusion_matrix": [
    [
      1476,
      18
    ],
    [
      152,
      91
    ]
  ],
  "true_share": {
    "negative": 0.8601036269430051,
    "positive": 0.13989637305699482
  },
  "predicted_share": {
    "negative": 0.9372481289579735,
    "positive": 0.06275187104202648
  }
}
```

### data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj — offline_phase/national/test/peninsula_proxy / heldout

Rows 9869; accuracy 0.935860; macro-F1 0.618176.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9386515697375193,
      "recall": 0.9959589340323285,
      "f1-score": 0.9664564675957819,
      "support": 9156.0
    },
    "positive": {
      "precision": 0.7597402597402597,
      "recall": 0.1640953716690042,
      "f1-score": 0.2698961937716263,
      "support": 713.0
    },
    "accuracy": 0.9358597628939103,
    "macro avg": {
      "precision": 0.8491959147388894,
      "recall": 0.5800271528506663,
      "f1-score": 0.618176330683704,
      "support": 9869.0
    },
    "weighted avg": {
      "precision": 0.9257258666239266,
      "recall": 0.9358597628939103,
      "f1-score": 0.916132475779324,
      "support": 9869.0
    }
  },
  "confusion_matrix": [
    [
      9119,
      37
    ],
    [
      596,
      117
    ]
  ],
  "true_share": {
    "negative": 0.9277535717904549,
    "positive": 0.07224642820954504
  },
  "predicted_share": {
    "negative": 0.9843955821258487,
    "positive": 0.015604417874151384
  }
}
```

### data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj — offline_phase/national/test/western_arid_proxy / heldout

Rows 2738; accuracy 0.996713; macro-F1 0.499177.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9981711777615215,
      "recall": 0.9985364068788877,
      "f1-score": 0.9983537589171392,
      "support": 2733.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 5.0
    },
    "accuracy": 0.9967129291453616,
    "macro avg": {
      "precision": 0.49908558888076077,
      "recall": 0.49926820343944384,
      "f1-score": 0.4991768794585696,
      "support": 2738.0
    },
    "weighted avg": {
      "precision": 0.9963483669913215,
      "recall": 0.9967129291453616,
      "f1-score": 0.9965306147262752,
      "support": 2738.0
    }
  },
  "confusion_matrix": [
    [
      2729,
      4
    ],
    [
      5,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9981738495252008,
    "positive": 0.0018261504747991235
  },
  "predicted_share": {
    "negative": 0.9985390796201608,
    "positive": 0.0014609203798392988
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_A.ubj — offline_phase/himalaya_holdout/test/A / heldout

Rows 2680; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2680.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    }
  },
  "confusion_matrix": [
    [
      2680,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_B.ubj — offline_phase/himalaya_holdout/test/B / heldout

Rows 2680; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2680.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    }
  },
  "confusion_matrix": [
    [
      2680,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj — offline_phase/himalaya_holdout/test/northern_plains_proxy / heldout

Rows 2680; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2680.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    }
  },
  "confusion_matrix": [
    [
      2680,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_D_peninsula_proxy.ubj — offline_phase/himalaya_holdout/test/peninsula_proxy / heldout

Rows 2680; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2680.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    }
  },
  "confusion_matrix": [
    [
      2680,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_D_western_arid_proxy.ubj — offline_phase/himalaya_holdout/test/western_arid_proxy / heldout

Rows 2680; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2680.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    }
  },
  "confusion_matrix": [
    [
      2680,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_A.ubj — offline_phase/himalaya_holdout/test/A / heldout

Rows 2651; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2651.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    }
  },
  "confusion_matrix": [
    [
      2651,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_B.ubj — offline_phase/himalaya_holdout/test/B / heldout

Rows 2651; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2651.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    }
  },
  "confusion_matrix": [
    [
      2651,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_northeast_proxy.ubj — offline_phase/himalaya_holdout/test/northeast_proxy / heldout

Rows 2651; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2651.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    }
  },
  "confusion_matrix": [
    [
      2651,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_northern_plains_proxy.ubj — offline_phase/himalaya_holdout/test/northern_plains_proxy / heldout

Rows 2651; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2651.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    }
  },
  "confusion_matrix": [
    [
      2651,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_peninsula_proxy.ubj — offline_phase/himalaya_holdout/test/peninsula_proxy / heldout

Rows 2651; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2651.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    }
  },
  "confusion_matrix": [
    [
      2651,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_western_arid_proxy.ubj — offline_phase/himalaya_holdout/test/western_arid_proxy / heldout

Rows 2651; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2651.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    }
  },
  "confusion_matrix": [
    [
      2651,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_A.ubj — offline_phase/himalaya_holdout/test/A / heldout

Rows 2643; accuracy 0.889141; macro-F1 0.653210.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9074519230769231,
      "recall": 0.9733562526858617,
      "f1-score": 0.9392494298154676,
      "support": 2327.0
    },
    "positive": {
      "precision": 0.5782312925170068,
      "recall": 0.2689873417721519,
      "f1-score": 0.367170626349892,
      "support": 316.0
    },
    "accuracy": 0.8891411275066212,
    "macro avg": {
      "precision": 0.742841607796965,
      "recall": 0.6211717972290067,
      "f1-score": 0.6532100280826798,
      "support": 2643.0
    },
    "weighted avg": {
      "precision": 0.8680899407625328,
      "recall": 0.8891411275066212,
      "f1-score": 0.8708510560375176,
      "support": 2643.0
    }
  },
  "confusion_matrix": [
    [
      2265,
      62
    ],
    [
      231,
      85
    ]
  ],
  "true_share": {
    "negative": 0.8804388951948543,
    "positive": 0.11956110480514567
  },
  "predicted_share": {
    "negative": 0.9443813847900113,
    "positive": 0.05561861520998865
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_B.ubj — offline_phase/himalaya_holdout/test/B / heldout

Rows 2643; accuracy 0.891033; macro-F1 0.679615.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9139261063743402,
      "recall": 0.9673399226471853,
      "f1-score": 0.939874739039666,
      "support": 2327.0
    },
    "positive": {
      "precision": 0.5777777777777777,
      "recall": 0.3291139240506329,
      "f1-score": 0.41935483870967744,
      "support": 316.0
    },
    "accuracy": 0.8910329171396141,
    "macro avg": {
      "precision": 0.745851942076059,
      "recall": 0.6482269233489091,
      "f1-score": 0.6796147888746717,
      "support": 2643.0
    },
    "weighted avg": {
      "precision": 0.873735840828932,
      "recall": 0.8910329171396141,
      "f1-score": 0.8776408046831483,
      "support": 2643.0
    }
  },
  "confusion_matrix": [
    [
      2251,
      76
    ],
    [
      212,
      104
    ]
  ],
  "true_share": {
    "negative": 0.8804388951948543,
    "positive": 0.11956110480514567
  },
  "predicted_share": {
    "negative": 0.9318955732122588,
    "positive": 0.0681044267877412
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_northeast_proxy.ubj — offline_phase/himalaya_holdout/test/northeast_proxy / heldout

Rows 2643; accuracy 0.894438; macro-F1 0.626975.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9009397024275646,
      "recall": 0.9888268156424581,
      "f1-score": 0.942839582052858,
      "support": 2327.0
    },
    "positive": {
      "precision": 0.7078651685393258,
      "recall": 0.19936708860759494,
      "f1-score": 0.3111111111111111,
      "support": 316.0
    },
    "accuracy": 0.8944381384790011,
    "macro avg": {
      "precision": 0.8044024354834451,
      "recall": 0.5940969521250266,
      "f1-score": 0.6269753465819845,
      "support": 2643.0
    },
    "weighted avg": {
      "precision": 0.8778554978461481,
      "recall": 0.8944381384790011,
      "f1-score": 0.8673094281301974,
      "support": 2643.0
    }
  },
  "confusion_matrix": [
    [
      2301,
      26
    ],
    [
      253,
      63
    ]
  ],
  "true_share": {
    "negative": 0.8804388951948543,
    "positive": 0.11956110480514567
  },
  "predicted_share": {
    "negative": 0.9663261445327279,
    "positive": 0.033673855467272036
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj — offline_phase/himalaya_holdout/test/northern_plains_proxy / heldout

Rows 2643; accuracy 0.884222; macro-F1 0.675886.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9149897330595482,
      "recall": 0.9574559518693597,
      "f1-score": 0.9357412851742966,
      "support": 2327.0
    },
    "positive": {
      "precision": 0.5240384615384616,
      "recall": 0.3449367088607595,
      "f1-score": 0.41603053435114506,
      "support": 316.0
    },
    "accuracy": 0.8842224744608399,
    "macro avg": {
      "precision": 0.7195140972990048,
      "recall": 0.6511963303650596,
      "f1-score": 0.6758859097627208,
      "support": 2643.0
    },
    "weighted avg": {
      "precision": 0.8682471671115105,
      "recall": 0.8842224744608399,
      "f1-score": 0.8736040936267687,
      "support": 2643.0
    }
  },
  "confusion_matrix": [
    [
      2228,
      99
    ],
    [
      207,
      109
    ]
  ],
  "true_share": {
    "negative": 0.8804388951948543,
    "positive": 0.11956110480514567
  },
  "predicted_share": {
    "negative": 0.921301551267499,
    "positive": 0.07869844873250094
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj — offline_phase/himalaya_holdout/test/peninsula_proxy / heldout

Rows 2643; accuracy 0.898222; macro-F1 0.663078.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9076862123613312,
      "recall": 0.9845294370434036,
      "f1-score": 0.9445475159760874,
      "support": 2327.0
    },
    "positive": {
      "precision": 0.6974789915966386,
      "recall": 0.2626582278481013,
      "f1-score": 0.3816091954022989,
      "support": 316.0
    },
    "accuracy": 0.8982217177449867,
    "macro avg": {
      "precision": 0.8025826019789849,
      "recall": 0.6235938324457524,
      "f1-score": 0.6630783556891932,
      "support": 2643.0
    },
    "weighted avg": {
      "precision": 0.8825536048086854,
      "recall": 0.8982217177449867,
      "f1-score": 0.877241988431132,
      "support": 2643.0
    }
  },
  "confusion_matrix": [
    [
      2291,
      36
    ],
    [
      233,
      83
    ]
  ],
  "true_share": {
    "negative": 0.8804388951948543,
    "positive": 0.11956110480514567
  },
  "predicted_share": {
    "negative": 0.9549754067347711,
    "positive": 0.04502459326522891
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj — offline_phase/himalaya_holdout/test/western_arid_proxy / heldout

Rows 2643; accuracy 0.875899; macro-F1 0.662847.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9135291683905669,
      "recall": 0.9488611946712505,
      "f1-score": 0.9308600337268128,
      "support": 2327.0
    },
    "positive": {
      "precision": 0.47345132743362833,
      "recall": 0.33860759493670883,
      "f1-score": 0.3948339483394834,
      "support": 316.0
    },
    "accuracy": 0.8758986000756716,
    "macro avg": {
      "precision": 0.6934902479120976,
      "recall": 0.6437343948039796,
      "f1-score": 0.662846991033148,
      "support": 2643.0
    },
    "weighted avg": {
      "precision": 0.8609129755254921,
      "recall": 0.8758986000756716,
      "f1-score": 0.8667721627535263,
      "support": 2643.0
    }
  },
  "confusion_matrix": [
    [
      2208,
      119
    ],
    [
      209,
      107
    ]
  ],
  "true_share": {
    "negative": 0.8804388951948543,
    "positive": 0.11956110480514567
  },
  "predicted_share": {
    "negative": 0.914491108588725,
    "positive": 0.08550889141127507
  }
}
```

### data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_A.ubj — offline_phase/temporal/test/A / heldout

Rows 88169; accuracy 0.999762; macro-F1 0.499940.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9997844998695657,
      "recall": 0.999977311401021,
      "f1-score": 0.9998808963401147,
      "support": 88150.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 19.0
    },
    "accuracy": 0.9997618210482142,
    "macro avg": {
      "precision": 0.4998922499347829,
      "recall": 0.4999886557005105,
      "f1-score": 0.49994044817005734,
      "support": 88169.0
    },
    "weighted avg": {
      "precision": 0.9995690510667267,
      "recall": 0.9997618210482142,
      "f1-score": 0.9996654267642948,
      "support": 88169.0
    }
  },
  "confusion_matrix": [
    [
      88148,
      2
    ],
    [
      19,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9997845047579081,
    "positive": 0.0002154952420918917
  },
  "predicted_share": {
    "negative": 0.9999773162903061,
    "positive": 2.2683709693883338e-05
  }
}
```

### data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_B.ubj — offline_phase/temporal/test/B / heldout

Rows 88169; accuracy 0.999750; macro-F1 0.499938.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9997844974253114,
      "recall": 0.9999659671015315,
      "f1-score": 0.9998752240295833,
      "support": 88150.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 19.0
    },
    "accuracy": 0.9997504791933672,
    "macro avg": {
      "precision": 0.4998922487126557,
      "recall": 0.49998298355076576,
      "f1-score": 0.49993761201479164,
      "support": 88169.0
    },
    "weighted avg": {
      "precision": 0.999569048622999,
      "recall": 0.9997504791933672,
      "f1-score": 0.9996597556761193,
      "support": 88169.0
    }
  },
  "confusion_matrix": [
    [
      88147,
      3
    ],
    [
      19,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9997845047579081,
    "positive": 0.0002154952420918917
  },
  "predicted_share": {
    "negative": 0.9999659744354592,
    "positive": 3.4025564540825004e-05
  }
}
```

### data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj — offline_phase/temporal/test/northern_plains_proxy / heldout

Rows 16389; accuracy 0.999878; macro-F1 0.499969.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9998779669290377,
      "recall": 1.0,
      "f1-score": 0.9999389797412741,
      "support": 16387.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 2.0
    },
    "accuracy": 0.9998779669290377,
    "macro avg": {
      "precision": 0.49993898346451887,
      "recall": 0.5,
      "f1-score": 0.49996948987063705,
      "support": 16389.0
    },
    "weighted avg": {
      "precision": 0.9997559487501458,
      "recall": 0.9998779669290377,
      "f1-score": 0.9998169541168014,
      "support": 16389.0
    }
  },
  "confusion_matrix": [
    [
      16387,
      0
    ],
    [
      2,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9998779669290377,
    "positive": 0.00012203307096223076
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_D_peninsula_proxy.ubj — offline_phase/temporal/test/peninsula_proxy / heldout

Rows 47652; accuracy 0.999664; macro-F1 0.499916.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9996852112232691,
      "recall": 0.9999790079140164,
      "f1-score": 0.9998320879858954,
      "support": 47637.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 15.0
    },
    "accuracy": 0.9996642323512129,
    "macro avg": {
      "precision": 0.49984260561163457,
      "recall": 0.4999895039570082,
      "f1-score": 0.4999160439929477,
      "support": 47652.0
    },
    "weighted avg": {
      "precision": 0.9993705281424257,
      "recall": 0.9996642323512129,
      "f1-score": 0.9995173586708659,
      "support": 47652.0
    }
  },
  "confusion_matrix": [
    [
      47636,
      1
    ],
    [
      15,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9996852178292621,
    "positive": 0.0003147821707378494
  },
  "predicted_share": {
    "negative": 0.9999790145219508,
    "positive": 2.0985478049189962e-05
  }
}
```

### data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_D_western_arid_proxy.ubj — offline_phase/temporal/test/western_arid_proxy / heldout

Rows 13526; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 13526.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 13526.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 13526.0
    }
  },
  "confusion_matrix": [
    [
      13526,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/temporal_hot_measurement_at_6h_A.ubj — offline_phase/temporal/test/A / heldout

Rows 87777; accuracy 0.997870; macro-F1 0.499467.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9979150763902339,
      "recall": 0.999954334771788,
      "f1-score": 0.9989336648286166,
      "support": 87594.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 183.0
    },
    "accuracy": 0.9978696013762147,
    "macro avg": {
      "precision": 0.49895753819511696,
      "recall": 0.499977167385894,
      "f1-score": 0.4994668324143083,
      "support": 87777.0
    },
    "weighted avg": {
      "precision": 0.9958345944988567,
      "recall": 0.9978696013762147,
      "f1-score": 0.9968510593549317,
      "support": 87777.0
    }
  },
  "confusion_matrix": [
    [
      87590,
      4
    ],
    [
      183,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9979151714002529,
    "positive": 0.0020848285997470866
  },
  "predicted_share": {
    "negative": 0.9999544299759618,
    "positive": 4.557002403818768e-05
  }
}
```

### data/india_sensor/offline/models/temporal_hot_measurement_at_6h_B.ubj — offline_phase/temporal/test/B / heldout

Rows 87777; accuracy 0.997892; macro-F1 0.499473.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9979151238963259,
      "recall": 0.999977167385894,
      "f1-score": 0.9989450815138365,
      "support": 87594.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 183.0
    },
    "accuracy": 0.9978923863882339,
    "macro avg": {
      "precision": 0.49895756194816293,
      "recall": 0.499988583692947,
      "f1-score": 0.49947254075691827,
      "support": 87777.0
    },
    "weighted avg": {
      "precision": 0.9958346419059066,
      "recall": 0.9978923863882339,
      "f1-score": 0.9968624522383197,
      "support": 87777.0
    }
  },
  "confusion_matrix": [
    [
      87592,
      2
    ],
    [
      183,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9979151714002529,
    "positive": 0.0020848285997470866
  },
  "predicted_share": {
    "negative": 0.9999772149879809,
    "positive": 2.278501201909384e-05
  }
}
```

### data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_mountain_proxy.ubj — offline_phase/temporal/test/mountain_proxy / heldout

Rows 2651; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2651.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    }
  },
  "confusion_matrix": [
    [
      2651,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_northeast_proxy.ubj — offline_phase/temporal/test/northeast_proxy / heldout

Rows 7921; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 7921.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 7921.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 7921.0
    }
  },
  "confusion_matrix": [
    [
      7921,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_northern_plains_proxy.ubj — offline_phase/temporal/test/northern_plains_proxy / heldout

Rows 16265; accuracy 0.999816; macro-F1 0.499954.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9998155548724255,
      "recall": 1.0,
      "f1-score": 0.999907768930427,
      "support": 16262.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 3.0
    },
    "accuracy": 0.9998155548724255,
    "macro avg": {
      "precision": 0.49990777743621273,
      "recall": 0.5,
      "f1-score": 0.4999538844652135,
      "support": 16265.0
    },
    "weighted avg": {
      "precision": 0.9996311437648561,
      "recall": 0.9998155548724255,
      "f1-score": 0.9997233408144238,
      "support": 16265.0
    }
  },
  "confusion_matrix": [
    [
      16262,
      0
    ],
    [
      3,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9998155548724255,
    "positive": 0.00018444512757454656
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_peninsula_proxy.ubj — offline_phase/temporal/test/peninsula_proxy / heldout

Rows 47608; accuracy 0.998110; macro-F1 0.499527.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.998109561418249,
      "recall": 1.0,
      "f1-score": 0.9990538864243215,
      "support": 47518.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 90.0
    },
    "accuracy": 0.998109561418249,
    "macro avg": {
      "precision": 0.4990547807091245,
      "recall": 0.5,
      "f1-score": 0.49952694321216073,
      "support": 47608.0
    },
    "weighted avg": {
      "precision": 0.9962226965945294,
      "recall": 0.998109561418249,
      "f1-score": 0.9971652364121767,
      "support": 47608.0
    }
  },
  "confusion_matrix": [
    [
      47518,
      0
    ],
    [
      90,
      0
    ]
  ],
  "true_share": {
    "negative": 0.998109561418249,
    "positive": 0.0018904385817509661
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_western_arid_proxy.ubj — offline_phase/temporal/test/western_arid_proxy / heldout

Rows 13332; accuracy 0.993024; macro-F1 0.555392.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9936922730344673,
      "recall": 0.9993203443588582,
      "f1-score": 0.9964983621371286,
      "support": 13242.0
    },
    "positive": {
      "precision": 0.4,
      "recall": 0.06666666666666667,
      "f1-score": 0.11428571428571428,
      "support": 90.0
    },
    "accuracy": 0.993024302430243,
    "macro avg": {
      "precision": 0.6968461365172336,
      "recall": 0.5329935055127625,
      "f1-score": 0.5553920382114215,
      "support": 13332.0
    },
    "weighted avg": {
      "precision": 0.989684449409122,
      "recall": 0.993024302430243,
      "f1-score": 0.9905428312110389,
      "support": 13332.0
    }
  },
  "confusion_matrix": [
    [
      13233,
      9
    ],
    [
      84,
      6
    ]
  ],
  "true_share": {
    "negative": 0.9932493249324933,
    "positive": 0.0067506750675067504
  },
  "predicted_share": {
    "negative": 0.9988748874887489,
    "positive": 0.0011251125112511251
  }
}
```

### data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_A.ubj — offline_phase/temporal/test/A / heldout

Rows 87726; accuracy 0.953777; macro-F1 0.698857.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9610963645505677,
      "recall": 0.9912204534491076,
      "f1-score": 0.9759260028853175,
      "support": 82920.0
    },
    "positive": {
      "precision": 0.670140462165836,
      "recall": 0.30774032459425715,
      "f1-score": 0.42178810779980036,
      "support": 4806.0
    },
    "accuracy": 0.9537765314729955,
    "macro avg": {
      "precision": 0.8156184133582018,
      "recall": 0.6494803890216824,
      "f1-score": 0.6988570553425589,
      "support": 87726.0
    },
    "weighted avg": {
      "precision": 0.9451565739883511,
      "recall": 0.9537765314729955,
      "f1-score": 0.9455679935861246,
      "support": 87726.0
    }
  },
  "confusion_matrix": [
    [
      82192,
      728
    ],
    [
      3327,
      1479
    ]
  ],
  "true_share": {
    "negative": 0.9452157855139868,
    "positive": 0.05478421448601327
  },
  "predicted_share": {
    "negative": 0.9748421220618745,
    "positive": 0.025157877938125527
  }
}
```

### data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_B.ubj — offline_phase/temporal/test/B / heldout

Rows 87726; accuracy 0.953389; macro-F1 0.699533.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9613183366299551,
      "recall": 0.9905451037144235,
      "f1-score": 0.9757129026318446,
      "support": 82920.0
    },
    "positive": {
      "precision": 0.6568927789934355,
      "recall": 0.31231793591344154,
      "f1-score": 0.4233535467494006,
      "support": 4806.0
    },
    "accuracy": 0.9533889610833732,
    "macro avg": {
      "precision": 0.8091055578116952,
      "recall": 0.6514315198139325,
      "f1-score": 0.6995332246906226,
      "support": 87726.0
    },
    "weighted avg": {
      "precision": 0.9446406215853718,
      "recall": 0.9533889610833732,
      "f1-score": 0.9454523292058248,
      "support": 87726.0
    }
  },
  "confusion_matrix": [
    [
      82136,
      784
    ],
    [
      3305,
      1501
    ]
  ],
  "true_share": {
    "negative": 0.9452157855139868,
    "positive": 0.05478421448601327
  },
  "predicted_share": {
    "negative": 0.9739529899915647,
    "positive": 0.026047010008435355
  }
}
```

### data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_mountain_proxy.ubj — offline_phase/temporal/test/mountain_proxy / heldout

Rows 2643; accuracy 0.890276; macro-F1 0.724177.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9302915082382763,
      "recall": 0.9462827675118178,
      "f1-score": 0.9382190029825309,
      "support": 2327.0
    },
    "positive": {
      "precision": 0.5471014492753623,
      "recall": 0.4778481012658228,
      "f1-score": 0.5101351351351351,
      "support": 316.0
    },
    "accuracy": 0.8902762012864169,
    "macro avg": {
      "precision": 0.7386964787568193,
      "recall": 0.7120654343888203,
      "f1-score": 0.724177069058833,
      "support": 2643.0
    },
    "weighted avg": {
      "precision": 0.8844768814383215,
      "recall": 0.8902762012864169,
      "f1-score": 0.8870368227934362,
      "support": 2643.0
    }
  },
  "confusion_matrix": [
    [
      2202,
      125
    ],
    [
      165,
      151
    ]
  ],
  "true_share": {
    "negative": 0.8804388951948543,
    "positive": 0.11956110480514567
  },
  "predicted_share": {
    "negative": 0.8955732122587968,
    "positive": 0.10442678774120318
  }
}
```

### data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_northeast_proxy.ubj — offline_phase/temporal/test/northeast_proxy / heldout

Rows 7911; accuracy 0.930982; macro-F1 0.677022.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.943693398083738,
      "recall": 0.9839879567537977,
      "f1-score": 0.9634195363794721,
      "support": 7307.0
    },
    "positive": {
      "precision": 0.5993150684931506,
      "recall": 0.2897350993377483,
      "f1-score": 0.390625,
      "support": 604.0
    },
    "accuracy": 0.9309821767159651,
    "macro avg": {
      "precision": 0.7715042332884443,
      "recall": 0.636861528045773,
      "f1-score": 0.677022268189736,
      "support": 7911.0
    },
    "weighted avg": {
      "precision": 0.9174003237476598,
      "recall": 0.9309821767159651,
      "f1-score": 0.9196870246902797,
      "support": 7911.0
    }
  },
  "confusion_matrix": [
    [
      7190,
      117
    ],
    [
      429,
      175
    ]
  ],
  "true_share": {
    "negative": 0.9236506130704083,
    "positive": 0.07634938692959171
  },
  "predicted_share": {
    "negative": 0.9630893692327139,
    "positive": 0.036910630767286054
  }
}
```

### data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj — offline_phase/temporal/test/northern_plains_proxy / heldout

Rows 16257; accuracy 0.945070; macro-F1 0.706668.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9509630005068423,
      "recall": 0.9921343115870183,
      "f1-score": 0.9711124769514444,
      "support": 15129.0
    },
    "positive": {
      "precision": 0.7484143763213531,
      "recall": 0.31382978723404253,
      "f1-score": 0.44222361024359774,
      "support": 1128.0
    },
    "accuracy": 0.9450698160792275,
    "macro avg": {
      "precision": 0.8496886884140977,
      "recall": 0.6529820494105304,
      "f1-score": 0.7066680435975211,
      "support": 16257.0
    },
    "weighted avg": {
      "precision": 0.9369090638591687,
      "recall": 0.9450698160792275,
      "f1-score": 0.9344152608816622,
      "support": 16257.0
    }
  },
  "confusion_matrix": [
    [
      15010,
      119
    ],
    [
      774,
      354
    ]
  ],
  "true_share": {
    "negative": 0.9306145045211294,
    "positive": 0.06938549547887064
  },
  "predicted_share": {
    "negative": 0.9709048409915728,
    "positive": 0.02909515900842714
  }
}
```

### data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj — offline_phase/temporal/test/peninsula_proxy / heldout

Rows 47592; accuracy 0.959111; macro-F1 0.702717.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9640948599635154,
      "recall": 0.9939595087952207,
      "f1-score": 0.9787994334894868,
      "support": 45195.0
    },
    "positive": {
      "precision": 0.7261785356068204,
      "recall": 0.3020442219440968,
      "f1-score": 0.4266352386564526,
      "support": 2397.0
    },
    "accuracy": 0.9591107749201546,
    "macro avg": {
      "precision": 0.845136697785168,
      "recall": 0.6480018653696588,
      "f1-score": 0.7027173360729697,
      "support": 47592.0
    },
    "weighted avg": {
      "precision": 0.9521120597138306,
      "recall": 0.9591107749201546,
      "f1-score": 0.9509893482857807,
      "support": 47592.0
    }
  },
  "confusion_matrix": [
    [
      44922,
      273
    ],
    [
      1673,
      724
    ]
  ],
  "true_share": {
    "negative": 0.9496343923348461,
    "positive": 0.05036560766515381
  },
  "predicted_share": {
    "negative": 0.9790511010253824,
    "positive": 0.02094889897461758
  }
}
```

### data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj — offline_phase/temporal/test/western_arid_proxy / heldout

Rows 13323; accuracy 0.979209; macro-F1 0.763464.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9847153228888039,
      "recall": 0.9940595587100756,
      "f1-score": 0.9893653779705917,
      "support": 12962.0
    },
    "positive": {
      "precision": 0.6764705882352942,
      "recall": 0.44598337950138506,
      "f1-score": 0.5375626043405676,
      "support": 361.0
    },
    "accuracy": 0.9792088868873376,
    "macro avg": {
      "precision": 0.830592955562049,
      "recall": 0.7200214691057303,
      "f1-score": 0.7634639911555796,
      "support": 13323.0
    },
    "weighted avg": {
      "precision": 0.9763631237437226,
      "recall": 0.9792088868873376,
      "f1-score": 0.9771233302876045,
      "support": 13323.0
    }
  },
  "confusion_matrix": [
    [
      12885,
      77
    ],
    [
      200,
      161
    ]
  ],
  "true_share": {
    "negative": 0.9729040006004653,
    "positive": 0.02709599939953464
  },
  "predicted_share": {
    "negative": 0.9821361555205285,
    "positive": 0.01786384447947159
  }
}
```

### data/india_sensor/offline/models/himalaya_only_hot_measurement_at_6h_A.ubj — offline_phase/himalaya_only/test/A / heldout

Rows 724; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 724.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 724.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 724.0
    }
  },
  "confusion_matrix": [
    [
      724,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_only_hot_measurement_at_6h_D_mountain_proxy.ubj — offline_phase/himalaya_only/test/B / heldout

Rows 724; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 724.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 724.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 724.0
    }
  },
  "confusion_matrix": [
    [
      724,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_only_hot_measurement_at_6h_D_mountain_proxy.ubj — offline_phase/himalaya_only/test/mountain_proxy / heldout

Rows 724; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 724.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 724.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 724.0
    }
  },
  "confusion_matrix": [
    [
      724,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_only_near_saturation_measurement_at_6h_A.ubj — offline_phase/himalaya_only/test/A / heldout

Rows 717; accuracy 0.871688; macro-F1 0.561643.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.8746438746438746,
      "recall": 0.9935275080906149,
      "f1-score": 0.9303030303030303,
      "support": 618.0
    },
    "positive": {
      "precision": 0.7333333333333333,
      "recall": 0.1111111111111111,
      "f1-score": 0.19298245614035087,
      "support": 99.0
    },
    "accuracy": 0.8716875871687587,
    "macro avg": {
      "precision": 0.803988603988604,
      "recall": 0.552319309600863,
      "f1-score": 0.5616427432216906,
      "support": 717.0
    },
    "weighted avg": {
      "precision": 0.8551323773081095,
      "recall": 0.8716875871687587,
      "f1-score": 0.8284972606487689,
      "support": 717.0
    }
  },
  "confusion_matrix": [
    [
      614,
      4
    ],
    [
      88,
      11
    ]
  ],
  "true_share": {
    "negative": 0.8619246861924686,
    "positive": 0.13807531380753138
  },
  "predicted_share": {
    "negative": 0.9790794979079498,
    "positive": 0.02092050209205021
  }
}
```

### data/india_sensor/offline/models/himalaya_only_near_saturation_measurement_at_6h_D_mountain_proxy.ubj — offline_phase/himalaya_only/test/B / heldout

Rows 717; accuracy 0.871688; macro-F1 0.561643.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.8746438746438746,
      "recall": 0.9935275080906149,
      "f1-score": 0.9303030303030303,
      "support": 618.0
    },
    "positive": {
      "precision": 0.7333333333333333,
      "recall": 0.1111111111111111,
      "f1-score": 0.19298245614035087,
      "support": 99.0
    },
    "accuracy": 0.8716875871687587,
    "macro avg": {
      "precision": 0.803988603988604,
      "recall": 0.552319309600863,
      "f1-score": 0.5616427432216906,
      "support": 717.0
    },
    "weighted avg": {
      "precision": 0.8551323773081095,
      "recall": 0.8716875871687587,
      "f1-score": 0.8284972606487689,
      "support": 717.0
    }
  },
  "confusion_matrix": [
    [
      614,
      4
    ],
    [
      88,
      11
    ]
  ],
  "true_share": {
    "negative": 0.8619246861924686,
    "positive": 0.13807531380753138
  },
  "predicted_share": {
    "negative": 0.9790794979079498,
    "positive": 0.02092050209205021
  }
}
```

### data/india_sensor/offline/models/himalaya_only_near_saturation_measurement_at_6h_D_mountain_proxy.ubj — offline_phase/himalaya_only/test/mountain_proxy / heldout

Rows 717; accuracy 0.871688; macro-F1 0.561643.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.8746438746438746,
      "recall": 0.9935275080906149,
      "f1-score": 0.9303030303030303,
      "support": 618.0
    },
    "positive": {
      "precision": 0.7333333333333333,
      "recall": 0.1111111111111111,
      "f1-score": 0.19298245614035087,
      "support": 99.0
    },
    "accuracy": 0.8716875871687587,
    "macro avg": {
      "precision": 0.803988603988604,
      "recall": 0.552319309600863,
      "f1-score": 0.5616427432216906,
      "support": 717.0
    },
    "weighted avg": {
      "precision": 0.8551323773081095,
      "recall": 0.8716875871687587,
      "f1-score": 0.8284972606487689,
      "support": 717.0
    }
  },
  "confusion_matrix": [
    [
      614,
      4
    ],
    [
      88,
      11
    ]
  ],
  "true_share": {
    "negative": 0.8619246861924686,
    "positive": 0.13807531380753138
  },
  "predicted_share": {
    "negative": 0.9790794979079498,
    "positive": 0.02092050209205021
  }
}
```

### data/india_sensor/models/national_high_wind_measurement_at_6h_A.ubj — india_sensor_phase/national/test/A / heldout

Rows 17858; accuracy 0.999888; macro-F1 0.499972.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.999888005375742,
      "recall": 1.0,
      "f1-score": 0.9999439995519964,
      "support": 17856.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 2.0
    },
    "accuracy": 0.999888005375742,
    "macro avg": {
      "precision": 0.499944002687871,
      "recall": 0.5,
      "f1-score": 0.4999719997759982,
      "support": 17858.0
    },
    "weighted avg": {
      "precision": 0.9997760232942798,
      "recall": 0.999888005375742,
      "f1-score": 0.9998320111994875,
      "support": 17858.0
    }
  },
  "confusion_matrix": [
    [
      17856,
      0
    ],
    [
      2,
      0
    ]
  ],
  "true_share": {
    "negative": 0.999888005375742,
    "positive": 0.00011199462425803562
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### ml/models/india_sensor_v1/national_high_wind_measurement_at_6h_B.ubj — india_sensor_phase/national/test/B / heldout

Rows 17858; accuracy 0.999888; macro-F1 0.499972.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.999888005375742,
      "recall": 1.0,
      "f1-score": 0.9999439995519964,
      "support": 17856.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 2.0
    },
    "accuracy": 0.999888005375742,
    "macro avg": {
      "precision": 0.499944002687871,
      "recall": 0.5,
      "f1-score": 0.4999719997759982,
      "support": 17858.0
    },
    "weighted avg": {
      "precision": 0.9997760232942798,
      "recall": 0.999888005375742,
      "f1-score": 0.9998320111994875,
      "support": 17858.0
    }
  },
  "confusion_matrix": [
    [
      17856,
      0
    ],
    [
      2,
      0
    ]
  ],
  "true_share": {
    "negative": 0.999888005375742,
    "positive": 0.00011199462425803562
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj — india_sensor_phase/national/test/northern_plains_proxy / heldout

Rows 1761; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 1761.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 1761.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 1761.0
    }
  },
  "confusion_matrix": [
    [
      1761,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_peninsula_proxy.ubj — india_sensor_phase/national/test/peninsula_proxy / heldout

Rows 9875; accuracy 0.999797; macro-F1 0.499949.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9997974683544304,
      "recall": 1.0,
      "f1-score": 0.9998987239214098,
      "support": 9873.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 2.0
    },
    "accuracy": 0.9997974683544304,
    "macro avg": {
      "precision": 0.4998987341772152,
      "recall": 0.5,
      "f1-score": 0.4999493619607049,
      "support": 9875.0
    },
    "weighted avg": {
      "precision": 0.9995949777279282,
      "recall": 0.9997974683544304,
      "f1-score": 0.999696212787451,
      "support": 9875.0
    }
  },
  "confusion_matrix": [
    [
      9873,
      0
    ],
    [
      2,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9997974683544304,
    "positive": 0.00020253164556962027
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_western_arid_proxy.ubj — india_sensor_phase/national/test/western_arid_proxy / heldout

Rows 2787; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2787.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2787.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2787.0
    }
  },
  "confusion_matrix": [
    [
      2787,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/models/national_hot_measurement_at_6h_A.ubj — india_sensor_phase/national/test/A / heldout

Rows 17785; accuracy 0.996177; macro-F1 0.499042.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9965687928900889,
      "recall": 0.9996050552922591,
      "f1-score": 0.9980846149512703,
      "support": 17724.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 61.0
    },
    "accuracy": 0.9961765532752319,
    "macro avg": {
      "precision": 0.49828439644504446,
      "recall": 0.49980252764612954,
      "f1-score": 0.49904230747563516,
      "support": 17785.0
    },
    "weighted avg": {
      "precision": 0.9931507048177641,
      "recall": 0.9961765532752319,
      "f1-score": 0.9946613278266132,
      "support": 17785.0
    }
  },
  "confusion_matrix": [
    [
      17717,
      7
    ],
    [
      61,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9965701433792522,
    "positive": 0.003429856620747821
  },
  "predicted_share": {
    "negative": 0.9996064098959797,
    "positive": 0.0003935901040202418
  }
}
```

### ml/models/india_sensor_v1/national_hot_measurement_at_6h_B.ubj — india_sensor_phase/national/test/B / heldout

Rows 17785; accuracy 0.996345; macro-F1 0.499085.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.996569371801361,
      "recall": 0.9997743173098623,
      "f1-score": 0.9981692719335304,
      "support": 17724.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 61.0
    },
    "accuracy": 0.9963452347483834,
    "macro avg": {
      "precision": 0.4982846859006805,
      "recall": 0.49988715865493116,
      "f1-score": 0.4990846359667652,
      "support": 17785.0
    },
    "weighted avg": {
      "precision": 0.9931512817434535,
      "recall": 0.9963452347483834,
      "f1-score": 0.9947456944475622,
      "support": 17785.0
    }
  },
  "confusion_matrix": [
    [
      17720,
      4
    ],
    [
      61,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9965701433792522,
    "positive": 0.003429856620747821
  },
  "predicted_share": {
    "negative": 0.9997750913691313,
    "positive": 0.00022490863086870958
  }
}
```

### data/india_sensor/offline/models/national_hot_measurement_at_6h_D_mountain_proxy.ubj — india_sensor_phase/national/test/mountain_proxy / heldout

Rows 238; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 238.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 238.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 238.0
    }
  },
  "confusion_matrix": [
    [
      238,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_hot_measurement_at_6h_D_northeast_proxy.ubj — india_sensor_phase/national/test/northeast_proxy / heldout

Rows 3197; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 3197.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 3197.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 3197.0
    }
  },
  "confusion_matrix": [
    [
      3197,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/national_hot_measurement_at_6h_D_northern_plains_proxy.ubj — india_sensor_phase/national/test/northern_plains_proxy / heldout

Rows 1737; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 1737.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 1737.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 1737.0
    }
  },
  "confusion_matrix": [
    [
      1737,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/models/national_hot_measurement_at_6h_D_peninsula_proxy.ubj — india_sensor_phase/national/test/peninsula_proxy / heldout

Rows 9873; accuracy 0.997974; macro-F1 0.499493.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9979742732705358,
      "recall": 1.0,
      "f1-score": 0.9989861097029301,
      "support": 9853.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 20.0
    },
    "accuracy": 0.9979742732705358,
    "macro avg": {
      "precision": 0.4989871366352679,
      "recall": 0.5,
      "f1-score": 0.49949305485146506,
      "support": 9873.0
    },
    "weighted avg": {
      "precision": 0.995952650109854,
      "recall": 0.9979742732705358,
      "f1-score": 0.9969624368381413,
      "support": 9873.0
    }
  },
  "confusion_matrix": [
    [
      9853,
      0
    ],
    [
      20,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9979742732705358,
    "positive": 0.0020257267294641955
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/models/national_hot_measurement_at_6h_D_western_arid_proxy.ubj — india_sensor_phase/national/test/western_arid_proxy / heldout

Rows 2740; accuracy 0.985036; macro-F1 0.496231.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9850364963503649,
      "recall": 1.0,
      "f1-score": 0.9924618496047067,
      "support": 2699.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 41.0
    },
    "accuracy": 0.9850364963503649,
    "macro avg": {
      "precision": 0.49251824817518247,
      "recall": 0.5,
      "f1-score": 0.49623092480235337,
      "support": 2740.0
    },
    "weighted avg": {
      "precision": 0.9702968991422025,
      "recall": 0.9850364963503649,
      "f1-score": 0.977611143096023,
      "support": 2740.0
    }
  },
  "confusion_matrix": [
    [
      2699,
      0
    ],
    [
      41,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9850364963503649,
    "positive": 0.014963503649635036
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/models/national_near_saturation_measurement_at_6h_A.ubj — india_sensor_phase/national/test/A / heldout

Rows 17777; accuracy 0.941497; macro-F1 0.681250.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9457900807381776,
      "recall": 0.9939393939393939,
      "f1-score": 0.9692671394799054,
      "support": 16500.0
    },
    "positive": {
      "precision": 0.7711670480549199,
      "recall": 0.2638997650743931,
      "f1-score": 0.39323220536756126,
      "support": 1277.0
    },
    "accuracy": 0.9414974405130224,
    "macro avg": {
      "precision": 0.8584785643965487,
      "recall": 0.6289195795068935,
      "f1-score": 0.6812496724237334,
      "support": 17777.0
    },
    "weighted avg": {
      "precision": 0.9332461412243945,
      "recall": 0.9414974405130224,
      "f1-score": 0.9278880197824614,
      "support": 17777.0
    }
  },
  "confusion_matrix": [
    [
      16400,
      100
    ],
    [
      940,
      337
    ]
  ],
  "true_share": {
    "negative": 0.9281656072453169,
    "positive": 0.07183439275468302
  },
  "predicted_share": {
    "negative": 0.9754176745232604,
    "positive": 0.024582325476739608
  }
}
```

### data/india_sensor/models/national_near_saturation_measurement_at_6h_B.ubj — india_sensor_phase/national/test/B / heldout

Rows 17777; accuracy 0.941160; macro-F1 0.681876.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9459771441763823,
      "recall": 0.9933333333333333,
      "f1-score": 0.9690770413291551,
      "support": 16500.0
    },
    "positive": {
      "precision": 0.7560975609756098,
      "recall": 0.26703210649960846,
      "f1-score": 0.39467592592592593,
      "support": 1277.0
    },
    "accuracy": 0.9411599257467514,
    "macro avg": {
      "precision": 0.851037352575996,
      "recall": 0.6301827199164709,
      "f1-score": 0.6818764836275405,
      "support": 17777.0
    },
    "weighted avg": {
      "precision": 0.9323372596206426,
      "recall": 0.9411599257467514,
      "f1-score": 0.9278152860065515,
      "support": 17777.0
    }
  },
  "confusion_matrix": [
    [
      16390,
      110
    ],
    [
      936,
      341
    ]
  ],
  "true_share": {
    "negative": 0.9281656072453169,
    "positive": 0.07183439275468302
  },
  "predicted_share": {
    "negative": 0.974630140068628,
    "positive": 0.025369859931372
  }
}
```

### data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_mountain_proxy.ubj — india_sensor_phase/national/test/mountain_proxy / heldout

Rows 238; accuracy 0.991597; macro-F1 0.497890.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9915966386554622,
      "recall": 1.0,
      "f1-score": 0.9957805907172996,
      "support": 236.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 2.0
    },
    "accuracy": 0.9915966386554622,
    "macro avg": {
      "precision": 0.4957983193277311,
      "recall": 0.5,
      "f1-score": 0.4978902953586498,
      "support": 238.0
    },
    "weighted avg": {
      "precision": 0.9832638937928112,
      "recall": 0.9915966386554622,
      "f1-score": 0.9874126865936248,
      "support": 238.0
    }
  },
  "confusion_matrix": [
    [
      236,
      0
    ],
    [
      2,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9915966386554622,
    "positive": 0.008403361344537815
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/models/national_near_saturation_measurement_at_6h_D_northeast_proxy.ubj — india_sensor_phase/national/test/northeast_proxy / heldout

Rows 3195; accuracy 0.933646; macro-F1 0.761231.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9405744470122153,
      "recall": 0.9888927455744533,
      "f1-score": 0.9641285956006769,
      "support": 2881.0
    },
    "positive": {
      "precision": 0.8072289156626506,
      "recall": 0.4267515923566879,
      "f1-score": 0.5583333333333333,
      "support": 314.0
    },
    "accuracy": 0.9336463223787167,
    "macro avg": {
      "precision": 0.873901681337433,
      "recall": 0.7078221689655706,
      "f1-score": 0.7612309644670051,
      "support": 3195.0
    },
    "weighted avg": {
      "precision": 0.9274694401753567,
      "recall": 0.9336463223787167,
      "f1-score": 0.9242476214686125,
      "support": 3195.0
    }
  },
  "confusion_matrix": [
    [
      2849,
      32
    ],
    [
      180,
      134
    ]
  ],
  "true_share": {
    "negative": 0.9017214397496087,
    "positive": 0.09827856025039124
  },
  "predicted_share": {
    "negative": 0.9480438184663537,
    "positive": 0.051956181533646326
  }
}
```

### data/india_sensor/models/national_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj — india_sensor_phase/national/test/northern_plains_proxy / heldout

Rows 1737; accuracy 0.906160; macro-F1 0.740396.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9080318822808093,
      "recall": 0.9912985274431058,
      "f1-score": 0.94784,
      "support": 1494.0
    },
    "positive": {
      "precision": 0.8773584905660378,
      "recall": 0.38271604938271603,
      "f1-score": 0.5329512893982808,
      "support": 243.0
    },
    "accuracy": 0.9061600460564191,
    "macro avg": {
      "precision": 0.8926951864234236,
      "recall": 0.6870072884129109,
      "f1-score": 0.7403956446991404,
      "support": 1737.0
    },
    "weighted avg": {
      "precision": 0.9037407860305563,
      "recall": 0.9061600460564191,
      "f1-score": 0.8897985741645262,
      "support": 1737.0
    }
  },
  "confusion_matrix": [
    [
      1481,
      13
    ],
    [
      150,
      93
    ]
  ],
  "true_share": {
    "negative": 0.8601036269430051,
    "positive": 0.13989637305699482
  },
  "predicted_share": {
    "negative": 0.9389752446747266,
    "positive": 0.06102475532527346
  }
}
```

### data/india_sensor/models/national_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj — india_sensor_phase/national/test/peninsula_proxy / heldout

Rows 9869; accuracy 0.939204; macro-F1 0.660079.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9430405965202983,
      "recall": 0.9945391000436872,
      "f1-score": 0.9681054645970657,
      "support": 9156.0
    },
    "positive": {
      "precision": 0.7652582159624414,
      "recall": 0.22861150070126227,
      "f1-score": 0.35205183585313177,
      "support": 713.0
    },
    "accuracy": 0.9392035667240856,
    "macro avg": {
      "precision": 0.8541494062413698,
      "recall": 0.6115753003724748,
      "f1-score": 0.6600786502250987,
      "support": 9869.0
    },
    "weighted avg": {
      "precision": 0.9301964545264029,
      "recall": 0.9392035667240856,
      "f1-score": 0.9235977903347874,
      "support": 9869.0
    }
  },
  "confusion_matrix": [
    [
      9106,
      50
    ],
    [
      550,
      163
    ]
  ],
  "true_share": {
    "negative": 0.9277535717904549,
    "positive": 0.07224642820954504
  },
  "predicted_share": {
    "negative": 0.9784172661870504,
    "positive": 0.02158273381294964
  }
}
```

### data/india_sensor/models/national_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj — india_sensor_phase/national/test/western_arid_proxy / heldout

Rows 2738; accuracy 0.996713; macro-F1 0.499177.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9981711777615215,
      "recall": 0.9985364068788877,
      "f1-score": 0.9983537589171392,
      "support": 2733.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 5.0
    },
    "accuracy": 0.9967129291453616,
    "macro avg": {
      "precision": 0.49908558888076077,
      "recall": 0.49926820343944384,
      "f1-score": 0.4991768794585696,
      "support": 2738.0
    },
    "weighted avg": {
      "precision": 0.9963483669913215,
      "recall": 0.9967129291453616,
      "f1-score": 0.9965306147262752,
      "support": 2738.0
    }
  },
  "confusion_matrix": [
    [
      2729,
      4
    ],
    [
      5,
      0
    ]
  ],
  "true_share": {
    "negative": 0.9981738495252008,
    "positive": 0.0018261504747991235
  },
  "predicted_share": {
    "negative": 0.9985390796201608,
    "positive": 0.0014609203798392988
  }
}
```

### data/india_sensor/models/himalaya_holdout_high_wind_measurement_at_6h_A.ubj — india_sensor_phase/himalaya_holdout/test/A / heldout

Rows 2680; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2680.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    }
  },
  "confusion_matrix": [
    [
      2680,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/models/himalaya_holdout_high_wind_measurement_at_6h_B.ubj — india_sensor_phase/himalaya_holdout/test/B / heldout

Rows 2680; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2680.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    }
  },
  "confusion_matrix": [
    [
      2680,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/models/himalaya_holdout_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj — india_sensor_phase/himalaya_holdout/test/northern_plains_proxy / heldout

Rows 2680; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2680.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    }
  },
  "confusion_matrix": [
    [
      2680,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_D_peninsula_proxy.ubj — india_sensor_phase/himalaya_holdout/test/peninsula_proxy / heldout

Rows 2680; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2680.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    }
  },
  "confusion_matrix": [
    [
      2680,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_D_western_arid_proxy.ubj — india_sensor_phase/himalaya_holdout/test/western_arid_proxy / heldout

Rows 2680; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2680.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2680.0
    }
  },
  "confusion_matrix": [
    [
      2680,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_A.ubj — india_sensor_phase/himalaya_holdout/test/A / heldout

Rows 2651; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2651.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    }
  },
  "confusion_matrix": [
    [
      2651,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_B.ubj — india_sensor_phase/himalaya_holdout/test/B / heldout

Rows 2651; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2651.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    }
  },
  "confusion_matrix": [
    [
      2651,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_D_northeast_proxy.ubj — india_sensor_phase/himalaya_holdout/test/northeast_proxy / heldout

Rows 2651; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2651.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    }
  },
  "confusion_matrix": [
    [
      2651,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_D_northern_plains_proxy.ubj — india_sensor_phase/himalaya_holdout/test/northern_plains_proxy / heldout

Rows 2651; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2651.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    }
  },
  "confusion_matrix": [
    [
      2651,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_D_peninsula_proxy.ubj — india_sensor_phase/himalaya_holdout/test/peninsula_proxy / heldout

Rows 2651; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2651.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    }
  },
  "confusion_matrix": [
    [
      2651,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_western_arid_proxy.ubj — india_sensor_phase/himalaya_holdout/test/western_arid_proxy / heldout

Rows 2651; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 2651.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2651.0
    }
  },
  "confusion_matrix": [
    [
      2651,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_A.ubj — india_sensor_phase/himalaya_holdout/test/A / heldout

Rows 2643; accuracy 0.890276; macro-F1 0.658758.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9085439229843562,
      "recall": 0.9733562526858617,
      "f1-score": 0.9398340248962656,
      "support": 2327.0
    },
    "positive": {
      "precision": 0.5866666666666667,
      "recall": 0.27848101265822783,
      "f1-score": 0.3776824034334764,
      "support": 316.0
    },
    "accuracy": 0.8902762012864169,
    "macro avg": {
      "precision": 0.7476052948255114,
      "recall": 0.6259186326720447,
      "f1-score": 0.658758214164871,
      "support": 2643.0
    },
    "weighted avg": {
      "precision": 0.8700599226073641,
      "recall": 0.8902762012864169,
      "f1-score": 0.8726225559661704,
      "support": 2643.0
    }
  },
  "confusion_matrix": [
    [
      2265,
      62
    ],
    [
      228,
      88
    ]
  ],
  "true_share": {
    "negative": 0.8804388951948543,
    "positive": 0.11956110480514567
  },
  "predicted_share": {
    "negative": 0.9432463110102156,
    "positive": 0.056753688989784334
  }
}
```

### data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_B.ubj — india_sensor_phase/himalaya_holdout/test/B / heldout

Rows 2643; accuracy 0.893303; macro-F1 0.688539.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9158194387962586,
      "recall": 0.9677696605070907,
      "f1-score": 0.9410781445883828,
      "support": 2327.0
    },
    "positive": {
      "precision": 0.592391304347826,
      "recall": 0.3449367088607595,
      "f1-score": 0.436,
      "support": 316.0
    },
    "accuracy": 0.8933030646992054,
    "macro avg": {
      "precision": 0.7541053715720423,
      "recall": 0.6563531846839251,
      "f1-score": 0.6885390722941914,
      "support": 2643.0
    },
    "weighted avg": {
      "precision": 0.8771500137165369,
      "recall": 0.8933030646992054,
      "f1-score": 0.8806904436084626,
      "support": 2643.0
    }
  },
  "confusion_matrix": [
    [
      2252,
      75
    ],
    [
      207,
      109
    ]
  ],
  "true_share": {
    "negative": 0.8804388951948543,
    "positive": 0.11956110480514567
  },
  "predicted_share": {
    "negative": 0.9303821415058645,
    "positive": 0.06961785849413545
  }
}
```

### data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_northeast_proxy.ubj — india_sensor_phase/himalaya_holdout/test/northeast_proxy / heldout

Rows 2643; accuracy 0.894438; macro-F1 0.626975.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9009397024275646,
      "recall": 0.9888268156424581,
      "f1-score": 0.942839582052858,
      "support": 2327.0
    },
    "positive": {
      "precision": 0.7078651685393258,
      "recall": 0.19936708860759494,
      "f1-score": 0.3111111111111111,
      "support": 316.0
    },
    "accuracy": 0.8944381384790011,
    "macro avg": {
      "precision": 0.8044024354834451,
      "recall": 0.5940969521250266,
      "f1-score": 0.6269753465819845,
      "support": 2643.0
    },
    "weighted avg": {
      "precision": 0.8778554978461481,
      "recall": 0.8944381384790011,
      "f1-score": 0.8673094281301974,
      "support": 2643.0
    }
  },
  "confusion_matrix": [
    [
      2301,
      26
    ],
    [
      253,
      63
    ]
  ],
  "true_share": {
    "negative": 0.8804388951948543,
    "positive": 0.11956110480514567
  },
  "predicted_share": {
    "negative": 0.9663261445327279,
    "positive": 0.033673855467272036
  }
}
```

### data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj — india_sensor_phase/himalaya_holdout/test/northern_plains_proxy / heldout

Rows 2643; accuracy 0.884601; macro-F1 0.676395.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9150246305418719,
      "recall": 0.9578856897292651,
      "f1-score": 0.9359647281125342,
      "support": 2327.0
    },
    "positive": {
      "precision": 0.5265700483091788,
      "recall": 0.3449367088607595,
      "f1-score": 0.4168260038240918,
      "support": 316.0
    },
    "accuracy": 0.8846008323874385,
    "macro avg": {
      "precision": 0.7207973394255254,
      "recall": 0.6514111992950123,
      "f1-score": 0.676395365968313,
      "support": 2643.0
    },
    "weighted avg": {
      "precision": 0.8685805715235098,
      "recall": 0.8846008323874385,
      "f1-score": 0.8738959286894742,
      "support": 2643.0
    }
  },
  "confusion_matrix": [
    [
      2229,
      98
    ],
    [
      207,
      109
    ]
  ],
  "true_share": {
    "negative": 0.8804388951948543,
    "positive": 0.11956110480514567
  },
  "predicted_share": {
    "negative": 0.9216799091940976,
    "positive": 0.07832009080590238
  }
}
```

### data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj — india_sensor_phase/himalaya_holdout/test/peninsula_proxy / heldout

Rows 2643; accuracy 0.894060; macro-F1 0.647084.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9050257222002375,
      "recall": 0.9828104856037817,
      "f1-score": 0.942315615986815,
      "support": 2327.0
    },
    "positive": {
      "precision": 0.6551724137931034,
      "recall": 0.24050632911392406,
      "f1-score": 0.35185185185185186,
      "support": 316.0
    },
    "accuracy": 0.8940597805524025,
    "macro avg": {
      "precision": 0.7800990679966704,
      "recall": 0.6116584073588529,
      "f1-score": 0.6470837339193334,
      "support": 2643.0
    },
    "weighted avg": {
      "precision": 0.8751529846078596,
      "recall": 0.8940597805524025,
      "f1-score": 0.871719115999434,
      "support": 2643.0
    }
  },
  "confusion_matrix": [
    [
      2287,
      40
    ],
    [
      240,
      76
    ]
  ],
  "true_share": {
    "negative": 0.8804388951948543,
    "positive": 0.11956110480514567
  },
  "predicted_share": {
    "negative": 0.9561104805145668,
    "positive": 0.04388951948543322
  }
}
```

### data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj — india_sensor_phase/himalaya_holdout/test/western_arid_proxy / heldout

Rows 2643; accuracy 0.868331; macro-F1 0.655715.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9134977016297534,
      "recall": 0.9394069617533305,
      "f1-score": 0.926271186440678,
      "support": 2327.0
    },
    "positive": {
      "precision": 0.436,
      "recall": 0.3449367088607595,
      "f1-score": 0.38515901060070673,
      "support": 316.0
    },
    "accuracy": 0.8683314415437003,
    "macro avg": {
      "precision": 0.6747488508148767,
      "recall": 0.642171835307045,
      "f1-score": 0.6557150985206923,
      "support": 2643.0
    },
    "weighted avg": {
      "precision": 0.8564075488809821,
      "recall": 0.8683314415437003,
      "f1-score": 0.8615752168737348,
      "support": 2643.0
    }
  },
  "confusion_matrix": [
    [
      2186,
      141
    ],
    [
      207,
      109
    ]
  ],
  "true_share": {
    "negative": 0.8804388951948543,
    "positive": 0.11956110480514567
  },
  "predicted_share": {
    "negative": 0.9054105183503595,
    "positive": 0.09458948164964057
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/light_moderate_rain.ubj — future_test / heldout

Rows 50597; accuracy 1.000000; macro-F1 1.000000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 50075.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 522.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 50597.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 50597.0
    }
  },
  "confusion_matrix": [
    [
      50075,
      0
    ],
    [
      0,
      522
    ]
  ],
  "true_share": {
    "negative": 0.9896831827973991,
    "positive": 0.010316817202600945
  },
  "predicted_share": {
    "negative": 0.9896831827973991,
    "positive": 0.010316817202600945
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/light_moderate_rain.ubj — geographic_test / heldout

Rows 16850; accuracy 1.000000; macro-F1 1.000000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 16689.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 161.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 16850.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 16850.0
    }
  },
  "confusion_matrix": [
    [
      16689,
      0
    ],
    [
      0,
      161
    ]
  ],
  "true_share": {
    "negative": 0.9904451038575668,
    "positive": 0.009554896142433234
  },
  "predicted_share": {
    "negative": 0.9904451038575668,
    "positive": 0.009554896142433234
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/freezing_rain_sleet.ubj — future_test / heldout

Rows 50597; accuracy 0.999822; macro-F1 0.981737.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9998217045049328,
      "f1-score": 0.999910844304437,
      "support": 50478.0
    },
    "positive": {
      "precision": 0.9296875,
      "recall": 1.0,
      "f1-score": 0.9635627530364372,
      "support": 119.0
    },
    "accuracy": 0.9998221238413345,
    "macro avg": {
      "precision": 0.96484375,
      "recall": 0.9999108522524665,
      "f1-score": 0.9817367986704371,
      "support": 50597.0
    },
    "weighted avg": {
      "precision": 0.9998346307587407,
      "recall": 0.9998221238413345,
      "f1-score": 0.9998253565707592,
      "support": 50597.0
    }
  },
  "confusion_matrix": [
    [
      50469,
      9
    ],
    [
      0,
      119
    ]
  ],
  "true_share": {
    "negative": 0.9976480819020891,
    "positive": 0.0023519180979109434
  },
  "predicted_share": {
    "negative": 0.9974702057434235,
    "positive": 0.002529794256576477
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/freezing_rain_sleet.ubj — geographic_test / heldout

Rows 16850; accuracy 0.999941; macro-F1 0.992943.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.999940529289325,
      "f1-score": 0.9999702637604448,
      "support": 16815.0
    },
    "positive": {
      "precision": 0.9722222222222222,
      "recall": 1.0,
      "f1-score": 0.9859154929577465,
      "support": 35.0
    },
    "accuracy": 0.9999406528189911,
    "macro avg": {
      "precision": 0.9861111111111112,
      "recall": 0.9999702646446624,
      "f1-score": 0.9929428783590957,
      "support": 16850.0
    },
    "weighted avg": {
      "precision": 0.9999423013517968,
      "recall": 0.9999406528189911,
      "f1-score": 0.9999410698745045,
      "support": 16850.0
    }
  },
  "confusion_matrix": [
    [
      16814,
      1
    ],
    [
      0,
      35
    ]
  ],
  "true_share": {
    "negative": 0.9979228486646884,
    "positive": 0.0020771513353115725
  },
  "predicted_share": {
    "negative": 0.9978635014836795,
    "positive": 0.002136498516320475
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/radiation_fog.ubj — future_test / heldout

Rows 50597; accuracy 0.999209; macro-F1 0.985615.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 0.9998797064838205,
      "recall": 0.9993187191920812,
      "f1-score": 0.9995991341297202,
      "support": 49906.0
    },
    "positive": {
      "precision": 0.952712100139082,
      "recall": 0.9913169319826338,
      "f1-score": 0.9716312056737588,
      "support": 691.0
    },
    "accuracy": 0.9992094392948199,
    "macro avg": {
      "precision": 0.9762959033114513,
      "recall": 0.9953178255873575,
      "f1-score": 0.9856151699017395,
      "support": 50597.0
    },
    "weighted avg": {
      "precision": 0.9992355414941134,
      "recall": 0.9992094392948199,
      "f1-score": 0.9992171779156548,
      "support": 50597.0
    }
  },
  "confusion_matrix": [
    [
      49872,
      34
    ],
    [
      6,
      685
    ]
  ],
  "true_share": {
    "negative": 0.986343063818013,
    "positive": 0.013656936181987074
  },
  "predicted_share": {
    "negative": 0.9857896713243868,
    "positive": 0.01421032867561318
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/radiation_fog.ubj — geographic_test / heldout

Rows 16850; accuracy 0.999703; macro-F1 0.992507.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9997003116758572,
      "f1-score": 0.9998501333812907,
      "support": 16684.0
    },
    "positive": {
      "precision": 0.9707602339181286,
      "recall": 1.0,
      "f1-score": 0.9851632047477745,
      "support": 166.0
    },
    "accuracy": 0.9997032640949555,
    "macro avg": {
      "precision": 0.9853801169590644,
      "recall": 0.9998501558379286,
      "f1-score": 0.9925066690645326,
      "support": 16850.0
    },
    "weighted avg": {
      "precision": 0.9997119405834072,
      "recall": 0.9997032640949555,
      "f1-score": 0.9997054431644857,
      "support": 16850.0
    }
  },
  "confusion_matrix": [
    [
      16679,
      5
    ],
    [
      0,
      166
    ]
  ],
  "true_share": {
    "negative": 0.9901483679525223,
    "positive": 0.009851632047477745
  },
  "predicted_share": {
    "negative": 0.9898516320474777,
    "positive": 0.010148367952522256
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/ground_frost.ubj — future_test / heldout

Rows 50597; accuracy 0.999704; macro-F1 0.999172.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9996708721887,
      "f1-score": 0.9998354090086136,
      "support": 45575.0
    },
    "positive": {
      "precision": 0.9970220369267421,
      "recall": 1.0,
      "f1-score": 0.9985087980912616,
      "support": 5022.0
    },
    "accuracy": 0.9997035397355575,
    "macro avg": {
      "precision": 0.998511018463371,
      "recall": 0.99983543609435,
      "f1-score": 0.9991721035499376,
      "support": 50597.0
    },
    "weighted avg": {
      "precision": 0.9997044225832776,
      "recall": 0.9997035397355575,
      "f1-score": 0.9997037363792691,
      "support": 50597.0
    }
  },
  "confusion_matrix": [
    [
      45560,
      15
    ],
    [
      0,
      5022
    ]
  ],
  "true_share": {
    "negative": 0.9007451034646323,
    "positive": 0.0992548965353677
  },
  "predicted_share": {
    "negative": 0.9004486432001897,
    "positive": 0.09955135679981027
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/ground_frost.ubj — geographic_test / heldout

Rows 16850; accuracy 0.999881; macro-F1 0.999708.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9998659068052297,
      "f1-score": 0.9999329489070672,
      "support": 14915.0
    },
    "positive": {
      "precision": 0.9989674754775426,
      "recall": 1.0,
      "f1-score": 0.9994834710743802,
      "support": 1935.0
    },
    "accuracy": 0.9998813056379822,
    "macro avg": {
      "precision": 0.9994837377387713,
      "recall": 0.9999329534026149,
      "f1-score": 0.9997082099907237,
      "support": 16850.0
    },
    "weighted avg": {
      "precision": 0.9998814281928217,
      "recall": 0.9998813056379822,
      "f1-score": 0.9998813323132245,
      "support": 16850.0
    }
  },
  "confusion_matrix": [
    [
      14913,
      2
    ],
    [
      0,
      1935
    ]
  ],
  "true_share": {
    "negative": 0.8851632047477744,
    "positive": 0.11483679525222552
  },
  "predicted_share": {
    "negative": 0.8850445103857567,
    "positive": 0.11495548961424332
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/extreme_heatwave.ubj — future_test / heldout

Rows 50597; accuracy 0.992213; macro-F1 0.833863.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9921504562298282,
      "f1-score": 0.9960597635858152,
      "support": 50194.0
    },
    "positive": {
      "precision": 0.5056461731493099,
      "recall": 1.0,
      "f1-score": 0.6716666666666666,
      "support": 403.0
    },
    "accuracy": 0.9922129770539755,
    "macro avg": {
      "precision": 0.752823086574655,
      "recall": 0.9960752281149141,
      "f1-score": 0.8338632151262408,
      "support": 50597.0
    },
    "weighted avg": {
      "precision": 0.9960625216471168,
      "recall": 0.9922129770539755,
      "f1-score": 0.9934760052985961,
      "support": 50597.0
    }
  },
  "confusion_matrix": [
    [
      49800,
      394
    ],
    [
      0,
      403
    ]
  ],
  "true_share": {
    "negative": 0.99203510089531,
    "positive": 0.00796489910469
  },
  "predicted_share": {
    "negative": 0.9842480779492855,
    "positive": 0.01575192205071447
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/extreme_heatwave.ubj — geographic_test / heldout

Rows 16850; accuracy 0.991513; macro-F1 0.755487.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9914749016334804,
      "f1-score": 0.9957192037120192,
      "support": 16774.0
    },
    "positive": {
      "precision": 0.3470319634703196,
      "recall": 1.0,
      "f1-score": 0.5152542372881356,
      "support": 76.0
    },
    "accuracy": 0.991513353115727,
    "macro avg": {
      "precision": 0.6735159817351598,
      "recall": 0.9957374508167403,
      "f1-score": 0.7554867205000774,
      "support": 16850.0
    },
    "weighted avg": {
      "precision": 0.9970548622684714,
      "recall": 0.991513353115727,
      "f1-score": 0.9935521213708788,
      "support": 16850.0
    }
  },
  "confusion_matrix": [
    [
      16631,
      143
    ],
    [
      0,
      76
    ]
  ],
  "true_share": {
    "negative": 0.9954896142433235,
    "positive": 0.004510385756676558
  },
  "predicted_share": {
    "negative": 0.9870029673590505,
    "positive": 0.012997032640949554
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/wildfire_evaporative_risk.ubj — future_test / heldout

Rows 50597; accuracy 1.000000; macro-F1 1.000000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 50583.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 14.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 50597.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 50597.0
    }
  },
  "confusion_matrix": [
    [
      50583,
      0
    ],
    [
      0,
      14
    ]
  ],
  "true_share": {
    "negative": 0.999723303753187,
    "positive": 0.00027669624681305214
  },
  "predicted_share": {
    "negative": 0.999723303753187,
    "positive": 0.00027669624681305214
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/wildfire_evaporative_risk.ubj — geographic_test / heldout

Rows 16850; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 16850.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 16850.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 16850.0
    }
  },
  "confusion_matrix": [
    [
      16850,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/dust_storm_haboob.ubj — future_test / heldout

Rows 50597; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 50597.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 50597.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 50597.0
    }
  },
  "confusion_matrix": [
    [
      50597,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/dust_storm_haboob.ubj — geographic_test / heldout

Rows 16850; accuracy 1.000000; macro-F1 0.500000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 16850.0
    },
    "positive": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 0.5,
      "recall": 0.5,
      "f1-score": 0.5,
      "support": 16850.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 16850.0
    }
  },
  "confusion_matrix": [
    [
      16850,
      0
    ],
    [
      0,
      0
    ]
  ],
  "true_share": {
    "negative": 1.0,
    "positive": 0.0
  },
  "predicted_share": {
    "negative": 1.0,
    "positive": 0.0
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/smoke_plume.ubj — future_test / heldout

Rows 50597; accuracy 0.999881; macro-F1 0.998134.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9998794769298757,
      "f1-score": 0.9999397348332664,
      "support": 49783.0
    },
    "positive": {
      "precision": 0.9926829268292683,
      "recall": 1.0,
      "f1-score": 0.996328029375765,
      "support": 814.0
    },
    "accuracy": 0.999881415894223,
    "macro avg": {
      "precision": 0.9963414634146341,
      "recall": 0.9999397384649378,
      "f1-score": 0.9981338821045157,
      "support": 50597.0
    },
    "weighted avg": {
      "precision": 0.9998822835828017,
      "recall": 0.999881415894223,
      "f1-score": 0.999881630039654,
      "support": 50597.0
    }
  },
  "confusion_matrix": [
    [
      49777,
      6
    ],
    [
      0,
      814
    ]
  ],
  "true_share": {
    "negative": 0.983912089649584,
    "positive": 0.016087910350416033
  },
  "predicted_share": {
    "negative": 0.983793505543807,
    "positive": 0.016206494456193054
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/smoke_plume.ubj — geographic_test / heldout

Rows 16850; accuracy 0.999941; macro-F1 0.998713.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9999399543653177,
      "f1-score": 0.9999699762812622,
      "support": 16654.0
    },
    "positive": {
      "precision": 0.9949238578680203,
      "recall": 1.0,
      "f1-score": 0.9974554707379135,
      "support": 196.0
    },
    "accuracy": 0.9999406528189911,
    "macro avg": {
      "precision": 0.9974619289340101,
      "recall": 0.9999699771826589,
      "f1-score": 0.9987127235095878,
      "support": 16850.0
    },
    "weighted avg": {
      "precision": 0.9999409540737171,
      "recall": 0.9999406528189911,
      "f1-score": 0.9999407274333988,
      "support": 16850.0
    }
  },
  "confusion_matrix": [
    [
      16653,
      1
    ],
    [
      0,
      196
    ]
  ],
  "true_share": {
    "negative": 0.9883679525222552,
    "positive": 0.011632047477744807
  },
  "predicted_share": {
    "negative": 0.9883086053412463,
    "positive": 0.011691394658753709
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/smog_inversion_trap.ubj — future_test / heldout

Rows 50597; accuracy 1.000000; macro-F1 1.000000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 50169.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 428.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 50597.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 50597.0
    }
  },
  "confusion_matrix": [
    [
      50169,
      0
    ],
    [
      0,
      428
    ]
  ],
  "true_share": {
    "negative": 0.9915410004545724,
    "positive": 0.008458999545427594
  },
  "predicted_share": {
    "negative": 0.9915410004545724,
    "positive": 0.008458999545427594
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/smog_inversion_trap.ubj — geographic_test / heldout

Rows 16850; accuracy 1.000000; macro-F1 1.000000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 16820.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 30.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 16850.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 16850.0
    }
  },
  "confusion_matrix": [
    [
      16820,
      0
    ],
    [
      0,
      30
    ]
  ],
  "true_share": {
    "negative": 0.9982195845697329,
    "positive": 0.0017804154302670622
  },
  "predicted_share": {
    "negative": 0.9982195845697329,
    "positive": 0.0017804154302670622
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/cold_frontal_passage.ubj — future_test / heldout

Rows 50597; accuracy 0.999980; macro-F1 0.961534.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 0.9999802336383942,
      "f1-score": 0.9999901167215188,
      "support": 50591.0
    },
    "positive": {
      "precision": 0.8571428571428571,
      "recall": 1.0,
      "f1-score": 0.9230769230769231,
      "support": 6.0
    },
    "accuracy": 0.9999802359823705,
    "macro avg": {
      "precision": 0.9285714285714286,
      "recall": 0.9999901168191971,
      "f1-score": 0.961533519899221,
      "support": 50597.0
    },
    "weighted avg": {
      "precision": 0.9999830594134603,
      "recall": 0.9999802359823705,
      "f1-score": 0.999980996039228,
      "support": 50597.0
    }
  },
  "confusion_matrix": [
    [
      50590,
      1
    ],
    [
      0,
      6
    ]
  ],
  "true_share": {
    "negative": 0.999881415894223,
    "positive": 0.00011858410577702236
  },
  "predicted_share": {
    "negative": 0.9998616518765935,
    "positive": 0.00013834812340652607
  }
}
```

### ml/models/uci_beijing_event_rules_6sensor/esp32_student/cold_frontal_passage.ubj — geographic_test / heldout

Rows 16850; accuracy 1.000000; macro-F1 1.000000.

```json
{
  "class_order": [
    "negative",
    "positive"
  ],
  "classification_report": {
    "negative": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 16848.0
    },
    "positive": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 2.0
    },
    "accuracy": 1.0,
    "macro avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 16850.0
    },
    "weighted avg": {
      "precision": 1.0,
      "recall": 1.0,
      "f1-score": 1.0,
      "support": 16850.0
    }
  },
  "confusion_matrix": [
    [
      16848,
      0
    ],
    [
      0,
      2
    ]
  ],
  "true_share": {
    "negative": 0.9998813056379822,
    "positive": 0.00011869436201780416
  },
  "predicted_share": {
    "negative": 0.9998813056379822,
    "positive": 0.00011869436201780416
  }
}
```

### archive:ml/model — Mandi exclusive proxy class report

```json
{
  "rows": 718,
  "accuracy": 0.4373259052924791,
  "macro_f1": 0.1498937836719705,
  "classification_report": {
    "normal": {
      "precision": 1.0,
      "recall": 0.4050073637702504,
      "f1-score": 0.5765199161425576,
      "support": 679.0
    },
    "wildfire": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "flood": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "storm": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "air_quality": {
      "precision": 0.09466019417475728,
      "recall": 1.0,
      "f1-score": 0.1729490022172949,
      "support": 39.0
    },
    "accuracy": 0.4373259052924791,
    "macro avg": {
      "precision": 0.21893203883495146,
      "recall": 0.2810014727540501,
      "f1-score": 0.1498937836719705,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9508241609649242,
      "recall": 0.4373259052924791,
      "f1-score": 0.5545989333527452,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      275,
      31,
      0,
      0,
      373
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      39
    ]
  ],
  "class_order": [
    "normal",
    "wildfire",
    "flood",
    "storm",
    "air_quality"
  ],
  "true_share": {
    "normal": 0.9456824512534819,
    "wildfire": 0.0,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.054317548746518104
  },
  "predicted_share": {
    "normal": 0.383008356545961,
    "wildfire": 0.04317548746518106,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.5738161559888579
  },
  "majority_normal_accuracy": 0.9456824512534819,
  "overlapping_head_prediction_hours": 17
}
```

### archive:ml/model_baseline — Mandi exclusive proxy class report

```json
{
  "rows": 718,
  "accuracy": 0.4373259052924791,
  "macro_f1": 0.1498937836719705,
  "classification_report": {
    "normal": {
      "precision": 1.0,
      "recall": 0.4050073637702504,
      "f1-score": 0.5765199161425576,
      "support": 679.0
    },
    "wildfire": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "flood": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "storm": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "air_quality": {
      "precision": 0.09466019417475728,
      "recall": 1.0,
      "f1-score": 0.1729490022172949,
      "support": 39.0
    },
    "accuracy": 0.4373259052924791,
    "macro avg": {
      "precision": 0.21893203883495146,
      "recall": 0.2810014727540501,
      "f1-score": 0.1498937836719705,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9508241609649242,
      "recall": 0.4373259052924791,
      "f1-score": 0.5545989333527452,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      275,
      31,
      0,
      0,
      373
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      39
    ]
  ],
  "class_order": [
    "normal",
    "wildfire",
    "flood",
    "storm",
    "air_quality"
  ],
  "true_share": {
    "normal": 0.9456824512534819,
    "wildfire": 0.0,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.054317548746518104
  },
  "predicted_share": {
    "normal": 0.383008356545961,
    "wildfire": 0.04317548746518106,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.5738161559888579
  },
  "majority_normal_accuracy": 0.9456824512534819,
  "overlapping_head_prediction_hours": 17
}
```

### archive:ml/model_india_26 — Mandi exclusive proxy class report

```json
{
  "rows": 718,
  "accuracy": 0.3064066852367688,
  "macro_f1": 0.11073276703768795,
  "classification_report": {
    "normal": {
      "precision": 0.9891891891891892,
      "recall": 0.2695139911634757,
      "f1-score": 0.4236111111111111,
      "support": 679.0
    },
    "wildfire": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "flood": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "storm": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "air_quality": {
      "precision": 0.06981132075471698,
      "recall": 0.9487179487179487,
      "f1-score": 0.13005272407732865,
      "support": 39.0
    },
    "accuracy": 0.3064066852367688,
    "macro avg": {
      "precision": 0.21180010198878124,
      "recall": 0.24364638797628485,
      "f1-score": 0.11073276703768795,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9392508370040298,
      "recall": 0.3064066852367688,
      "f1-score": 0.4076657391134544,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      183,
      3,
      0,
      0,
      493
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      2,
      0,
      0,
      0,
      37
    ]
  ],
  "class_order": [
    "normal",
    "wildfire",
    "flood",
    "storm",
    "air_quality"
  ],
  "true_share": {
    "normal": 0.9456824512534819,
    "wildfire": 0.0,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.054317548746518104
  },
  "predicted_share": {
    "normal": 0.2576601671309192,
    "wildfire": 0.004178272980501393,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.7381615598885793
  },
  "majority_normal_accuracy": 0.9456824512534819,
  "overlapping_head_prediction_hours": 1
}
```

### archive:ml/model_india_26_baseline_repro — Mandi exclusive proxy class report

```json
{
  "rows": 718,
  "accuracy": 0.5487465181058496,
  "macro_f1": 0.17504060876563987,
  "classification_report": {
    "normal": {
      "precision": 0.9944289693593314,
      "recall": 0.5257731958762887,
      "f1-score": 0.6878612716763006,
      "support": 679.0
    },
    "wildfire": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "flood": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "storm": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "air_quality": {
      "precision": 0.10393258426966293,
      "recall": 0.9487179487179487,
      "f1-score": 0.18734177215189873,
      "support": 39.0
    },
    "accuracy": 0.5487465181058496,
    "macro avg": {
      "precision": 0.21967231072579887,
      "recall": 0.2948982289188475,
      "f1-score": 0.17504060876563987,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9460593885536254,
      "recall": 0.5487465181058496,
      "f1-score": 0.660674279362301,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      357,
      3,
      0,
      0,
      319
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      2,
      0,
      0,
      0,
      37
    ]
  ],
  "class_order": [
    "normal",
    "wildfire",
    "flood",
    "storm",
    "air_quality"
  ],
  "true_share": {
    "normal": 0.9456824512534819,
    "wildfire": 0.0,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.054317548746518104
  },
  "predicted_share": {
    "normal": 0.5,
    "wildfire": 0.004178272980501393,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.4958217270194986
  },
  "majority_normal_accuracy": 0.9456824512534819,
  "overlapping_head_prediction_hours": 0
}
```

### archive:ml/model_india_26_distilled — Mandi exclusive proxy class report

```json
{
  "rows": 718,
  "accuracy": 0.9930362116991643,
  "macro_f1": 0.3939999224295078,
  "classification_report": {
    "normal": {
      "precision": 0.9970501474926253,
      "recall": 0.9955817378497791,
      "f1-score": 0.9963154016212233,
      "support": 679.0
    },
    "wildfire": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "flood": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "storm": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "air_quality": {
      "precision": 1.0,
      "recall": 0.9487179487179487,
      "f1-score": 0.9736842105263158,
      "support": 39.0
    },
    "accuracy": 0.9930362116991643,
    "macro avg": {
      "precision": 0.3994100294985251,
      "recall": 0.38885993731354557,
      "f1-score": 0.3939999224295078,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9972103762499896,
      "recall": 0.9930362116991643,
      "f1-score": 0.995086130795734,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      676,
      3,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      2,
      0,
      0,
      0,
      37
    ]
  ],
  "class_order": [
    "normal",
    "wildfire",
    "flood",
    "storm",
    "air_quality"
  ],
  "true_share": {
    "normal": 0.9456824512534819,
    "wildfire": 0.0,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.054317548746518104
  },
  "predicted_share": {
    "normal": 0.9442896935933147,
    "wildfire": 0.004178272980501393,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.05153203342618384
  },
  "majority_normal_accuracy": 0.9456824512534819,
  "overlapping_head_prediction_hours": 0
}
```

### archive:ml/model_india_26_distilled_context — Mandi exclusive proxy class report

```json
{
  "rows": 718,
  "accuracy": 0.9930362116991643,
  "macro_f1": 0.3939999224295078,
  "classification_report": {
    "normal": {
      "precision": 0.9970501474926253,
      "recall": 0.9955817378497791,
      "f1-score": 0.9963154016212233,
      "support": 679.0
    },
    "wildfire": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "flood": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "storm": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "air_quality": {
      "precision": 1.0,
      "recall": 0.9487179487179487,
      "f1-score": 0.9736842105263158,
      "support": 39.0
    },
    "accuracy": 0.9930362116991643,
    "macro avg": {
      "precision": 0.3994100294985251,
      "recall": 0.38885993731354557,
      "f1-score": 0.3939999224295078,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9972103762499896,
      "recall": 0.9930362116991643,
      "f1-score": 0.995086130795734,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      676,
      3,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      2,
      0,
      0,
      0,
      37
    ]
  ],
  "class_order": [
    "normal",
    "wildfire",
    "flood",
    "storm",
    "air_quality"
  ],
  "true_share": {
    "normal": 0.9456824512534819,
    "wildfire": 0.0,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.054317548746518104
  },
  "predicted_share": {
    "normal": 0.9442896935933147,
    "wildfire": 0.004178272980501393,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.05153203342618384
  },
  "majority_normal_accuracy": 0.9456824512534819,
  "overlapping_head_prediction_hours": 0
}
```

### archive:ml/model_india_26_geo_temporal — Mandi exclusive proxy class report

```json
{
  "rows": 718,
  "accuracy": 0.5487465181058496,
  "macro_f1": 0.17504060876563987,
  "classification_report": {
    "normal": {
      "precision": 0.9944289693593314,
      "recall": 0.5257731958762887,
      "f1-score": 0.6878612716763006,
      "support": 679.0
    },
    "wildfire": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "flood": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "storm": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "air_quality": {
      "precision": 0.10393258426966293,
      "recall": 0.9487179487179487,
      "f1-score": 0.18734177215189873,
      "support": 39.0
    },
    "accuracy": 0.5487465181058496,
    "macro avg": {
      "precision": 0.21967231072579887,
      "recall": 0.2948982289188475,
      "f1-score": 0.17504060876563987,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9460593885536254,
      "recall": 0.5487465181058496,
      "f1-score": 0.660674279362301,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      357,
      3,
      0,
      0,
      319
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      2,
      0,
      0,
      0,
      37
    ]
  ],
  "class_order": [
    "normal",
    "wildfire",
    "flood",
    "storm",
    "air_quality"
  ],
  "true_share": {
    "normal": 0.9456824512534819,
    "wildfire": 0.0,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.054317548746518104
  },
  "predicted_share": {
    "normal": 0.5,
    "wildfire": 0.004178272980501393,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.4958217270194986
  },
  "majority_normal_accuracy": 0.9456824512534819,
  "overlapping_head_prediction_hours": 0
}
```

### archive:ml/model_india_26_masked_distilled_edge — Mandi exclusive proxy class report

```json
{
  "rows": 718,
  "accuracy": 0.9930362116991643,
  "macro_f1": 0.3939999224295078,
  "classification_report": {
    "normal": {
      "precision": 0.9970501474926253,
      "recall": 0.9955817378497791,
      "f1-score": 0.9963154016212233,
      "support": 679.0
    },
    "wildfire": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "flood": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "storm": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "air_quality": {
      "precision": 1.0,
      "recall": 0.9487179487179487,
      "f1-score": 0.9736842105263158,
      "support": 39.0
    },
    "accuracy": 0.9930362116991643,
    "macro avg": {
      "precision": 0.3994100294985251,
      "recall": 0.38885993731354557,
      "f1-score": 0.3939999224295078,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9972103762499896,
      "recall": 0.9930362116991643,
      "f1-score": 0.995086130795734,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      676,
      3,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      2,
      0,
      0,
      0,
      37
    ]
  ],
  "class_order": [
    "normal",
    "wildfire",
    "flood",
    "storm",
    "air_quality"
  ],
  "true_share": {
    "normal": 0.9456824512534819,
    "wildfire": 0.0,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.054317548746518104
  },
  "predicted_share": {
    "normal": 0.9442896935933147,
    "wildfire": 0.004178272980501393,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.05153203342618384
  },
  "majority_normal_accuracy": 0.9456824512534819,
  "overlapping_head_prediction_hours": 0
}
```

### archive:ml/model_india_26_verified_storm_candidate — Mandi exclusive proxy class report

```json
{
  "rows": 718,
  "accuracy": 0.9930362116991643,
  "macro_f1": 0.3939999224295078,
  "classification_report": {
    "normal": {
      "precision": 0.9970501474926253,
      "recall": 0.9955817378497791,
      "f1-score": 0.9963154016212233,
      "support": 679.0
    },
    "wildfire": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "flood": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "storm": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "air_quality": {
      "precision": 1.0,
      "recall": 0.9487179487179487,
      "f1-score": 0.9736842105263158,
      "support": 39.0
    },
    "accuracy": 0.9930362116991643,
    "macro avg": {
      "precision": 0.3994100294985251,
      "recall": 0.38885993731354557,
      "f1-score": 0.3939999224295078,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9972103762499896,
      "recall": 0.9930362116991643,
      "f1-score": 0.995086130795734,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      676,
      3,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      2,
      0,
      0,
      0,
      37
    ]
  ],
  "class_order": [
    "normal",
    "wildfire",
    "flood",
    "storm",
    "air_quality"
  ],
  "true_share": {
    "normal": 0.9456824512534819,
    "wildfire": 0.0,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.054317548746518104
  },
  "predicted_share": {
    "normal": 0.9442896935933147,
    "wildfire": 0.004178272980501393,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.05153203342618384
  },
  "majority_normal_accuracy": 0.9456824512534819,
  "overlapping_head_prediction_hours": 0
}
```

### archive:ml/model_india_pilot — Mandi exclusive proxy class report

```json
{
  "rows": 718,
  "accuracy": 0.8091922005571031,
  "macro_f1": 0.2511442832197549,
  "classification_report": {
    "normal": {
      "precision": 1.0,
      "recall": 0.7982326951399117,
      "f1-score": 0.8877968877968878,
      "support": 679.0
    },
    "wildfire": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "flood": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "storm": {
      "precision": 0.0,
      "recall": 0.0,
      "f1-score": 0.0,
      "support": 0.0
    },
    "air_quality": {
      "precision": 0.2254335260115607,
      "recall": 1.0,
      "f1-score": 0.36792452830188677,
      "support": 39.0
    },
    "accuracy": 0.8091922005571031,
    "macro avg": {
      "precision": 0.24508670520231216,
      "recall": 0.3596465390279823,
      "f1-score": 0.2511442832197549,
      "support": 718.0
    },
    "weighted avg": {
      "precision": 0.9579274477917142,
      "recall": 0.8091922005571031,
      "f1-score": 0.8595586955680506,
      "support": 718.0
    }
  },
  "confusion_matrix": [
    [
      542,
      3,
      0,
      0,
      134
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      39
    ]
  ],
  "class_order": [
    "normal",
    "wildfire",
    "flood",
    "storm",
    "air_quality"
  ],
  "true_share": {
    "normal": 0.9456824512534819,
    "wildfire": 0.0,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.054317548746518104
  },
  "predicted_share": {
    "normal": 0.754874651810585,
    "wildfire": 0.004178272980501393,
    "flood": 0.0,
    "storm": 0.0,
    "air_quality": 0.24094707520891365
  },
  "majority_normal_accuracy": 0.9456824512534819,
  "overlapping_head_prediction_hours": 0
}
```

## Current deployable India national-B model

These are three separate +6h measured-threshold classifiers. Rare positives make accuracy alone misleading; positive recall is included. They have no trained flood/storm/wildfire/air-quality hazard heads.

| Target | Accuracy | Binary macro-F1 | Positive recall | Positive test hours |
| --- | ---: | ---: | ---: | ---: |
| high_wind_measurement_at_6h | 0.999888 | 0.499972 | 0.000000 | 2.0 |
| hot_measurement_at_6h | 0.996345 | 0.499085 | 0.000000 | 61.0 |
| near_saturation_measurement_at_6h | 0.943579 | 0.696785 | 0.288175 | 1277.0 |

## Complete model inventory (current tree and recovered archive)

| Weight path / SHA-256 prefix | Objective / width | Status |
| --- | --- | --- |
| data/india_sensor/models/himalaya_holdout_high_wind_measurement_at_6h_A.ubj / d17854f65778 | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_high_wind_measurement_at_6h_B.ubj / d7b9ad739943 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj / 184a3cb6a3a1 | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_high_wind_measurement_at_6h_D_peninsula_proxy.ubj / d16581589440 | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_high_wind_measurement_at_6h_D_western_arid_proxy.ubj / af5b220fe2fd | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_A.ubj / 2a45a4e1582e | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_B.ubj / 3fe9acf65792 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_D_northeast_proxy.ubj / 9855dcb9007e | binary:logistic / 55 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_D_northern_plains_proxy.ubj / 3dd4873c1f14 | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_D_peninsula_proxy.ubj / 5499cafd37f2 | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_hot_measurement_at_6h_D_western_arid_proxy.ubj / 23298d50612e | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_A.ubj / ea9c2cb7ca24 | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_B.ubj / 75275fd2ada4 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_D_northeast_proxy.ubj / a8fd7532daf6 | binary:logistic / 55 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj / 873484edb1c0 | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj / 559b063cc8ec | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/models/himalaya_holdout_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj / b11a3520da63 | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/models/national_high_wind_measurement_at_6h_A.ubj / 29b8e723e5c0 | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_high_wind_measurement_at_6h_B.ubj / 4d19f2f45305 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj / d40587efa432 | binary:logistic / 70 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_high_wind_measurement_at_6h_D_peninsula_proxy.ubj / 87fff969434b | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_high_wind_measurement_at_6h_D_western_arid_proxy.ubj / b4703da6b342 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_hot_measurement_at_6h_A.ubj / 25049a6165c4 | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_hot_measurement_at_6h_B.ubj / 960f5154711c | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_hot_measurement_at_6h_D_mountain_proxy.ubj / eea88cf3f797 | binary:logistic / 55 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_hot_measurement_at_6h_D_northeast_proxy.ubj / 9d199b374e04 | binary:logistic / 55 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_hot_measurement_at_6h_D_northern_plains_proxy.ubj / ee1ae6faacbb | binary:logistic / 70 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_hot_measurement_at_6h_D_peninsula_proxy.ubj / 814efd3a72ab | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_hot_measurement_at_6h_D_western_arid_proxy.ubj / d9dd2c82c9ec | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_near_saturation_measurement_at_6h_A.ubj / 3ca03ff07a3b | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_near_saturation_measurement_at_6h_B.ubj / e37711da39a4 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_near_saturation_measurement_at_6h_D_mountain_proxy.ubj / ae7a2f3f4d7b | binary:logistic / 55 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_near_saturation_measurement_at_6h_D_northeast_proxy.ubj / ccafe358860b | binary:logistic / 55 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj / 8366d6a10366 | binary:logistic / 70 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj / d58f78a9608b | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/models/national_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj / c74b5bf37eb5 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_A.ubj / 94e28d7e770a | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_B.ubj / e35e06968bc2 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj / a34ef9c809bf | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_D_peninsula_proxy.ubj / d16581589440 | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_high_wind_measurement_at_6h_D_western_arid_proxy.ubj / af5b220fe2fd | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_A.ubj / 2294876b8438 | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_B.ubj / 9489f20434c0 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_northeast_proxy.ubj / 83e749fa30aa | binary:logistic / 55 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_northern_plains_proxy.ubj / 580d9fa66141 | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_peninsula_proxy.ubj / 4469ae38374d | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_hot_measurement_at_6h_D_western_arid_proxy.ubj / 23298d50612e | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_A.ubj / f3d24d294491 | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_B.ubj / 3f7a076acb91 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_northeast_proxy.ubj / a8fd7532daf6 | binary:logistic / 55 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj / bd582fbc409e | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj / 955068f72b76 | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_holdout_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj / e2a93ca07f17 | binary:logistic / 72 | freshly_evaluated: cross_region_transfer_no_native_routed_test_rows; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_only_hot_measurement_at_6h_A.ubj / 616b4d362aca | binary:logistic / 30 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_only_hot_measurement_at_6h_B.ubj / d77d5b318696 | binary:logistic / 33 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_only_hot_measurement_at_6h_D_mountain_proxy.ubj / d77d5b318696 | binary:logistic / 33 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_only_near_saturation_measurement_at_6h_A.ubj / 29abc2dff1b1 | binary:logistic / 30 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_only_near_saturation_measurement_at_6h_B.ubj / dffc1d13d23e | binary:logistic / 33 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/himalaya_only_near_saturation_measurement_at_6h_D_mountain_proxy.ubj / dffc1d13d23e | binary:logistic / 33 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_high_wind_measurement_at_6h_A.ubj / fe846e421e5e | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_high_wind_measurement_at_6h_B.ubj / 4d19f2f45305 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj / d40587efa432 | binary:logistic / 70 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_peninsula_proxy.ubj / 87fff969434b | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_high_wind_measurement_at_6h_D_western_arid_proxy.ubj / b4703da6b342 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_hot_measurement_at_6h_A.ubj / bfa552757062 | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_hot_measurement_at_6h_B.ubj / 960f5154711c | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_hot_measurement_at_6h_D_mountain_proxy.ubj / eea88cf3f797 | binary:logistic / 55 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_hot_measurement_at_6h_D_northeast_proxy.ubj / 9d199b374e04 | binary:logistic / 55 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_hot_measurement_at_6h_D_northern_plains_proxy.ubj / ee1ae6faacbb | binary:logistic / 70 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_hot_measurement_at_6h_D_peninsula_proxy.ubj / 97d45e968732 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_hot_measurement_at_6h_D_western_arid_proxy.ubj / 3b030fc9f6f4 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_A.ubj / 8a8e69b503c2 | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_B.ubj / 97856ffd10cf | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_mountain_proxy.ubj / ae7a2f3f4d7b | binary:logistic / 55 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_northeast_proxy.ubj / 204401b1938a | binary:logistic / 55 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj / bd69473d9cf4 | binary:logistic / 70 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj / 697b0874bfbc | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/national_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj / 08c6a9b3d46e | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_A.ubj / 3ca28a08b53f | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_B.ubj / 3789fdc33f00 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_D_northern_plains_proxy.ubj / d79b51b22ffa | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_D_peninsula_proxy.ubj / bb4d1ccb046d | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_high_wind_measurement_at_6h_D_western_arid_proxy.ubj / c5f818cdd18f | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_hot_measurement_at_6h_A.ubj / b4e2fbee7921 | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_hot_measurement_at_6h_B.ubj / 0fe85ca6caac | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_mountain_proxy.ubj / da2a1fafd715 | binary:logistic / 55 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_northeast_proxy.ubj / 0559e7a01118 | binary:logistic / 70 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_northern_plains_proxy.ubj / e44c38237232 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_peninsula_proxy.ubj / 004b1c2ecb23 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_hot_measurement_at_6h_D_western_arid_proxy.ubj / c3fc338e0433 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_A.ubj / e2cf8adf3a9b | binary:logistic / 69 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_B.ubj / 5de985896bb7 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_mountain_proxy.ubj / 014f64766ebd | binary:logistic / 55 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_northeast_proxy.ubj / 13ca3dd4ab27 | binary:logistic / 70 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_northern_plains_proxy.ubj / 99479b138ce7 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_peninsula_proxy.ubj / a47328f1772e | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| data/india_sensor/offline/models/temporal_near_saturation_measurement_at_6h_D_western_arid_proxy.ubj / 40837191dfff | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| ml/models/india_cpcb_5sensor_6h/esp32_student/pm10_ug_m3.ubj / 60c97d9d7bb0 | reg:squarederror / 5 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_cpcb_5sensor_6h/esp32_student/pm25_ug_m3.ubj / ec1c8435e849 | reg:squarederror / 5 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_cpcb_5sensor_6h/esp32_student/relative_humidity_pct.ubj / 8369d71905dc | reg:squarederror / 5 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_cpcb_5sensor_6h/esp32_student/temperature_c.ubj / 5a8cb6ae705b | reg:squarederror / 5 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_cpcb_5sensor_6h/esp32_student/wind_speed_mps.ubj / e1f767ca62e9 | reg:squarederror / 5 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_cpcb_5sensor_6h/teacher/pm10_ug_m3.ubj / aced3f2bc9f6 | reg:squarederror / 55 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_cpcb_5sensor_6h/teacher/pm25_ug_m3.ubj / ffb8bf884c43 | reg:squarederror / 55 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_cpcb_5sensor_6h/teacher/relative_humidity_pct.ubj / d01b29032604 | reg:squarederror / 55 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_cpcb_5sensor_6h/teacher/temperature_c.ubj / 2a14c4cb2015 | reg:squarederror / 55 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_cpcb_5sensor_6h/teacher/wind_speed_mps.ubj / 081085b0f315 | reg:squarederror / 55 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_cpcb_pm_6h/esp32_student/pm10_ug_m3.ubj / ffece5bdc72a | reg:squarederror / 2 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_cpcb_pm_6h/esp32_student/pm25_ug_m3.ubj / 53f3ce35fb93 | reg:squarederror / 2 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_cpcb_pm_6h/teacher/pm10_ug_m3.ubj / 16088c1ce6bf | reg:squarederror / 22 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_cpcb_pm_6h/teacher/pm25_ug_m3.ubj / 6f20d0cb1f4a | reg:squarederror / 22 | freshly_evaluated: modeled_numeric_proxy_not_hazard_accuracy; native_holdout; aliases share results by weight hash |
| ml/models/india_sensor_v1/national_high_wind_measurement_at_6h_B.ubj / 4d19f2f45305 | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| ml/models/india_sensor_v1/national_hot_measurement_at_6h_B.ubj / 960f5154711c | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| ml/models/india_sensor_v1/national_near_saturation_measurement_at_6h_B.ubj / 97856ffd10cf | binary:logistic / 72 | freshly_evaluated: native_holdout_future_measured_threshold; aliases share results by weight hash |
| ml/models/uci_beijing_5sensor_6h/esp32_student/pm10_ug_m3.ubj / 2a0e0ffcb012 | reg:squarederror / 5 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_5sensor_6h/esp32_student/pm25_ug_m3.ubj / ebb87cf19c64 | reg:squarederror / 5 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_5sensor_6h/esp32_student/relative_humidity_pct.ubj / 8e10c208ff63 | reg:squarederror / 5 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_5sensor_6h/esp32_student/temperature_c.ubj / c4edc7e79df5 | reg:squarederror / 5 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_5sensor_6h/esp32_student/wind_speed_mps.ubj / a1a738bad068 | reg:squarederror / 5 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_5sensor_6h/teacher/pm10_ug_m3.ubj / 89b6853359ea | reg:squarederror / 55 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_5sensor_6h/teacher/pm25_ug_m3.ubj / 8cb884fdebe9 | reg:squarederror / 55 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_5sensor_6h/teacher/relative_humidity_pct.ubj / ebd7cbcb70df | reg:squarederror / 55 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_5sensor_6h/teacher/temperature_c.ubj / d01f001ede25 | reg:squarederror / 55 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_5sensor_6h/teacher/wind_speed_mps.ubj / fcecb79aa956 | reg:squarederror / 55 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_6h/esp32_student/pm10_ug_m3.ubj / 8f4f47573eb9 | reg:squarederror / 6 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_6h/esp32_student/pm25_ug_m3.ubj / d580a740e330 | reg:squarederror / 6 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_6h/esp32_student/pressure_hpa.ubj / c84f2a44e013 | reg:squarederror / 6 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_6h/esp32_student/relative_humidity_pct.ubj / 7b52f9296f4b | reg:squarederror / 6 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_6h/esp32_student/temperature_c.ubj / 24d42c14608c | reg:squarederror / 6 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_6h/esp32_student/wind_speed_mps.ubj / 626ffa2c7490 | reg:squarederror / 6 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_6h/teacher/pm10_ug_m3.ubj / 844784e48384 | reg:squarederror / 66 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_6h/teacher/pm25_ug_m3.ubj / 22799877b03a | reg:squarederror / 66 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_6h/teacher/pressure_hpa.ubj / d591b2a93796 | reg:squarederror / 66 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_6h/teacher/relative_humidity_pct.ubj / 5c93720bb573 | reg:squarederror / 66 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_6h/teacher/temperature_c.ubj / d98a2709286c | reg:squarederror / 66 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_6h/teacher/wind_speed_mps.ubj / 28454443562c | reg:squarederror / 66 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_event_rules_6sensor/esp32_student/cold_frontal_passage.ubj / b40911b258d0 | binary:logistic / 17 | recorded_metrics_only: Original native raw data is cloud-only; saved confusion counts reproduced, weights hash-verified; no fresh heldout accuracy claim |
| ml/models/uci_beijing_event_rules_6sensor/esp32_student/dust_storm_haboob.ubj / 8d425aadcc54 | binary:logistic / 17 | recorded_metrics_only: Original native raw data is cloud-only; saved confusion counts reproduced, weights hash-verified; no fresh heldout accuracy claim |
| ml/models/uci_beijing_event_rules_6sensor/esp32_student/extreme_heatwave.ubj / 932eac91129c | binary:logistic / 17 | recorded_metrics_only: Original native raw data is cloud-only; saved confusion counts reproduced, weights hash-verified; no fresh heldout accuracy claim |
| ml/models/uci_beijing_event_rules_6sensor/esp32_student/freezing_rain_sleet.ubj / 392206f2d605 | binary:logistic / 17 | recorded_metrics_only: Original native raw data is cloud-only; saved confusion counts reproduced, weights hash-verified; no fresh heldout accuracy claim |
| ml/models/uci_beijing_event_rules_6sensor/esp32_student/ground_frost.ubj / 2b2a8c7db210 | binary:logistic / 17 | recorded_metrics_only: Original native raw data is cloud-only; saved confusion counts reproduced, weights hash-verified; no fresh heldout accuracy claim |
| ml/models/uci_beijing_event_rules_6sensor/esp32_student/light_moderate_rain.ubj / 16b5edbf603a | binary:logistic / 17 | recorded_metrics_only: Original native raw data is cloud-only; saved confusion counts reproduced, weights hash-verified; no fresh heldout accuracy claim |
| ml/models/uci_beijing_event_rules_6sensor/esp32_student/radiation_fog.ubj / cacef570983f | binary:logistic / 17 | recorded_metrics_only: Original native raw data is cloud-only; saved confusion counts reproduced, weights hash-verified; no fresh heldout accuracy claim |
| ml/models/uci_beijing_event_rules_6sensor/esp32_student/smog_inversion_trap.ubj / 03a79e3fb17d | binary:logistic / 17 | recorded_metrics_only: Original native raw data is cloud-only; saved confusion counts reproduced, weights hash-verified; no fresh heldout accuracy claim |
| ml/models/uci_beijing_event_rules_6sensor/esp32_student/smoke_plume.ubj / fc0d33de6002 | binary:logistic / 17 | recorded_metrics_only: Original native raw data is cloud-only; saved confusion counts reproduced, weights hash-verified; no fresh heldout accuracy claim |
| ml/models/uci_beijing_event_rules_6sensor/esp32_student/wildfire_evaporative_risk.ubj / 3bbc99014a65 | binary:logistic / 17 | recorded_metrics_only: Original native raw data is cloud-only; saved confusion counts reproduced, weights hash-verified; no fresh heldout accuracy claim |
| ml/models/uci_beijing_pm_6h/esp32_student/pm10_ug_m3.ubj / bdc9ab9e769e | reg:squarederror / 2 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_pm_6h/esp32_student/pm25_ug_m3.ubj / 940aee40cb30 | reg:squarederror / 2 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_pm_6h/teacher/pm10_ug_m3.ubj / 342a9e3f3ed1 | reg:squarederror / 22 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| ml/models/uci_beijing_pm_6h/teacher/pm25_ug_m3.ubj / 464776a549f3 | reg:squarederror / 22 | freshly_evaluated: RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED; modeled_numeric_proxy_not_hazard_accuracy; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model/xgboost_wildfire.json / 42974ac3e80c | binary:logistic / 14 | freshly_evaluated: native_random_holdout; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model/xgboost_flood.json / ad1dea40340c | binary:logistic / 14 | freshly_evaluated: native_random_holdout; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model/xgboost_storm.json / 0ca90af2c501 | binary:logistic / 14 | freshly_evaluated: native_random_holdout; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model/xgboost_air_quality.json / 6552dcc9722d | binary:logistic / 14 | freshly_evaluated: native_random_holdout; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_baseline/xgboost_wildfire.json / 959d5411ea02 | binary:logistic / 14 | freshly_evaluated: native_random_holdout; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_baseline/xgboost_flood.json / 9f913a36c777 | binary:logistic / 14 | freshly_evaluated: native_random_holdout; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_baseline/xgboost_storm.json / c0350cfa6018 | binary:logistic / 14 | freshly_evaluated: native_random_holdout; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_baseline/xgboost_air_quality.json / c68a973f71c7 | binary:logistic / 14 | freshly_evaluated: native_random_holdout; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26/xgboost_wildfire.json / c9aa25290dca | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26/xgboost_flood.json / b53665769674 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26/xgboost_storm.json / 82383c99bc54 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26/xgboost_air_quality.json / bb7828dd7990 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_baseline_repro/xgboost_wildfire.json / 5368680b2bca | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_baseline_repro/xgboost_flood.json / a69ad5665fd6 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_baseline_repro/xgboost_storm.json / f04f47d201fb | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_baseline_repro/xgboost_air_quality.json / 59a913ac673d | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_distilled/xgboost_wildfire.json / 5368680b2bca | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_distilled/xgboost_flood.json / a69ad5665fd6 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_distilled/xgboost_storm.json / f04f47d201fb | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_distilled/xgboost_air_quality.json / e6ce11866c84 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_distilled_context/xgboost_wildfire.json / 5368680b2bca | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_distilled_context/xgboost_flood.json / a69ad5665fd6 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_distilled_context/xgboost_storm.json / f04f47d201fb | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_distilled_context/xgboost_air_quality.json / 9e6738049a5d | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_geo_temporal/xgboost_wildfire.json / 5368680b2bca | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_geo_temporal/xgboost_flood.json / a69ad5665fd6 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_geo_temporal/xgboost_storm.json / f04f47d201fb | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_geo_temporal/xgboost_air_quality.json / 59a913ac673d | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_masked_distilled_edge/xgboost_wildfire.json / c340797ecf93 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_masked_distilled_edge/xgboost_flood.json / c85cc8b22a81 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_masked_distilled_edge/xgboost_storm.json / d554e0dbd995 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_masked_distilled_edge/xgboost_air_quality.json / 075eb9f2c762 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_verified_storm_candidate/xgboost_wildfire.json / 5368680b2bca | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_verified_storm_candidate/xgboost_flood.json / a69ad5665fd6 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_verified_storm_candidate/xgboost_storm.json / 57458c357e5f | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_verified_storm_candidate/xgboost_air_quality.json / 9e6738049a5d | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_pilot/xgboost_wildfire.json / 911ac26e69bc | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_pilot/xgboost_flood.json / 71f057954572 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_pilot/xgboost_storm.json / 45a0f5f5c7f8 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_pilot/xgboost_air_quality.json / d0fb62b9ec06 | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_storm_verified/xgboost_storm.json / 57458c357e5f | binary:logistic / 14 | freshly_evaluated: weatherHistory_transfer_diagnostic_not_original_test; aliases share results by weight hash |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_masked_verified_teacher_context/xgboost_air_quality.json / ddeac514c7d3 | binary:logistic / 24 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_masked_verified_teacher_context/xgboost_flood.json / 1a7712ca6ff6 | binary:logistic / 24 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_masked_verified_teacher_context/xgboost_storm.json / 0f4933fa7d76 | binary:logistic / 24 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_masked_verified_teacher_context/xgboost_wildfire.json / 6bc5a3d01943 | binary:logistic / 24 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_offline/xgboost_air_quality.json / b9f4e7903dd2 | binary:logistic / 19 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_offline/xgboost_flood.json / 07f4d6326edd | binary:logistic / 19 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_offline/xgboost_storm.json / f82a42c20ad8 | binary:logistic / 19 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_offline/xgboost_wildfire.json / ca8a5787a025 | binary:logistic / 19 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_teacher_context/xgboost_air_quality.json / 0a0f6a7a3fec | binary:logistic / 24 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_teacher_context/xgboost_flood.json / ba2b08332ceb | binary:logistic / 24 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_teacher_context/xgboost_storm.json / d9d7814c68e6 | binary:logistic / 24 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_26_teacher_context/xgboost_wildfire.json / f14e65e6a964 | binary:logistic / 24 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_aq_teacher_openaq_2cities_2020/next_day_pm25.json / 802b2ad01ada | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_aq_teacher_openaq_2cities_geo_temporal/next_day_pm25.json / 5d9242f46072 | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_aq_teacher_openaq_4cities_geo_temporal/next_day_pm25.json / 1a11a7104397 | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_aq_teacher_openaq_5cities_geo_temporal/next_day_pm25.json / d6a5685f8ca1 | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_aq_teacher_openaq_delhi_2020/next_day_pm25.json / 5d9242f46072 | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_aq_teacher_openaq_mumbai_2020/next_day_pm25.json / 7d322f421106 | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_flood_weather_verified_56/xgboost_flood.json / fea718e6ed54 | binary:logistic / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_storm_weather_verified_1982_2020/xgboost_storm.json / c7351982dca7 | binary:logistic / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_storm_weather_verified_56/xgboost_storm.json / 304f14df7f25 | binary:logistic / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher/next_day_humidity.json / f3ad57742102 | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher/next_day_precipitation_mm.json / 22823d21c9c9 | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher/next_day_pressure_mb.json / bbdf64fddc07 | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher/next_day_temperature_celsius.json / 570409bfe4d1 | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher/next_day_wind_kph.json / b0bf635bd54a | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56/next_day_humidity.json / ced287b827fe | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56/next_day_precipitation_mm.json / 7bd92847d6be | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56/next_day_pressure_mb.json / b41c146928d8 | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56/next_day_temperature_celsius.json / fb24b11ee18a | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56/next_day_wind_kph.json / 0c59a5753a1b | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56_geo_temporal/next_day_humidity.json / df0667b6c4ed | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56_geo_temporal/next_day_precipitation_mm.json / 4d9a2774293a | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56_geo_temporal/next_day_pressure_mb.json / fbe504ceb62b | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56_geo_temporal/next_day_temperature_celsius.json / b041513fa2bd | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56_geo_temporal/next_day_wind_kph.json / e133f336918d | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56_geo_temporal_repro/next_day_humidity.json / df0667b6c4ed | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56_geo_temporal_repro/next_day_precipitation_mm.json / 4d9a2774293a | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56_geo_temporal_repro/next_day_pressure_mb.json / fbe504ceb62b | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56_geo_temporal_repro/next_day_temperature_celsius.json / b041513fa2bd | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_india_weather_teacher_56_geo_temporal_repro/next_day_wind_kph.json / e133f336918d | reg:squarederror / 7 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_v2_baseline/xgboost_air_quality.json / e846c97c6ff1 | binary:logistic / 22 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_v2_baseline/xgboost_flood.json / 1e31992340c0 | binary:logistic / 22 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_v2_baseline/xgboost_storm.json / f88ec74cd818 | binary:logistic / 22 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |
| git:bd862890dfce48f810fc9efc02748a407b6a3b37:ml/model_v2_baseline/xgboost_wildfire.json / d456508ba308 | binary:logistic / 22 | incompatible_archived_contract: Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed |

## Errors and unavailable tests


Current models do not accept the archived 14-feature matrix. Regression models have continuous targets; current event models have twelve multilabel slots (two untrained); India classifiers predict three measured thresholds at +6h. No five-class label mapping is invented for them. Historical Indian 14-feature models were tested on weatherHistory only as transfer diagnostics, because their original split differs.

Beijing observations.csv and source.zip were iCloud-only placeholders during this run. Their original native metrics are explicitly marked RECORDED_ONLY and were not freshly reproduced. Beijing regression weights were freshly evaluated against modeled Mandi six-hour outcomes. India regional experts with zero native routed test rows were tested separately on the full geographic holdout as cross-region transfer diagnostics. Rankings do not mix these evidence categories.

Full machine-readable results and the console transcript are saved under the ignored results/model_tests directory. Source/model hashes allow identifying precisely what was evaluated. No model was selected or tuned using these new proxy scores.
