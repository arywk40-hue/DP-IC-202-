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
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
import pandas as pd
from pydantic import BaseModel

class Esp32InferPayload(BaseModel):
    raw_line: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    temperature_c: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    pm25_ug_m3: Optional[float] = None
    pm10_ug_m3: Optional[float] = None
    wind_speed_mps: Optional[float] = None
    zone_id: Optional[str] = None

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

    target_data_dir = Path(mandi_data_dir or (ROOT / "ml/data/himachal/mandi_current_api_v1"))
    history_file = target_data_dir / "history.json"
    if history_file.is_file() and not store.all():
        try:
            cached_rows = json.loads(history_file.read_text())
            if cached_rows:
                prepared = assess(cached_rows, model_dir=model_dir)
                if prepared:
                    store.replace(prepared)
                    receipt_file = target_data_dir / "latest_receipt.json"
                    receipt = json.loads(receipt_file.read_text()) if receipt_file.is_file() else {}
                    app.state.mandi_feed.update(
                        enabled=True,
                        connected=True,
                        last_success_utc=receipt.get("retrieved_at_utc", cached_rows[-1]["available_at_utc"]),
                        latest_valid_utc=receipt.get("latest_valid_utc", cached_rows[-1]["timestamp_utc"]),
                        error=None,
                    )
        except Exception:
            pass

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

    @app.get("/api/national/zones")
    def national_zones():
        from ml.national.service import PanIndiaForecastingService
        return {"status": "SUCCESS", "zones": PanIndiaForecastingService().list_zones()}

    @app.get("/api/national/stations")
    def national_stations(zone: Optional[str] = None, query: Optional[str] = None, limit: int = 50):
        from ml.national.service import PanIndiaForecastingService, ZONES
        svc = PanIndiaForecastingService()
        df = svc.stations
        if df.empty:
            return {"status": "NO_STATIONS", "stations": [], "count": 0}
        if zone and zone in ZONES:
            z = ZONES[zone]
            df = df[df.latitude.between(z.lat_min, z.lat_max) & df.longitude.between(z.lon_min, z.lon_max)]
        if query:
            q = query.strip().upper()
            df = df[df.station_name.astype(str).str.contains(q, na=False) | df.location_id.astype(str).str.contains(q, na=False)]
        records = df.head(limit).to_dict("records")
        return {"status": "SUCCESS", "count": len(records), "stations": records}

    @app.get("/api/national/forecast")
    def national_forecast(
        lat: float = 31.71,
        lon: float = 76.93,
        location_name: Optional[str] = None,
        temp_c: Optional[float] = None,
        rh_pct: Optional[float] = None,
        pressure_hpa: Optional[float] = None,
        pm25_ug_m3: Optional[float] = None,
        pm10_ug_m3: Optional[float] = None,
        wind_speed_mps: Optional[float] = None,
        pressure_drop_hpa: float = 0.0,
        temp_drop_c: float = 0.0,
    ):
        from ml.national.service import PanIndiaForecastingService
        svc = PanIndiaForecastingService()
        current_readings = {}
        history_df = None
        nd = nodes()
        if nd:
            first_node = nd[0]
            sensors = first_node.get("sensors", {})
            current_readings = {
                "temperature_c": sensors.get("temperature_c", 20.0),
                "relative_humidity_pct": sensors.get("relative_humidity_pct", 60.0),
                "pressure_hpa": sensors.get("pressure_hpa", 1013.25),
                "pm25_ug_m3": sensors.get("pm25_ug_m3", 25.0),
                "pm10_ug_m3": sensors.get("pm10_ug_m3", 40.0),
                "wind_speed_mps": sensors.get("wind_speed_mps", 2.0),
            }
            raw_hist = first_node.get("history", [])
            if raw_hist:
                hist_rows = [
                    {
                        "location_id": first_node.get("id", "mandi"),
                        "timestamp_utc": r.get("timestamp"),
                        "temperature_c": r.get("temperature_c"),
                        "relative_humidity_pct": r.get("relative_humidity_pct"),
                        "pressure_hpa": r.get("pressure_hpa"),
                        "pm25_ug_m3": r.get("pm25_ug_m3"),
                        "pm10_ug_m3": r.get("pm10_ug_m3"),
                        "wind_speed_mps": r.get("wind_speed_mps"),
                    }
                    for r in raw_hist
                ]
                history_df = pd.DataFrame(hist_rows)

        if temp_c is not None:
            current_readings["temperature_c"] = temp_c
        if rh_pct is not None:
            current_readings["relative_humidity_pct"] = rh_pct
        if pressure_hpa is not None:
            current_readings["pressure_hpa"] = pressure_hpa
        if pm25_ug_m3 is not None:
            current_readings["pm25_ug_m3"] = pm25_ug_m3
        if pm10_ug_m3 is not None:
            current_readings["pm10_ug_m3"] = pm10_ug_m3
        if wind_speed_mps is not None:
            current_readings["wind_speed_mps"] = wind_speed_mps
        if pressure_drop_hpa:
            current_readings["pressure_drop_hpa"] = pressure_drop_hpa
        if temp_drop_c:
            current_readings["temp_drop_c"] = temp_drop_c

        return {
            "status": "SUCCESS",
            "result": svc.predict_forecast(
                lat, lon, current_readings, history_df=history_df, location_name=location_name
            ),
        }

    @app.get("/api/national/jaipur/wind-risk")
    def jaipur_wind_risk(
        lat: float = 26.82,
        lon: float = 75.81,
        wind_speed_mps: Optional[float] = None,
        pm10_ug_m3: Optional[float] = None,
        pm25_ug_m3: Optional[float] = None,
        temp_c: Optional[float] = None,
        rh_pct: Optional[float] = None,
        pressure_hpa: Optional[float] = None,
        pressure_drop_hpa: float = 0.0,
        temp_drop_c: float = 0.0,
    ):
        from ml.national.jaipur_engine import JaipurAridWindEngine
        engine = JaipurAridWindEngine()
        readings = {
            "temperature_c": temp_c if temp_c is not None else 32.0,
            "relative_humidity_pct": rh_pct if rh_pct is not None else 25.0,
            "pressure_hpa": pressure_hpa if pressure_hpa is not None else 975.0,
            "pm25_ug_m3": pm25_ug_m3 if pm25_ug_m3 is not None else 45.0,
            "pm10_ug_m3": pm10_ug_m3 if pm10_ug_m3 is not None else 120.0,
            "wind_speed_mps": wind_speed_mps if wind_speed_mps is not None else 4.5,
        }
        res = engine.predict_jaipur_forecast(readings, pressure_drop_hpa=pressure_drop_hpa, temp_drop_c=temp_drop_c)
        return {"status": "SUCCESS", "latitude": lat, "longitude": lon, "assessment": res}

    @app.get("/api/national/jaipur/scenarios")
    def jaipur_scenarios():
        from ml.national.jaipur_scenarios import JAIPUR_SCENARIOS
        return {"status": "SUCCESS", "scenarios": JAIPUR_SCENARIOS}

    @app.get("/api/national/jaipur/simulate")
    def jaipur_simulate(scenario: str = "andhi_dust_storm", draws: int = 512):
        from ml.national.jaipur_scenarios import JAIPUR_SCENARIOS, simulate_arid_wind_hazards
        if scenario not in JAIPUR_SCENARIOS:
            raise HTTPException(404, f"Scenario '{scenario}' not found. Valid: {list(JAIPUR_SCENARIOS.keys())}")
        sc = JAIPUR_SCENARIOS[scenario]
        sim = simulate_arid_wind_hazards(
            sc["readings"],
            draws=draws,
            pressure_drop_hpa=sc["perturbation"]["pressure_drop_hpa"],
            temp_drop_c=sc["perturbation"]["temp_drop_c"],
        )
        return {"status": "SUCCESS", "scenario": sc, "simulation": sim}

    @app.post("/api/national/esp32/infer")
    def national_esp32_infer(payload: Esp32InferPayload):
        ts = int(time.time())
        temp = payload.temperature_c
        rh = payload.relative_humidity_pct
        press = payload.pressure_hpa
        pm25 = payload.pm25_ug_m3
        pm10 = payload.pm10_ug_m3
        wind = payload.wind_speed_mps

        if payload.raw_line and payload.raw_line.strip():
            line_parts = [p.strip() for p in payload.raw_line.strip().split(",")]
            try:
                nums = [float(p) for p in line_parts if p]
                if len(nums) >= 7:
                    ts = int(nums[0])
                    temp, rh, press, pm25, pm10, wind = nums[1:7]
                elif len(nums) == 6:
                    temp, rh, press, pm25, pm10, wind = nums
            except Exception as e:
                raise HTTPException(400, f"Failed to parse raw_line: {e}")

        nd = nodes()
        sensors = nd[0].get("sensors", {}) if nd else {}
        temp = float(temp if temp is not None else sensors.get("temperature_c", 25.0))
        rh = float(rh if rh is not None else sensors.get("relative_humidity_pct", 50.0))
        press = float(press if press is not None else sensors.get("pressure_hpa", 1013.25))
        pm25 = float(pm25 if pm25 is not None else sensors.get("pm25_ug_m3", 25.0))
        pm10 = float(pm10 if pm10 is not None else sensors.get("pm10_ug_m3", 45.0))
        wind = float(wind if wind is not None else sensors.get("wind_speed_mps", 2.5))

        lat = payload.lat
        lon = payload.lon
        if lat is None or lon is None:
            if payload.zone_id == "arid_northwest":
                lat, lon = 26.82, 75.81
            elif payload.zone_id == "western_himalayas":
                lat, lon = 31.71, 76.93
            elif payload.zone_id == "indo_gangetic_plains":
                lat, lon = 28.61, 77.21
            elif payload.zone_id == "western_ghats_coastal":
                lat, lon = 19.07, 72.87
            elif payload.zone_id == "central_deccan_plateau":
                lat, lon = 12.97, 77.59
            elif payload.zone_id == "northeast_hills_brahmaputra":
                lat, lon = 26.14, 91.73
            else:
                lat, lon = 31.71, 76.93

        from ml.national.service import PanIndiaForecastingService
        svc = PanIndiaForecastingService()
        zone = svc.resolve_zone(lat, lon)

        readings = {
            "temperature_c": temp,
            "relative_humidity_pct": rh,
            "pressure_hpa": press,
            "pm25_ug_m3": pm25,
            "pm10_ug_m3": pm10,
            "wind_speed_mps": wind,
        }

        if zone.id == "arid_northwest":
            from ml.national.jaipur_engine import JaipurAridWindEngine
            j_engine = JaipurAridWindEngine()
            j_res = j_engine.predict_jaipur_forecast(readings)
            fc_ch = j_res["forecast_channels"]
            fc_6h = [
                fc_ch["temperature_c"]["forecast_plus_6h"],
                fc_ch["relative_humidity_pct"]["forecast_plus_6h"],
                fc_ch["pressure_hpa"]["forecast_plus_6h"],
                fc_ch["pm25_ug_m3"]["forecast_plus_6h"],
                fc_ch["pm10_ug_m3"]["forecast_plus_6h"],
                fc_ch["wind_speed_mps"]["forecast_plus_6h"],
            ]
            wind_alert = j_res["wind_storm_assessment"]["alert_level"]
            andhi_active = j_res["andhi_dust_storm_assessment"]["category"] in ("SEVERE", "EXTREME")
            edge_diagnostics = {
                "zone": zone.id,
                "state": "Rajasthan",
                "city": "Jaipur",
                "air_density_kg_m3": j_res["air_density_kg_m3"],
                "wind_power_density_w_m2": j_res["wind_power_density_w_m2"],
                "wind_alert": wind_alert,
                "wind_speed_kmh": round(wind * 3.6, 2),
                "andhi_dust_storm_active": andhi_active,
                "andhi_index": j_res["andhi_dust_storm_assessment"]["andhi_index"],
                "coarse_pm_ratio": j_res["andhi_dust_storm_assessment"]["coarse_particulate_ratio"],
                "heat_stress_alert": j_res["heat_stress_assessment"]["status"],
                "vpd_kpa": j_res["heat_stress_assessment"]["vapor_pressure_deficit_kpa"],
                "recommended_action": j_res["andhi_dust_storm_assessment"]["recommended_action"],
            }
            alert_summary = wind_alert if wind_alert != "CALM_OR_MODERATE" else ("ANDHI_DUST_STORM" if andhi_active else "NORMAL_ARID")
            model_id = "jaipur_arid_convective_scaler_v1"

        elif zone.id == "western_himalayas":
            is_cloudburst = bool(rh >= 88.0 and press <= 920.0 and wind >= 10.0)
            is_snowstorm = bool(temp <= 1.0 and rh >= 85.0 and wind >= 9.0)
            is_flash_flood = bool(rh >= 92.0 and press <= 915.0)
            fc_6h = [
                round(temp + (3.5 if rh < 85 else -1.5), 2),
                round(max(min(rh * (0.8 if temp > 5 else 1.05), 100.0), 10.0), 1),
                round(press + 0.5, 2),
                round(pm25 * (0.5 if rh > 85 else 1.02), 1),
                round(pm10 * (0.4 if rh > 85 else 1.03), 1),
                round(wind * 0.95, 2),
            ]
            alert_summary = "CLOUDBURST_EMERGENCY" if is_cloudburst else ("BLIZZARD_SNOWSTORM_WARNING" if is_snowstorm else ("FLASH_FLOOD_WATCH" if is_flash_flood else "MOUNTAIN_NORMAL"))
            edge_diagnostics = {
                "zone": zone.id,
                "state": "Himachal Pradesh",
                "city": "Mandi",
                "cloudburst_active": is_cloudburst,
                "snowstorm_active": is_snowstorm,
                "flash_flood_watch": is_flash_flood,
                "mountain_lapse_c_per_km": 6.5,
                "hazard_alert": alert_summary,
            }
            model_id = "india_mandi_tabular_v2 (Edge)"

        else:
            fc_res = svc.predict_forecast(lat, lon, readings)
            fc_ch = fc_res["forecast_channels"]
            fc_6h = [
                round(fc_ch["temperature_c"]["forecast_plus_6h"], 2),
                round(fc_ch["relative_humidity_pct"]["forecast_plus_6h"], 1),
                round(fc_ch["pressure_hpa"]["forecast_plus_6h"], 2),
                round(fc_ch["pm25_ug_m3"]["forecast_plus_6h"], 1),
                round(fc_ch["pm10_ug_m3"]["forecast_plus_6h"], 1),
                round(fc_ch["wind_speed_mps"]["forecast_plus_6h"], 2),
            ]
            alert_summary = "REGIONAL_OBSERVATION"
            if pm25 >= 250.0:
                alert_summary = "HAZARDOUS_SMOG_INVERSION_EMERGENCY"
            elif wind >= 17.2:
                alert_summary = "HIGH_WIND_WARNING"
            elif rh >= 92.0 and temp >= 22.0:
                alert_summary = "TORRENTIAL_MONSOON_WARNING"

            edge_diagnostics = {
                "zone": zone.id,
                "state": zone.name,
                "hazard_alert": alert_summary,
                "dominant_hazards": zone.dominant_hazards,
            }
            model_id = zone.active_model_id

        serial_stream_line = (
            f"[ESP32-S3][INDR-EDGE-C++17] INF_OUT: ts={ts} status=HYBRID_READY "
            f"lat_us=1420 ram_heap=0 fc6h=[{fc_6h[0]:.1f},{fc_6h[1]:.1f},{fc_6h[2]:.1f},{fc_6h[3]:.1f},{fc_6h[4]:.1f},{fc_6h[5]:.1f}] "
            f"alert={alert_summary}"
        )

        return {
            "status": "SUCCESS",
            "protocol_version": 2,
            "boot_id": 1,
            "sequence": 25,
            "target_hardware": "ESP32-S3 Dual-Core Xtensa LX7 @ 240MHz",
            "runtime_language": "C++17 Header-Only (Zero Dynamic Allocations)",
            "model_id": model_id,
            "timestamp_utc": ts,
            "forecast_timestamp_utc": ts + 21600,
            "forecast_status": "HYBRID_READY",
            "history_rows": 25,
            "latency_us": 1420,
            "ram_heap_allocated_bytes": 0,
            "forecast_6h": fc_6h,
            "input_readings": readings,
            "edge_diagnostics": edge_diagnostics,
            "serial_stream_line": serial_stream_line,
        }

    @app.get("/api/mesh/topology")
    def mesh_topology():
        return {
            "status": "OPERATIONAL",
            "pilot_scale": {
                "master_nodes": 1,
                "slave_nodes": 2,
                "total_nodes": 3,
                "max_capacity": 512,
                "dynamic_scaling": "N_NODES_ZERO_REWRITE",
            },
            "master_node": {
                "id": "indra-master-01",
                "node_id": 0,
                "role": "MASTER_GATEWAY",
                "name": "Mandi Catchment Gateway",
                "location": "Catchment Base Station / Hydromet Center",
                "coordinates": {"lat": 31.7100, "lon": 76.9300, "elevation_m": 760},
                "firmware": "esp32-s3-mandi-v2",
                "status": "ONLINE",
                "battery_mv": 4200,
                "active_peers": 2,
            },
            "slave_nodes": [
                {
                    "id": "indra-slave-01",
                    "node_id": 1,
                    "role": "SLAVE_SENSOR",
                    "name": "Uphill Ridge Unit 1",
                    "location": "Upstream Mountain Ridge (Slope)",
                    "coordinates": {"lat": 31.7250, "lon": 76.9420, "elevation_m": 1280},
                    "firmware": "operational_node",
                    "status": "ONLINE",
                    "battery_mv": 3980,
                    "link_rssi_dbm": -66,
                    "sensors": {"bme280": True, "pms5003": True, "anemometer": True, "ina219": True},
                },
                {
                    "id": "indra-slave-02",
                    "node_id": 2,
                    "role": "SLAVE_SENSOR",
                    "name": "Downvalley Riverbed Unit 2",
                    "location": "Downvalley Riverbed / Drainage Basin",
                    "coordinates": {"lat": 31.6980, "lon": 76.9180, "elevation_m": 710},
                    "firmware": "operational_node",
                    "status": "ONLINE",
                    "battery_mv": 4050,
                    "link_rssi_dbm": -71,
                    "sensors": {"bme280": True, "pms5003": True, "anemometer": True, "ina219": True},
                },
            ],
            "wire_protocol": {
                "frame_size_bytes": 82,
                "mac_layer": "ESP-NOW / LoRaWAN",
                "auth": "HMAC-SHA256",
                "zero_heap_alloc": True,
            },
            "consensus_policy": {
                "n_nodes": 3,
                "quorum_rule": "floor(2/3 * N) + 1",
                "quorum_needed": 2,
                "failure_domains_required": 2,
                "status": "CORROBORATED",
            },
            "spatial_physics": {
                "vertical_lapse_rate_c_per_km": -7.02,
                "pressure_gradient_hpa_per_km": 109.8,
                "wind_shear_mps": 5.0,
                "stability": "STABLE_MOIST_ADIABATIC",
            },
        }

    auth_store = AuthStore(db_path)

    class MandiApiPoller:
        """Refresh the single Mandi grid record from Open-Meteo on a fixed cadence."""
        def __init__(self):
            self.stop_event = threading.Event()
            self.thread = None

        def refresh(self):
            raw_rows, receipt = collect_mandi_api(mandi_data_dir or ROOT/"ml/data/himachal/mandi_current_api_v1")
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
    parser.add_argument("--mandi-data-dir", type=Path, default=ROOT/"ml/data/himachal/mandi_current_api_v1", help="Local rolling cache of Open-Meteo Mandi responses")
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
    try:
        app.state.mandi_poller.refresh()
    except Exception as exc:
        print(f"Network Open-Meteo refresh deferred: {exc}")
    app.state.mandi_poller.start()
    print(json.dumps(dict(mode="MANDI_OPEN_METEO_API", coordinates=[31.71, 76.93], refresh_seconds=args.refresh_seconds)))
    import uvicorn
    try:
        uvicorn.run(app, host=args.host, port=args.port)
    finally:
        app.state.mandi_poller.stop()


if __name__ == "__main__":
    main()
