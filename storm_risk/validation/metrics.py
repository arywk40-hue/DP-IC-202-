"""Brier and counted-bin Murphy decomposition, with binning remainder explicit."""
from __future__ import annotations

import numpy as np

from storm_risk.validation.reliability import reliability_bins


def metrics(y: np.ndarray, scores: np.ndarray, cfg: dict) -> dict:
    """Compute diagnostics without selecting any threshold or fitted parameter."""
    y, scores = np.asarray(y, float), np.asarray(scores, float)
    if not len(y) or len(y) != len(scores) or not np.isfinite(scores).all() or not np.isin(y, [0, 1]).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError('Finite bounded scores and explicit binary outcomes required')
    bins = reliability_bins(y, scores, cfg)
    rate, brier = float(y.mean()), float(np.mean((scores - y) ** 2))
    reliability = sum(b['count'] / len(y) * (b['mean_forecast'] - b['observed_frequency']) ** 2 for b in bins['bins'] if b['count'])
    resolution = sum(b['count'] / len(y) * (b['observed_frequency'] - rate) ** 2 for b in bins['bins'] if b['count'])
    uncertainty = rate * (1 - rate)
    binned = reliability - resolution + uncertainty
    return dict(total_samples=len(y), positive_samples=int(y.sum()), base_rate=rate, brier_score=brier,
        reliability=reliability, resolution=resolution, uncertainty=uncertainty,
        binned_brier_score=binned, binning_remainder=brier - binned,
        decomposition='MURPHY_COUNTED_BIN_ESTIMATE_WITH_EXPLICIT_CONTINUOUS_SCORE_REMAINDER',
        brier_skill_score=1 - brier / uncertainty if uncertainty > 0 else None,
        climatology_reference='HELD_OUT_BASE_RATE_FOR_DIAGNOSTIC_REFERENCE_ONLY', reliability_diagram=bins)
