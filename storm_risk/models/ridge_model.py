"""Configured bounded linear ranking model."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.linear_model import LogisticRegression, Ridge, RidgeClassifier


def fit_ridge(x: pd.DataFrame, y: pd.Series, cfg: dict) -> object:
    """Fit one linear variant using training rows only."""
    args = cfg['models']['ridge']
    if args['variant'] == 'ridge_regression':
        model = Ridge(alpha=args['alpha'])
    elif args['variant'] == 'ridge_classifier':
        model = RidgeClassifier(alpha=args['alpha'])
    elif args['variant'] == 'logistic_l2':
        model = LogisticRegression(C=1 / args['alpha'], max_iter=args['max_iter'], random_state=cfg['models']['seed'])
    else:
        raise ValueError('Unknown configured linear variant')
    return model.fit(x, y)


def score_ridge(model: object, x: pd.DataFrame, variant: str) -> np.ndarray:
    """Return a bounded ranking score, without implying calibration."""
    if variant == 'ridge_regression':
        return np.clip(model.predict(x), 0, 1)
    return expit(model.decision_function(x))
