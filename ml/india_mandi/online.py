"""Durable numerical shadow learning with exact +6h delayed truth.

The active offline forecast is never overwritten. Forecasts are persisted before
any update; late historical inputs cannot masquerade as live forecast accuracy.
SQLite checkpoints contain numerical SGD state, never executable pickle objects.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import SGDRegressor

from ml.india_mandi.hybrid import bounded
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from contracts.provenance import append as audit_append


def stamp(value):
    t = pd.Timestamp(value)
    if pd.isna(t) or t.tzinfo is None:
        raise ValueError("Timezone-aware online clock required")
    return int(t.timestamp())


def encode(value):
    return json.dumps(value, separators=(",", ":"), allow_nan=False, sort_keys=True)


class OnlineLearner:
    """Single-writer transactional SGD residual corrector, separated by source/site."""

    def __init__(self, path, model_sha, mean, std, residual_scale):
        self.path, self.model_sha = Path(path), model_sha
        self.mean, self.std, self.scale = (
            np.asarray(x, float) for x in (mean, std, residual_scale)
        )
        if (
            self.mean.shape != (66,)
            or self.std.shape != (66,)
            or self.scale.shape != (6,)
            or not all(np.isfinite(x).all() for x in (self.mean, self.std, self.scale))
            or (self.std <= 0).any()
            or (self.scale <= 0).any()
        ):
            raise ValueError("Fixed finite train-only online scaler required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        identity = encode(
            {
                "schema": "indra_delayed_numeric_sgd_v1",
                "model": model_sha,
                "mean": self.mean.tolist(),
                "std": self.std.tolist(),
                "residual_scale": self.scale.tolist(),
            }
        )
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS identity (id INTEGER PRIMARY KEY, value TEXT NOT NULL)"
            )
            row = db.execute("SELECT value FROM identity WHERE id=1").fetchone()
            if row and json.loads(row[0]) != json.loads(identity):
                raise ValueError(
                    "Online checkpoint belongs to a different model/scaler"
                )
            db.execute("INSERT OR IGNORE INTO identity VALUES (1,?)", (identity,))
            db.execute(
                "CREATE TABLE IF NOT EXISTS state (namespace TEXT PRIMARY KEY, checkpoint TEXT NOT NULL, updates INTEGER NOT NULL, clock INTEGER NOT NULL, mode TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS observations (namespace TEXT, time INTEGER, available INTEGER, measurements TEXT, PRIMARY KEY(namespace,time))"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS forecasts (namespace TEXT, issue INTEGER, target INTEGER, issued_at INTEGER, revision INTEGER, features TEXT, base TEXT, shadow TEXT, eligible INTEGER, scored INTEGER DEFAULT 0, truth TEXT, learned_at INTEGER, PRIMARY KEY(namespace,issue))"
            )

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    @staticmethod
    def models(checkpoint=None):
        result = []
        for j in range(6):
            model = SGDRegressor(
                loss="huber",
                epsilon=0.2,
                learning_rate="constant",
                eta0=0.001,
                alpha=0.0001,
                random_state=42,
                shuffle=False,
            )
            model.partial_fit(np.zeros((1, 66)), np.zeros(1))
            if checkpoint:
                model.coef_ = np.array(checkpoint["coef"][j])
                model.intercept_ = np.array([checkpoint["intercept"][j]])
                model.t_ = checkpoint["steps"][j]
            result.append(model)
        return result

    @staticmethod
    def checkpoint(models):
        return {
            "coef": [m.coef_.tolist() for m in models],
            "intercept": [float(m.intercept_[0]) for m in models],
            "steps": [float(m.t_) for m in models],
        }

    def observe(
        self,
        namespace,
        time,
        available,
        values,
        features,
        base,
        processed_at,
        *,
        mode="LIVE_SHADOW",
    ):
        """Store one observation/forecast, then score and learn only matured labels."""
        if not isinstance(namespace, str) or not 1 <= len(namespace) <= 200:
            raise ValueError("Bounded source namespace required")
        t, a = map(stamp, (time, available))
        if t % 3600 or a < t:
            raise ValueError(
                "Valid hourly observation and actual availability required"
            )
        values = list(values)
        if len(values) != 6 or any(
            v is not None and not np.isfinite(v) for v in values
        ):
            raise ValueError("Six finite values or explicit missing channels required")
        payload = encode(values)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            # Live writers take their processing clock only after acquiring the
            # write lock. Concurrent importer/worker calls cannot backdate it.
            clock = stamp(
                processed_at if processed_at is not None else pd.Timestamp.now(tz="UTC")
            )
            if clock < a:
                raise ValueError("Observation is not yet available at processing time")
            old = db.execute(
                "SELECT measurements,available FROM observations WHERE namespace=? AND time=?",
                (namespace, t),
            ).fetchone()
            if old:
                if old[0] != payload or a < old[1]:
                    raise ValueError(
                        "Conflicting observation revision requires a new namespace"
                    )
                # A later download can contain the same observation again. Keep
                # its first recorded availability; never learn the label twice.
                return {"duplicate": True, "updated": 0}
            state = db.execute(
                "SELECT checkpoint,updates,clock,mode FROM state WHERE namespace=?",
                (namespace,),
            ).fetchone()
            if state and (clock < state[2] or mode != state[3]):
                raise ValueError("Online clock/source mode changed")
            models = self.models(json.loads(state[0]) if state else None)
            revision = state[1] if state else 0
            db.execute(
                "INSERT INTO observations VALUES (?,?,?,?)", (namespace, t, a, payload)
            )
            audit_append(db, "OBSERVATION", dict(namespace=namespace, valid=t,
                         available=a, processed=clock, values=values, mode=mode,
                         model_sha256=self.model_sha))
            if features is not None and base is not None:
                x, b = np.asarray(features, float), np.asarray(base, float)
                if (
                    x.shape != (66,)
                    or b.shape != (6,)
                    or not np.isfinite(x).all()
                    or not np.isfinite(b).all()
                ):
                    raise ValueError("Complete numerical forecast/features required")
                z = np.clip((x - self.mean) / self.std, -8, 8)
                correction = (
                    np.clip(np.array([m.predict(z[None, :])[0] for m in models]), -2, 2)
                    * self.scale
                )
                shadow = bounded((b + correction)[None, :])[0]
                # Target already in the past at processing time: retain for audit,
                # but never score/learn it as a pre-issued online forecast.
                eligible = int(clock < t + 21600)
                db.execute(
                    "INSERT INTO forecasts (namespace,issue,target,issued_at,revision,features,base,shadow,eligible) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        namespace,
                        t,
                        t + 21600,
                        clock,
                        revision,
                        encode(z.tolist()),
                        encode(b.tolist()),
                        encode(shadow.tolist()),
                        eligible,
                    ),
                )
                audit_append(db, "FORECAST_ISSUED", dict(namespace=namespace,
                             valid=t, target=t+21600, issued_at=clock,
                             revision=revision, base=b.tolist(), shadow=shadow.tolist(),
                             features=z.tolist(), model_sha256=self.model_sha,
                             eligible=eligible))
            pending = db.execute(
                "SELECT f.issue,f.features,f.base,o.measurements FROM forecasts f JOIN observations o ON f.namespace=o.namespace AND f.target=o.time WHERE f.namespace=? AND f.scored=0 AND f.eligible=1 AND o.available<=? AND f.target<=? ORDER BY f.target",
                (namespace, clock, clock),
            ).fetchall()
            updated = 0
            for issue, x_json, b_json, truth_json in pending:
                truth = json.loads(truth_json)
                if any(v is None for v in truth):
                    continue
                x, b = np.array(json.loads(x_json)), np.array(json.loads(b_json))
                residual = np.clip((np.array(truth) - b) / self.scale, -5, 5)
                # Immutable pre-update forecasts already exist in this transaction.
                for j, m in enumerate(models):
                    m.partial_fit(x[None, :], np.array([residual[j]]))
                db.execute(
                    "UPDATE forecasts SET scored=1,truth=?,learned_at=? WHERE namespace=? AND issue=?",
                    (truth_json, clock, namespace, issue),
                )
                updated += 1
                audit_append(db, "SHADOW_UPDATE", dict(namespace=namespace,
                             issue=issue, target=issue+21600, learned_at=clock,
                             truth=truth, base=json.loads(b_json),
                             revision=revision+updated,
                             checkpoint=self.checkpoint(models)))
            db.execute(
                "INSERT OR REPLACE INTO state VALUES (?,?,?,?,?)",
                (
                    namespace,
                    encode(self.checkpoint(models)),
                    revision + updated,
                    clock,
                    mode,
                ),
            )
            return {
                "duplicate": False,
                "updated": updated,
                "revision": revision + updated,
            }

    def summary(self):
        """Read model/learning identity and per-target prequential diagnostics."""
        with self.connect() as db:
            db.execute("BEGIN")  # One snapshot while the collector can keep writing.
            states = db.execute(
                "SELECT namespace,updates,clock,mode FROM state ORDER BY namespace"
            ).fetchall()
            total, eligible, scored = db.execute(
                "SELECT count(*),coalesce(sum(eligible),0),coalesce(sum(scored),0) FROM forecasts"
            ).fetchone()
            rows = db.execute(
                "SELECT base,shadow,truth FROM forecasts WHERE scored=1 ORDER BY target DESC LIMIT 720"
            ).fetchall()
            timely, timely_scored, lead_min, lead_max = db.execute(
                "SELECT coalesce(sum(eligible=1 AND issued_at<issue+3600),0),"
                "coalesce(sum(scored=1 AND issued_at<issue+3600),0),"
                "min(CASE WHEN scored=1 THEN (target-issued_at)/60.0 END),"
                "max(CASE WHEN scored=1 THEN (target-issued_at)/60.0 END) FROM forecasts"
            ).fetchone()
        metrics = {}
        drift = False
        if rows:
            base, shadow, truth = [
                np.array([json.loads(r[i]) for r in rows]) for i in range(3)
            ]
            for j, c in enumerate(RAW_SENSOR_COLUMNS):
                b = float(np.abs(base[:, j] - truth[:, j]).mean())
                s = float(np.abs(shadow[:, j] - truth[:, j]).mean())
                metrics[c] = {"base_mae": b, "shadow_mae": s, "rows": len(rows)}
            drift = bool(
                np.mean((np.abs(shadow - truth) - np.abs(base - truth)) / self.scale)
                > 0.05
            )
        return {
            "enabled": True,
            "status": "AWAITING_HOURLY_INPUT"
            if not total
            else "HISTORICAL_ONLY_NO_LIVE_UPDATE"
            if not eligible
            else "LEARNING_SHADOW",
            "role": "SHADOW_ONLY_OFFLINE_OUTPUTS_UNCHANGED",
            "model_sha256": self.model_sha,
            "scaler": "FROZEN_TRAIN_ONLY",
            "updates": sum(s[1] for s in states),
            "forecasts": total,
            "eligible_forecasts": eligible,
            "scored_forecasts": scored,
            "pending": eligible - scored,
            "historical_ineligible_forecasts": total - eligible,
            "drift_warning": drift,
            "rolling_metrics": metrics,
            "timing": {
                "definition": "ISSUED_IN_INPUT_HOUR_MEANS_ISSUE_TIME_WITHIN_60_MINUTES_OF_INPUT_VALID_TIME",
                "issued_in_input_hour_forecasts": timely,
                "scored_issued_in_input_hour": timely_scored,
                "scored_delayed_input_forecasts": scored - timely_scored,
                "scored_actual_lead_min_minutes": lead_min,
                "scored_actual_lead_max_minutes": lead_max,
                "metrics_include_delayed_inputs": True,
                "verified_full_six_hour_skill": False,
            },
            "namespaces": [
                {
                    "id": s[0],
                    "updates": s[1],
                    "last_processed_at": pd.Timestamp(
                        s[2], unit="s", tz="UTC"
                    ).isoformat(),
                    "mode": s[3],
                }
                for s in states
            ],
            "field_validated": False,
        }


def for_model(path, engine):
    with np.load(engine.directory / "online_scaler.npz", allow_pickle=False) as data:
        return OnlineLearner(
            path,
            engine.profile_sha256,
            data["mean"],
            data["std"],
            data["residual_scale"],
        )


def ingest_native(records, path, engine, *, clock=None):
    """Live-file importer; actual availability is never replaced by valid time."""
    import hashlib

    from ml.himachal.contracts import METADATA, snapshot
    from ml.six_sensor_forecast.features import build_features

    canonical = [snapshot(r) for r in records]
    groups = {}
    skipped = 0
    for r in canonical:
        if r["native_interval_seconds"] != 3600:
            skipped += 1
            continue
        identity = {
            k: r[k]
            for k in METADATA
            if k not in {"timestamp_utc", "valid_time_utc", "available_at_utc"}
        }
        ns = "live:" + hashlib.sha256(encode(identity).encode()).hexdigest()[:32]
        groups.setdefault(ns, []).append(r)
    learner = for_model(path, engine)
    for ns, items in groups.items():
        # Reuse persisted history when the input file contains only new readings.
        with learner.connect() as db:
            old = db.execute(
                "SELECT time,measurements FROM observations WHERE namespace=? ORDER BY time DESC LIMIT 25",
                (ns,),
            ).fetchall()
        lookup = {
            pd.Timestamp(t, unit="s", tz="UTC").isoformat(): json.loads(v)
            for t, v in old
        }
        for r in items:
            lookup[r["timestamp_utc"]] = [
                r["measurements"][c] for c in RAW_SENSOR_COLUMNS
            ]
        frame = pd.DataFrame(
            [
                dict(
                    location_id=ns, timestamp_utc=t, **dict(zip(RAW_SENSOR_COLUMNS, v))
                )
                for t, v in lookup.items()
            ]
        )
        f, x = build_features(frame)
        pred = engine.predict(frame)
        positions = {t: i for i, t in enumerate(f.timestamp_utc)}
        for r in sorted(items, key=lambda r: pd.Timestamp(r["timestamp_utc"])):
            if r["native_interval_seconds"] != 3600:
                continue  # No false hourly interpretation of native high-rate input.
            i = positions[pd.Timestamp(r["timestamp_utc"])]
            complete = pred.iloc[i]["status"] == "HYBRID_READY"
            learner.observe(
                ns,
                r["timestamp_utc"],
                r["available_at_utc"],
                [r["measurements"][c] for c in RAW_SENSOR_COLUMNS],
                x.iloc[i].to_numpy() if complete else None,
                pred.iloc[i][["forecast_" + c for c in RAW_SENSOR_COLUMNS]].to_numpy(
                    float
                )
                if complete
                else None,
                clock,
            )
    summary = learner.summary()
    summary["skipped_nonhourly_rows"] = skipped
    return summary
