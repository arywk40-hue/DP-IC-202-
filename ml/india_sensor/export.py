"""Standalone C99 export of India B trees; host parity, never hardware approval.

The exact float32 engineered-feature interface is the primary export contract.
Hourly raw-to-feature C preprocessing is generated separately from its names.
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from ml.datasets.registry import digest
from ml.india_sensor.config import load
from ml.india_sensor.preprocess_c import generate
from ml.six_sensor_forecast.c_codegen import _c_float, _parse_tree, _tree_depth


def export(cfg, output, scope='national'):
    meta_path = Path(cfg['models'])/'metadata.json'
    meta = json.loads(meta_path.read_text())
    heads = [(t, meta['artifacts'][f'{scope}/{t}']['B']) for t in meta['labels']]
    if any(h.get('status') != 'RESEARCH_FITTED' for _, h in heads):
        raise ValueError('Cannot export untrained heads')
    names = list(dict.fromkeys(c for _, h in heads for c in h['features']))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    lines = ['/* India observed measurement forecasts. No disaster model. NOT HARDWARE VALIDATED. */',
             '#ifndef INDRA_INDIA_MODEL_H', '#define INDRA_INDIA_MODEL_H', '#include <math.h>', '#include <stdint.h>',
             f'#define INDRA_INDIA_FEATURES {len(names)}', f'#define INDRA_INDIA_HEADS {len(heads)}',
             '#define INDRA_DISASTER_OUTPUTS_ENABLED 0', '#define INDRA_INDIA_HARDWARE_VALIDATED 0',
             '#define INDRA_INDIA_HORIZON_HOURS 6',
             'enum { INDRA_UNTRAINED=0, INDRA_UNCALIBRATED=1, INDRA_ARCHIVE_CALIBRATED=2, INDRA_OOD=3, INDRA_INVALID_CORE=4 };',
             '/* Status/calibration are research evidence only. No field alerts. */']
    expected_models, boundaries, nodes_total = [], [], 0
    prepared = json.loads(Path(cfg['reports'], 'preparation.json').read_text())
    samples = pd.concat([pd.read_parquet(item['features'], columns=names).iloc[::100].head(30) for item in prepared['files']], ignore_index=True)
    samples = samples.sample(min(2048, len(samples)), random_state=42).to_numpy('float32')
    for j, (target, head) in enumerate(heads):
        if digest(head['artifact']) != head['sha256']:
            raise ValueError('Changed teacher artifact')
        model = XGBClassifier()
        model.load_model(head['artifact'])
        booster = model.get_booster()
        settings = json.loads(booster.save_config())['learner']
        if settings['objective']['name'] != 'binary:logistic':
            raise ValueError('Only binary-logistic measurement heads supported')
        base = float(str(settings['learner_model_param']['base_score']).strip('[]'))
        trees = [json.loads(t) for t in booster.get_dump(dump_format='json')]
        if not 0 < base < 1 or len(trees) > 40 or any(_tree_depth(t) > 3 for t in trees):
            raise ValueError('Unsupported teacher budget')
        expected_models.append(model)
        for k, tree in enumerate(trees):
            nodes = _parse_tree(tree, head['features'])
            nodes_total += len(nodes)
            lines.append(f'static inline float indra_tree_{j}_{k}(const float *x) {{')
            def emit(index, indent):
                node = nodes[index]
                if node['feature_index'] == -1:
                    lines.append(f"{indent}return {_c_float(node['leaf_value'])};")
                    return
                feature = names.index(head['features'][node['feature_index']])
                threshold = np.float32(node['threshold'])
                for value in [np.nextafter(threshold, np.float32(-np.inf)), threshold, np.nextafter(threshold, np.float32(np.inf)), np.nan]:
                    row = samples[len(boundaries) % len(samples)].copy()
                    row[feature] = value
                    boundaries.append(row)
                default = node['missing_child'] == node['left_child']
                condition = f'(isnan(x[{feature}]) || x[{feature}] < {_c_float(threshold)})' if default else f'(!isnan(x[{feature}]) && x[{feature}] < {_c_float(threshold)})'
                lines.append(f'{indent}if {condition} {{')
                emit(node['left_child'], indent+'  ')
                lines.append(indent+'} else {')
                emit(node['right_child'], indent+'  ')
                lines.append(indent+'}')
            emit(0, '  ')
            lines.append('}')
        lines += [f'static inline float indra_raw_{j}(const float *x) {{', f'  float margin={_c_float(np.log(base/(1-base)))};']
        lines += [f'  margin+=indra_tree_{j}_{k}(x);' for k in range(len(trees))]
        lines += ['  return 1.0f/(1.0f+expf(-margin));', '}']
    lines += ['/* Caller supplies exact ordered float32 features. Missing optional features use NAN; infinities refuse. */',
              'static inline int indra_india_predict(const float *x, float *raw, float *prob, int *flags, uint8_t *status) {',
              '  if (!x || !raw || !prob || !flags || !status) return 0;',
              '  for (int h=0;h<INDRA_INDIA_HEADS;++h) { raw[h]=prob[h]=NAN; flags[h]=-1; status[h]=INDRA_UNTRAINED; }',
              '  for (int i=0;i<INDRA_INDIA_FEATURES;++i) if (isinf(x[i])) return 0;']
    for c in ['temperature_c', 'relative_humidity_pct', 'wind_speed_mps']:
        i = names.index(c)
        lines += [f'  if (!isfinite(x[{i}])) {{ for (int h=0;h<INDRA_INDIA_HEADS;++h) status[h]=INDRA_INVALID_CORE; return 0; }}']
    for j, (_, head) in enumerate(heads):
        checks = [f'(!isnan(x[{names.index(c)}]) && (x[{names.index(c)}] < {_c_float(lo)} || x[{names.index(c)}] > {_c_float(hi)}))' for c, (lo, hi) in head['training_bounds'].items()]
        lines += [f'  if ({" || ".join(checks)}) status[{j}]=INDRA_OOD;', '  else {', f'    raw[{j}]=indra_raw_{j}(x);']
        fit = head.get('calibration')
        if fit:
            lines += [f'    float p=fminf(1.0f-1e-6f,fmaxf(1e-6f,raw[{j}]));',
                      f'    prob[{j}]=1.0f/(1.0f+expf(-({_c_float(fit["coefficient"])}*logf(p/(1-p))+{_c_float(fit["intercept"])})));', f'    status[{j}]=INDRA_ARCHIVE_CALIBRATED;']
        else:
            lines += [f'    status[{j}]=INDRA_UNCALIBRATED;']
        cutoff = (head.get('threshold_selection') or {}).get('raw_threshold')
        if cutoff is not None:
            lines += [f'    flags[{j}]=(raw[{j}] >= {_c_float(cutoff)});']
        lines += ['  }']
    lines += ['  return 1;', '}', '#endif', '']
    header = output/'indra_india_model.h'
    header.write_text('\n'.join(lines))
    fixture = np.vstack([samples, boundaries]).astype('float32')
    runner = '#include <stdio.h>\n#include "indra_india_model.h"\nint main(void){ float x[INDRA_INDIA_FEATURES]; while(1){for(int i=0;i<INDRA_INDIA_FEATURES;i++) if(scanf("%f",&x[i])!=1)return 0;'
    runner += ' printf("%g %g %g\\n",(double)indra_raw_0(x),(double)indra_raw_1(x),(double)indra_raw_2(x)); }}\n'
    # Raw-tree parity includes all split boundaries and missing branches;
    # serving gates are verified separately by integration tests.
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp)/'runner.c'
        source.write_text(runner)
        binary = Path(temp)/'runner'
        subprocess.run([shutil.which('cc') or 'cc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror', str(source), '-I'+str(output.resolve()), '-lm', '-o', str(binary)], check=True, capture_output=True)
        data = '\n'.join(' '.join(f'{float(v):.9g}' for v in r) for r in fixture)+'\n'
        actual = np.array([[float(v) for v in line.split()] for line in subprocess.run([str(binary)], input=data, capture_output=True, text=True, check=True).stdout.splitlines()])
        expected = np.column_stack([m.predict_proba(fixture[:, [names.index(c) for c in h['features']]])[:, 1] for m, (_, h) in zip(expected_models, heads)])
        errors = np.max(np.abs(actual-expected), axis=0)
        if actual.shape != expected.shape or not np.isfinite(errors).all() or errors.max() > 5e-5:
            raise RuntimeError('Python/C raw-tree parity failed: '+str(errors))
    preprocessing = generate(names, output)
    report = {'status': 'HOST_VERIFIED_NOT_HARDWARE_VALIDATED', 'scope': scope, 'strategy': 'B',
              'feature_order': names, 'targets': [t for t, _ in heads], 'thresholds': {t: h.get('threshold_selection') for t, h in heads},
              'calibration': {t: h.get('calibration') for t, h in heads}, 'teacher_model_sha256': {t: h['sha256'] for t, h in heads},
              'metadata_sha256': digest(meta_path), 'header_sha256': digest(header), 'preprocessing_header_sha256': digest(output/'indra_india_preprocess.h'), 'header_bytes': header.stat().st_size,
              'total_tree_nodes': nodes_total, 'host_parity_rows': len(fixture), 'host_max_raw_error': errors.tolist(),
              'heap_allocation': False, 'disaster_outputs': 'DISABLED', 'sampling_seconds': 3600,
              'preprocessing': preprocessing,
              'board_ram_flash_cpu': 'Cross-compile/static size separately; actual board runtime/power/soak unverified'}
    (output/'export_manifest.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--config', default='configs/india_sensor_offline.json')
    p.add_argument('--output', default='esp32/india_sensor/export')
    p.add_argument('--scope', default='national')
    a = p.parse_args()
    print(json.dumps(export(load(a.config), a.output, a.scope), indent=2))
