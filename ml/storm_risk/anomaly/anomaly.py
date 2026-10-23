"""Training-only monthly percentile climatology."""
from __future__ import annotations

import pandas as pd


def fit_thresholds(train: pd.DataFrame, features: list[str], cfg: dict) -> dict:
    """Fit spatial-grid monthly context thresholds from train rows only."""
    if not train.split.eq('train').all():
        raise ValueError('Anomaly climatology requires train rows')
    return {str(month): group[features].quantile(cfg['anomaly']['percentile'] / 100).to_dict()
            for month, group in train.groupby(train.time.dt.month)}


def flag_anomalies(frame: pd.DataFrame, thresholds: dict, features: list[str]) -> pd.DataFrame:
    """Report uncovered months explicitly; an anomaly is not a fault or event."""
    values = []
    for row in frame.itertuples(index=False):
        monthly = thresholds.get(str(row.time.month))
        names = [] if monthly is None else [name for name in features if getattr(row, name) > monthly[name]]
        values.append(dict(anomaly_flag=bool(names), anomaly_features=','.join(names), anomaly_available=monthly is not None))
    return pd.DataFrame(values, index=frame.index)
