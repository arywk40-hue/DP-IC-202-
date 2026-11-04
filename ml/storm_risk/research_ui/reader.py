"""Read configured, owner-generated JSON/CSV/NPZ outputs; never load joblib."""
from __future__ import annotations

from collections import deque
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import threading

import numpy as np


class StormRun:
    """Isolate retrospective gridded research from physical-node telemetry."""
    def __init__(self, directory: Path | None):
        self.directory = Path(directory).resolve() if directory else None
        self.lock = threading.RLock()
        self.cached_signature = None
        self.cached_rows = []

    def report(self) -> dict:
        """Return a bounded report; missing configuration is explicit."""
        if self.directory is None:
            return dict(configured=False, status='NOT_CONFIGURED', calibrated=False, warnings=['NO_LOCAL_STORM_RUN_SELECTED'])
        path = self.directory / 'report.json'
        if path.stat().st_size > 64 * 1024 * 1024:
            raise ValueError('Storm report exceeds local serving budget')
        report = json.loads(path.read_text(), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite storm report')))
        if report.get('schema_version') != 'indra_storm_risk_report_v1' or type(report.get('calibrated')) is not bool:
            raise ValueError('Incompatible storm report')
        if report['calibrated'] and (report['gate_failures'] or report['evidence_kind'] != 'confirmed_event_records'):
            raise ValueError('Inconsistent storm gate state')
        fields = ['run_id', 'status', 'evidence_kind', 'target', 'calibrated', 'calibration_method', 'gate_failures', 'warnings',
            'sample_counts', 'metrics', 'confidence_intervals', 'ensemble_weights', 'score_columns', 'output_kind', 'online']
        result = {key: report.get(key) for key in fields}
        maps = report.get('heatmaps', {})
        result['heatmaps'] = dict(features=maps.get('features', []), times=[f['time'] for f in maps.get('frames', [])], method=maps.get('method'))
        result['configured'] = True
        return result

    def scores(self, limit: int = 200) -> dict:
        """Serve recent cells from a bounded cache, with evidence and gate labels."""
        if not 1 <= limit <= 200:
            raise ValueError('Use a bounded recent-cell limit')
        report = self.report()
        if not report['configured']:
            return dict(rows=[], configured=False)
        path = self.directory / 'scores.csv'
        stat = path.stat()
        if stat.st_size > 512 * 1024 * 1024:
            raise ValueError('Storm scores exceed local serving budget')
        signature = (stat.st_mtime_ns, stat.st_size)
        with self.lock:
            if signature != self.cached_signature:
                rows = deque(maxlen=200)
                with path.open(newline='') as stream:
                    reader = csv.DictReader(stream)
                    fields = reader.fieldnames or []
                    if not report['calibrated'] and any(c.endswith('_cal_prob') for c in fields):
                        raise ValueError('Unpassed gate cannot expose mapped event columns')
                    for row in reader:
                        out = {}
                        for key, value in row.items():
                            if key.endswith(('_risk_uncal', '_cal_prob')) or key in {'lat', 'lon'}:
                                number = float(value) if value else None
                                if number is not None and not math.isfinite(number):
                                    raise ValueError('Nonfinite served score')
                                out[key] = number
                            elif key in {'anomaly_flag', 'neighbour_confirmed', 'anomaly_available'}:
                                out[key] = value.lower() == 'true'
                            elif key == 'time':
                                stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                if stamp.tzinfo is None:
                                    raise ValueError('Storm score time requires a UTC offset')
                                out[key] = stamp.astimezone(timezone.utc).isoformat()
                            else:
                                out[key] = value
                        rows.append(out)
                self.cached_rows = list(rows)
                self.cached_signature = signature
            chosen = self.cached_rows[-limit:]
        latest = chosen[-1]['time'] if chosen else None
        return dict(configured=True, rows=[r for r in chosen if r['time'] == latest], time=latest,
            evidence_kind=report['evidence_kind'], calibrated=report['calibrated'], scope='LATEST_CELLS_UP_TO_LIMIT_NOT_COMPLETE_GRID_HISTORY')

    def heatmap(self, feature: str | None = None, time: str | None = None) -> dict:
        """Read an allow-listed, hash-checked feature array without interpolation."""
        report = self.report()
        if not report['configured'] or not report['heatmaps']['features']:
            return dict(configured=report['configured'], status='NO_FEATURE_MAP', cells=[])
        maps = json.loads((self.directory / 'heatmaps/manifest.json').read_text())
        feature = feature or maps['features'][0]
        if feature not in maps['features']:
            raise ValueError('Unknown feature map')
        matches = [f for f in maps['frames'] if time is None or f['time'] == time]
        if not matches:
            raise ValueError('Unknown feature map timestamp')
        item = matches[-1]
        root = (self.directory / 'heatmaps').resolve()
        path = (root / item['file']).resolve()
        if not path.is_relative_to(root) or path.stat().st_size > 64 * 1024 * 1024:
            raise ValueError('Invalid feature map path/size')
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Feature map checksum mismatch')
        with np.load(path, allow_pickle=False) as arrays:
            lat, lon, values = arrays['lat'], arrays['lon'], arrays[feature]
        if lat.ndim != 1 or lon.ndim != 1 or values.shape != (len(lat), len(lon)) or values.size > 50000:
            raise ValueError('Feature grid shape/budget mismatch')
        if not np.isfinite(lat).all() or not np.isfinite(lon).all() or np.isinf(values).any():
            raise ValueError('Invalid feature grid values')
        return dict(configured=True, status='AVAILABLE', feature=feature, time=item['time'], lat=lat.tolist(), lon=lon.tolist(),
            unit=maps.get('units', {}).get(feature),
            values=[[float(v) if np.isfinite(v) else None for v in row] for row in values],
            method=maps['method'], evidence_kind=report['evidence_kind'])
