"""Bounded arrival-order replay; synthetic streams never establish accuracy."""
import argparse
from collections import deque
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.india_sensor.config import DEFAULT, load
from ml.india_sensor.features import METADATA, build, utc
from ml.india_sensor.predict import predict
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


class Stream:
    def __init__(self, cfg, strategy='B', scope='national', inference=True):
        self.cfg, self.strategy, self.scope, self.inference = cfg, strategy, scope, inference
        self.rows = deque(maxlen=26)
        self.last = None
        self.site = None

    def push(self, row):
        if set(row) != set(METADATA+RAW_SENSOR_COLUMNS):
            return {'status': 'REJECTED_SCHEMA'}
        try:
            t, received = utc([row['timestamp_utc'], row['available_at_utc']])
            if self.last is not None and t <= self.last:
                return {'status': 'REJECTED_DUPLICATE_OR_OUT_OF_ORDER'}
            if received > t:
                return {'status': 'LATE_PACKET_OMITTED'}
            if self.site is not None and row['physical_site_id'] != self.site:
                return {'status': 'REJECTED_SITE_SWITCH'}
            runtime = {**self.cfg, 'allowed_sources': self.cfg['allowed_sources']+['indra_owner_nodes']}
            candidate = pd.DataFrame([*self.rows, row])
            features = build(candidate, runtime)
        except (ValueError, TypeError, KeyError):
            return {'status': 'REJECTED_INVALID_PACKET'}
        self.rows.append(dict(row))
        # Time bound matters as well as row count when packets have long gaps.
        while self.rows and t-pd.Timestamp(self.rows[0]['timestamp_utc']) > pd.Timedelta(hours=25):
            self.rows.popleft()
        self.last, self.site = t, row['physical_site_id']
        result = predict(pd.DataFrame(self.rows), self.cfg, self.strategy, self.scope) if self.inference else {'status': 'FEATURES_ONLY'}
        result['history_rows'] = len(self.rows)
        result['issue_time_utc'] = t.isoformat()
        return {'status': 'ACCEPTED', 'result': result, 'features': features.iloc[-1]}


def synthetic(template, count=120):
    """Contract fixture with failures; no independent event truth is generated."""
    rows = []
    start = pd.Timestamp('2024-11-01T00:00:00Z')
    for i in range(count):
        if i == 45:
            continue
        r = dict(template)
        r.update(timestamp_utc=start+pd.Timedelta(hours=i), available_at_utc=start+pd.Timedelta(hours=i),
                 source_id='indra_owner_nodes', location_id='synthetic_node', physical_site_id='synthetic_site',
                 temperature_c=22+4*np.sin(i/24*2*np.pi), relative_humidity_pct=65-10*np.sin(i/24*2*np.pi), wind_speed_mps=3.)
        if i == 65:
            r['available_at_utc'] += pd.Timedelta(hours=1)
        if i == 75:
            r['wind_speed_mps'] = np.nan
        if i == 85:
            r['temperature_c'] = 80.
        rows.append(r)
        if i == 55:
            rows.append(dict(r))
    return pd.DataFrame(rows)


def run(frame, cfg, output, synthetic_fixture=False, strategy='B', scope='national'):
    stream = Stream(cfg, strategy, scope)
    counts, predictions, max_error = {}, [], 0.
    columns = None
    for row in frame.to_dict('records'):
        entry = stream.push(row)
        counts[entry['status']] = counts.get(entry['status'], 0)+1
        if entry['status'] != 'ACCEPTED':
            continue
        result = entry['result']
        predictions.append(result)
        # Compare arrival-prefix, bounded history against batch features at the
        # same issue time; labels/future rows are never available to Stream.
        check = build(pd.DataFrame(stream.rows), {**cfg, 'allowed_sources': cfg['allowed_sources']+['indra_owner_nodes']}).iloc[-1]
        columns = [c for c in check.index if c not in METADATA]
        a, b = entry['features'][columns].to_numpy(float), check[columns].to_numpy(float)
        if not np.array_equal(np.isnan(a), np.isnan(b)):
            raise RuntimeError('Replay/batch missing masks differ')
        good = np.isfinite(a)&np.isfinite(b)
        if good.any():
            max_error = max(max_error, float(np.abs(a[good]-b[good]).max()))
    report = {'evidence': 'SYNTHETIC_CONTRACT_ONLY' if synthetic_fixture else 'HISTORICAL_REPLAY_NOT_FIELD_VALIDATION',
              'packet_counts': counts, 'accepted_predictions': len(predictions), 'max_history_rows': max((p['history_rows'] for p in predictions), default=0),
              'feature_prefix_parity_max_absolute_error': max_error, 'no_future_data_in_stream': True,
              'disaster_outputs': 'DISABLED', 'predictions': predictions}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    return {k: v for k, v in report.items() if k != 'predictions'}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--config', default=str(DEFAULT))
    p.add_argument('--input', required=True, help='One node sensor-view CSV in arrival order')
    p.add_argument('--output', required=True)
    p.add_argument('--synthetic', action='store_true')
    p.add_argument('--strategy', choices=list('ABCD'), default='B')
    p.add_argument('--scope', default='national')
    p.add_argument('--model-dir', help='Verified serving bundle directory')
    a = p.parse_args()
    cfg = load(a.config)
    if a.model_dir:
        cfg['models'] = str(Path(a.model_dir).resolve())
    frame = pd.read_csv(a.input, nrows=cfg['max_expanded_station_rows']+1)
    if len(frame) > cfg['max_expanded_station_rows']:
        raise ValueError('Replay row budget exceeded')
    if a.synthetic:
        frame = synthetic(frame.iloc[0].to_dict())
    print(json.dumps(run(frame, cfg, a.output, a.synthetic, a.strategy, a.scope), indent=2))
