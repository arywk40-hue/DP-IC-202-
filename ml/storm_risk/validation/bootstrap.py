"""Resample entire UTC days, retaining all hours/cells within selected days."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.storm_risk.validation.metrics import metrics


def day_bootstrap(frame: pd.DataFrame, scores: np.ndarray, cfg: dict) -> dict:
    """Return fixed-seed percentile intervals; degenerate draws remain missing."""
    gate = cfg['gate']
    groups = list(frame.groupby(frame.time.dt.floor('D'), sort=True).indices.values())
    names = ['brier_score', 'reliability', 'resolution', 'uncertainty', 'brier_skill_score']
    output = dict(method='WHOLE_UTC_DAY_BLOCK_BOOTSTRAP', resamples=gate['bootstrap_resamples'],
        seed=gate['bootstrap_seed'], days=len(groups), confidence_level=gate['confidence_level'], intervals={})
    if len(groups) < gate['min_test_days']:
        output['intervals'] = {name: dict(lower=None, upper=None, valid_resamples=0) for name in names}
        return output
    rng = np.random.default_rng(gate['bootstrap_seed'])
    values = {name: [] for name in names}
    y = frame.label.to_numpy(int)
    for _ in range(gate['bootstrap_resamples']):
        indices = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        result = metrics(y[indices], scores[indices], cfg)
        for name in names:
            if result[name] is not None:
                values[name].append(result[name])
    alpha = (1 - gate['confidence_level']) / 2
    for name, draws in values.items():
        interval = np.quantile(draws, [alpha, 1 - alpha]).tolist() if draws else [None, None]
        output['intervals'][name] = dict(lower=interval[0], upper=interval[1], valid_resamples=len(draws))
    return output
