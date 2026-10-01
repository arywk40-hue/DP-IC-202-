"""Verified event-rule inference with explicit unknown scores and real history."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from ml.event_classifier.features import ALL_EVENT_FEATURE_COLS, EVENT_NAMES, build_features
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import sha256


class EventPredictor:
    def __init__(self, model_dir: Path):
        model_dir = Path(model_dir)
        self.report = json.loads((model_dir / 'event_training_report.json').read_text())
        if (self.report.get('schema_version') != 'indra_event_rules_v1'
                or self.report.get('event_names') != EVENT_NAMES
                or self.report.get('input_features') != ALL_EVENT_FEATURE_COLS
                or set(self.report.get('models', {})) != set(EVENT_NAMES)):
            raise ValueError('Event model schema mismatch')
        self.models = []
        for name in EVENT_NAMES:
            entry = self.report['models'][name]
            if entry.get('skipped'):
                self.models.append(None)
                continue
            path = model_dir / entry['student_file']
            if sha256(path) != entry['student_sha256']:
                raise ValueError('Event model checksum mismatch: ' + name)
            model = xgb.Booster(params={'nthread': 1})
            model.load_model(path)
            if model.feature_names != ALL_EVENT_FEATURE_COLS:
                raise ValueError('Event feature order mismatch: ' + name)
            config = json.loads(model.save_config())['learner']
            if config['objective']['name'] != 'binary:logistic':
                raise ValueError('Unexpected event objective')
            self.models.append(model)
        self.trained_mask = np.array([m is not None for m in self.models])

    def predict_features(self, features: np.ndarray) -> np.ndarray:
        features = np.asarray(features, dtype=np.float32)
        if features.ndim != 2 or features.shape[1] != len(ALL_EVENT_FEATURE_COLS):
            raise ValueError('Expected rows of 17 event features')
        result = np.full((len(features), len(EVENT_NAMES)), np.nan, dtype=np.float32)
        valid = np.isfinite(features).all(axis=1)
        if valid.any():
            matrix = xgb.DMatrix(features[valid], feature_names=ALL_EVENT_FEATURE_COLS)
            for i, model in enumerate(self.models):
                if model is not None:
                    result[valid, i] = model.predict(matrix)
        return result

    def predict(self, observations: pd.DataFrame) -> pd.DataFrame:
        frame, features = build_features(observations)
        # Match the firmware's seven complete, consecutive observations. The
        # legacy training feature builder alone can overlook an interior gap.
        ready = np.zeros(len(frame), dtype=bool)
        for _, group in frame.groupby('location_id', sort=False):
            hourly = group.set_index('timestamp_utc')[RAW_SENSOR_COLUMNS].reindex(
                pd.date_range(group.timestamp_utc.min(), group.timestamp_utc.max(), freq='h'))
            complete = np.isfinite(hourly.to_numpy()).all(axis=1)
            history = pd.Series(complete, index=hourly.index).rolling(7, min_periods=7).sum().eq(7)
            ready[group.index] = history.loc[group.timestamp_utc].to_numpy()
        values = features[ALL_EVENT_FEATURE_COLS].to_numpy(dtype=np.float32)
        values[~ready] = np.nan
        scores = self.predict_features(values)
        result = frame[['timestamp_utc', 'location_id']].copy()
        result['status'] = np.where(np.isfinite(scores).any(axis=1), 'RULE_SCORES_ONLY', 'UNAVAILABLE')
        for i, name in enumerate(EVENT_NAMES):
            result[name] = scores[:, i]
        return result
