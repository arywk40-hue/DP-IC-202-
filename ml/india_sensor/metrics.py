"""Rare-target metrics and station-cluster error bands, never accuracy alone."""
import numpy as np
from sklearn.metrics import average_precision_score, f1_score

from ml.deployment.field_validation import binary_metrics


def metrics(y, p, cadence_seconds=3600):
    y, p = np.asarray(y), np.asarray(p)
    good = np.isfinite(y) & np.isfinite(p)
    y, p = y[good], p[good]
    if not len(y):
        return {'rows': 0}
    report = binary_metrics(y, p)
    if not y.sum():
        report['recall_at_0_5'] = None
    report['pr_auc_average_precision'] = float(average_precision_score(y, p)) if y.sum() else None
    report['f1_at_0_5'] = float(f1_score(y, p >= .5, zero_division=0))
    report['monitored_station_days'] = len(y)*cadence_seconds/86400
    report['false_alarm_hours_per_monitored_station_day'] = report['false_positives']/report['monitored_station_days']
    report['missed_positive_hour_fraction'] = report['false_negatives']/int(y.sum()) if y.sum() else None
    report['confusion_matrix_actual_rows_predicted_columns'] = [[int(((y == 0) & (p < .5)).sum()), report['false_positives']],
                                                               [report['false_negatives'], int(((y == 1) & (p >= .5)).sum())]]
    bins = np.minimum((p*10).astype(int), 9)
    calibration = []
    for b in range(10):
        m = bins == b
        if m.any():
            calibration.append({'bin': b, 'rows': int(m.sum()), 'mean_probability': float(p[m].mean()),
                                'observed_fraction': float(y[m].mean())})
    report['reliability_bins'] = calibration
    report['ece_10bins'] = float(sum(v['rows']/len(y)*abs(v['mean_probability']-v['observed_fraction']) for v in calibration))
    return report


def cluster_brier_interval(y, p, sites, seed=42, repeats=200):
    good = np.isfinite(y) & np.isfinite(p)
    y, p, sites = np.asarray(y)[good], np.asarray(p)[good], np.asarray(sites)[good]
    unique = np.unique(sites)
    if len(unique) < 2:
        return None
    # Aggregate within station first; resample whole stations, retaining hours.
    totals = np.array([(((p[sites == s]-y[sites == s])**2).sum(), (sites == s).sum()) for s in unique])
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(unique), size=(repeats, len(unique)))
    sums = totals[indices].sum(axis=1)
    return np.quantile(sums[:, 0]/sums[:, 1], [.025, .975]).tolist()
