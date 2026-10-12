# India-only six-channel Mandi forecast test

Executed 2026-10-12T04:41:19.247909+00:00. No Chinese data or weights were used.

**Evidence:** retrospective Open-Meteo/ECMWF/CAMS modeled values at Mandi; not measured six-channel field accuracy.
The weather and air variables use different grids. Global CAMS is approximately 45 km and 3-hourly underneath the hourly API output.
Grid surface pressure is not verified station pressure. No operational hazard accuracy or lead time is established.

Source dates: 2024-01-01 through 2026-10-10. Complete modeled rows: 24,336.

| Split | Eligible rows | First issue UTC | Last issue UTC |
| --- | ---: | --- | --- |
| train | 22602 | 2024-01-02T00:00:00+00:00 | 2026-07-31T17:00:00+00:00 |
| validation | 738 | 2026-08-01T00:00:00+00:00 | 2026-08-31T17:00:00+00:00 |
| future_test | 954 | 2026-09-01T00:00:00+00:00 | 2026-10-10T17:00:00+00:00 |
| fresh_future_test | 90 | 2026-10-07T00:00:00+00:00 | 2026-10-10T17:00:00+00:00 |

## Six-hour future-test MAE — lower is better

| Target | Persistence | Compact student | History teacher | Temporal ridge | Validation-selected head | Selected MAE |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| temperature_c | 4.8331 | 3.7926 | 1.7724 | 1.2724 | teacher | 1.7724 |
| relative_humidity_pct | 18.9686 | 14.1338 | 7.8542 | 7.0027 | teacher | 7.8542 |
| pressure_hpa | 1.6804 | 1.4844 | 1.0429 | 0.9467 | temporal_ridge | 0.9467 |
| pm25_ug_m3 | 10.1762 | 8.4077 | 6.9577 | 7.0209 | teacher | 6.9577 |
| pm10_ug_m3 | 12.6751 | 10.5534 | 9.3210 | 9.2795 | teacher | 9.3210 |
| wind_speed_mps | 0.5945 | 0.4642 | 0.3215 | 0.3415 | teacher | 0.3215 |

Selections and blend weights use validation only. Persistence may win; no forecast is automatically promoted to ESP32.

## Existing India-trained research models

CPCB profiles are reduced-input experiments: five channels or particulate-only. Neither tests station pressure.

| Profile | Kind | Target | Split | Rows | MAE | Persistence MAE |
| --- | --- | --- | --- | ---: | ---: | ---: |
| india_cpcb_5sensor_6h | teacher | temperature_c | Mandi_modeled_future_test | 954 | 2.1605 | 4.8331 |
| india_cpcb_5sensor_6h | teacher | temperature_c | future_test | 3592 | 1.9817 | 5.1476 |
| india_cpcb_5sensor_6h | teacher | temperature_c | geographic_test | 1705 | 1.3091 | 1.7272 |
| india_cpcb_5sensor_6h | student | temperature_c | Mandi_modeled_future_test | 954 | 4.4069 | 4.8331 |
| india_cpcb_5sensor_6h | student | temperature_c | future_test | 3592 | 4.3360 | 5.1476 |
| india_cpcb_5sensor_6h | student | temperature_c | geographic_test | 1705 | 1.6722 | 1.7272 |
| india_cpcb_5sensor_6h | teacher | relative_humidity_pct | Mandi_modeled_future_test | 954 | 9.1913 | 18.9686 |
| india_cpcb_5sensor_6h | teacher | relative_humidity_pct | future_test | 3592 | 7.9380 | 16.5203 |
| india_cpcb_5sensor_6h | teacher | relative_humidity_pct | geographic_test | 1597 | 10.0177 | 14.0484 |
| india_cpcb_5sensor_6h | student | relative_humidity_pct | Mandi_modeled_future_test | 954 | 15.6409 | 18.9686 |
| india_cpcb_5sensor_6h | student | relative_humidity_pct | future_test | 3592 | 14.4333 | 16.5203 |
| india_cpcb_5sensor_6h | student | relative_humidity_pct | geographic_test | 1597 | 13.1858 | 14.0484 |
| india_cpcb_5sensor_6h | teacher | pm25_ug_m3 | Mandi_modeled_future_test | 954 | 10.3457 | 10.1762 |
| india_cpcb_5sensor_6h | teacher | pm25_ug_m3 | future_test | 3468 | 31.1475 | 56.4357 |
| india_cpcb_5sensor_6h | teacher | pm25_ug_m3 | geographic_test | 1689 | 35.3524 | 46.6596 |
| india_cpcb_5sensor_6h | student | pm25_ug_m3 | Mandi_modeled_future_test | 954 | 9.8057 | 10.1762 |
| india_cpcb_5sensor_6h | student | pm25_ug_m3 | future_test | 3468 | 45.6098 | 56.4357 |
| india_cpcb_5sensor_6h | student | pm25_ug_m3 | geographic_test | 1689 | 40.5030 | 46.6596 |
| india_cpcb_5sensor_6h | teacher | pm10_ug_m3 | Mandi_modeled_future_test | 954 | 20.8397 | 12.6751 |
| india_cpcb_5sensor_6h | teacher | pm10_ug_m3 | future_test | 3459 | 61.6146 | 109.1259 |
| india_cpcb_5sensor_6h | teacher | pm10_ug_m3 | geographic_test | 1684 | 58.7451 | 80.7685 |
| india_cpcb_5sensor_6h | student | pm10_ug_m3 | Mandi_modeled_future_test | 954 | 17.4339 | 12.6751 |
| india_cpcb_5sensor_6h | student | pm10_ug_m3 | future_test | 3459 | 87.1932 | 109.1259 |
| india_cpcb_5sensor_6h | student | pm10_ug_m3 | geographic_test | 1684 | 69.0722 | 80.7685 |
| india_cpcb_5sensor_6h | teacher | wind_speed_mps | Mandi_modeled_future_test | 954 | 0.3741 | 0.5945 |
| india_cpcb_5sensor_6h | teacher | wind_speed_mps | future_test | 3591 | 0.2954 | 0.4185 |
| india_cpcb_5sensor_6h | teacher | wind_speed_mps | geographic_test | 1705 | 0.5801 | 0.8345 |
| india_cpcb_5sensor_6h | student | wind_speed_mps | Mandi_modeled_future_test | 954 | 0.4752 | 0.5945 |
| india_cpcb_5sensor_6h | student | wind_speed_mps | future_test | 3591 | 0.3490 | 0.4185 |
| india_cpcb_5sensor_6h | student | wind_speed_mps | geographic_test | 1705 | 0.6646 | 0.8345 |
| india_cpcb_pm_6h | teacher | pm25_ug_m3 | Mandi_modeled_future_test | 954 | 9.5452 | 10.1762 |
| india_cpcb_pm_6h | teacher | pm25_ug_m3 | future_test | 10157 | 27.9861 | 36.8508 |
| india_cpcb_pm_6h | teacher | pm25_ug_m3 | geographic_test | 1897 | 39.0144 | 48.8202 |
| india_cpcb_pm_6h | student | pm25_ug_m3 | Mandi_modeled_future_test | 954 | 10.1762 | 10.1762 |
| india_cpcb_pm_6h | student | pm25_ug_m3 | future_test | 10157 | 36.8508 | 36.8508 |
| india_cpcb_pm_6h | student | pm25_ug_m3 | geographic_test | 1897 | 48.8202 | 48.8202 |
| india_cpcb_pm_6h | teacher | pm10_ug_m3 | Mandi_modeled_future_test | 954 | 13.9090 | 12.6751 |
| india_cpcb_pm_6h | teacher | pm10_ug_m3 | future_test | 10159 | 50.1999 | 66.7302 |
| india_cpcb_pm_6h | teacher | pm10_ug_m3 | geographic_test | 1891 | 62.0317 | 82.5453 |
| india_cpcb_pm_6h | student | pm10_ug_m3 | Mandi_modeled_future_test | 954 | 13.5715 | 12.6751 |
| india_cpcb_pm_6h | student | pm10_ug_m3 | future_test | 10159 | 64.9717 | 66.7302 |
| india_cpcb_pm_6h | student | pm10_ug_m3 | geographic_test | 1891 | 79.6957 | 82.5453 |

The original Indian secondary source assumes local timezone and excludes unverified pressure. Its completed-hour means differ from the modeled instantaneous Mandi values; this is a transfer diagnostic with an aggregation mismatch. Original Indian holdout replay performed: True.

## Himalayan hazard status

| Target | Status |
| --- | --- |
| cloudburst | NOT_EVALUABLE_NO_ADMITTED_EVENT_LABELS |
| storm | NOT_EVALUABLE_NO_ADMITTED_EVENT_LABELS |
| flash_flood | NOT_EVALUABLE_NO_ADMITTED_EVENT_LABELS |
| landslide | NOT_EVALUABLE_NO_ADMITTED_EVENT_LABELS |
| snowstorm | NOT_EVALUABLE_NO_ADMITTED_EVENT_LABELS |

Compact heads with negative future-test R2: temperature_c, relative_humidity_pct, wind_speed_mps. They beat persistence MAE here but remain weaker than a constant test-mean reference by squared error.

## Compact C export — host parity only

```json
{
  "schema_version": "indra_hourly_forecast_v1",
  "model_country": "IN",
  "evidence_kind": "MODELED_GRID_RETROSPECTIVE",
  "hardware_execution_verified": false,
  "status": "OFFLINE_RESEARCH_ONLY",
  "input_features": [
    "temperature_c",
    "relative_humidity_pct",
    "pressure_hpa",
    "pm25_ug_m3",
    "pm10_ug_m3",
    "wind_speed_mps"
  ],
  "horizon_hours": 6,
  "heads": 6,
  "trees_per_head": 16,
  "max_depth": 3,
  "total_nodes": 1438,
  "header_bytes": 66666,
  "header_sha256": "2acb38526ca2af4f7419e276a4989aa1e8a9cf38d798a00e8cd79a6ed780ff33",
  "model_report_sha256": "1a73833635ac8a9d8c92c890214d0826bed9c9b25f14b7829379286b94774fc7",
  "parity": {
    "valid_rows": 4063,
    "invalid_rows": 18,
    "absolute_tolerance": 0.0002,
    "max_absolute_error_by_target": {
      "temperature_c": 4.9975586335904154e-08,
      "relative_humidity_pct": 4.999999703159119e-08,
      "pressure_hpa": 1.757812469804776e-06,
      "pm25_ug_m3": 2.968749868159648e-06,
      "pm10_ug_m3": 2.968749868159648e-06,
      "wind_speed_mps": 2.4166625989252566e-07
    },
    "passed": true
  }
}
```

This compiled-host check is not a physical ESP32 execution or a field-accuracy test.

These heads need admitted independent events and monitored negatives; API rainfall is not cloudburst gauge truth.

## Input, prediction and later API examples

```json
[
  {
    "input_timestamp_utc": "2026-09-01T00:00:00+00:00",
    "forecast_timestamp_utc": "2026-09-01T06:00:00+00:00",
    "input": {
      "temperature_c": 23.9,
      "relative_humidity_pct": 94.0,
      "pressure_hpa": 920.8,
      "pm25_ug_m3": 21.9,
      "pm10_ug_m3": 43.1,
      "wind_speed_mps": 0.22
    },
    "student_prediction": {
      "temperature_c": 24.590438985824584,
      "relative_humidity_pct": 86.58553504943848,
      "pressure_hpa": 920.9462369710207,
      "pm25_ug_m3": 18.556346321105956,
      "pm10_ug_m3": 40.73976550102234,
      "wind_speed_mps": 0.5770171296596527
    },
    "validation_selected_prediction": {
      "temperature_c": 27.621428394317626,
      "relative_humidity_pct": 76.36319541931152,
      "pressure_hpa": 922.1780430785177,
      "pm25_ug_m3": 19.795890474319457,
      "pm10_ug_m3": 50.74849185943604,
      "wind_speed_mps": 1.0319917511940002
    },
    "later_api_value": {
      "temperature_c": 29.600000381469727,
      "relative_humidity_pct": 66.0,
      "pressure_hpa": 923.9000244140625,
      "pm25_ug_m3": 27.799999237060547,
      "pm10_ug_m3": 54.400001525878906,
      "wind_speed_mps": 1.1799999475479126
    }
  },
  {
    "input_timestamp_utc": "2026-09-01T01:00:00+00:00",
    "forecast_timestamp_utc": "2026-09-01T07:00:00+00:00",
    "input": {
      "temperature_c": 23.6,
      "relative_humidity_pct": 94.0,
      "pressure_hpa": 921.2,
      "pm25_ug_m3": 24.7,
      "pm10_ug_m3": 48.4,
      "wind_speed_mps": 0.16
    },
    "student_prediction": {
      "temperature_c": 23.981039440631868,
      "relative_humidity_pct": 86.90411567687988,
      "pressure_hpa": 921.2840997770429,
      "pm25_ug_m3": 21.63565273284912,
      "pm10_ug_m3": 46.24429025650024,
      "wind_speed_mps": 0.5170171296596527
    },
    "validation_selected_prediction": {
      "temperature_c": 27.69278440475464,
      "relative_humidity_pct": 77.75275230407715,
      "pressure_hpa": 921.9636694931708,
      "pm25_ug_m3": 22.025533151626586,
      "pm10_ug_m3": 53.78622808456421,
      "wind_speed_mps": 0.8275404310226441
    },
    "later_api_value": {
      "temperature_c": 29.600000381469727,
      "relative_humidity_pct": 68.0,
      "pressure_hpa": 923.7999877929688,
      "pm25_ug_m3": 29.600000381469727,
      "pm10_ug_m3": 56.79999923706055,
      "wind_speed_mps": 1.659999966621399
    }
  },
  {
    "input_timestamp_utc": "2026-09-01T02:00:00+00:00",
    "forecast_timestamp_utc": "2026-09-01T08:00:00+00:00",
    "input": {
      "temperature_c": 24.1,
      "relative_humidity_pct": 97.0,
      "pressure_hpa": 922.1,
      "pm25_ug_m3": 29.3,
      "pm10_ug_m3": 59.8,
      "wind_speed_mps": 0.59
    },
    "student_prediction": {
      "temperature_c": 24.016742235422136,
      "relative_humidity_pct": 88.70283317565918,
      "pressure_hpa": 922.0637513682246,
      "pm25_ug_m3": 23.43262701034546,
      "pm10_ug_m3": 52.056674289703366,
      "wind_speed_mps": 0.7821851485967636
    },
    "validation_selected_prediction": {
      "temperature_c": 28.194808578491212,
      "relative_humidity_pct": 78.45303726196289,
      "pressure_hpa": 921.9869666962687,
      "pm25_ug_m3": 26.14709882736206,
      "pm10_ug_m3": 62.1907299041748,
      "wind_speed_mps": 1.0146620535850523
    },
    "later_api_value": {
      "temperature_c": 29.799999237060547,
      "relative_humidity_pct": 68.0,
      "pressure_hpa": 923.2999877929688,
      "pm25_ug_m3": 31.899999618530273,
      "pm10_ug_m3": 59.29999923706055,
      "wind_speed_mps": 0.8100000023841858
    }
  }
]
```

## Full numerical evidence

MAE/RMSE/R² are reported in their physical units; classification accuracy/F1 do not apply to these numeric targets.
No independent-site test is available for the Mandi grid. Some September/October dates appeared in earlier API transfer diagnostics; no new model selection uses test results. The October 7-10 subset is reported separately.

```json
{
  "config_sha256": "b1f0fd8065f8eb31a4dbf751bfba1bd214a9f17ee54247c9f61b1b1d760cf051",
  "split": {
    "train": {
      "rows": 22602,
      "first_issue_utc": "2024-01-02T00:00:00+00:00",
      "last_issue_utc": "2026-07-31T17:00:00+00:00"
    },
    "validation": {
      "rows": 738,
      "first_issue_utc": "2026-08-01T00:00:00+00:00",
      "last_issue_utc": "2026-08-31T17:00:00+00:00"
    },
    "future_test": {
      "rows": 954,
      "first_issue_utc": "2026-09-01T00:00:00+00:00",
      "last_issue_utc": "2026-10-10T17:00:00+00:00"
    },
    "fresh_future_test": {
      "rows": 90,
      "first_issue_utc": "2026-10-07T00:00:00+00:00",
      "last_issue_utc": "2026-10-10T17:00:00+00:00"
    }
  },
  "results": {
    "temperature_c": {
      "train": {
        "persistence": {
          "rows": 22602,
          "mae": 6.075856119054441,
          "rmse": 7.522274588438157,
          "r2": 0.24227619211514428,
          "persistence_mae": 6.075856119054441,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 22602,
          "mae": 1.5045476081643703,
          "rmse": 1.9979209744276507,
          "r2": 0.9465473574600797,
          "persistence_mae": 6.075856119054441,
          "mae_skill_vs_persistence": 0.7523727391361406
        },
        "teacher": {
          "rows": 22602,
          "mae": 1.236509376430114,
          "rmse": 1.6585919533162874,
          "r2": 0.9631623704602599,
          "persistence_mae": 6.075856119054441,
          "mae_skill_vs_persistence": 0.7964880418164763
        },
        "student": {
          "rows": 22602,
          "mae": 4.171819806465995,
          "rmse": 5.128279365556507,
          "r2": 0.6478271117898418,
          "persistence_mae": 6.075856119054441,
          "mae_skill_vs_persistence": 0.3133774525399333
        }
      },
      "validation": {
        "persistence": {
          "rows": 738,
          "mae": 3.138211396586927,
          "rmse": 3.828002664107903,
          "r2": -1.0397307252636825,
          "persistence_mae": 3.138211396586927,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 738,
          "mae": 1.2391723803704526,
          "rmse": 1.6868370227157852,
          "r2": 0.6039275599669129,
          "persistence_mae": 3.138211396586927,
          "mae_skill_vs_persistence": 0.6051341914957805
        },
        "teacher": {
          "rows": 738,
          "mae": 1.233380055049722,
          "rmse": 1.6087481568429347,
          "r2": 0.6397495766413236,
          "persistence_mae": 3.138211396586927,
          "mae_skill_vs_persistence": 0.6069799324573455
        },
        "student": {
          "rows": 738,
          "mae": 2.4206590833854142,
          "rmse": 2.9643673198052927,
          "r2": -0.2231857383479312,
          "persistence_mae": 3.138211396586927,
          "mae_skill_vs_persistence": 0.22865008838534973
        }
      },
      "future_test": {
        "persistence": {
          "rows": 954,
          "mae": 4.833123672533335,
          "rmse": 5.770230089607133,
          "r2": -0.9041758055211646,
          "persistence_mae": 4.833123672533335,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 954,
          "mae": 1.2724251009585383,
          "rmse": 1.659647879318134,
          "r2": 0.8424738382756479,
          "persistence_mae": 4.833123672533335,
          "mae_skill_vs_persistence": 0.7367282140554904
        },
        "teacher": {
          "rows": 954,
          "mae": 1.7723963753193368,
          "rmse": 2.3149445751174995,
          "r2": 0.6935201153740584,
          "persistence_mae": 4.833123672533335,
          "mae_skill_vs_persistence": 0.6332813941029745
        },
        "student": {
          "rows": 954,
          "mae": 3.7926353356006324,
          "rmse": 4.9037551019650465,
          "r2": -0.37523946408080344,
          "persistence_mae": 4.833123672533335,
          "mae_skill_vs_persistence": 0.2152827875781046
        }
      },
      "fresh_future_test": {
        "persistence": {
          "rows": 90,
          "mae": 5.167777745988634,
          "rmse": 5.966899392794591,
          "r2": -1.1117470723947545,
          "persistence_mae": 5.167777745988634,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 90,
          "mae": 1.1847246956744977,
          "rmse": 1.5121074864049062,
          "r2": 0.864384353920454,
          "persistence_mae": 5.167777745988634,
          "mae_skill_vs_persistence": 0.7707477461479235
        },
        "teacher": {
          "rows": 90,
          "mae": 2.0592275443673134,
          "rmse": 2.4991797485650125,
          "r2": 0.6295415918987048,
          "persistence_mae": 5.167777745988634,
          "mae_skill_vs_persistence": 0.6015255211070676
        },
        "student": {
          "rows": 90,
          "mae": 3.6945869336856743,
          "rmse": 5.040029642390525,
          "r2": -0.5066440178689307,
          "persistence_mae": 5.167777745988634,
          "mae_skill_vs_persistence": 0.2850724014682112
        }
      }
    },
    "relative_humidity_pct": {
      "train": {
        "persistence": {
          "rows": 22602,
          "mae": 19.082647553313866,
          "rmse": 23.398051373353344,
          "r2": -0.05213866740233186,
          "persistence_mae": 19.082647553313866,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 22602,
          "mae": 7.287738316654105,
          "rmse": 9.714680972361526,
          "r2": 0.8186278139624441,
          "persistence_mae": 19.082647553313866,
          "mae_skill_vs_persistence": 0.6180960584062913
        },
        "teacher": {
          "rows": 22602,
          "mae": 5.66443146948946,
          "rmse": 7.647030803984116,
          "r2": 0.8876173468861993,
          "persistence_mae": 19.082647553313866,
          "mae_skill_vs_persistence": 0.7031632296480903
        },
        "student": {
          "rows": 22602,
          "mae": 12.519530932705873,
          "rmse": 15.385145900914225,
          "r2": 0.5450990543748518,
          "persistence_mae": 19.082647553313866,
          "mae_skill_vs_persistence": 0.34393113441264866
        }
      },
      "validation": {
        "persistence": {
          "rows": 738,
          "mae": 13.59349593495935,
          "rmse": 17.829210829635397,
          "r2": -1.1152425034952809,
          "persistence_mae": 13.59349593495935,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 738,
          "mae": 6.953045559590289,
          "rmse": 9.167292552363007,
          "r2": 0.44078590970483844,
          "persistence_mae": 13.59349593495935,
          "mae_skill_vs_persistence": 0.488502031202389
        },
        "teacher": {
          "rows": 738,
          "mae": 6.424407810351349,
          "rmse": 8.29446320785606,
          "r2": 0.5422034729858178,
          "persistence_mae": 13.59349593495935,
          "mae_skill_vs_persistence": 0.5273910522289378
        },
        "student": {
          "rows": 738,
          "mae": 10.852798748266729,
          "rmse": 13.12920381726263,
          "r2": -0.1470245260505807,
          "persistence_mae": 13.59349593495935,
          "mae_skill_vs_persistence": 0.20161827390143083
        }
      },
      "future_test": {
        "persistence": {
          "rows": 954,
          "mae": 18.968553459119498,
          "rmse": 23.546688533220614,
          "r2": -0.9410949753768498,
          "persistence_mae": 18.968553459119498,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 954,
          "mae": 7.002695704368452,
          "rmse": 9.144840646238853,
          "r2": 0.7072213585687527,
          "persistence_mae": 18.968553459119498,
          "mae_skill_vs_persistence": 0.6308260553731486
        },
        "teacher": {
          "rows": 954,
          "mae": 7.854233288358452,
          "rmse": 10.382159338304081,
          "r2": 0.6226342447307058,
          "persistence_mae": 18.968553459119498,
          "mae_skill_vs_persistence": 0.5859339877821639
        },
        "student": {
          "rows": 954,
          "mae": 14.133797403870139,
          "rmse": 17.11721624348284,
          "r2": -0.025778002374465148,
          "persistence_mae": 18.968553459119498,
          "mae_skill_vs_persistence": 0.254882696546634
        }
      },
      "fresh_future_test": {
        "persistence": {
          "rows": 90,
          "mae": 21.555555555555557,
          "rmse": 26.06487632385348,
          "r2": -1.206217706318737,
          "persistence_mae": 21.555555555555557,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 90,
          "mae": 7.342887890372188,
          "rmse": 9.705034882045293,
          "r2": 0.6941339814120302,
          "persistence_mae": 21.555555555555557,
          "mae_skill_vs_persistence": 0.6593505617868574
        },
        "teacher": {
          "rows": 90,
          "mae": 8.92585039668613,
          "rmse": 11.349097073417752,
          "r2": 0.5817271745241699,
          "persistence_mae": 21.555555555555557,
          "mae_skill_vs_persistence": 0.5859141568547672
        },
        "student": {
          "rows": 90,
          "mae": 14.626060695118374,
          "rmse": 18.09341342084683,
          "r2": -0.06310960473945748,
          "persistence_mae": 21.555555555555557,
          "mae_skill_vs_persistence": 0.32147141105120947
        }
      }
    },
    "pressure_hpa": {
      "train": {
        "persistence": {
          "rows": 22602,
          "mae": 2.026820717435127,
          "rmse": 2.501766954752881,
          "r2": 0.6625810165890942,
          "persistence_mae": 2.026820717435127,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 22602,
          "mae": 0.8674349104415908,
          "rmse": 1.1180968011050887,
          "r2": 0.9326039228020973,
          "persistence_mae": 2.026820717435127,
          "mae_skill_vs_persistence": 0.572021884826942
        },
        "teacher": {
          "rows": 22602,
          "mae": 0.7131379567247317,
          "rmse": 0.9233389258502729,
          "r2": 0.9540380867419752,
          "persistence_mae": 2.026820717435127,
          "mae_skill_vs_persistence": 0.6481494635464435
        },
        "student": {
          "rows": 22602,
          "mae": 1.3631429796532102,
          "rmse": 1.7284354990804365,
          "r2": 0.8389420511101757,
          "persistence_mae": 2.026820717435127,
          "mae_skill_vs_persistence": 0.3274476780668487
        }
      },
      "validation": {
        "persistence": {
          "rows": 738,
          "mae": 1.2804877056338912,
          "rmse": 1.5327139560840326,
          "r2": -0.2619946416062875,
          "persistence_mae": 1.2804877056338912,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 738,
          "mae": 0.6481694009875891,
          "rmse": 0.8189649568263926,
          "r2": 0.6396986205140863,
          "persistence_mae": 1.2804877056338912,
          "mae_skill_vs_persistence": 0.49381052380606805
        },
        "teacher": {
          "rows": 738,
          "mae": 0.7033458840936093,
          "rmse": 0.879968650991475,
          "r2": 0.5840226456876234,
          "persistence_mae": 1.2804877056338912,
          "mae_skill_vs_persistence": 0.4507203146121378
        },
        "student": {
          "rows": 738,
          "mae": 1.0910738242275215,
          "rmse": 1.305712551679861,
          "r2": 0.08413714594661248,
          "persistence_mae": 1.2804877056338912,
          "mae_skill_vs_persistence": 0.14792323313452083
        }
      },
      "future_test": {
        "persistence": {
          "rows": 954,
          "mae": 1.6803977214565318,
          "rmse": 2.0705243293997175,
          "r2": 0.4325861219968167,
          "persistence_mae": 1.6803977214565318,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 954,
          "mae": 0.946704354898543,
          "rmse": 1.1878148192818552,
          "r2": 0.8132602572094231,
          "persistence_mae": 1.6803977214565318,
          "mae_skill_vs_persistence": 0.4366188772989049
        },
        "teacher": {
          "rows": 954,
          "mae": 1.0429262218872652,
          "rmse": 1.3271037110319128,
          "r2": 0.7668963869862576,
          "persistence_mae": 1.6803977214565318,
          "mae_skill_vs_persistence": 0.3793575124683698
        },
        "student": {
          "rows": 954,
          "mae": 1.4844258325627424,
          "rmse": 1.883154128286018,
          "r2": 0.5306346655894331,
          "persistence_mae": 1.6803977214565318,
          "mae_skill_vs_persistence": 0.1166223248172018
        }
      },
      "fresh_future_test": {
        "persistence": {
          "rows": 90,
          "mae": 1.8011073133680549,
          "rmse": 2.230368749650877,
          "r2": -0.5204436385748967,
          "persistence_mae": 1.8011073133680549,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 90,
          "mae": 0.9166847118603729,
          "rmse": 1.1982730648726605,
          "r2": 0.5611373941762114,
          "persistence_mae": 1.8011073133680549,
          "mae_skill_vs_persistence": 0.4910438122944598
        },
        "teacher": {
          "rows": 90,
          "mae": 1.057737348223255,
          "rmse": 1.3706169802064563,
          "r2": 0.4258184957008968,
          "persistence_mae": 1.8011073133680549,
          "mae_skill_vs_persistence": 0.41272941352656245
        },
        "student": {
          "rows": 90,
          "mae": 1.688598914299573,
          "rmse": 2.1677916913048763,
          "r2": -0.43632287721095353,
          "persistence_mae": 1.8011073133680549,
          "mae_skill_vs_persistence": 0.06246623853749844
        }
      }
    },
    "pm25_ug_m3": {
      "train": {
        "persistence": {
          "rows": 22602,
          "mae": 11.294717283556285,
          "rmse": 15.49231421659099,
          "r2": 0.1596833858948894,
          "persistence_mae": 11.294717283556285,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 22602,
          "mae": 6.271376851437474,
          "rmse": 8.701934143264484,
          "r2": 0.734880335819639,
          "persistence_mae": 11.294717283556285,
          "mae_skill_vs_persistence": 0.44475132099430004
        },
        "teacher": {
          "rows": 22602,
          "mae": 4.696258847162497,
          "rmse": 6.28807245333722,
          "r2": 0.8615651511491638,
          "persistence_mae": 11.294717283556285,
          "mae_skill_vs_persistence": 0.5842074901689066
        },
        "student": {
          "rows": 22602,
          "mae": 8.665299002306433,
          "rmse": 11.736267344922819,
          "r2": 0.5177521008467989,
          "persistence_mae": 11.294717283556285,
          "mae_skill_vs_persistence": 0.23280071694029558
        }
      },
      "validation": {
        "persistence": {
          "rows": 738,
          "mae": 8.439159889143657,
          "rmse": 10.69356301250892,
          "r2": -0.13062889096984054,
          "persistence_mae": 8.439159889143657,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 738,
          "mae": 6.2177500783715685,
          "rmse": 7.859762864097404,
          "r2": 0.38920693215668645,
          "persistence_mae": 8.439159889143657,
          "mae_skill_vs_persistence": 0.2632264158935731
        },
        "teacher": {
          "rows": 738,
          "mae": 5.682051399150273,
          "rmse": 7.28671327211137,
          "r2": 0.47502505794974614,
          "persistence_mae": 8.439159889143657,
          "mae_skill_vs_persistence": 0.32670414190637576
        },
        "student": {
          "rows": 738,
          "mae": 6.3763572824235535,
          "rmse": 8.291790267356065,
          "r2": 0.3202146043767635,
          "persistence_mae": 8.439159889143657,
          "mae_skill_vs_persistence": 0.24443222237959294
        }
      },
      "future_test": {
        "persistence": {
          "rows": 954,
          "mae": 10.176205457131568,
          "rmse": 12.819650067466565,
          "r2": 0.27504352848010183,
          "persistence_mae": 10.176205457131568,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 954,
          "mae": 7.020861456931086,
          "rmse": 9.23720977847021,
          "r2": 0.6236072902235088,
          "persistence_mae": 10.176205457131568,
          "mae_skill_vs_persistence": 0.3100707836032527
        },
        "teacher": {
          "rows": 954,
          "mae": 6.95767584686603,
          "rmse": 9.289235568331089,
          "r2": 0.6193555142649154,
          "persistence_mae": 10.176205457131568,
          "mae_skill_vs_persistence": 0.3162799359568714
        },
        "student": {
          "rows": 954,
          "mae": 8.407680095613502,
          "rmse": 10.798335221195885,
          "r2": 0.4856328781675311,
          "persistence_mae": 10.176205457131568,
          "mae_skill_vs_persistence": 0.17379025698411665
        }
      },
      "fresh_future_test": {
        "persistence": {
          "rows": 90,
          "mae": 10.88222232606676,
          "rmse": 13.14877271025037,
          "r2": -0.6882327465240123,
          "persistence_mae": 10.88222232606676,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 90,
          "mae": 6.404076692356008,
          "rmse": 8.199775812304374,
          "r2": 0.34345297040512957,
          "persistence_mae": 10.88222232606676,
          "mae_skill_vs_persistence": 0.4115102135879005
        },
        "teacher": {
          "rows": 90,
          "mae": 6.453386553625266,
          "rmse": 8.269008748131945,
          "r2": 0.33231935589798733,
          "persistence_mae": 10.88222232606676,
          "mae_skill_vs_persistence": 0.40697898276098177
        },
        "student": {
          "rows": 90,
          "mae": 7.748085442913903,
          "rmse": 9.250891096261116,
          "r2": 0.1643411435170702,
          "persistence_mae": 10.88222232606676,
          "mae_skill_vs_persistence": 0.288005224415007
        }
      }
    },
    "pm10_ug_m3": {
      "train": {
        "persistence": {
          "rows": 22602,
          "mae": 18.111795412591153,
          "rmse": 26.675335756254995,
          "r2": 0.2124369612157766,
          "persistence_mae": 18.111795412591153,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 22602,
          "mae": 11.285434897604725,
          "rmse": 17.98891274062062,
          "r2": 0.6418414135594803,
          "persistence_mae": 18.111795412591153,
          "mae_skill_vs_persistence": 0.37690137059746187
        },
        "teacher": {
          "rows": 22602,
          "mae": 8.566222554348585,
          "rmse": 12.95328514177144,
          "r2": 0.8142942339126324,
          "persistence_mae": 18.111795412591153,
          "mae_skill_vs_persistence": 0.5270362568034848
        },
        "student": {
          "rows": 22602,
          "mae": 14.80548947102667,
          "rmse": 22.405815822120807,
          "r2": 0.44436824213442816,
          "persistence_mae": 18.111795412591153,
          "mae_skill_vs_persistence": 0.1825498724033714
        }
      },
      "validation": {
        "persistence": {
          "rows": 738,
          "mae": 10.288211386248994,
          "rmse": 13.04834504173575,
          "r2": 0.10993069712791503,
          "persistence_mae": 10.288211386248994,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 738,
          "mae": 8.155404607033871,
          "rmse": 10.352140690551341,
          "r2": 0.4397610625503118,
          "persistence_mae": 10.288211386248994,
          "mae_skill_vs_persistence": 0.20730588623653157
        },
        "teacher": {
          "rows": 738,
          "mae": 7.487447029250727,
          "rmse": 9.643766763007203,
          "r2": 0.5138096271943072,
          "persistence_mae": 10.288211386248994,
          "mae_skill_vs_persistence": 0.2722304443259894
        },
        "student": {
          "rows": 738,
          "mae": 8.329084361061897,
          "rmse": 10.454440405609521,
          "r2": 0.4286338058803342,
          "persistence_mae": 10.288211386248994,
          "mae_skill_vs_persistence": 0.19042445296231225
        }
      },
      "future_test": {
        "persistence": {
          "rows": 954,
          "mae": 12.675052378912392,
          "rmse": 15.937590462737825,
          "r2": 0.3270722270068033,
          "persistence_mae": 12.675052378912392,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 954,
          "mae": 9.279459337783694,
          "rmse": 12.153168445709923,
          "r2": 0.6087069251091308,
          "persistence_mae": 12.675052378912392,
          "mae_skill_vs_persistence": 0.26789577980584756
        },
        "teacher": {
          "rows": 954,
          "mae": 9.32101182430998,
          "rmse": 12.051406996172854,
          "r2": 0.6152322761637998,
          "persistence_mae": 12.675052378912392,
          "mae_skill_vs_persistence": 0.26461749066872187
        },
        "student": {
          "rows": 954,
          "mae": 10.55336964672404,
          "rmse": 13.469497062190204,
          "r2": 0.5193533863494878,
          "persistence_mae": 12.675052378912392,
          "mae_skill_vs_persistence": 0.16739045084485937
        }
      },
      "fresh_future_test": {
        "persistence": {
          "rows": 90,
          "mae": 17.411110975477428,
          "rmse": 20.259049910918883,
          "r2": -0.9020818777756408,
          "persistence_mae": 17.411110975477428,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 90,
          "mae": 9.97517549678426,
          "rmse": 12.782838479322923,
          "r2": 0.24273887609182987,
          "persistence_mae": 17.411110975477428,
          "mae_skill_vs_persistence": 0.4270798968064855
        },
        "teacher": {
          "rows": 90,
          "mae": 10.379931932886443,
          "rmse": 12.572327277304668,
          "r2": 0.2674750613119584,
          "persistence_mae": 17.411110975477428,
          "mae_skill_vs_persistence": 0.4038328773214992
        },
        "student": {
          "rows": 90,
          "mae": 12.8609429145356,
          "rmse": 15.574335721074426,
          "r2": -0.12411339601033977,
          "persistence_mae": 17.411110975477428,
          "mae_skill_vs_persistence": 0.2613370317006469
        }
      }
    },
    "wind_speed_mps": {
      "train": {
        "persistence": {
          "rows": 22602,
          "mae": 0.7130948582956492,
          "rmse": 0.9067612948892042,
          "r2": -0.7163059605227546,
          "persistence_mae": 0.7130948582956492,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 22602,
          "mae": 0.41067214544499464,
          "rmse": 0.5318189333482872,
          "r2": 0.40961358991666674,
          "persistence_mae": 0.7130948582956492,
          "mae_skill_vs_persistence": 0.42409885491737775
        },
        "teacher": {
          "rows": 22602,
          "mae": 0.32720371647080854,
          "rmse": 0.4274692401187743,
          "r2": 0.6185667914742292,
          "persistence_mae": 0.7130948582956492,
          "mae_skill_vs_persistence": 0.5411498026323591
        },
        "student": {
          "rows": 22602,
          "mae": 0.5306836576442229,
          "rmse": 0.6658426930688233,
          "r2": 0.07455196181921597,
          "persistence_mae": 0.7130948582956492,
          "mae_skill_vs_persistence": 0.25580215385005434
        }
      },
      "validation": {
        "persistence": {
          "rows": 738,
          "mae": 0.5761111115870194,
          "rmse": 0.7480501301874067,
          "r2": -1.2396686944148936,
          "persistence_mae": 0.5761111115870194,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 738,
          "mae": 0.3649667216146817,
          "rmse": 0.44299033425943246,
          "r2": 0.21456387072614191,
          "persistence_mae": 0.5761111115870194,
          "mae_skill_vs_persistence": 0.366499422985778
        },
        "teacher": {
          "rows": 738,
          "mae": 0.32151187170956913,
          "rmse": 0.38726905088669156,
          "r2": 0.39972817934739124,
          "persistence_mae": 0.5761111115870194,
          "mae_skill_vs_persistence": 0.4419273205408295
        },
        "student": {
          "rows": 738,
          "mae": 0.4929690501025972,
          "rmse": 0.5959831084613008,
          "r2": -0.42164209947417675,
          "persistence_mae": 0.5761111115870194,
          "mae_skill_vs_persistence": 0.14431601788653226
        }
      },
      "future_test": {
        "persistence": {
          "rows": 954,
          "mae": 0.5945492655006033,
          "rmse": 0.7637696143574855,
          "r2": -1.253095574459456,
          "persistence_mae": 0.5945492655006033,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 954,
          "mae": 0.3415043818932995,
          "rmse": 0.43046199977263033,
          "r2": 0.28431074104612186,
          "persistence_mae": 0.5945492655006033,
          "mae_skill_vs_persistence": 0.42560793241287254
        },
        "teacher": {
          "rows": 954,
          "mae": 0.3215255226971156,
          "rmse": 0.40310595292089735,
          "r2": 0.37238504299928177,
          "persistence_mae": 0.5945492655006033,
          "mae_skill_vs_persistence": 0.4592113028238375
        },
        "student": {
          "rows": 954,
          "mae": 0.46416526483696935,
          "rmse": 0.5784783880983098,
          "r2": -0.2924957933850123,
          "persistence_mae": 0.5945492655006033,
          "mae_skill_vs_persistence": 0.2192989012506006
        }
      },
      "fresh_future_test": {
        "persistence": {
          "rows": 90,
          "mae": 0.5626666671335697,
          "rmse": 0.6934406971773235,
          "r2": -1.0672397147666448,
          "persistence_mae": 0.5626666671335697,
          "mae_skill_vs_persistence": 0.0
        },
        "temporal_ridge": {
          "rows": 90,
          "mae": 0.3556611302014093,
          "rmse": 0.4310787621478386,
          "r2": 0.20111283923618783,
          "persistence_mae": 0.5626666671335697,
          "mae_skill_vs_persistence": 0.3679008354746204
        },
        "teacher": {
          "rows": 90,
          "mae": 0.3215734614133835,
          "rmse": 0.40802721505773243,
          "r2": 0.28426797560575034,
          "persistence_mae": 0.5626666671335697,
          "mae_skill_vs_persistence": 0.42848318516610095
        },
        "student": {
          "rows": 90,
          "mae": 0.41336495951997737,
          "rmse": 0.5292065490552024,
          "r2": -0.2039892447516185,
          "persistence_mae": 0.5626666671335697,
          "mae_skill_vs_persistence": 0.26534663653382917
        }
      }
    }
  },
  "validation_selected_heads": {
    "temperature_c": "teacher",
    "relative_humidity_pct": "teacher",
    "pressure_hpa": "temporal_ridge",
    "pm25_ug_m3": "teacher",
    "pm10_ug_m3": "teacher",
    "wind_speed_mps": "teacher"
  },
  "hazard_results": {
    "cloudburst": {
      "status": "NOT_EVALUABLE_NO_ADMITTED_EVENT_LABELS",
      "trained": false,
      "accuracy": null,
      "reason": "Modeled weather/rain cannot supply independent Himalayan occurrence labels or monitored negatives"
    },
    "storm": {
      "status": "NOT_EVALUABLE_NO_ADMITTED_EVENT_LABELS",
      "trained": false,
      "accuracy": null,
      "reason": "Modeled weather/rain cannot supply independent Himalayan occurrence labels or monitored negatives"
    },
    "flash_flood": {
      "status": "NOT_EVALUABLE_NO_ADMITTED_EVENT_LABELS",
      "trained": false,
      "accuracy": null,
      "reason": "Modeled weather/rain cannot supply independent Himalayan occurrence labels or monitored negatives"
    },
    "landslide": {
      "status": "NOT_EVALUABLE_NO_ADMITTED_EVENT_LABELS",
      "trained": false,
      "accuracy": null,
      "reason": "Modeled weather/rain cannot supply independent Himalayan occurrence labels or monitored negatives"
    },
    "snowstorm": {
      "status": "NOT_EVALUABLE_NO_ADMITTED_EVENT_LABELS",
      "trained": false,
      "accuracy": null,
      "reason": "Modeled weather/rain cannot supply independent Himalayan occurrence labels or monitored negatives"
    }
  }
}
```

Attribution: Open-Meteo, ECMWF IFS and Copernicus Atmosphere Monitoring Service (CAMS).
Source methods: https://open-meteo.com/en/docs/historical-weather-api and https://open-meteo.com/en/docs/air-quality-api.
