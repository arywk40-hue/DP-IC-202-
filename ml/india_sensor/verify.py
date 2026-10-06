"""Recompute frozen archive features and source/split contracts without retraining."""
import argparse
import json
from pathlib import Path

import pandas as pd

from ml.datasets.registry import digest
from ml.india_sensor.config import load
from ml.india_sensor.features import build
from ml.india_sensor.prepare import normalize


def run(cfg):
    preparation = json.loads(Path(cfg['reports'], 'preparation.json').read_text())
    model = json.loads(Path(cfg['reports'], 'model_manifest.json').read_text())
    summary = {'rows': 0, 'source_rows': {}, 'country_rows': {}, 'recomputed_feature_files': 0,
               'station_coverage': [], 'all_frozen_hashes_match': True}
    for path, expected in preparation['input_sha256'].items():
        if digest(path) != expected:
            raise ValueError('Changed source: '+path)
    original, _ = normalize(pd.read_parquet(cfg['hours']), pd.read_csv(cfg['stations']), pd.read_csv(cfg['station_qc']), cfg)
    groups = original.groupby('physical_site_id').groups
    for i, item in enumerate(preparation['files']):
        path = Path(item['features'])
        if digest(path) != item['feature_sha256'] or digest(item['labels']) != item['label_sha256']:
            raise ValueError('Changed prepared features/labels')
        raw = original.loc[groups[item['physical_site_id']]].sort_values('timestamp_utc').reset_index(drop=True)
        old = pd.read_parquet(path)
        new = build(raw, cfg)
        # Exact same already-QC'd raw channels; compare all feature names/masks/values.
        pd.testing.assert_frame_equal(old, new, check_exact=True)
        summary['recomputed_feature_files'] += 1
        summary['rows'] += len(raw)
        for col, key in [('source_id','source_rows'), ('country_code','country_rows')]:
            for source, n in raw[col].value_counts().items():
                summary[key][source] = summary[key].get(source,0)+int(n)
        summary['station_coverage'].append({'physical_site_id':item['physical_site_id'], 'rows':len(raw),
                                          'start_utc':raw.timestamp_utc.min().isoformat(), 'end_utc':raw.timestamp_utc.max().isoformat(),
                                          'observed_core':{c:int(raw[c].notna().sum()) for c in ['temperature_c','relative_humidity_pct','pressure_hpa','wind_speed_mps']}})
        if i%50==0:
            print('Rechecked',i+1,'stations',flush=True)
    if set(summary['source_rows']) != {'noaa_ghcnh'} or set(summary['country_rows']) != {'IN'}:
        raise ValueError('Source/country isolation failed')
    summary['china_training_evaluation_rows'] = 0
    heads = []
    for key, strategies in model['artifacts'].items():
        for strategy, head in strategies.items():
            candidates = head.get('experts',{}).items() if strategy=='D' else [(strategy,head)]
            for name, h in candidates:
                if h.get('status')=='RESEARCH_FITTED':
                    if digest(h['artifact']) != h['sha256']:
                        raise ValueError('Changed model')
                    if not h.get('reproducibility',{}).get('identical_model_bytes'):
                        raise ValueError('Reproducibility not verified')
                    heads.append({'head':key+'/'+name, 'sha256':h['sha256'], 'selected_weight':h.get('selected_weight'),
                                  'threshold':h.get('threshold_selection'), 'calibration_available':bool(h.get('calibration'))})
    summary['repeated_identical_fits'] = len(heads)
    summary['fitted_heads'] = heads
    summary['hardware_validated'] = False
    summary['implementation_sha256_current'] = {p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}
    summary['implementation_changed_since_fit'] = [name for name, old in model['implementation_sha256'].items() if summary['implementation_sha256_current'].get(name)!=old]
    summary['feature_change_receipt'] = 'All frozen archive feature matrices exactly reproduced by current source; serving reference-mask fix does not change measured fit data.'
    Path(cfg['reports'],'validation.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    pd.DataFrame(summary['station_coverage']).drop(columns='observed_core').to_csv(Path(cfg['reports'],'station_coverage.csv'),index=False)
    return {k:v for k,v in summary.items() if k not in ['station_coverage','fitted_heads','implementation_sha256_current']}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--config',default='configs/india_sensor_offline.json')
    a=p.parse_args()
    print(json.dumps(run(load(a.config)),indent=2))
