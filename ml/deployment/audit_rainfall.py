"""Check official rainfall overlap; do not turn wet-hour evidence into 12 hazard labels."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
from ml.deployment.audit_himachal import audit, KEYS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rainfall', type=Path, default=Path('data/field_sources/raw/himachal_rainfall_2021_2025.csv'))
    parser.add_argument('--weather', type=Path, default=Path('himachal 4-sensor dataset'))
    parser.add_argument('--output', type=Path, default=Path('reports/deployment/rainfall_overlap.json'))
    args = parser.parse_args()
    _, weather = audit(args.weather, return_frame=True)
    column = 'Telemetry Hourly Rainfall (mm)'
    rain = pd.read_csv(args.rainfall, usecols=KEYS + [column])
    rain['Data Acquisition Time'] = pd.to_datetime(rain['Data Acquisition Time'], format='%d-%m-%Y %H:%M', errors='coerce')
    rain['rainfall_mm'] = pd.to_numeric(rain[column], errors='coerce')
    duplicate = rain.duplicated(KEYS, keep=False)
    valid = rain.rainfall_mm.ge(0) & rain[KEYS].notna().all(axis=1)
    clean = rain.loc[valid & ~duplicate, KEYS + ['rainfall_mm']]
    joined = weather.merge(clean, on=KEYS, validate='one_to_one')
    joined['observed_wet_hour_candidate'] = joined.rainfall_mm.gt(0).astype(int)
    future = clean.copy()
    future['Data Acquisition Time'] -= pd.Timedelta(hours=6)
    future = future.rename(columns={'rainfall_mm': 'rainfall_mm_at_t_plus_6h'})
    pairs = joined.merge(future, on=KEYS, validate='one_to_one')
    with args.rainfall.open('rb') as handle:
        checksum = hashlib.file_digest(handle, 'sha256').hexdigest()
    report = {'source': 'NWIC Himachal Pradesh telemetry hourly rainfall 2021-2025 resource',
              'download_sha256': checksum, 'download_bytes': args.rainfall.stat().st_size,
              'raw_rows': len(rain), 'stations': int(rain.Station.nunique()),
              'zero_rainfall_rows': int(rain.rainfall_mm.eq(0).sum()),
              'negative_rainfall_rows': int(rain.rainfall_mm.lt(0).sum()),
              'max_reported_rainfall_mm': float(rain.rainfall_mm.max()),
              'actual_start': str(rain['Data Acquisition Time'].min()),
              'actual_end': str(rain['Data Acquisition Time'].max()),
              'duplicate_key_rows': int(duplicate.sum()), 'invalid_rows': int((~valid).sum()),
              'screened_rainfall_rows': len(clean), 'matched_four_weather_plus_rain_rows': len(joined),
              'wet_hour_candidates': int(joined.observed_wet_hour_candidate.sum()),
              'exact_six_hour_future_pairs': len(pairs),
              'future_wet_hour_candidates': int(pairs.rainfall_mm_at_t_plus_6h.gt(0).sum()),
              'by_station': {str(k): {'rows': len(g), 'wet_hour_candidates': int(g.observed_wet_hour_candidate.sum())}
                             for k, g in joined.groupby('Station')},
              'deployment_ready': False,
              'limitations': ['No zero-rainfall records in this downloaded source; missing hours cannot be labeled dry',
                              'Positive-only overlap cannot train or validate a binary rain detector',
                              'No PM2.5/PM10 in aligned records', 'Timezone remains unresolved; matching uses source-local clock strings',
                              'Gauge accumulation interval and quality flags require verification',
                              'Wet hour is not a confirmed light/moderate rain, squall, snow, or other hazard label',
                              'Pressure quality/reference remains unresolved; no model trained from these candidates']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    candidate = args.rainfall.parent/'screened_weather_rain_candidates.csv'
    pairs.to_csv(candidate, index=False)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
