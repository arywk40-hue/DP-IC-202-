#!/usr/bin/env python3
"""Download a separate recent Mandi API snapshot; never overwrite training data."""
import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ml.india_mandi.data import prepare  # noqa: E402
from ml.india_mandi.submission import replay_records  # noqa: E402
from ml.six_sensor_forecast.data import sha256  # noqa: E402
import pandas as pd  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    last_day = datetime.now(timezone.utc).date()-timedelta(days=1)
    parser.add_argument('--end', type=date.fromisoformat, default=last_day)
    parser.add_argument('--start', type=date.fromisoformat)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--offline', action='store_true', help='Use an already cached snapshot only')
    args = parser.parse_args()
    start = args.start or args.end-timedelta(days=29)
    if not start <= args.end <= last_day or (args.end-start).days >= 366:
        parser.error('Choose at most 366 completed UTC days; do not request future/partial days')
    output = (args.output or ROOT/f'ml/data/himachal/mandi_api/{start}_{args.end}').resolve()
    if not output.is_relative_to(ROOT/'ml/data/himachal'):
        parser.error('Refresh snapshots must stay under ignored ml/data/himachal; frozen training data is protected')
    request = dict(schema_version='indra_mandi_download_request_v1', latitude=31.71, longitude=76.93,
        start_date=start.isoformat(), end_date=args.end.isoformat(), weather_model='ecmwf_ifs',
        air_domain='cams_global', purpose='SEPARATE_MODELED_REFRESH_NO_RETRAINING')
    request_path = output/'download_request.json'
    if request_path.exists() and json.loads(request_path.read_text()) != request:
        parser.error('Output already contains a different request; choose a new output folder')
    output.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps(request, indent=2)+'\n')
    manifest = prepare({**request, 'data': str(output), '_config_sha256': sha256(request_path)}, args.offline)
    frame = pd.read_csv(output/'observations.csv')
    frame['timestamp_utc'] = pd.to_datetime(frame.timestamp_utc, utc=True)
    replay_path = output/'replay.json'
    replay_status = 'UNAVAILABLE_INCOMPLETE_RECENT_HISTORY'
    try:
        replay = replay_records(frame, manifest)
    except ValueError as error:
        replay_reason = str(error)
    else:
        replay_path.write_text(json.dumps(replay, indent=2, allow_nan=False)+'\n')
        replay_status, replay_reason = 'COMPLETE_25_HOUR_SNAPSHOTS', None
    summary = dict(source='Open-Meteo ECMWF IFS + CAMS global, Mandi',
        evidence='RETROSPECTIVE_MODELED_GRID_NOT_IMD_STATION_OBSERVATIONS',
        requested_start=start.isoformat(), requested_end=args.end.isoformat(),
        rows=manifest['rows'], complete_six_channel_rows=manifest['complete_six_channel_rows'],
        missing_measurements=manifest['missing_measurements'],
        observations_sha256=manifest['observations_sha256'], retrieved_at_utc=manifest['retrieved_at_utc'],
        replay_status=replay_status, replay_reason=replay_reason,
        training_dataset_modified=False, models_retrained=False)
    (output/'download_summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    print(json.dumps(summary, indent=2))
    print('Saved:', output)
    if replay_status == 'COMPLETE_25_HOUR_SNAPSHOTS':
        print('Dashboard input:', replay_path)


if __name__ == '__main__':
    main()
