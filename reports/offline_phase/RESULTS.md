# India sensor-only forecast results

**Real NOAA observations; not disaster or physical INDRA sensor validation.**

Exact completed-hour measurements at issue time +6h. Brier is squared probability error (lower is better); AP is average precision (higher is better).

A: sensor/time; B: +GPS/height; C: B with independently fitted mountain calibration if available; D: regional experts with B fallback.

Calibration and threshold availability are head-specific; consult the model manifest. Persistence repeats the current threshold; prevalence uses training labels only.

Table values use eight significant digits; full precision and per-region metrics are in [results.json](results.json).

## national

| Target | Method | Hours / positives | Brier | 95% station-bootstrap CI | AP | Recall at 0.5 | False-positive hours/station-day |
|---|---|---:|---:|---|---:|---:|---:|
| high_wind_measurement_at_6h | A | 17858 / 2 | 0.00024178576 | [8.4514944e-05, 0.00048942599] | 0.00028505722 | 0 | 0 |
| high_wind_measurement_at_6h | B | 17858 / 2 | 0.00011236372 | [1.7451709e-07, 0.00029377529] | 0.00034244517 | 0 | 0 |
| high_wind_measurement_at_6h | C | 17858 / 2 | 0.00011236372 | [1.7451709e-07, 0.00029377529] | 0.00034244517 | 0 | 0 |
| high_wind_measurement_at_6h | D | 17858 / 2 | 0.00011236372 | [1.7451709e-07, 0.00029377529] | 0.00034244517 | 0 | 0 |
| high_wind_measurement_at_6h | current_measurement_persistence | 17858 / 2 | 0.00027998656 | [0, 0.00076843303] | 0.00011199462 | 0 | 0.0040318065 |
| high_wind_measurement_at_6h | training_prevalence | 17858 / 2 | 0.00011233911 | [5.0341e-07, 0.00029338209] | 0.00011199462 | 0 | 0 |
| hot_measurement_at_6h | A | 17785 / 61 | 0.0036803389 | [0.0014006796, 0.0066789704] | 0.044474354 | 0 | 0.0094461625 |
| hot_measurement_at_6h | B | 17785 / 61 | 0.0035164754 | [0.0014223003, 0.0064666487] | 0.050302271 | 0 | 0.0053978071 |
| hot_measurement_at_6h | C | 17785 / 61 | 0.0035164754 | [0.0014223003, 0.0064666487] | 0.050302271 | 0 | 0.0053978071 |
| hot_measurement_at_6h | D | 17785 / 61 | 0.00315376 | [0.0014002873, 0.0055563132] | 0.15721889 | 0.016393443 | 0 |
| hot_measurement_at_6h | current_measurement_persistence | 17785 / 61 | 0.0065223503 | [0.0022433961, 0.012375538] | 0.0034298566 | 0 | 0.074219848 |
| hot_measurement_at_6h | training_prevalence | 17785 / 61 | 0.010365441 | [0.0087088024, 0.012930689] | 0.0034298566 | 0 | 0 |
| near_saturation_measurement_at_6h | A | 17777 / 1277 | 0.04166555 | [0.020350395, 0.067452035] | 0.61632492 | 0.29913861 | 0.13635597 |
| near_saturation_measurement_at_6h | B | 17777 / 1277 | 0.041937429 | [0.020470573, 0.068513731] | 0.61436578 | 0.28817541 | 0.12690555 |
| near_saturation_measurement_at_6h | C | 17777 / 1277 | 0.041937429 | [0.020470573, 0.068513731] | 0.61436578 | 0.28817541 | 0.12690555 |
| near_saturation_measurement_at_6h | D | 17777 / 1277 | 0.041857053 | [0.021380207, 0.066425561] | 0.62122615 | 0.25920125 | 0.11610508 |
| near_saturation_measurement_at_6h | current_measurement_persistence | 17777 / 1277 | 0.10333577 | [0.047331792, 0.1700068] | 0.14796911 | 0.33202819 | 1.3284581 |
| near_saturation_measurement_at_6h | training_prevalence | 17777 / 1277 | 0.067556965 | [0.032598048, 0.11087906] | 0.071834393 | 0 | 0 |

| Target | Method | Tuned precision | Tuned recall | F1 | Positive hours |
|---|---|---:|---:|---:|---:|
| high_wind_measurement_at_6h | A | 0 | 0 | 0 | 2 |
| high_wind_measurement_at_6h | B | 0 | 0 | 0 | 2 |
| high_wind_measurement_at_6h | C | 0 | 0 | 0 | 2 |
| high_wind_measurement_at_6h | D | 0 | 0 | 0 | 2 |
| hot_measurement_at_6h | A | 0 | 0 | 0 | 61 |
| hot_measurement_at_6h | B | 0 | 0 | 0 | 61 |
| hot_measurement_at_6h | C | 0 | 0 | 0 | 61 |
| hot_measurement_at_6h | D | 0 | 0 | 0 | 61 |
| near_saturation_measurement_at_6h | A | 0.82492582 | 0.21769773 | 0.34448575 | 1277 |
| near_saturation_measurement_at_6h | B | 0.80909091 | 0.20908379 | 0.3322962 | 1277 |
| near_saturation_measurement_at_6h | C | 0.80909091 | 0.20908379 | 0.3322962 | 1277 |
| near_saturation_measurement_at_6h | D | 0.79714286 | 0.21848081 | 0.34296251 | 1277 |

## himalaya_holdout

| Target | Method | Hours / positives | Brier | 95% station-bootstrap CI | AP | Recall at 0.5 | False-positive hours/station-day |
|---|---|---:|---:|---|---:|---:|---:|
| high_wind_measurement_at_6h | A | 2680 / 0 | 1.5051155e-07 | [4.7769392e-08, 2.9855733e-07] | — | — | 0 |
| high_wind_measurement_at_6h | B | 2680 / 0 | 8.0351818e-08 | [2.2974552e-08, 1.4567191e-07] | — | — | 0 |
| high_wind_measurement_at_6h | C | 2680 / 0 | 8.0351818e-08 | [2.2974552e-08, 1.4567191e-07] | — | — | 0 |
| high_wind_measurement_at_6h | D | 2680 / 0 | 8.0351818e-08 | [2.2974552e-08, 1.4567191e-07] | — | — | 0 |
| high_wind_measurement_at_6h | current_measurement_persistence | 2680 / 0 | 0 | [0, 0] | — | — | 0 |
| high_wind_measurement_at_6h | training_prevalence | 2680 / 0 | 4.8196428e-07 | [4.8196428e-07, 4.8196428e-07] | — | — | 0 |
| hot_measurement_at_6h | A | 2651 / 0 | 1.325066e-06 | [3.9300518e-07, 3.3859842e-06] | — | — | 0 |
| hot_measurement_at_6h | B | 2651 / 0 | 1.9506199e-06 | [4.8837611e-07, 5.676095e-06] | — | — | 0 |
| hot_measurement_at_6h | C | 2651 / 0 | 1.9506199e-06 | [4.8837611e-07, 5.676095e-06] | — | — | 0 |
| hot_measurement_at_6h | D | 2651 / 0 | 1.9506199e-06 | [4.8837611e-07, 5.676095e-06] | — | — | 0 |
| hot_measurement_at_6h | current_measurement_persistence | 2651 / 0 | 0 | [0, 0] | — | — | 0 |
| hot_measurement_at_6h | training_prevalence | 2651 / 0 | 0.0084868467 | [0.0084868467, 0.0084868467] | — | — | 0 |
| near_saturation_measurement_at_6h | A | 2643 / 316 | 0.087803125 | [0.034455296, 0.11938565] | 0.42777584 | 0.26898734 | 0.56299659 |
| near_saturation_measurement_at_6h | B | 2643 / 316 | 0.087284856 | [0.034566132, 0.1188478] | 0.44061365 | 0.32911392 | 0.69012486 |
| near_saturation_measurement_at_6h | C | 2643 / 316 | 0.087284856 | [0.034566132, 0.1188478] | 0.44061365 | 0.32911392 | 0.69012486 |
| near_saturation_measurement_at_6h | D | 2643 / 316 | 0.087284856 | [0.034566132, 0.1188478] | 0.44061365 | 0.32911392 | 0.69012486 |
| near_saturation_measurement_at_6h | current_measurement_persistence | 2643 / 316 | 0.23117669 | [0.092823523, 0.32892595] | 0.13118568 | 0.23734177 | 3.3598184 |
| near_saturation_measurement_at_6h | training_prevalence | 2643 / 316 | 0.11044563 | [0.041775681, 0.16182187] | 0.1195611 | 0 | 0 |

| Target | Method | Tuned precision | Tuned recall | F1 | Positive hours |
|---|---|---:|---:|---:|---:|
| high_wind_measurement_at_6h | A | 0 | — | 0 | 0 |
| high_wind_measurement_at_6h | B | 0 | — | 0 | 0 |
| high_wind_measurement_at_6h | C | 0 | — | 0 | 0 |
| high_wind_measurement_at_6h | D | 0 | — | 0 | 0 |
| hot_measurement_at_6h | A | 0 | — | 0 | 0 |
| hot_measurement_at_6h | B | 0 | — | 0 | 0 |
| hot_measurement_at_6h | C | 0 | — | 0 | 0 |
| hot_measurement_at_6h | D | 0 | — | 0 | 0 |
| near_saturation_measurement_at_6h | A | 0.79104478 | 0.16772152 | 0.2767624 | 316 |
| near_saturation_measurement_at_6h | B | 0.8115942 | 0.17721519 | 0.29090909 | 316 |
| near_saturation_measurement_at_6h | C | 0.8115942 | 0.17721519 | 0.29090909 | 316 |
| near_saturation_measurement_at_6h | D | 0.8115942 | 0.17721519 | 0.29090909 | 316 |

## temporal

| Target | Method | Hours / positives | Brier | 95% station-bootstrap CI | AP | Recall at 0.5 | False-positive hours/station-day |
|---|---|---:|---:|---|---:|---:|---:|
| high_wind_measurement_at_6h | A | 88169 / 19 | 0.00022831847 | [0.00011491195, 0.00033354024] | 0.00069179768 | 0 | 0.00054440903 |
| high_wind_measurement_at_6h | B | 88169 / 19 | 0.00023125886 | [0.00011794728, 0.00033979131] | 0.0013756828 | 0 | 0.00081661355 |
| high_wind_measurement_at_6h | C | 88169 / 19 | 0.00023125886 | [0.00011794728, 0.00033979131] | 0.0013756828 | 0 | 0.00081661355 |
| high_wind_measurement_at_6h | D | 88169 / 19 | 0.00023125886 | [0.00011794728, 0.00033979131] | 0.0013756828 | 0 | 0.00081661355 |
| high_wind_measurement_at_6h | current_measurement_persistence | 88169 / 19 | 0.00031757194 | [0.00015167268, 0.00048027723] | 0.00021549524 | 0 | 0.0024498406 |
| high_wind_measurement_at_6h | training_prevalence | 88169 / 19 | 0.00021566935 | [0.00010188741, 0.0003161219] | 0.00021549524 | 0 | 0 |
| hot_measurement_at_6h | A | 87777 / 183 | 0.002076156 | [0.0012560921, 0.0028021106] | 0.041774207 | 0 | 0.0010936806 |
| hot_measurement_at_6h | B | 87777 / 183 | 0.0020591391 | [0.0012548306, 0.0027748295] | 0.041565393 | 0 | 0.00054684029 |
| hot_measurement_at_6h | C | 87777 / 183 | 0.0020591391 | [0.0012548306, 0.0027748295] | 0.041565393 | 0 | 0.00054684029 |
| hot_measurement_at_6h | D | 87777 / 183 | 0.0018503189 | [0.0011052967, 0.0025078655] | 0.18403415 | 0.032786885 | 0.0024607813 |
| hot_measurement_at_6h | current_measurement_persistence | 87777 / 183 | 0.003713957 | [0.0021761103, 0.0051920772] | 0.0021111222 | 0.0054644809 | 0.039372501 |
| hot_measurement_at_6h | training_prevalence | 87777 / 183 | 0.0092195793 | [0.0085191934, 0.0098479101] | 0.0020848286 | 0 | 0 |
| near_saturation_measurement_at_6h | A | 87726 / 4806 | 0.035896059 | [0.027976354, 0.043955056] | 0.50559062 | 0.30774032 | 0.19916558 |
| near_saturation_measurement_at_6h | B | 87726 / 4806 | 0.035820927 | [0.027897217, 0.043839485] | 0.50752153 | 0.31231794 | 0.21448601 |
| near_saturation_measurement_at_6h | C | 87726 / 4806 | 0.035814378 | [0.027881708, 0.043852918] | 0.50750772 | 0.31231794 | 0.21448601 |
| near_saturation_measurement_at_6h | D | 87726 / 4806 | 0.034692299 | [0.026946251, 0.042531461] | 0.53076035 | 0.32563462 | 0.19451474 |
| near_saturation_measurement_at_6h | current_measurement_persistence | 87726 / 4806 | 0.080717233 | [0.06086726, 0.10235676] | 0.12967572 | 0.32126509 | 1.0447986 |
| near_saturation_measurement_at_6h | training_prevalence | 87726 / 4806 | 0.051814871 | [0.03873892, 0.064672048] | 0.054784214 | 0 | 0 |

| Target | Method | Tuned precision | Tuned recall | F1 | Positive hours |
|---|---|---:|---:|---:|---:|
| high_wind_measurement_at_6h | A | 0 | 0 | 0 | 19 |
| high_wind_measurement_at_6h | B | 0 | 0 | 0 | 19 |
| high_wind_measurement_at_6h | C | 0 | 0 | 0 | 19 |
| high_wind_measurement_at_6h | D | 0 | 0 | 0 | 19 |
| hot_measurement_at_6h | A | 0 | 0 | 0 | 183 |
| hot_measurement_at_6h | B | 0 | 0 | 0 | 183 |
| hot_measurement_at_6h | C | 0 | 0 | 0 | 183 |
| hot_measurement_at_6h | D | 0.18181818 | 0.010928962 | 0.020618557 | 183 |
| near_saturation_measurement_at_6h | A | 0.72578348 | 0.21202663 | 0.32818035 | 4806 |
| near_saturation_measurement_at_6h | B | 0.72597865 | 0.21223471 | 0.32844953 | 4806 |
| near_saturation_measurement_at_6h | C | 0.72597865 | 0.21223471 | 0.32844953 | 4806 |
| near_saturation_measurement_at_6h | D | 0.74 | 0.22326259 | 0.34303069 | 4806 |

## himalaya_only

| Target | Method | Hours / positives | Brier | 95% station-bootstrap CI | AP | Recall at 0.5 | False-positive hours/station-day |
|---|---|---:|---:|---|---:|---:|---:|
| high_wind_measurement_at_6h | A | 0 / 0 | — | — | — | — | — |
| high_wind_measurement_at_6h | B | 0 / 0 | — | — | — | — | — |
| high_wind_measurement_at_6h | C | 0 / 0 | — | — | — | — | — |
| high_wind_measurement_at_6h | D | 0 / 0 | — | — | — | — | — |
| hot_measurement_at_6h | A | 724 / 0 | 8.9494563e-08 | [8.1733609e-08, 9.2081771e-08] | — | — | 0 |
| hot_measurement_at_6h | B | 724 / 0 | 8.9494563e-08 | [8.1733609e-08, 9.2081771e-08] | — | — | 0 |
| hot_measurement_at_6h | C | 724 / 0 | 8.9494563e-08 | [8.1733609e-08, 9.2081771e-08] | — | — | 0 |
| hot_measurement_at_6h | D | 724 / 0 | 8.9494563e-08 | [8.1733609e-08, 9.2081771e-08] | — | — | 0 |
| hot_measurement_at_6h | current_measurement_persistence | 724 / 0 | 0 | [0, 0] | — | — | 0 |
| hot_measurement_at_6h | training_prevalence | 724 / 0 | 5.7335678e-05 | [5.7335678e-05, 5.7335678e-05] | — | — | 0 |
| near_saturation_measurement_at_6h | A | 717 / 99 | 0.1420362 | [0.0020569373, 0.18689143] | 0.20137044 | 0.11111111 | 0.13389121 |
| near_saturation_measurement_at_6h | B | 717 / 99 | 0.1420362 | [0.0020569373, 0.18689143] | 0.20137044 | 0.11111111 | 0.13389121 |
| near_saturation_measurement_at_6h | C | 717 / 99 | 0.1420362 | [0.0020569373, 0.18689143] | 0.20137044 | 0.11111111 | 0.13389121 |
| near_saturation_measurement_at_6h | D | 717 / 99 | 0.1420362 | [0.0020569373, 0.18689143] | 0.20137044 | 0.11111111 | 0.13389121 |
| near_saturation_measurement_at_6h | current_measurement_persistence | 717 / 99 | 0.34449093 | [0.0057471264, 0.45303867] | 0.12975496 | 0.13131313 | 5.3891213 |
| near_saturation_measurement_at_6h | training_prevalence | 717 / 99 | 0.12470542 | [0.003920106, 0.16341011] | 0.13807531 | 0 | 0 |

| Target | Method | Tuned precision | Tuned recall | F1 | Positive hours |
|---|---|---:|---:|---:|---:|
| hot_measurement_at_6h | A | 0 | — | 0 | 0 |
| hot_measurement_at_6h | B | 0 | — | 0 | 0 |
| hot_measurement_at_6h | C | 0 | — | 0 | 0 |
| hot_measurement_at_6h | D | 0 | — | 0 | 0 |
| near_saturation_measurement_at_6h | A | 0.73333333 | 0.11111111 | 0.19298246 | 99 |
| near_saturation_measurement_at_6h | B | 0.73333333 | 0.11111111 | 0.19298246 | 99 |
| near_saturation_measurement_at_6h | C | 0.73333333 | 0.11111111 | 0.19298246 | 99 |
| near_saturation_measurement_at_6h | D | 0.73333333 | 0.11111111 | 0.19298246 | 99 |

## Losses and interpretation

- national, high_wind_measurement_at_6h: A loses on Brier to training_prevalence (0.00024178576 vs 0.00011233911).
- national, high_wind_measurement_at_6h: B loses on Brier to training_prevalence (0.00011236372 vs 0.00011233911).
- national, high_wind_measurement_at_6h: C loses on Brier to training_prevalence (0.00011236372 vs 0.00011233911).
- national, high_wind_measurement_at_6h: D loses on Brier to training_prevalence (0.00011236372 vs 0.00011233911).
- national, hot_measurement_at_6h: A loses on Brier to D (0.0036803389 vs 0.00315376).
- national, hot_measurement_at_6h: B loses on Brier to D (0.0035164754 vs 0.00315376).
- national, hot_measurement_at_6h: C loses on Brier to D (0.0035164754 vs 0.00315376).
- national, near_saturation_measurement_at_6h: B loses on Brier to A (0.041937429 vs 0.04166555).
- national, near_saturation_measurement_at_6h: C loses on Brier to A (0.041937429 vs 0.04166555).
- national, near_saturation_measurement_at_6h: D loses on Brier to A (0.041857053 vs 0.04166555).
- himalaya_holdout, high_wind_measurement_at_6h: A loses on Brier to current_measurement_persistence (1.5051155e-07 vs 0).
- himalaya_holdout, high_wind_measurement_at_6h: B loses on Brier to current_measurement_persistence (8.0351818e-08 vs 0).
- himalaya_holdout, high_wind_measurement_at_6h: C loses on Brier to current_measurement_persistence (8.0351818e-08 vs 0).
- himalaya_holdout, high_wind_measurement_at_6h: D loses on Brier to current_measurement_persistence (8.0351818e-08 vs 0).
- himalaya_holdout, hot_measurement_at_6h: A loses on Brier to current_measurement_persistence (1.325066e-06 vs 0).
- himalaya_holdout, hot_measurement_at_6h: B loses on Brier to current_measurement_persistence (1.9506199e-06 vs 0).
- himalaya_holdout, hot_measurement_at_6h: C loses on Brier to current_measurement_persistence (1.9506199e-06 vs 0).
- himalaya_holdout, hot_measurement_at_6h: D loses on Brier to current_measurement_persistence (1.9506199e-06 vs 0).
- himalaya_holdout, near_saturation_measurement_at_6h: A loses on Brier to B (0.087803125 vs 0.087284856).
- temporal, high_wind_measurement_at_6h: A loses on Brier to training_prevalence (0.00022831847 vs 0.00021566935).
- temporal, high_wind_measurement_at_6h: B loses on Brier to training_prevalence (0.00023125886 vs 0.00021566935).
- temporal, high_wind_measurement_at_6h: C loses on Brier to training_prevalence (0.00023125886 vs 0.00021566935).
- temporal, high_wind_measurement_at_6h: D loses on Brier to training_prevalence (0.00023125886 vs 0.00021566935).
- temporal, hot_measurement_at_6h: A loses on Brier to D (0.002076156 vs 0.0018503189).
- temporal, hot_measurement_at_6h: B loses on Brier to D (0.0020591391 vs 0.0018503189).
- temporal, hot_measurement_at_6h: C loses on Brier to D (0.0020591391 vs 0.0018503189).
- temporal, near_saturation_measurement_at_6h: A loses on Brier to D (0.035896059 vs 0.034692299).
- temporal, near_saturation_measurement_at_6h: B loses on Brier to D (0.035820927 vs 0.034692299).
- temporal, near_saturation_measurement_at_6h: C loses on Brier to D (0.035814378 vs 0.034692299).
- himalaya_only, hot_measurement_at_6h: A loses on Brier to current_measurement_persistence (8.9494563e-08 vs 0).
- himalaya_only, hot_measurement_at_6h: B loses on Brier to current_measurement_persistence (8.9494563e-08 vs 0).
- himalaya_only, hot_measurement_at_6h: C loses on Brier to current_measurement_persistence (8.9494563e-08 vs 0).
- himalaya_only, hot_measurement_at_6h: D loses on Brier to current_measurement_persistence (8.9494563e-08 vs 0).
- himalaya_only, near_saturation_measurement_at_6h: A loses on Brier to training_prevalence (0.1420362 vs 0.12470542).
- himalaya_only, near_saturation_measurement_at_6h: B loses on Brier to training_prevalence (0.1420362 vs 0.12470542).
- himalaya_only, near_saturation_measurement_at_6h: C loses on Brier to training_prevalence (0.1420362 vs 0.12470542).
- himalaya_only, near_saturation_measurement_at_6h: D loses on Brier to training_prevalence (0.1420362 vs 0.12470542).

B/C/D do not universally improve A. C/D fallback and calibration vary by scope/head. In the whole-Himalaya holdout the mountain expert has no training observations; it cannot establish regional expertise.

Check positive counts before interpreting small Brier scores: zero positives cannot establish detection skill. RH is near saturation, not verified fog or rainfall. Recall counts positive hours, not distinct storms.

Bootstrap resamples whole stations; shared storms and long-term temporal dependence remain. These are metric confidence intervals, not 80/90% prediction bands. The diagnostic benchmark includes all eligible test forecasts; serving also checks fitted ranges and may refuse them.

Thresholds and class weights were selected using validation hours only, before calibration and testing. Unsupported cutoffs are withheld in serving; diagnostic fallback at 0.5 is explicitly labeled. All disaster heads remain unavailable; field calibration is not established.
