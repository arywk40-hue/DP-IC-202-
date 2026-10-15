"""Chronological inner validation for boosted context classification."""
from __future__ import annotations

import pandas as pd
from xgboost import XGBClassifier


def fit_xgb(x: pd.DataFrame, y: pd.Series, validation_x: pd.DataFrame, validation_y: pd.Series, cfg: dict) -> XGBClassifier:
    """Early-stop solely on the tail of the training partition."""
    counts = y.value_counts()
    if len(counts) != 2:
        raise ValueError('Boosted training requires both explicit classes')
    model = XGBClassifier(**cfg['models']['xgb'], objective='binary:logistic', eval_metric='logloss',
        scale_pos_weight=float(counts[0] / counts[1]), random_state=cfg['models']['seed'])
    model.fit(x, y, eval_set=[(validation_x, validation_y)], verbose=False)
    return model
