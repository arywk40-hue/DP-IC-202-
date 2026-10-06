"""Summarize a completed frozen benchmark; no retraining/test-set tuning."""
import argparse
import json
from pathlib import Path

from ml.india_sensor.config import DEFAULT, load


def number(value):
    return '—' if value is None else f'{value:.8g}'


def run(cfg):
    path = Path(cfg['reports']) / 'results.json'
    result = json.loads(path.read_text())
    lines = ['# India sensor-only forecast results', '',
             '**Real NOAA observations; not disaster or physical INDRA sensor validation.**', '',
             'Exact completed-hour measurements at issue time +6h. Brier is squared probability error (lower is better); AP is average precision (higher is better).', '',
             'A: sensor/time; B: +GPS/height; C: B with independently fitted mountain calibration if available; D: regional experts with B fallback.', '',
             'Calibration and threshold availability are head-specific; consult the model manifest. Persistence repeats the current threshold; prevalence uses training labels only.', '',
             'Table values use eight significant digits; full precision and per-region metrics are in [results.json](results.json).', '']
    losses = []
    for scope, experiment in result['experiment'].items():
        lines += [f'## {scope}', '', '| Target | Method | Hours / positives | Brier | 95% station-bootstrap CI | AP | Recall at 0.5 | False-positive hours/station-day |',
                  '|---|---|---:|---:|---|---:|---:|---:|']
        for name, target in experiment['targets'].items():
            methods = {**target['strategies'], **target.get('baselines', {})}
            for method, report in methods.items():
                r = report.get('overall', {'rows': 0})
                ci = r.get('brier_station_bootstrap_95ci')
                interval = '—' if ci is None else f'[{number(ci[0])}, {number(ci[1])}]'
                lines.append(f"| {name} | {method} | {r['rows']} / {r.get('positives', 0)} | {number(r.get('brier'))} | {interval} | {number(r.get('pr_auc_average_precision'))} | {number(r.get('recall_at_0_5'))} | {number(r.get('false_alarm_hours_per_monitored_station_day'))} |")
            available = {k: v['overall']['brier'] for k, v in methods.items() if v.get('overall', {}).get('rows', 0)}
            if available:
                best = min(available, key=available.get)
                for method in ['A', 'B', 'C', 'D']:
                    if method in available and available[method] > available[best]:
                        losses.append(f'{scope}, {name}: {method} loses on Brier to {best} ({number(available[method])} vs {number(available[best])}).')
        lines += ['', '| Target | Method | Tuned precision | Tuned recall | F1 | Positive hours |', '|---|---|---:|---:|---:|---:|']
        for name, target in experiment['targets'].items():
            for method, report in target['strategies'].items():
                d = report.get('raw_validation_cutoff_test')
                if d:
                    lines.append(f"| {name} | {method} | {number(d['precision'])} | {number(d['recall'])} | {number(d['f1'])} | {d['positives']} |")
        lines.append('')
    lines += ['## Losses and interpretation', '', *['- '+s for s in losses], '',
              'B/C/D do not universally improve A. C/D fallback and calibration vary by scope/head. In the whole-Himalaya holdout the mountain expert has no training observations; it cannot establish regional expertise.', '',
              'Check positive counts before interpreting small Brier scores: zero positives cannot establish detection skill. RH is near saturation, not verified fog or rainfall. Recall counts positive hours, not distinct storms.', '',
              'Bootstrap resamples whole stations; shared storms and long-term temporal dependence remain. These are metric confidence intervals, not 80/90% prediction bands. The diagnostic benchmark includes all eligible test forecasts; serving also checks fitted ranges and may refuse them.', '',
              'Thresholds and class weights were selected using validation hours only, before calibration and testing. Unsupported cutoffs are withheld in serving; diagnostic fallback at 0.5 is explicitly labeled. All disaster heads remain unavailable; field calibration is not established.']
    output = Path(cfg['reports']) / 'RESULTS.md'
    output.write_text('\n'.join(lines)+'\n')
    print(output)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--config', default=str(DEFAULT))
    a = p.parse_args()
    run(load(a.config))
