# Experimental ERA5 storm-risk pipeline

This is the implementation of the [supplied specification](../docs/reference/STORM_RISK_IMPLEMENTATION_SPEC.md).
It is a local-file, retrospective context experiment. It is separate from the
six physical measurement channels and the six-hour numerical forecast shown in
the node telemetry dashboard. It does not add sensors or replace edge weights.

The default target is **current-hour cloudburst risk** (`lead_hours: 0`), following
the selected current-risk submission scope. A positive lead is configurable;
target alignment and split-boundary purging change with it. ERA5 context does
not establish what an operational system actually knew at issue time. A replay
with later reanalysis is not a demonstrated live advance warning.

## Run

From the repository root, in a dedicated Python environment:

```sh
python -m pip install -r requirements-storm-risk.txt -r requirements-dashboard.txt
python -m storm_risk.cli demo --config storm_risk/config/default.yaml --fixture-dir data/hazard_context/storm_demo_inputs --run-id storm_demo --online
python -m server.dashboard --demo --ui apps/indra-himachal-ui/dist --storm-risk-run outputs/storm_demo
```

Build the frontend first with `npm ci && npm run build` inside
`apps/indra-himachal-ui`. Open `http://127.0.0.1:8080` and expand **ERA5 storm-risk
research**. The example serves a labelled synthetic sensor demo separately from
the synthetic gridded research run. No physical hardware is implied.

For real local inputs, edit `storm_risk/config/default.yaml` and its `paths`:

```sh
python -m storm_risk.cli run --config storm_risk/config/default.yaml --run-id reviewed_local_run
python -m pytest tests/storm_risk -q
```

Run IDs must be new; existing artifacts are never overwritten. Local raw files,
training labels and `outputs/` are ignored by Git. The pipeline makes no portal
requests. A missing-input run writes `report.json` and an empty `scores.csv`,
returns `NOT_READY`, and exits with status 2. It never fabricates fitted heads.

## Inputs and evidence

- Default coverage is India, 2016–2025, on a configured 0.25-degree grid. Dates,
  region, years, resource budgets and every model/gate setting are in YAML.
  Partition large exports by configured time/region before exceeding memory
  budgets; this delivery is not a nationally fitted model.
- Supply the seventeen configured ERA5 variables in hourly NetCDF files.
  Actual variable names, dimensions and units are checked on import. Temperature
  is converted from K to degrees C, pressure from Pa to hPa, and the declared
  hourly precipitation accumulations from metres to mm/h. Different accumulation
  periods require preprocessing; cumulative multi-hour fields are not supported.
- Labels require `time,lat,lon,label,split`; `available_at` is recommended.
  Time means the outcome hour, with an explicit UTC offset. Splits must match the
  predeclared dates. Coordinates map to the nearest available grid cell only
  within the configured matching radius; collisions and out-of-radius records
  are excluded for review. Unknown hours stay unknown.
- Event records require the full schema from the supplied specification. Two
  distinct declared source domains, known time/location and accepted confidence
  are required. Cloudburst positives additionally need the configured intensity
  and unit. These source declarations still require the owner's review; the
  software does not verify the content of external records.
- A zero needs a matched `monitored_non_event` coverage record with supporting
  sources. Missing incident reports do not establish zero. Unbacked, conflicting
  and incomplete records are exported in exclusion CSVs. Shared event IDs across
  splits are excluded from supervised fitting/evaluation.
- Snowstorm training requires a reviewed target definition and matching records;
  rainfall intensity is not a snowstorm label. No labels come from ERA5 or IMERG.

No real ERA5 exports or independently confirmed event files were available for
this implementation run. All demonstrated fitted artifacts are explicitly
synthetic engineering artifacts, not deployable empirical event models.

## Models and leakage controls

Each of 17 base variables plus four derived features has its current value,
lags 1–24, change over 24 hours and trailing min/max: **588 ordered features**.
Missing hours are reindexed without filling; incomplete histories are dropped
and counted. Wind direction is encoded as sine/cosine; calm wind uses a zero
vector, and missing wind remains missing.

The first 80 percent of training timestamps fit the scaler and three base
models. The last 20 percent form chronological inner validation, with unavailable
outcomes and target-boundary overlap removed from the fit. Models are:

1. Configured ridge regression, RidgeClassifier or L2 logistic alternative.
2. XGBoost with training class ratio and inner-validation early stopping.
3. A small MLP with fixed epochs, no shuffled rows and no random validation split.

The simplex weights are selected on eligible `calib` rows only, using a fixed
grid over nonnegative coefficients summing to one. The same calibration
partition fits the optional isotonic/Platt mapping; this reuse can be optimistic,
which is why it does not establish validation by itself. Class-count checks can
skip mapping. No test row is used for fitting, weight selection or thresholds.

The test report contains counted reliability bins, Brier diagnostics and whole
UTC-day bootstrap intervals with at least 1,000 resamples. Continuous scores are
binned for the Murphy components, so the report includes the binning remainder
instead of incorrectly claiming exact equality for the raw continuous scores.
The decomposition follows [Murphy (1973)](https://journals.ametsoc.org/abstract/journals/apme/12/4/1520-0450_1973_012_0595_anvpot_2_0_co_2.xml).

The gate checks Brier skill lower bound, reliability, populated-bin counts and
independent positive test-event count. Mapping must also have been fitted.
Single-class/insufficient-day diagnostics stay unavailable. A failed gate keeps
all score columns ending in `_risk_uncal`. Only a passing mapped ensemble can
be named `ensemble_cal_prob`; unmapped base heads retain their risk names.
Synthetic mode always fails the evidence gate and withholds diagnostic values
from the report rather than presenting synthetic skill.

## Separate outputs

- Monthly percentile anomalies are fitted only from training-period features.
  Missing climatology months are marked unavailable. Anomalies are neither
  sensor faults nor confirmed weather events, and never modify ensemble scores.
- Neighbour confirmation counts distinct other grid cells within the configured
  degree radius and trailing window, including no future hour. The current cell
  must also exceed the configured threshold. Grid-cell agreement is spatially
  correlated context, not independent physical-node quorum.
- Every sampled map timestamp has a compressed feature `.npz`; the default
  stride exports every hour. Latest per-feature PNGs have coordinates and units.
  Unsupported cells stay NaN; the exporter does no spatial interpolation.
- Optional online SGD is a separate daily retrospective replay. Warm-up scaling
  and class weights remain fixed. Daily scores are written before mature labels
  update the model, and all updates stop before the test period. Unknown/delayed
  labels remain pending. Rolling diagnostics, drift flags, dated checkpoints and
  an audit JSON are separate from batch-model gate results. This is not a live
  six-sensor online-learning service.

Each run saves `ensemble_<train_end_date>.joblib`, `scores.csv`, `report.json`,
exclusion CSVs, `heatmaps/`, and optional `online_scores.csv`,
`online_metrics.csv`, `online_audit.json`, and `checkpoints/`. Joblib contains
models, scaler, weights, mapper, settings and software versions. Load only
trusted owner-generated joblib files; the dashboard never loads them.

## Dashboard contract

Start the existing FastAPI backend with `--storm-risk-run <run directory>`.
Three additive read-only endpoints serve the selected local outputs:

- `GET /api/storm-risk/report`: evidence, warnings, gate state and model weights.
- `GET /api/storm-risk/scores`: up to 200 recent cells, explicitly scoped.
- `GET /api/storm-risk/heatmap?feature=t2m&time=<UTC timestamp>`: a hash-checked
  feature grid from the exported manifest; omitted time selects the latest frame.

The React panel shows uncalibrated score labels, per-cell anomaly markers,
neighbour-confirmed experimental status, feature grids and gate failures.
Unavailable runs and corrupted files produce explicit errors, without creating
browser data or simulated physical acknowledgements. The node telemetry
forecast remains the existing Mandi XGBoost student until its separate ensemble
integration is completed. Public notifications remain disabled.
