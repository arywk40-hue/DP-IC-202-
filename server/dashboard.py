"""Read-only, loopback dashboard adapter over validated INDRA observations.

Inputs are operator-imported snapshots, never untrusted API claims of physical
identity. No RPC, RF, public warnings, empirical hazard probabilities or cloud
credentials are implemented by this adapter.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import copy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3
import time

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import pandas as pd

from ml.himachal.contracts import METADATA, snapshot
from ml.himachal.features import build_packet
from ml.himachal.rules import evaluate
from ml.operational.contracts import UNITS, utc
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.india_mandi.registry import ACTIVE_MODEL, load_forecaster
from server.storm_run import StormRun
from ml.provenance import append as audit_append, initialize as audit_initialize, batch as audit_batch
from ml.himachal.weather_categories import WeatherCategories, synthetic_episodes
from ml.himachal.hazard_scenarios import HazardScenarios
from ml.himachal.parameter_maps import parameter_maps, geojson

ROOT = Path(__file__).resolve().parents[1]
MODEL = ACTIVE_MODEL
API_VERSION = "0.5.0"
MAX_ROWS = 50_000


def demo_observations(now=None):
    """Deterministic engineering fixtures; not downloaded or observed weather."""
    end = pd.Timestamp(now or datetime.now(timezone.utc)).floor("15min")
    rows = []
    for number, scenario in enumerate(("rain", "snow", "cloudburst", "incomplete"), 1):
        for tick in range(97 if scenario != "incomplete" else 1):
            stamp = (end - pd.Timedelta(minutes=15 * (96-tick) if scenario != "incomplete" else 0)).isoformat()
            temperature, humidity, pressure, pm25, pm10, wind = 20., 90., 900.-tick*.25, 40., 80., 5.
            if scenario == "snow":
                temperature, wind = 0., 10.
            if tick == 96:
                pm25, pm10 = 20., 40.
                if scenario == "cloudburst":
                    temperature, pressure, wind = 17., pressure-1.25, 10.
            rows.append(dict(node_id=f"demo-{number:02d}", physical_site_id=f"synthetic-site-{number}",
                registration_id=f"synthetic-registration-{number}", latitude=31.71+(number%2)*.012,
                longitude=76.93+(number//2)*.012, elevation_m=1000.+number*100,
                elevation_datum="surveyed_orthometric", sensor_height_m=2., wind_height_m=10.,
                native_interval_seconds=900, source_class="synthetic_demo", source_id="dashboard_engineering_fixture",
                source_cell_id=None, pressure_reference="station", timestamp_utc=stamp, valid_time_utc=stamp,
                available_at_utc=stamp, sensor_model="synthetic_not_hardware",
                calibration_ids={c: "synthetic_contract_only" for c in RAW_SENSOR_COLUMNS},
                measurements=dict(zip(RAW_SENSOR_COLUMNS, (temperature,humidity,pressure,pm25,pm10,wind))),
                units=UNITS.copy()))
    return rows


def read_observations(path):
    path = Path(path)
    if path.stat().st_size > 64*1024*1024:
        raise ValueError("Observation file exceeds 64 MiB")
    data = json.loads(path.read_text(), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    if not isinstance(data, list) or not 1 <= len(data) <= MAX_ROWS:
        raise ValueError("Expected bounded nonempty list of native six-channel snapshots")
    return data


def weather_demo_observations(now=None):
    """Multi-location synthetic scenario demonstration, never measured Mandi data."""
    end=pd.Timestamp(now or datetime.now(timezone.utc)).floor('h')
    rows=demo_observations(end)
    episodes,_,labels=synthetic_episodes(400,707)
    for offset,j in enumerate([3,4,5,6,7,8,2,9],5):
        episode=episodes[next(i for i in range(len(labels)) if labels[i,j])]
        template=copy.deepcopy(rows[0])
        template.update(node_id=f'demo-{offset:02d}',physical_site_id=f'synthetic-site-{offset}',
            registration_id=f'synthetic-registration-{offset}',latitude=31.70+(offset%3)*.012,
            longitude=76.91+(offset//3)*.014)
        for tick in range(25):
            r=copy.deepcopy(template);stamp=(end-pd.Timedelta(hours=24-tick)).isoformat()
            r.update(native_interval_seconds=3600,timestamp_utc=stamp,valid_time_utc=stamp,available_at_utc=stamp,
                measurements=dict(zip(RAW_SENSOR_COLUMNS,episode[max(0,tick-18)].tolist())))
            rows.append(r)
    return rows


def apply_forecasts(nodes, histories, engine, clock):
    """Take exact hourly snapshots ending at each observation; never fill values."""
    rows = []
    for node in nodes:
        end = pd.Timestamp(node['timestamp'], unit='ms', tz='UTC')
        lookup = {utc(r['timestamp']): r for r in histories[node['id']]}
        expected = [end-pd.Timedelta(hours=h) for h in range(24, -1, -1)]
        stored = []
        missing = []
        for stamp in expected:
            observation = lookup.get(stamp)
            values = {c: None if observation is None else observation.get(c) for c in RAW_SENSOR_COLUMNS}
            if observation is not None:
                stored.append(dict(timestamp=stamp.isoformat(), **values))
            if any(v is None for v in values.values()):
                missing.append(stamp.isoformat())
            rows.append(dict(location_id=node['id'], timestamp_utc=stamp.isoformat(), **values))
        node['forecastHistory'] = stored
        node['forecastHistoryRows'] = 25-len(missing)
        node['forecastHistoryRequired'] = 25
        node['forecastMissingHours'] = missing
    forecasts = engine.predict(pd.DataFrame(rows))
    latest = forecasts.groupby('location_id', sort=False).tail(1).set_index('location_id')
    for node in nodes:
        forecast = latest.loc[node['id']]
        ready = forecast['status'] == 'HYBRID_READY'
        node['forecast6h'] = {c: float(forecast['forecast_'+c]) if math.isfinite(forecast['forecast_'+c]) else None for c in RAW_SENSOR_COLUMNS}
        node['forecastTimestamp'] = forecast['forecast_timestamp_utc'].isoformat()
        node['forecastIssuedAt'] = clock.isoformat()
        node['forecastStatus'] = forecast['status']
        node['forecastModel'] = dict(id=forecast['model_id'], configuredId=engine.profile['id'],
            displayName=engine.profile.get('display_name','Mandi neural hybrid') if ready else 'Persistence warm-up' if forecast['status']=='WARMING_UP_PERSISTENCE' else 'Unavailable',
            family=engine.profile.get('family','Neural + history XGBoost + ridge') if ready else 'Persistence' if forecast['status']=='WARMING_UP_PERSISTENCE' else None,
            country='IN', trainingEvidence='MODELED_GRID_RETROSPECTIVE', fieldValidated=False,
            profileSha256=engine.profile_sha256, blendWeights=engine.weights['heads'] if ready else None,
            historySampling='EXACT_ONE_HOUR_SPACING_AT_OBSERVATION_PHASE_NO_INTERPOLATION')
        node['assessmentAsOf'] = node['timestamp']
    return nodes


def assess(rows, *, now=None, model_dir=MODEL):
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
        raise ValueError("Bounded native snapshot list required")
    clock = utc(now or datetime.now(timezone.utc).isoformat())
    groups = defaultdict(list)
    for raw in rows:
        row = snapshot(raw)
        if utc(row["available_at_utc"]) > clock or utc(row["timestamp_utc"]) > clock:
            raise ValueError("Future or not-yet-available observations cannot be displayed")
        if len(row["node_id"]) > 80 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in row["node_id"]):
            raise ValueError("Node IDs must be bounded URL-safe identifiers")
        # build_packet revalidates canonical fields, not its own extra outputs.
        groups[row["node_id"]].append({k: row[k] for k in METADATA | {"measurements", "units", "quality_flags"}})
    if len(groups) > 200:
        raise ValueError("Dashboard import supports at most 200 nodes")
    result = []
    classifier=WeatherCategories()
    scenario_engine=HazardScenarios()
    forecast_histories = {}
    for node_id, history in sorted(groups.items()):
        history.sort(key=lambda x: utc(x["timestamp_utc"]))
        latest = history[-1]
        packet = build_packet(history, latest["timestamp_utc"])
        profile = "hourly_companion" if latest["native_interval_seconds"] == 3600 else "native_15min"
        rules = evaluate(packet, profile=profile)
        timestamp = int(utc(latest["timestamp_utc"]).timestamp()*1000)
        age = (clock-utc(latest["timestamp_utc"])).total_seconds()
        stale = age > max(120, latest["native_interval_seconds"]*2)
        forecast_histories[node_id] = [dict(timestamp=r['timestamp_utc'], **r['measurements']) for r in history]
        class_history=[dict(timestamp=r['timestamp_utc'],**r['measurements']) for r in history]
        categories=classifier.predict(class_history,latest['native_interval_seconds'])
        categories.update(observation_timestamp=timestamp,assessed_at_utc=clock.isoformat(),source_class=latest['source_class'])
        scenarios=scenario_engine.predict(class_history,latest['native_interval_seconds'])
        scenarios.update(source_class=latest['source_class'],assessed_at_utc=clock.isoformat())
        result.append(dict(id=node_id, name=node_id, lat=latest["latitude"], lng=latest["longitude"],
            lastSeen=timestamp, battery=None, anomalyIndex=None, anomalyLabel="Experimental risk assessment",
            stale=stale, reportingIntervalSeconds=latest["native_interval_seconds"],
            sourceClass=latest["source_class"], sourceId=latest["source_id"], sourceCellId=latest["source_cell_id"],
            pressureReference=latest["pressure_reference"], registrationId=latest["registration_id"],
            physicalSiteId=latest['physical_site_id'],weatherCategories=categories,hazardScenarios=scenarios,
            elevationM=latest["elevation_m"], timestamp=timestamp, sensors=latest["measurements"], units=UNITS.copy(),
            risks=rules["outputs"], stormSequence=rules["rainstorm_sequence"],
            history=[dict(timestamp=r["timestamp_utc"], **r["measurements"]) for r in history[-97:]],
            featureAvailability=packet["history_availability"],
            empiricalValidation="NOT_EVALUATED", probability=None, publicNotificationsEnabled=False,
            unavailableTargets=["flash_flood", "landslide"],
            syntheticDemo=latest["source_class"] == "synthetic_demo"))
    return apply_forecasts(result, forecast_histories, load_forecaster(Path(model_dir)), clock)


class Store:
    """Atomic whole-import replacement; no mixing demo and physical histories."""
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            audit_initialize(db)

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def replace(self, nodes):
        payloads = [(n["id"], json.dumps(n, allow_nan=False, separators=(",", ":"))) for n in nodes]
        with self.connect() as db:
            db.execute("DELETE FROM nodes")
            db.executemany("INSERT INTO nodes VALUES (?, ?)", payloads)
            audit_append(db, "DASHBOARD_SNAPSHOT", {"nodes": nodes})

    def all(self):
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute("SELECT payload FROM nodes ORDER BY id LIMIT 201")]


def create_app(db_path, *, ui_dir=None, clock=None, storm_risk_run=None, model_dir=MODEL, online_state=None):
    store = Store(db_path)
    started = time.monotonic()
    app = FastAPI(title="INDRA local dashboard adapter", version=API_VERSION)
    app.state.store = store
    engine = load_forecaster(model_dir)
    classifier=WeatherCategories()
    scenario_engine=HazardScenarios()
    app.state.forecaster = engine
    existing = store.all()
    if existing:
        if any(n.get('forecastModel', {}).get('profileSha256') != engine.profile_sha256 for n in existing):
            # Recompute old persisted predictions from retained canonical history.
            # A new model label is never attached to an old XGBoost prediction.
            now = pd.Timestamp(clock() if clock else time.time(), unit='s', tz='UTC')
            histories = {n['id']: n.get('forecastHistory', n.get('history', [])) for n in existing}
            store.replace(apply_forecasts(existing, histories, engine, now))
        existing=store.all()
        if any(n.get('weatherCategories',{}).get('profile_sha256')!=classifier.sha256 for n in existing):
            for n in existing:
                n['weatherCategories']=classifier.predict(n.get('history',[]),n['reportingIntervalSeconds'])
                n['weatherCategories'].update(observation_timestamp=n['timestamp'],assessed_at_utc=datetime.fromtimestamp(clock() if clock else time.time(),timezone.utc).isoformat(),source_class=n['sourceClass'])
            store.replace(existing)
        existing=store.all()
        if any(n.get('hazardScenarios',{}).get('config_sha256')!=scenario_engine.sha256 or n.get('hazardScenarios',{}).get('implementation_sha256')!=scenario_engine.implementation_sha256 for n in existing):
            for n in existing:
                n['hazardScenarios']=scenario_engine.predict(n.get('history',[]),n['reportingIntervalSeconds'])
                n['hazardScenarios'].update(source_class=n['sourceClass'],assessed_at_utc=datetime.fromtimestamp(clock() if clock else time.time(),timezone.utc).isoformat())
            store.replace(existing)
    storm = StormRun(storm_risk_run)
    online_learner=None
    if online_state is not None:
        if engine.profile['id']!='india_mandi_tabular_v2': raise ValueError('Online shadow learning requires the v2 fixed scaler')
        from ml.india_mandi.online import for_model
        online_learner=for_model(online_state,engine)

    @app.get('/api/model-lab')
    def model_lab():
        if engine.profile['id'] != 'india_mandi_tabular_v2':
            return dict(configured=False,active_model=engine.profile['id'],online=dict(enabled=False))
        report=json.loads((ROOT/'reports/mandi_pipeline_v2/results.json').read_text())
        if report['profile_sha256'] != engine.profile_sha256:
            raise HTTPException(422,'Model evaluation/profile identity mismatch')
        online=dict(enabled=False,role='NOT_CONFIGURED',updates=0)
        if online_learner is not None: online=online_learner.summary()
        replay_path=ROOT/'reports/mandi_pipeline_v2/online_replay.json'
        replay=json.loads(replay_path.read_text()) if replay_path.exists() else None
        return dict(configured=True,active_model=engine.profile['id'],display_name=engine.profile['display_name'],
            data_rows=report['data_rows'],source_start=report['source_start'],source_end=report['source_end'],
            rows_by_role=report['rows_by_role'],source_kind=report['source_kind'],features=len(engine.profile['features']),
            metrics={k:report['metrics'][k] for k in ('validation','future_test','new_date_extension')},
            blend=engine.weights,online=online,online_replay=replay,field_validated=False,
            test_status=report['test_status'],tabpfn_status=report['tabpfn'])

    def storm_read(method, *args):
        try:
            return method(*args)
        except (ValueError, KeyError, OSError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get('/api/storm-risk/report')
    def storm_report():
        return storm_read(storm.report)

    @app.get('/api/storm-risk/scores')
    def storm_scores(limit: int = 200):
        return storm_read(storm.scores, limit)

    @app.get('/api/storm-risk/heatmap')
    def storm_heatmap(feature: str | None = None, time: str | None = None):
        return storm_read(storm.heatmap, feature, time)

    def nodes():
        now_ms = (clock() if clock else time.time())*1000
        values = copy.deepcopy(store.all())
        for n in values:
            n["stale"] = now_ms-n["lastSeen"] > max(120, n["reportingIntervalSeconds"]*2)*1000
            n["ageSeconds"] = max(0., (now_ms-n["lastSeen"])/1000)
            n["assessmentUsableNow"] = not n["stale"]
        return values

    def node(identity):
        item = next((n for n in nodes() if n["id"] == identity), None)
        if item is None:
            raise HTTPException(404, "Unknown node")
        return item

    @app.get("/api/nodes")
    def list_nodes():
        return [{k: n[k] for k in ("id", "name", "lat", "lng", "lastSeen", "battery", "anomalyIndex", "stale",
                "sourceClass", "reportingIntervalSeconds")} for n in nodes()]

    @app.get("/api/nodes/{identity}/telemetry")
    def telemetry(identity: str):
        return node(identity)

    @app.get("/api/status")
    def status():
        items = nodes()
        return dict(appVersion=API_VERSION, uptimeSeconds=int(time.monotonic()-started), batteryVoltage=None,
            meshNodeCount=len(items), sourceClasses=sorted({n["sourceClass"] for n in items}),
            syntheticDemo=any(n["syntheticDemo"] for n in items), adapter="INDRA_READ_ONLY_LOCAL",
            rpcAvailable=False, hardwareConnected=False, empiricalHazardModels="NOT_READY",
            empiricalAccuracy="NOT_EVALUATED", publicNotificationsEnabled=False,
            forecastModel=engine.profile['id'], forecastArchitecture=engine.profile.get('family','NEURAL_XGB_RIDGE_HISTORY_ENSEMBLE'),
            forecastModelsInUse=sorted({n['forecastModel']['id'] for n in items}), forecastHistoryHours=24,
            forecastFallback='PERSISTENCE_WITH_EXPLICIT_WARMUP_STATUS', transport="HTTP_LOCAL_NO_RF",
            empty=not items, staleNodes=sum(n["stale"] for n in items))

    @app.get("/api/provenance")
    def provenance():
        try:
            proof = audit_batch(store.path)
            return {**proof['manifest'], 'batch_id': proof['batch_id'],
                    'status': 'LOCAL_ONLY', 'on_chain_verified': False}
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get('/api/parameter-heatmaps')
    def all_parameter_maps(resolution: int=24):
        try:return parameter_maps(nodes(),resolution)
        except ValueError as exc:raise HTTPException(422,str(exc)) from exc

    @app.get("/api/kriging/heatmap")
    def heatmap(channel: str='temperature_c',resolution: int=24):
        # Legacy route name retained; the actual method is explicitly IDW.
        try:return geojson(parameter_maps(nodes(),resolution),channel)
        except ValueError as exc:raise HTTPException(422,str(exc)) from exc

    @app.post("/api/rpc/{identity}")
    def rpc(identity: str):
        node(identity)
        raise HTTPException(501, "No connected hardware RPC transport; command not sent or acknowledged")

    if ui_dir is not None:
        path = Path(ui_dir)
        if not (path/"index.html").is_file():
            raise ValueError("Build the dashboard before serving its static assets")
        app.mount("/", StaticFiles(directory=path, html=True), name="dashboard")
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT/"data/himachal/dashboard.sqlite")
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument("--observations", type=Path)
    sources.add_argument("--demo", action="store_true", help="Replace store with clearly marked synthetic fixtures")
    sources.add_argument('--weather-demo',action='store_true',help='All-category multi-location synthetic engineering demonstration')
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument('--host',default='127.0.0.1',choices=['127.0.0.1','0.0.0.0','::1','::'],help='Listen address; loopback by default, explicit public interface for hosted deployments')
    parser.add_argument("--ui", type=Path)
    parser.add_argument('--storm-risk-run', type=Path, help='Owner-generated experimental ERA5 run directory')
    parser.add_argument('--forecast-model',type=Path,default=MODEL,help='Versioned gateway model; v1 remains available explicitly')
    parser.add_argument('--online-state',type=Path,help='Optional delayed-label shadow checkpoint, never overwrites offline outputs')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use a local unprivileged port")
    app = create_app(args.db, ui_dir=args.ui, storm_risk_run=args.storm_risk_run,model_dir=args.forecast_model,online_state=args.online_state)
    if args.observations or args.demo or args.weather_demo:
        raw = weather_demo_observations() if args.weather_demo else demo_observations() if args.demo else read_observations(args.observations)
        prepared = assess(raw,model_dir=args.forecast_model)
        app.state.store.replace(prepared)
        if args.online_state is not None:
            from ml.india_mandi.online import ingest_native
            ingest_native(raw,args.online_state,app.state.forecaster)
        print(json.dumps(dict(nodes=len(prepared), mode="SYNTHETIC_DEMO" if args.demo or args.weather_demo else "OPERATOR_IMPORT",
            probabilities="UNAVAILABLE", hardware_rpc=False)))
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
