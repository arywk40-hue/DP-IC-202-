"""Keep risk naming unless the independent held-out gate passes."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


def fit_calibrator(scores: np.ndarray, frame: pd.DataFrame, cfg: dict, audit: list) -> tuple[object | None, str, list[str]]:
    """Fit only declared calib rows after checking both class counts."""
    if not frame.split.eq('calib').all():
        raise ValueError('Calibrator fitting accepts only calib rows')
    args = cfg['calibration']
    if (args['method'] == 'none' or frame.label.eq(1).sum() < args['min_positives_calib']
            or frame.label.eq(0).sum() < args['min_negatives_calib']):
        return None, 'none', ['CALIBRATION_SKIPPED_DISABLED_OR_INSUFFICIENT_CLASSES']
    model = IsotonicRegression(out_of_bounds='clip') if args['method'] == 'isotonic' else LogisticRegression(
        random_state=cfg['models']['seed'], max_iter=cfg['models']['ridge']['max_iter'])
    model.fit(scores if args['method'] == 'isotonic' else scores.reshape(-1, 1), frame.label)
    audit.append(dict(stage='calibrator_fit', role='calib', row_ids=frame.index.tolist()))
    return model, args['method'], []


def apply_calibrator(model: object | None, method: str, scores: np.ndarray) -> np.ndarray:
    """Return a bounded mapped score; naming is a separate gate decision."""
    if model is None:
        return scores.copy()
    return np.asarray(model.predict(scores) if method == 'isotonic' else model.predict_proba(scores.reshape(-1, 1))[:, 1])
