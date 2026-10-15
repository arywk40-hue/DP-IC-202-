"""Small fixed-epoch neural ranking model, no random early-stopping split."""
from __future__ import annotations

import pandas as pd
from sklearn.neural_network import MLPClassifier


def fit_mlp(x: pd.DataFrame, y: pd.Series, cfg: dict) -> MLPClassifier:
    """Train in row order with a predeclared epoch budget."""
    args = cfg['models']['mlp']
    model = MLPClassifier(hidden_layer_sizes=tuple(args['hidden_layers']), max_iter=args['epochs'],
        alpha=args['alpha'], learning_rate_init=args['learning_rate'], batch_size=min(args['batch_size'], len(x)),
        random_state=cfg['models']['seed'], early_stopping=False, shuffle=False)
    model.set_params(tol=0, n_iter_no_change=args['epochs'] + 1)
    return model.fit(x, y)
