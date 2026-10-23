"""Counted, fixed-edge reliability bins, including boundary scores."""
from __future__ import annotations

import numpy as np


def reliability_bins(y: np.ndarray, scores: np.ndarray, cfg: dict) -> dict:
    """Retain empty bins and mark undersampled populated bins."""
    edges = np.linspace(0, 1, cfg['gate']['bin_count'] + 1)
    bins = np.minimum(np.searchsorted(edges, scores, side='right') - 1, len(edges) - 2)
    rows = []
    for index in range(len(edges) - 1):
        selected = bins == index
        n = int(selected.sum())
        rows.append(dict(lower=float(edges[index]), upper=float(edges[index + 1]), count=n,
            mean_forecast=float(scores[selected].mean()) if n else None,
            observed_frequency=float(y[selected].mean()) if n else None,
            unreliable=bool(n and n < cfg['gate']['min_bin_count'])))
    return dict(bin_edges=edges.tolist(), bins=rows, total_count=len(y))
