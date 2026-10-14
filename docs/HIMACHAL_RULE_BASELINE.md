# Three-target current-condition rule baseline

`ml.himachal.rules.evaluate` consumes a versioned native feature packet and
returns exactly `rain`, `snowstorm` and `cloudburst_risk`. These are exploratory
sensor-pattern assessments. None confirms rainfall intensity, snowfall,
visibility, a blizzard or a cloudburst. No learned hazard head is fitted here.

All thresholds are research defaults in `configs/himachal_rules_v1.json`, derived
from the supplied review/build specification. They are not validated IMD warning
definitions. They must be evaluated/selected on independent development data
before any operational claim.

## Rain and snowstorm risk

Rain pattern is the complete conjunction of RH ≥85%, same-site six-hour pressure
fall ≤−1.5 hPa, temperature >3 C and the new hourly two-channel PM-decline proxy.
Snowstorm risk requires temperature ≤1 C, RH ≥85%, wind ≥9 m/s, six-hour pressure
fall ≤−3 hPa and the hourly PM-decline proxy. PM baselines and noise handling use
the feature contract; this is not the legacy classifier's non-increasing-PM rule.

Complete matches have rule score 1, complete non-matches score 0. The score is not
an event probability. Any unavailable required feature gives null score and
abstention. Clean-air rain can have unavailable PM evidence: the output is unknown,
not a certified absence of rain. Neither non-match nor missing evidence means safe.

An auxiliary `rainstorm_sequence` assessment explicitly separates a six-hour
pressure pre-drop ending 15 minutes ago (≤−3.5 hPa) from the following 15-minute
rebound (≥1.5 hPa). It additionally requires a 15-minute temperature fall ≤−3 C,
current temperature >3 C, wind ≥10 m/s and native PM-decline proxy. The pre-drop
duration is an explicitly chosen initial research setting; it was unspecified
in the older proposed matrix. This needs 6 h 15 min of native support and cannot
be established from a six-hour net delta alone. It is auxiliary sequence evidence,
not a fourth independent storm detector or a trained storm forecast.

## Cloudburst risk

The native profile's fixed weights are:

| Criterion | Weight |
| --- | ---: |
| RH ≥90% | .20 |
| Actual 15-minute pressure fall ≤−1 hPa | .20 |
| Actual 15-minute temperature fall ≤−2 C | .20 |
| Calibrated wind-increase proxy | .15 |
| Available native two-PM decline proxy | .15 |
| Indian local calendar June–September | .05 |
| Reviewed, already available terrain-exposure source | .05 |

Score is the sum of weights of observed matching criteria. Missing features do
not match and their weights are **not redistributed**. Availability and coverage
remain explicit even when a lower-bound observed score can be computed. No
terrain threshold is guessed from elevation. A terrain prior requires review,
source identity and an availability time no later than issue time.

The hourly companion has a different profile identity. Its experimental pressure
criterion is ≤−1.5 hPa/hour, temperature ≤−2 C/hour, and calibrated wind increase
≥3 m/s/hour with current wind ≥8 m/s. It uses hourly PM decline. These are hourly
patterns, with no implied quarter-hour precursor or actual gust. Both profiles
require the same explicit source/reference and evidence-status handling.

## Levels, missing states and next policy stages

Display defaults are watch ≥.4 and local warning-candidate ≥.7. A high local
candidate also requires ≥3 matching dynamic measurement criteria and ≥.9 available
weight. Fewer than three available dynamic criteria or insufficient coverage
abstains. Calendar/terrain alone cannot create a candidate.

This phase produces only `LOCAL_ONLY` assessments; `warning_candidate` remains
false, corroboration is `NOT_ASSESSED`, and dispatch is `DISABLED`. A complete
network/human-confirm policy must explicitly promote a candidate later. High
scores cannot bypass quorum or public-alert readiness gates. Unknown/stale states
must not be rendered as green zero risk.

Each output includes profile/version/config identity, source kind, evidence
IDs/values/units/operators/thresholds, triggered evidence, feature availability,
coverage, abstention and score interpretation. Probability and lead time remain
null; task is `current_condition_heuristic`. Cloudburst/snowstorm are always risk
only. These current-time patterns do not establish six-hour advance skill.

Grid-surface/sea-level/unknown pressure and modeled-only context cannot satisfy
the observed-station rule profile. Synthetic demo packets are visibly tagged
and must stay out of empirical model training, evaluation and field-accuracy
reports. Rule outputs are always inadmissible as independent training labels.
