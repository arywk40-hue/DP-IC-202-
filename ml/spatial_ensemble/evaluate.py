"""Held-out-node evaluation requiring a VERIFIED station coordinate table.

python -m ml.spatial_ensemble.evaluate --observations observations.csv
 --stations stations.csv --validation-stations A B --test-stations C D
 --validation-start 2024-01-01T00:00:00Z --test-start 2025-01-01T00:00:00Z
 --output reports/review/spatial_metrics.json

Station table: location_id,latitude,longitude. Observation schema is the
existing six-channel contract. No coordinates are guessed or geocoded here.
"""
from __future__ import annotations
import argparse
import json
import platform
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from ml.six_sensor_forecast.data import sha256
from ml.six_sensor_forecast.features import validate_observations
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.spatial_ensemble.model import SpatialEnsemble, snapshot_features, coordinates


def examples(frame, station_ids, context_ids):
    rows, features, labels, baselines = [], [], [], []
    for _, group in frame.groupby('timestamp_utc', sort=True):
        context = group[group.location_id.isin(context_ids)]
        for _, query in group[group.location_id.isin(station_ids)].iterrows():
            # Query sensor values ONLY enter truth, never neighbor inputs.
            nodes = context[context.location_id != query.location_id].to_dict('records')
            x, idw, _ = snapshot_features(nodes, query.latitude, query.longitude, query.timestamp_utc)
            truth = query[RAW_SENSOR_COLUMNS].to_numpy(dtype=float)
            rows.append(dict(nodes=nodes, latitude=query.latitude, longitude=query.longitude,
                             timestamp=query.timestamp_utc))
            features.append(x)
            labels.append(truth)
            baselines.append(idw)
    return rows, np.asarray(features).reshape(-1, 25), np.asarray(labels).reshape(-1, 6), np.asarray(baselines).reshape(-1, 6)


def metric(y, p):
    valid = np.isfinite(y) & np.isfinite(p)
    if not valid.any():
        return dict(rows=0, mae=None, rmse=None)
    error = y[valid]-p[valid]
    return dict(rows=int(valid.sum()), mae=float(np.abs(error).mean()), rmse=float(np.sqrt((error**2).mean())))


def evaluate(observations, stations, validation_stations, test_stations, validation_start, test_start):
    frame = validate_observations(observations)
    if set(stations.columns) != {'location_id', 'latitude', 'longitude'} or stations.location_id.duplicated().any():
        raise ValueError('Unique verified station coordinates required')
    stations = stations.copy()
    stations['location_id'] = stations.location_id.astype(str)
    for row in stations.itertuples():
        coordinates(row.latitude, row.longitude)
    frame = frame.merge(stations, on='location_id', validate='many_to_one')
    if len(frame) != len(observations):
        raise ValueError('Missing station coordinates')
    v, t = pd.Timestamp(validation_start), pd.Timestamp(test_start)
    if v.tzinfo is None or t.tzinfo is None or v >= t:
        raise ValueError('Ordered timezone-aware cutoffs required')
    available = set(frame.location_id)
    val, test = set(validation_stations), set(test_stations)
    training = available - val - test
    if not val or not test or val & test or not (val | test) <= available or len(training) < 3:
        raise ValueError('Disjoint nonempty station splits and >=3 training nodes required')
    # Also ban co-located aliases across splits, which otherwise leak node truth.
    positions = stations.set_index('location_id')[['latitude', 'longitude']]
    for a, b in [(training, val), (training, test), (val, test)]:
        if set(map(tuple, positions.loc[list(a)].to_numpy())) & set(map(tuple, positions.loc[list(b)].to_numpy())):
            raise ValueError('Co-located stations cross split boundaries')
    _, x, y, _ = examples(frame[frame.timestamp_utc < v], training, training)
    _, vx, vy, _ = examples(frame[(frame.timestamp_utc >= v) & (frame.timestamp_utc < t)], val, training)
    rows, tx, ty, idw = examples(frame[frame.timestamp_utc >= t], test, training)
    if not len(x) or not len(vx) or not len(tx):
        raise ValueError('Empty training, validation or test examples')
    ensemble = SpatialEnsemble().fit(x, y, vx, vy)
    output = [ensemble.predict(**row)['targets'] for row in rows]
    pred = np.array([[r[c]['prediction'] if r[c]['prediction'] is not None else np.nan for c in RAW_SENSOR_COLUMNS] for r in output])
    nearest, mean = np.full_like(idw, np.nan), np.full_like(idw, np.nan)
    for j, row in enumerate(rows):
        for i, target in enumerate(RAW_SENSOR_COLUMNS):
            candidates = []
            for node in row['nodes']:
                _, b, count = snapshot_features([node], row['latitude'], row['longitude'], row['timestamp'])
                if count[i]:
                    a, b_lon = np.radians([node['latitude'], node['longitude']])
                    q_a, q_b = np.radians([row['latitude'], row['longitude']])
                    angle = np.clip(np.sin(a)*np.sin(q_a)+np.cos(a)*np.cos(q_a)*np.cos(b_lon-q_b), -1, 1)
                    candidates.append((np.arccos(angle), b[i]))
            if candidates:
                nearest[j, i] = min(candidates)[1]
                mean[j, i] = np.mean([value for _, value in candidates])
    metrics = {}
    for i, target in enumerate(RAW_SENSOR_COLUMNS):
        # Paired finite rows for all methods; report missing coverage separately.
        paired = np.isfinite(ty[:, i]) & np.isfinite(pred[:, i]) & np.isfinite(idw[:, i])
        metrics[target] = {kind: metric(ty[paired, i], values[paired, i]) for kind, values in
                          [('ensemble', pred), ('idw', idw), ('nearest_node', nearest), ('node_mean', mean)]}
        metrics[target]['unavailable_predictions'] = int((~np.isfinite(pred[:, i])).sum())
        bands = np.array([r[target]['absolute_error_p90'] if r[target]['absolute_error_p90'] is not None else np.nan for r in output])
        calibrated = paired & np.isfinite(bands)
        metrics[target]['band_rows'] = int(calibrated.sum())
        metrics[target]['empirical_band_coverage'] = float(np.mean(np.abs(ty[calibrated, i]-pred[calibrated, i]) <= bands[calibrated])) if calibrated.any() else None
    return dict(schema_version='indra_spatial_experiment_v1', task='current-time withheld-node interpolation',
        seed=42, python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__, sklearn=sklearn.__version__,
        split=dict(training_stations=sorted(training), validation_stations=sorted(val), test_stations=sorted(test),
                   validation_start=str(v), test_start=str(t), context='training stations only; query always excluded'),
        examples=dict(train=len(x), validation=len(vx), test=len(tx)), metrics=metrics,
        heads={name: dict(weights=head['weights'], absolute_error_p90=head['p90'], training_failures=head['failures']) for name, head in ensemble.heads.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['observations', 'stations', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ['validation-stations', 'test-stations']:
        parser.add_argument('--'+name, nargs='+', required=True)
    for name in ['validation-start', 'test-start']:
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    report = evaluate(pd.read_csv(args.observations), pd.read_csv(args.stations), args.validation_stations,
                      args.test_stations, args.validation_start, args.test_start)
    report['input_sha256'] = {str(path): sha256(path) for path in [args.observations, args.stations]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
