"""Reproducible harness smoke test ONLY; no field accuracy evidence."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from ml.spatial_ensemble.evaluate import evaluate
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


def main():
    stations = pd.DataFrame([
        ('a', 31., 76.), ('b', 31., 76.1), ('c', 31.1, 76.), ('d', 31.1, 76.1),
        ('validation', 31.04, 76.06), ('test', 31.06, 76.04),
    ], columns=['location_id', 'latitude', 'longitude'])
    rng = np.random.default_rng(42)
    records = []
    times = pd.date_range('2025-01-01', periods=180, freq='h', tz='UTC')
    for row in stations.itertuples():
        for hour, stamp in enumerate(times):
            spatial = (row.latitude-31)*10 + (row.longitude-76)*10
            wave = np.sin(2*np.pi*hour/24)
            values = np.array([20+wave+spatial, 60+wave*5+spatial, 1000+wave+spatial,
                               30+wave*4+spatial, 50+wave*6+spatial, 3+wave*.5+spatial*.1])
            values += rng.normal(0, [.1, .3, .1, .5, .7, .05])
            records.append(dict(location_id=row.location_id, timestamp_utc=stamp,
                                **dict(zip(RAW_SENSOR_COLUMNS, values))))
    report = evaluate(pd.DataFrame(records), stations, ['validation'], ['test'], str(times[80]), str(times[130]))
    report['evidence'] = 'SYNTHETIC_SMOKE_TEST_ONLY_NOT_WEATHER_ACCURACY'
    Path('reports/review/synthetic_metrics.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(report['metrics'], indent=2))


if __name__ == '__main__':
    main()
