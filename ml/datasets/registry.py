"""SQLite observation store. Unknown source rights/units/time fail closed."""
from __future__ import annotations
import hashlib
import json
import math
import sqlite3
from pathlib import Path
import pandas as pd

REGISTRY = Path('data/registry/sources.json')


def connect(path, registry=REGISTRY):
    db = sqlite3.connect(path)
    db.executescript('DROP VIEW IF EXISTS training_open; DROP VIEW IF EXISTS training_restricted; DROP VIEW IF EXISTS quarantine; DROP VIEW IF EXISTS background_open;')
    db.executescript(Path(__file__).with_name('schema.sql').read_text())
    definitions = json.loads(Path(registry).read_text())
    if definitions['schema_version'] != 'indra_observations_v1':
        raise ValueError('Registry schema mismatch')
    for source in definitions['sources']:
        source = dict(source)
        evidence = source.pop('approval_evidence', {})
        if (source.get('timezone_verified') or source.get('pressure_verified')) and not evidence:
            raise ValueError('Verified source metadata requires approval evidence')
        source['approval_evidence'] = json.dumps(evidence, sort_keys=True)
        allowed = {entry[1] for entry in db.execute('PRAGMA table_info(sources)')}
        if not set(source) <= allowed:raise ValueError('Unexpected registry fields')
        fields = list(source)
        db.execute(f"INSERT INTO sources ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)}) "
                   f"ON CONFLICT(source_id) DO UPDATE SET " + ','.join(f'{k}=excluded.{k}' for k in fields if k != 'source_id'),
                   [source[k] for k in fields])
    db.commit()
    return db


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_long_row(row):
    """Validate canonical units, timezone-aware UTC fields and interval ordering."""
    units = {'temperature_c':'degC', 'relative_humidity_pct':'%', 'pressure_hpa':'hPa',
             'wind_speed_mps':'m/s', 'pm25_ug_m3':'ug/m3', 'pm10_ug_m3':'ug/m3'}
    if row['variable'] not in units or row['unit'] != units[row['variable']]:
        raise ValueError('Unknown variable or noncanonical unit')
    stamps = []
    for key in ['interval_start_utc', 'interval_end_utc', 'available_at_utc']:
        value = row.get(key)
        stamp = None if value is None else pd.Timestamp(value)
        if stamp is not None and (pd.isna(stamp) or stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0):
            raise ValueError('Use explicit UTC timestamps')
        stamps.append(stamp)
    start, end, available = stamps
    if start is not None and end is not None and start > end:
        raise ValueError('Reversed interval')
    if end is not None and available is not None and available < end:
        raise ValueError('Observation available before interval end')
    if row['status'] == 'approved' and (start is None or end is None or available is None):
        raise ValueError('Approved observations need complete time semantics')
    for key in ['latitude_deg','longitude_deg','value','elevation_m','uncertainty']:
        val=row.get(key)
        if val is not None and not math.isfinite(float(val)):raise ValueError('Nonfinite observation field')
    if row['status']=='approved':
        from ml.six_sensor_forecast.contract import PHYSICAL_RANGES
        lo,hi=PHYSICAL_RANGES[row['variable']]
        if row.get('value') is None or not lo<=row['value']<=hi:raise ValueError('Invalid approved value')
    flags = json.loads(row['qc_flags'])
    if not isinstance(flags, list) or not all(isinstance(x, str) for x in flags):
        raise ValueError('QC flags must be a string list')


def insert_rows(db, rows):
    if not rows:
        return
    for row in rows:
        validate_long_row(row)
    fields = list(rows[0])
    if any(set(row) != set(fields) for row in rows):
        raise ValueError('Inconsistent long-form rows')
    # Fixed whitelist protects SQL identifiers supplied by callers.
    allowed = {entry[1] for entry in db.execute('PRAGMA table_info(observations)')}
    if not set(fields) <= allowed:
        raise ValueError('Unexpected observation fields')
    db.executemany(f"INSERT INTO observations ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
                   [[row[k] for k in fields] for row in rows])


def export_view(db, output, restricted=False):
    view = 'training_restricted' if restricted else 'training_open'
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    first = True
    for chunk in pd.read_sql_query(f'SELECT * FROM {view} ORDER BY station_id,interval_end_utc,variable', db, chunksize=10000):
        chunk.to_csv(output, index=False, mode='w' if first else 'a', header=first)
        first = False
