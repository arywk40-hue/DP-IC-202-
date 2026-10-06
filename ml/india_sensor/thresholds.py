"""Fixed-policy validation-only decision tuning; no test-label arguments."""
import numpy as np


def decision_metrics(y, scores, threshold, cadence=3600):
    y, scores = np.asarray(y, float), np.asarray(scores, float)
    good = np.isfinite(y) & np.isfinite(scores)
    y, scores = y[good], scores[good]
    if not len(y) or threshold is None:
        return {'rows': len(y), 'status': 'NO_VALIDATED_DECISION_THRESHOLD'}
    flag = scores >= threshold
    tp = int(((y == 1) & flag).sum())
    fp = int(((y == 0) & flag).sum())
    fn = int(((y == 1) & ~flag).sum())
    tn = int(((y == 0) & ~flag).sum())
    return {'rows': len(y), 'positives': tp+fn, 'threshold': float(threshold),
            'precision': tp/(tp+fp) if tp+fp else 0., 'recall': tp/(tp+fn) if tp+fn else None,
            'f1': 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.,
            'f2': 5*tp/(5*tp+4*fn+fp) if 5*tp+4*fn+fp else 0.,
            'false_positive_hours_per_station_day': fp/(len(y)*cadence/86400),
            'confusion_matrix': [[tn, fp], [fn, tp]], 'missed_positive_hours': fn}


def tune(y, scores, episode_ids, sites, policy, cadence=3600):
    y, scores = np.asarray(y, float), np.asarray(scores, float)
    episodes, sites = np.asarray(episode_ids), np.asarray(sites)
    if not (len(y) == len(scores) == len(episodes) == len(sites)):
        raise ValueError('Validation arrays differ in length')
    good = np.isfinite(y) & np.isfinite(scores)
    y, scores, episodes, sites = y[good], scores[good], episodes[good], sites[good]
    if not np.isin(y, [0, 1]).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError('Invalid observed binary labels/scores')
    support = {'positive_hours': int((y == 1).sum()), 'negative_hours': int((y == 0).sum()),
               'positive_episodes': len(np.unique(episodes[y == 1])), 'positive_sites': len(np.unique(sites[y == 1]))}
    result = {'status': 'INSUFFICIENT_VALIDATION_SUPPORT', 'raw_threshold': None, 'support': support,
              'policy': policy, 'selection_data': 'validation_only'}
    if support['positive_hours'] < policy['minimum_positive_hours'] or not support['negative_hours'] or support['positive_episodes'] < policy['minimum_positive_episodes'] or support['positive_sites'] < policy['minimum_positive_sites']:
        return result
    order = np.argsort(-scores, kind='stable')
    p, truth = scores[order], y[order]
    ends = np.r_[np.flatnonzero(p[:-1] != p[1:]), len(p)-1]
    tp = np.cumsum(truth)[ends]
    fp = ends+1-tp
    fn = truth.sum()-tp
    b2 = policy['beta']**2
    f = (1+b2)*tp/np.maximum((1+b2)*tp+b2*fn+fp, 1)
    allowed = fp/(len(y)*cadence/86400) <= policy['max_false_positive_hours_per_station_day']
    # Prefer higher threshold on equal objective; never force an alarm cutoff.
    eligible = np.flatnonzero(allowed & (tp > 0))
    if not len(eligible):
        result['status'] = 'NO_FEASIBLE_VALIDATION_CUTOFF'
        return result
    best = eligible[np.argmax(f[eligible])]
    cutoff = float(p[ends[best]])
    return {**result, 'status': 'VALIDATION_SELECTED_RESEARCH_ONLY', 'raw_threshold': cutoff,
            'validation_decisions': decision_metrics(y, scores, cutoff, cadence)}
