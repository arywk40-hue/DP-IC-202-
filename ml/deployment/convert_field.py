"""Convert accepted recorder observations to six-channel evaluation CSV."""

import argparse
from collections import Counter
import json
from pathlib import Path

import pandas as pd

from esp32.ml_integration.tools.record_field import Validator
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import sha256
from ml.six_sensor_forecast.features import validate_observations


def convert(paths):
    rows, seen, sources = [], {}, []
    counts = Counter()
    for path in map(Path, paths):
        validator = None
        station = None
        with path.open() as handle:
            for number, line in enumerate(handle, 1):
                if not line.endswith('\n'):
                    counts['truncated_final_line'] += 1
                    continue
                try:
                    record = json.loads(line)
                except ValueError as exc:
                    raise ValueError(f'{path}:{number}: malformed journal record') from exc
                if not isinstance(record, dict):
                    raise ValueError(f'{path}:{number}: journal record must be an object')
                kind = record.get('kind')
                if kind == 'SESSION_START':
                    build, station = record.get('expected_build'), record.get('station')
                    if (validator is not None or not isinstance(build, str) or len(build) != 64
                            or any(c not in '0123456789abcdef' for c in build)
                            or not isinstance(station, str) or not station.strip()):
                        raise ValueError(f'{path}:{number}: invalid or repeated SESSION_START')
                    validator = Validator(build)
                if validator is None or record.get('station') != station:
                    raise ValueError(f'{path}:{number}: missing session identity or station changed')
                # Replay identity, sequence and self-test state even for excluded rows.
                classified = None
                if 'payload' in record:
                    classified, _ = validator.classify(record['payload'])
                if kind != 'OBSERVATION':
                    counts['excluded_' + str(kind)] += 1
                    continue
                if classified != 'OBSERVATION':
                    counts['rejected_on_revalidation'] += 1
                    continue
                payload = record['payload']
                measurements = payload['measurements']
                if any(not low <= value <= high for value, (low, high) in
                       zip(measurements, PHYSICAL_RANGES.values())):
                    counts['out_of_range'] += 1
                    continue
                key = (station, payload['timestamp_utc'])
                if key in seen:
                    if seen[key] != measurements:
                        raise ValueError(f'{path}:{number}: conflicting measurements for {key}')
                    counts['duplicate_observation'] += 1
                    continue
                seen[key] = measurements
                rows.append(dict(location_id=station,
                                 timestamp_utc=pd.Timestamp(key[1], unit='s', tz='UTC'),
                                 **dict(zip(RAW_SENSOR_COLUMNS, measurements))))
        sources.append({'path': str(path), 'sha256': sha256(path)})
    if not rows:
        raise ValueError('No accepted complete six-channel observations in the journals')
    frame = validate_observations(pd.DataFrame(rows))
    frame = frame[['timestamp_utc', 'location_id', *RAW_SENSOR_COLUMNS]]
    report = {'source_journals': sources, 'exported_observations': len(frame),
              'counts': dict(counts), 'provenance_verified': False,
              'note': 'Only measured inputs are exported. Verify sensor units, clock and '
                      'station pressure separately before declaring evaluation provenance.'}
    return frame, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', nargs='+', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() == args.report.resolve() or args.output.exists() or args.report.exists():
        parser.error('CSV and report must be distinct new files')
    try:
        frame, report = convert(args.input)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        frame.to_csv(handle, index=False)
    report['output_sha256'] = sha256(args.output)
    with args.report.open('x') as handle:
        handle.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(f'{len(frame)} observations written to {args.output}')


if __name__ == '__main__':
    main()
