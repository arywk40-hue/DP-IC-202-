"""Read-only dashboard backed by the Open-Meteo modeled grid at Mandi."""
from __future__ import annotations

import argparse
from collections import defaultdict
import copy
from datetime import datetime, timezone
from functools import lru_cache
import json
import math
from pathlib import Path
import sqlite3
import threading
import time

from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
import pandas as pd

from server.auth import AuthStore, GoogleAuthPayload, DemoAuthPayload, verify_google_credential, GOOGLE_CLIENT_ID

from ml.himachal.contracts import snapshot
from ml.operational.contracts import UNITS, utc
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.india_mandi.registry import ACTIVE_MODEL, load_forecaster
from contracts.provenance import append as audit_append, initialize as audit_initialize, batch as audit_batch
from ml.himachal.parameter_maps import parameter_maps, geojson
from ml.himachal.weather_categories import WeatherCategories
from ml.himachal.hazard_scenarios import HazardScenarios
from ml.india_mandi.live import collect as collect_mandi_api

ROOT = Path(__file__).resolve().parents[1]
MODEL = ACTIVE_MODEL
API_VERSION = "0.7.0"
MAX_ROWS = 50_000


@lru_cache(maxsize=1)
def hazard_engines():
    """Load the versioned synthetic pattern and scenario engines once."""
    return WeatherCategories(), HazardScenarios()


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
        groups[row["node_id"]].append(row)
    if len(groups) > 200:
        raise ValueError("Dashboard import supports at most 200 nodes")
    result = []
    classifier, scenario_engine = hazard_engines()
    forecast_histories = {}
    for node_id, history in sorted(groups.items()):
        history.sort(key=lambda x: utc(x["timestamp_utc"]))
        timestamps = [utc(x["timestamp_utc"]) for x in history]
        if len(set(timestamps)) != len(timestamps):
            raise ValueError("Duplicate Mandi API timestamps are not accepted")
        identity = (history[0]["source_id"], history[0]["source_cell_id"],
                    history[0]["latitude"], history[0]["longitude"], history[0]["pressure_reference"])
        if any((r["source_id"], r["source_cell_id"], r["latitude"], r["longitude"], r["pressure_reference"]) != identity for r in history):
            raise ValueError("Mandi API source identity or fixed site changed inside the history")
        if identity[2:] != (31.71, 76.93, "grid_surface"):
            raise ValueError("Dashboard accepts only the configured Mandi model-grid point")
        latest = history[-1]
        timestamp = int(utc(latest["timestamp_utc"]).timestamp()*1000)
        age = (clock-utc(latest["timestamp_utc"])).total_seconds()
        stale = age > max(120, latest["native_interval_seconds"]*2)
        forecast_histories[node_id] = [dict(timestamp=r['timestamp_utc'], **r['measurements']) for r in history]
        class_history = [dict(timestamp=r["timestamp_utc"], **r["measurements"]) for r in history]
        source_provenance = dict(
            source_class=latest["source_class"],
            source_id=latest["source_id"],
            source_cell_id=latest["source_cell_id"],
            pressure_reference=latest["pressure_reference"],
            coordinates=[latest["latitude"], latest["longitude"]],
        )
        categories = classifier.predict(class_history, latest["native_interval_seconds"])
        categories.update(
            observation_timestamp=utc(latest["timestamp_utc"]).isoformat(),
            assessed_at_utc=clock.isoformat(),
            **source_provenance,
        )
        scenarios = scenario_engine.predict(class_history, latest["native_interval_seconds"])
        scenarios.update(assessed_at_utc=clock.isoformat(), **source_provenance)
        result.append(dict(id=node_id, name=node_id, lat=latest["latitude"], lng=latest["longitude"],
            lastSeen=timestamp,
            stale=stale, reportingIntervalSeconds=latest["native_interval_seconds"],
            sourceClass=latest["source_class"], sourceId=latest["source_id"], sourceCellId=latest["source_cell_id"],
            pressureReference=latest["pressure_reference"], registrationId=latest["registration_id"],
            physicalSiteId=latest['physical_site_id'],
            elevationM=latest["elevation_m"], timestamp=timestamp, sensors=latest["measurements"], units=UNITS.copy(),
            history=[dict(timestamp=r["timestamp_utc"], **r["measurements"]) for r in history[-97:]],
            featureAvailability={"history_rows": len(history), "history_hours": max(0, len(history) - 1)},
            weatherCategories=categories, hazardScenarios=scenarios,
            syntheticDemo=False))
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


def create_app(db_path, *, ui_dir=None, clock=None, model_dir=MODEL, demo_auth_enabled=False, mandi_data_dir=None, mandi_refresh_seconds=900):
    store = Store(db_path)
    started = time.monotonic()
    app = FastAPI(title="INDRA local dashboard adapter", version=API_VERSION)
    app.state.store = store
    engine = load_forecaster(model_dir)
    app.state.forecaster = engine
    app.state.mandi_feed = dict(enabled=False, connected=False, provider="Open-Meteo", coordinates=[31.71, 76.93], last_success_utc=None, latest_valid_utc=None, error=None)

    @app.get('/api/model-lab')
    def model_lab():
        if engine.profile['id'] != 'india_mandi_tabular_v2':
            return dict(configured=False,active_model=engine.profile['id'],online=dict(enabled=False))
        report=json.loads((ROOT/'ml/reports/mandi_pipeline_v2/results.json').read_text())
        if report['profile_sha256'] != engine.profile_sha256:
            raise HTTPException(422,'Model evaluation/profile identity mismatch')
        online=dict(enabled=False,role='NOT_CONFIGURED',updates=0)
        replay_path=ROOT/'ml/reports/mandi_pipeline_v2/online_replay.json'
        replay=json.loads(replay_path.read_text()) if replay_path.exists() else None
        return dict(configured=True,active_model=engine.profile['id'],display_name=engine.profile['display_name'],
            data_rows=report['data_rows'],source_start=report['source_start'],source_end=report['source_end'],
            rows_by_role=report['rows_by_role'],source_kind=report['source_kind'],features=len(engine.profile['features']),
            metrics={k:report['metrics'][k] for k in ('validation','future_test','new_date_extension')},
            blend=engine.weights,online=online,online_replay=replay,field_validated=False,
            test_status=report['test_status'],tabpfn_status=report['tabpfn'])

    def nodes():
        now_ms = (clock() if clock else time.time())*1000
        values = copy.deepcopy(store.all())
        legacy = [n for n in values if n.get("forecastModel", {}).get("id") != engine.profile["id"]]
        if legacy:
            histories = {
                n["id"]: n.get("history", n.get("forecastHistory", []))
                for n in legacy
            }
            issued = pd.Timestamp(datetime.fromtimestamp(now_ms / 1000, timezone.utc))
            apply_forecasts(legacy, histories, engine, issued)
        for n in values:
            replacement = next((item for item in legacy if item["id"] == n["id"]), None)
            if replacement is not None:
                n.update(replacement)
            if "weatherCategories" not in n or n["weatherCategories"].get("model_id") != "himachal_sensor_patterns_v1":
                source = dict(
                    source_class=n.get("sourceClass"), source_id=n.get("sourceId"),
                    source_cell_id=n.get("sourceCellId"),
                    pressure_reference=n.get("pressureReference"),
                    coordinates=[n.get("lat"), n.get("lng")],
                )
                history = n.get("history", n.get("forecastHistory", []))
                classification = hazard_engines()[0].predict(history, n.get("reportingIntervalSeconds", 3600))
                classification.update(observation_timestamp=datetime.fromtimestamp(n["lastSeen"] / 1000, timezone.utc).isoformat(), **source)
                n["weatherCategories"] = classification
            if "hazardScenarios" not in n or n["hazardScenarios"].get("model_id") != "himalayan_synthetic_scenarios_v1":
                source = dict(
                    source_class=n.get("sourceClass"), source_id=n.get("sourceId"),
                    source_cell_id=n.get("sourceCellId"),
                    pressure_reference=n.get("pressureReference"),
                    coordinates=[n.get("lat"), n.get("lng")],
                )
                history = n.get("history", n.get("forecastHistory", []))
                scenarios = hazard_engines()[1].predict(history, n.get("reportingIntervalSeconds", 3600))
                scenarios.update(assessed_at_utc=issued.isoformat(), **source)
                n["hazardScenarios"] = scenarios
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
        return [{k: n[k] for k in ("id", "name", "lat", "lng", "lastSeen", "stale",
                "sourceClass", "reportingIntervalSeconds")} for n in nodes()]

    @app.get("/api/nodes/{identity}/telemetry")
    def telemetry(identity: str):
        return node(identity)

    @app.get("/api/status")
    def status():
        items = nodes()
        return dict(appVersion=API_VERSION, uptimeSeconds=int(time.monotonic()-started),
            locationCount=len(items), sourceClasses=sorted({n["sourceClass"] for n in items}),
            syntheticDemo=False, adapter="OPEN_METEO_MANDI_READ_ONLY",
            mandiApi=copy.deepcopy(app.state.mandi_feed),
            forecastModel=engine.profile['id'], forecastArchitecture=engine.profile.get('family','NEURAL_XGB_RIDGE_HISTORY_ENSEMBLE'),
            forecastModelsInUse=sorted({n['forecastModel']['id'] for n in items}), forecastHistoryHours=24,
            forecastFallback='PERSISTENCE_WITH_EXPLICIT_WARMUP_STATUS',
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

    auth_store = AuthStore(db_path)

    class MandiApiPoller:
        """Refresh the single Mandi grid record from Open-Meteo on a fixed cadence."""
        def __init__(self):
            self.stop_event = threading.Event()
            self.thread = None

        def refresh(self):
            raw_rows, receipt = collect_mandi_api(mandi_data_dir or ROOT/"ml/data/himachal/mandi_api_live")
            if any(r.get("source_class") != "modeled_grid" or r.get("source_id") != "OpenMeteo_current_ECMWF_IFS_CAMS_global" for r in raw_rows):
                raise ValueError("Only the configured Mandi Open-Meteo source is accepted")
            prepared = assess(raw_rows, model_dir=model_dir)
            if not prepared or any(n["sourceClass"] != "modeled_grid" for n in prepared):
                raise ValueError("Mandi API returned no valid modeled-grid observations")
            store.replace(prepared)
            app.state.mandi_feed.update(enabled=True, connected=True,
                last_success_utc=receipt["retrieved_at_utc"], latest_valid_utc=receipt["latest_valid_utc"], error=None)

        def run(self):
            while not self.stop_event.is_set():
                try:
                    self.refresh()
                except Exception as exc:
                    app.state.mandi_feed.update(enabled=True, connected=False, error=f"{type(exc).__name__}: {exc}")
                self.stop_event.wait(mandi_refresh_seconds)

        def start(self):
            if self.thread is None:
                self.stop_event.clear()
                app.state.mandi_feed.update(enabled=True)
                self.thread = threading.Thread(target=self.run, name="indra-mandi-open-meteo", daemon=True)
                self.thread.start()

        def stop(self):
            self.stop_event.set()
            if self.thread is not None:
                self.thread.join(timeout=2)

    app.state.mandi_poller = MandiApiPoller()

    @app.get('/api/auth/config')
    def auth_config():
        return dict(googleClientId=GOOGLE_CLIENT_ID, demoAuthEnabled=demo_auth_enabled,
                    authEnabled=bool(GOOGLE_CLIENT_ID) or demo_auth_enabled,
                    mode='google_oauth' if GOOGLE_CLIENT_ID else 'demo' if demo_auth_enabled else 'disabled')

    @app.post('/api/auth/google')
    def auth_google(payload: GoogleAuthPayload):
        try:
            user_info = verify_google_credential(payload.credential, GOOGLE_CLIENT_ID)
            user = auth_store.upsert_user(user_info)
            token = auth_store.create_session(user['id'])
            return dict(token=token, user=user)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(503, 'Google sign-in is not configured') from exc

    @app.post('/api/auth/demo-login')
    def auth_demo(payload: DemoAuthPayload = None):
        if not demo_auth_enabled:
            raise HTTPException(404, 'Demo sign-in is disabled')
        user_info = dict(id='demo_local_operator', email='demo@localhost',
                         name='Local Demo Operator', picture='', provider='demo')
        user = auth_store.upsert_user(user_info)
        token = auth_store.create_session(user['id'])
        return dict(token=token, user=user)

    @app.get('/api/auth/me')
    def auth_me(authorization: str | None = Header(None)):
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(401, 'Authentication required')
        token = authorization[7:].strip()
        user = auth_store.get_user_by_token(token)
        if not user:
            raise HTTPException(401, 'Invalid or expired session')
        return dict(user=user)

    @app.post('/api/auth/logout')
    def auth_logout(authorization: str | None = Header(None)):
        if authorization and authorization.startswith('Bearer '):
            token = authorization[7:].strip()
            auth_store.delete_session(token)
        return dict(ok=True)

    if ui_dir is not None:
        path = Path(ui_dir)
        if not (path/"index.html").is_file():
            raise ValueError("Build the dashboard before serving its static assets")
        app.mount("/", StaticFiles(directory=path, html=True), name="dashboard")
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT/"ml/data/himachal/mandi_api.sqlite")
    parser.add_argument("--mandi-data-dir", type=Path, default=ROOT/"ml/data/himachal/mandi_api_live", help="Local rolling cache of Open-Meteo Mandi responses")
    parser.add_argument("--refresh-seconds", type=int, default=900, help="Mandi API polling interval")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument('--host',default='127.0.0.1',choices=['127.0.0.1','0.0.0.0','::1','::'],help='Listen address; loopback by default, explicit public interface for hosted deployments')
    parser.add_argument("--ui", type=Path)
    parser.add_argument('--forecast-model',type=Path,default=MODEL,help='Versioned gateway model; v1 remains available explicitly')
    parser.add_argument('--enable-demo-auth', action='store_true', help='Enable a fixed local demo identity; never use for hosted deployments')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use a local unprivileged port")
    if args.refresh_seconds < 60:
        parser.error("Use a refresh interval of at least 60 seconds")
    app = create_app(args.db, ui_dir=args.ui, model_dir=args.forecast_model,mandi_data_dir=args.mandi_data_dir,mandi_refresh_seconds=args.refresh_seconds)
    # Start with an empty runtime store: old demo/import rows must never appear
    # while the Mandi API connection is being established.
    app.state.store.replace([])
    app.state.mandi_poller.start()
    print(json.dumps(dict(mode="MANDI_OPEN_METEO_API", coordinates=[31.71, 76.93], refresh_seconds=args.refresh_seconds)))
    import uvicorn
    try:
        uvicorn.run(app, host=args.host, port=args.port)
    finally:
        app.state.mandi_poller.stop()


if __name__ == "__main__":
    main()
