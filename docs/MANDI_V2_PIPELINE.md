# Mandi v2 pipeline and online learning

Current gateway: `india_mandi_tabular_v2`, API/PWA 0.4.0. The six physical channels
and +6h numerical task are unchanged. This is a local research prototype.

## What changed

- Expanded the complete source from 24,336 to **35,520 hourly modeled positions**,
  October 2022–19 October 2026. Older PM probes were empty; no PM history was invented.
- Trained six LightGBM residual heads and a shared 66→64→32→6 residual MLP on the
  expanded training partition. The retained v1 hybrid and persistence remain candidates.
- Selected nonnegative per-target prediction blends using August validation only.
  Components are bounded, checksummed and versioned; originals remain unchanged.
- Added a model workspace: data coverage, per-channel v1/v2 errors, regressions,
  cohort selection, blend details, live-shadow status and separate replay diagnostics.
- Implemented durable delayed-label SGD residual learning with a file-watching worker.

## Results and evidence

[Full report](../reports/mandi_pipeline_v2/REPORT.md), [metrics](../reports/mandi_pipeline_v2/results.json),
[TabPFN comparison](../reports/mandi_pipeline_v2/tabpfn.json), and
[online replay](../reports/mandi_pipeline_v2/online_replay.json).

Train: 33,570 eligible rows before August. Validation: 738 August rows. Test:
1,170 September–October pairs, including 210 new-date pairs on 11–19 October.
Exact +6h targets are purged at split boundaries. The older test was examined
before; its reuse is explicit. Model selection never receives these test errors.

The v2 pipeline improves humidity/wind over v1 on the full test, but regresses
on several other channels. It improves five of six channels on the new-date
extension. Do not call it universally more accurate. V1 used a shorter history,
so this comparison changes both training data and architecture. No synchronized
station, geographic holdout or independently labelled hazard skill is established.

TabPFN v2 ran locally with 512 training-context rows and 96 fixed test rows.
Other models were scored on those same 96 rows, but their training histories
are longer. This is a bounded CPU diagnostic, not production selection. Its
prior weights have separate licensing/attribution and are not redistributed.

## Install, reproduce and retest

```sh
.venv/bin/python -m pip install -r requirements-dashboard.txt
# Download/cache the configured source if missing; raw files remain ignored:
.venv/bin/python scripts/train_mandi_v2.py --prepare
# Retest the committed, frozen models; no fitting or new blend selection:
.venv/bin/python scripts/train_mandi_v2.py --evaluate
```

`--train` fits a new experiment and refuses to overwrite an existing version.
Keep original source snapshots: if upstream values change, source checks fail
instead of silently relabelling the old model evaluation. The config is
`configs/mandi_pipeline_v2.json`; weights are in `ml/models/india_mandi_tabular_v2`.
Raw source is `data/himachal/mandi_expanded_v2`. API inference needs only committed
artifacts, not raw source or TabPFN/Torch.

Optional TabPFN reproduction uses an isolated `.venv/tabpfn` environment with
`tabpfn==2.2.1`; `scripts/benchmark_tabpfn_mandi.py` reads bounded local NumPy
inputs, downloads the public checkpoint on first use, and disables telemetry.
It never calls hosted inference. The local input archive/checkpoint stays ignored.
Prepare its frozen bounded input with `scripts/train_mandi_v2.py --tabpfn-inputs`
in the main environment, then run the benchmark using the isolated environment.

Older PM gaps are handled by a [separate synthetic experiment](../reports/mandi_synthetic_pm_v1/README.md).
Those flagged rows do not enter the active v2 fit, validation or reported tests.

## Online learning: what is active

The worker is **implemented in shadow mode**. It produces and persists a separate
shadow forecast and learns residual corrections; it does not overwrite the
published offline v2 forecast or promote itself after looking at test errors.

For each source/site/calibration namespace it:

1. Validates an exact hourly six-channel arrival and actual availability.
2. Saves the base/shadow forecast and the current checkpoint revision first.
3. Matches truth at exactly issue+6h, only after that observation is available.
4. Records errors from the immutable pre-update forecast, then updates six
   `SGDRegressor(loss="huber")` heads with a fixed train-only scaler.
5. Saves numerical checkpoints and update state atomically in SQLite, with no pickle.

Duplicates do not train twice; later downloads retain first recorded availability.
Conflicting revisions, backward clocks or changed scaler/model identity fail closed.
Missing truth is not zero or nearest-hour truth. Source/site/location/calibration
identities separate state. High-rate observations are explicitly skipped; a reviewed
hourly aggregation must precede this worker. Public training/write APIs are absent.

Late historical inputs are ineligible for live forecast scoring or updates. Therefore
the current archived Mandi input correctly shows zero live updates. Future hourly
arrivals and their +6h outcomes will drive the same worker without a batch retrain.

The separate replay simulated timely arrivals: **1,170 updates, 6 pending forecasts**.
Its last-720-score MAEs improved over the frozen base on all six channels, but this
is retrospective prequential evidence. Original issue-time API availability is
unverified; do not present simulated timing as live sensor performance.

## Run locally

The stable input file is `data/himachal/live_hourly.json`, initially containing
historical modeled Mandi snapshots. Replace it atomically with reviewed hourly
arrivals. Keep source metadata honest; do not turn model grids into physical nodes.

```sh
.venv/bin/python scripts/run_himachal_demo.py --offline --observations data/himachal/live_hourly.json --db data/himachal/mandi_dashboard.sqlite --online-state data/himachal/mandi_v2_online_live.sqlite
# In another terminal, if new input files will arrive:
.venv/bin/python scripts/online_mandi_worker.py --input data/himachal/live_hourly.json --state data/himachal/mandi_v2_online_live.sqlite --watch-seconds 5
# Development frontend (optional; backend also serves the built UI on :8080):
npm run dev --prefix apps/indra-himachal-ui
```

Frontend: http://127.0.0.1:5173 · Backend: http://127.0.0.1:8080.
Importing refreshed readings can update both dashboard and learner explicitly:

```sh
.venv/bin/python scripts/import_dashboard_observations.py --input data/himachal/live_hourly.json --db data/himachal/mandi_dashboard.sqlite --online-state data/himachal/mandi_v2_online_live.sqlite
```

Rollback: start the backend/demo runner with
`--forecast-model ml/models/india_mandi_hybrid_6h_v1` and omit `--online-state`.
A new model/scaler requires a separate shadow-state database. The simulated replay
state `mandi_v2_online_replay.sqlite` is never the live state.

Cloudburst/storm/flood/landslide/snowstorm probabilities, physical ESP32 execution
and RF delivery remain independently unvalidated. Do not use the model workspace’s
numerical MAE or rule scores as evidence of those outcomes. Keep deployment local.
