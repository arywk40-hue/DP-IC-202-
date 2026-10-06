# India sensor-only forecast results

**Real NOAA observations; not disaster or physical INDRA sensor validation.**

Exact completed-hour measurements at issue time +6h. Brier is squared probability error (lower is better); AP is average precision (higher is better).

A: sensor/time; B: +GPS/height; C: B with independently fitted mountain calibration if available; D: regional experts with B fallback.

Wind scores are uncalibrated: insufficient calibration positives. Persistence repeats the current threshold; prevalence uses training labels only.

Table values use eight significant digits; full precision and per-region metrics are in [results.json](results.json).

## national

| Target | Method | Hours / positives | Brier | 95% station-bootstrap CI | AP | Recall at 0.5 | False-positive hours/station-day |
|---|---|---:|---:|---|---:|---:|---:|
| high_wind_measurement_at_6h | A | 17858 / 2 | 0.00011235216 | [2.3083121e-07, 0.00029389846] | 0.00027590516 | 0 | 0 |
| high_wind_measurement_at_6h | B | 17858 / 2 | 0.00011236372 | [1.7451709e-07, 0.00029377529] | 0.00034244517 | 0 | 0 |
| high_wind_measurement_at_6h | C | 17858 / 2 | 0.00011236372 | [1.7451709e-07, 0.00029377529] | 0.00034244517 | 0 | 0 |
| high_wind_measurement_at_6h | D | 17858 / 2 | 0.00011236372 | [1.7451709e-07, 0.00029377529] | 0.00034244517 | 0 | 0 |
| high_wind_measurement_at_6h | current_measurement_persistence | 17858 / 2 | 0.00027998656 | [0, 0.00076843303] | 0.00011199462 | 0 | 0.0040318065 |
| high_wind_measurement_at_6h | training_prevalence | 17858 / 2 | 0.00011233911 | [5.0341e-07, 0.00029338209] | 0.00011199462 | 0 | 0 |
| hot_measurement_at_6h | A | 17785 / 61 | 0.0036471663 | [0.0014266507, 0.0066827854] | 0.042069527 | 0 | 0.0094461625 |
| hot_measurement_at_6h | B | 17785 / 61 | 0.0035164754 | [0.0014223003, 0.0064666487] | 0.050302271 | 0 | 0.0053978071 |
| hot_measurement_at_6h | C | 17785 / 61 | 0.0035164754 | [0.0014223003, 0.0064666487] | 0.050302271 | 0 | 0.0053978071 |
| hot_measurement_at_6h | D | 17785 / 61 | 0.0032258171 | [0.0014433876, 0.005786038] | 0.12721934 | 0 | 0 |
| hot_measurement_at_6h | current_measurement_persistence | 17785 / 61 | 0.0065223503 | [0.0022433961, 0.012375538] | 0.0034298566 | 0 | 0.074219848 |
| hot_measurement_at_6h | training_prevalence | 17785 / 61 | 0.010365441 | [0.0087088024, 0.012930689] | 0.0034298566 | 0 | 0 |
| near_saturation_measurement_at_6h | A | 17777 / 1277 | 0.042115334 | [0.020123876, 0.067772608] | 0.60222516 | 0.26389977 | 0.13500591 |
| near_saturation_measurement_at_6h | B | 17777 / 1277 | 0.042836264 | [0.02032375, 0.069518735] | 0.59031176 | 0.26703211 | 0.1485065 |
| near_saturation_measurement_at_6h | C | 17777 / 1277 | 0.042836264 | [0.02032375, 0.069518735] | 0.59031176 | 0.26703211 | 0.1485065 |
| near_saturation_measurement_at_6h | D | 17777 / 1277 | 0.042084828 | [0.021344613, 0.066565726] | 0.60347179 | 0.30540329 | 0.13365585 |
| near_saturation_measurement_at_6h | current_measurement_persistence | 17777 / 1277 | 0.10333577 | [0.047331792, 0.1700068] | 0.14796911 | 0.33202819 | 1.3284581 |
| near_saturation_measurement_at_6h | training_prevalence | 17777 / 1277 | 0.067556965 | [0.032598048, 0.11087906] | 0.071834393 | 0 | 0 |

## himalaya_holdout

| Target | Method | Hours / positives | Brier | 95% station-bootstrap CI | AP | Recall at 0.5 | False-positive hours/station-day |
|---|---|---:|---:|---|---:|---:|---:|
| high_wind_measurement_at_6h | A | 2680 / 0 | 1.5050955e-07 | [4.7766218e-08, 2.9855753e-07] | — | 0 | 0 |
| high_wind_measurement_at_6h | B | 2680 / 0 | 8.0348713e-08 | [2.2973469e-08, 1.4566947e-07] | — | 0 | 0 |
| high_wind_measurement_at_6h | C | 2680 / 0 | 8.0348713e-08 | [2.2973469e-08, 1.4566947e-07] | — | 0 | 0 |
| high_wind_measurement_at_6h | D | 2680 / 0 | 8.0348713e-08 | [2.2973469e-08, 1.4566947e-07] | — | 0 | 0 |
| high_wind_measurement_at_6h | current_measurement_persistence | 2680 / 0 | 0 | [0, 0] | — | 0 | 0 |
| high_wind_measurement_at_6h | training_prevalence | 2680 / 0 | 4.81961e-07 | [4.81961e-07, 4.81961e-07] | — | 0 | 0 |
| hot_measurement_at_6h | A | 2651 / 0 | 2.7516262e-06 | [9.6638077e-07, 6.0725921e-06] | — | 0 | 0 |
| hot_measurement_at_6h | B | 2651 / 0 | 2.7880826e-06 | [1.0199924e-06, 6.0495662e-06] | — | 0 | 0 |
| hot_measurement_at_6h | C | 2651 / 0 | 2.7880826e-06 | [1.0199924e-06, 6.0495662e-06] | — | 0 | 0 |
| hot_measurement_at_6h | D | 2651 / 0 | 2.7880826e-06 | [1.0199924e-06, 6.0495662e-06] | — | 0 | 0 |
| hot_measurement_at_6h | current_measurement_persistence | 2651 / 0 | 0 | [0, 0] | — | 0 | 0 |
| hot_measurement_at_6h | training_prevalence | 2651 / 0 | 0.0084867889 | [0.0084867889, 0.0084867889] | — | 0 | 0 |
| near_saturation_measurement_at_6h | A | 2643 / 316 | 0.087715432 | [0.034230866, 0.11887395] | 0.43285677 | 0.27848101 | 0.56299659 |
| near_saturation_measurement_at_6h | B | 2643 / 316 | 0.088100106 | [0.034710253, 0.1196359] | 0.43491958 | 0.34493671 | 0.68104427 |
| near_saturation_measurement_at_6h | C | 2643 / 316 | 0.088100106 | [0.034710253, 0.1196359] | 0.43491958 | 0.34493671 | 0.68104427 |
| near_saturation_measurement_at_6h | D | 2643 / 316 | 0.088100106 | [0.034710253, 0.1196359] | 0.43491958 | 0.34493671 | 0.68104427 |
| near_saturation_measurement_at_6h | current_measurement_persistence | 2643 / 316 | 0.23117669 | [0.092823523, 0.32892595] | 0.13118568 | 0.23734177 | 3.3598184 |
| near_saturation_measurement_at_6h | training_prevalence | 2643 / 316 | 0.11044566 | [0.041775679, 0.16182191] | 0.1195611 | 0 | 0 |

## Losses and interpretation

- national, high_wind_measurement_at_6h: A loses on Brier to training_prevalence (0.00011235216 vs 0.00011233911).
- national, high_wind_measurement_at_6h: B loses on Brier to training_prevalence (0.00011236372 vs 0.00011233911).
- national, high_wind_measurement_at_6h: C loses on Brier to training_prevalence (0.00011236372 vs 0.00011233911).
- national, high_wind_measurement_at_6h: D loses on Brier to training_prevalence (0.00011236372 vs 0.00011233911).
- national, hot_measurement_at_6h: A loses on Brier to D (0.0036471663 vs 0.0032258171).
- national, hot_measurement_at_6h: B loses on Brier to D (0.0035164754 vs 0.0032258171).
- national, hot_measurement_at_6h: C loses on Brier to D (0.0035164754 vs 0.0032258171).
- national, near_saturation_measurement_at_6h: A loses on Brier to D (0.042115334 vs 0.042084828).
- national, near_saturation_measurement_at_6h: B loses on Brier to D (0.042836264 vs 0.042084828).
- national, near_saturation_measurement_at_6h: C loses on Brier to D (0.042836264 vs 0.042084828).
- himalaya_holdout, high_wind_measurement_at_6h: A loses on Brier to current_measurement_persistence (1.5050955e-07 vs 0).
- himalaya_holdout, high_wind_measurement_at_6h: B loses on Brier to current_measurement_persistence (8.0348713e-08 vs 0).
- himalaya_holdout, high_wind_measurement_at_6h: C loses on Brier to current_measurement_persistence (8.0348713e-08 vs 0).
- himalaya_holdout, high_wind_measurement_at_6h: D loses on Brier to current_measurement_persistence (8.0348713e-08 vs 0).
- himalaya_holdout, hot_measurement_at_6h: A loses on Brier to current_measurement_persistence (2.7516262e-06 vs 0).
- himalaya_holdout, hot_measurement_at_6h: B loses on Brier to current_measurement_persistence (2.7880826e-06 vs 0).
- himalaya_holdout, hot_measurement_at_6h: C loses on Brier to current_measurement_persistence (2.7880826e-06 vs 0).
- himalaya_holdout, hot_measurement_at_6h: D loses on Brier to current_measurement_persistence (2.7880826e-06 vs 0).
- himalaya_holdout, near_saturation_measurement_at_6h: B loses on Brier to A (0.088100106 vs 0.087715432).
- himalaya_holdout, near_saturation_measurement_at_6h: C loses on Brier to A (0.088100106 vs 0.087715432).
- himalaya_holdout, near_saturation_measurement_at_6h: D loses on Brier to A (0.088100106 vs 0.087715432).

B/C/D do not universally improve A. C is a national fallback in every current head because no eligible mountain calibration has enough positive and negative hours. D also falls back in the whole-Himalaya test; these are not independently successful mountain experts.

Check positive counts before interpreting small Brier scores: zero positives cannot establish detection skill. RH is near saturation, not verified fog or rainfall. Recall counts positive hours, not distinct storms.

Bootstrap resamples whole stations; shared storms and long-term temporal dependence remain. These are metric confidence intervals, not 80/90% prediction bands. The diagnostic benchmark includes all eligible test forecasts; serving also checks fitted ranges and may refuse them.

All disaster heads remain unavailable. No release, threshold optimization, ensemble replacement or field-calibration claim follows from this benchmark.
