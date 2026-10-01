"""Audit the supplied Himachal CSVs without inventing PM readings or timezones."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from ml.six_sensor_forecast.contract import PHYSICAL_RANGES

KEYS = ['Station', 'Latitude', 'Longitude', 'Data Acquisition Time']
SOURCES = {
    'Air Temperature Telemetry Hourly (AoC)': ('temperature_c', 1),
    'Telemetry Hourly Relative Humidity (%)': ('relative_humidity_pct', 1),
    'Telemetry_Hourly_Atmospheric Pressure (mb)': ('pressure_hpa', 1),
    'Telemetry Hourly Wind Speed (Km/Hr)': ('wind_speed_mps', 1 / 3.6),
}


def audit(directory, return_frame=False):
    report = {'source_files': {}, 'timezone': 'UNRESOLVED_IN_SOURCE_FILES',
              'missing_channels': ['pm25_ug_m3', 'pm10_ug_m3'],
              'independent_event_labels': 'ABSENT_IN_THESE_FOUR_FILES',
              'six_input_training_ready': False}
    joined = None
    for path in sorted(Path(directory).glob('*.csv')):
        header = pd.read_csv(path, nrows=0).columns
        found = [column for column in SOURCES if column in header]
        if len(found) != 1:
            continue
        source = found[0]
        name, factor = SOURCES[source]
        frame = pd.read_csv(path, usecols=KEYS + [source])
        frame['Data Acquisition Time'] = pd.to_datetime(frame['Data Acquisition Time'], format='%d-%m-%Y %H:%M', errors='coerce')
        frame[name] = pd.to_numeric(frame[source], errors='coerce') * factor
        duplicate = frame.duplicated(KEYS, keep=False)
        low, high = PHYSICAL_RANGES[name]
        valid = frame[name].between(low, high) & frame[KEYS].notna().all(axis=1)
        clean = frame.loc[valid & ~duplicate, KEYS + [name]]
        with path.open('rb') as handle:
            checksum = hashlib.file_digest(handle, 'sha256').hexdigest()
        report['source_files'][name] = {
            'path': str(path), 'sha256': checksum, 'raw_rows': len(frame),
            'stations': int(frame.Station.nunique()), 'duplicate_key_rows': int(duplicate.sum()),
            'invalid_rows': int((~valid).sum()), 'screened_rows': len(clean),
            'first_timestamp': str(frame['Data Acquisition Time'].min()),
            'last_timestamp': str(frame['Data Acquisition Time'].max()),
            'common_values': {str(k): int(v) for k, v in frame[name].value_counts().head(5).items()},
        }
        joined = clean if joined is None else joined.merge(clean, on=KEYS, how='inner', validate='one_to_one')
    if set(report['source_files']) != {v[0] for v in SOURCES.values()}:
        raise ValueError('All four expected weather sources are required')
    report['aligned_screened_four_channel_rows'] = len(joined)
    report['aligned_by_station'] = {str(k): int(v) for k, v in joined.Station.value_counts().items()}
    report['blockers'] = ['No colocated hourly PM2.5/PM10 in supplied files',
                          'Timezone and station pressure reference require source confirmation',
                          'Repeated pressure values require quality investigation',
                          'No independently observed event labels in supplied files']
    return (report, joined) if return_frame else report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('himachal 4-sensor dataset'))
    parser.add_argument('--output', type=Path, default=Path('reports/deployment/himachal_readiness.json'))
    args = parser.parse_args()
    report = audit(args.data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'source_files'}, indent=2))


if __name__ == '__main__':
    main()
