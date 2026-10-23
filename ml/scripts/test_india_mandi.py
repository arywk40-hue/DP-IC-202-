#!/usr/bin/env python3
"""India-only six-channel Mandi benchmark. --prepare downloads; --train fits fresh weights.

Default testing does not retrain or read any Chinese model. Raw datasets stay local.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from ml.india_mandi.data import load_config,prepare
from ml.india_mandi.benchmark import evaluate,fit,indian_transfer_tests
from ml.six_sensor_forecast.export import export
from ml.six_sensor_forecast.data import sha256


def render(result):
    lines=['# India-only six-channel Mandi forecast test','',
           f"Executed {result['executed_at_utc']}. No Chinese data or weights were used.",'',
           '**Evidence:** retrospective Open-Meteo/ECMWF/CAMS modeled values at Mandi; not measured six-channel field accuracy.',
           'The weather and air variables use different grids. Global CAMS is approximately 45 km and 3-hourly underneath the hourly API output.',
           'Grid surface pressure is not verified station pressure. No operational hazard accuracy or lead time is established.','',
           f"Source dates: {result['source_period']['start']} through {result['source_period']['end']}. Complete modeled rows: {result['source_manifest']['complete_six_channel_rows']:,}.",'',
           '| Split | Eligible rows | First issue UTC | Last issue UTC |','| --- | ---: | --- | --- |']
    for role,row in result['split'].items():lines.append(f"| {role} | {row['rows']} | {row['first_issue_utc']} | {row['last_issue_utc']} |")
    lines+=['','## Six-hour future-test MAE — lower is better','',
            '| Target | Persistence | Compact student | History teacher | Temporal ridge | Validation-selected head | Selected MAE |',
            '| --- | ---: | ---: | ---: | ---: | --- | ---: |']
    for target,roles in result['results'].items():
        r=roles['future_test'];chosen=result['validation_selected_heads'][target]
        lines.append(f"| {target} | {r['persistence']['mae']:.4f} | {r['student']['mae']:.4f} | {r['teacher']['mae']:.4f} | {r['temporal_ridge']['mae']:.4f} | {chosen} | {r[chosen]['mae']:.4f} |")
    lines+=['','Selections and blend weights use validation only. Persistence may win; no forecast is automatically promoted to ESP32.','',
            '## Existing India-trained research models','',
            'CPCB profiles are reduced-input experiments: five channels or particulate-only. Neither tests station pressure.','',
            '| Profile | Kind | Target | Split | Rows | MAE | Persistence MAE |','| --- | --- | --- | --- | ---: | ---: | ---: |']
    for row in result['indian_transfer_tests']:
        m=row['metrics'];lines.append(f"| {row['profile']} | {row['kind']} | {row['target']} | {row['split']} | {m['rows']} | {m['mae']:.4f} | {m['persistence_mae']:.4f} |")
    lines+=['','The original Indian secondary source assumes local timezone and excludes unverified pressure. Its completed-hour means differ from the modeled instantaneous Mandi values; this is a transfer diagnostic with an aggregation mismatch. Original Indian holdout replay performed: '+str(result['original_indian_holdout_replayed'])+'.','',
            '## Himalayan hazard status','',
            '| Target | Status |','| --- | --- |']
    for name,row in result['hazard_results'].items():lines.append(f"| {name} | {row['status']} |")
    weak=[t for t,r in result['results'].items() if r['future_test']['student']['r2']<0]
    lines+=['','Compact heads with negative future-test R2: '+', '.join(weak)+'. They beat persistence MAE here but remain weaker than a constant test-mean reference by squared error.']
    if result.get('student_c_parity'):
        lines+=['','## Compact C export — host parity only','', '```json',json.dumps(result['student_c_parity'],indent=2,allow_nan=False),'```','',
                'This compiled-host check is not a physical ESP32 execution or a field-accuracy test.']
    lines+=['','These heads need admitted independent events and monitored negatives; API rainfall is not cloudburst gauge truth.','',
            '## Input, prediction and later API examples','', '```json',json.dumps(result['examples'],indent=2,allow_nan=False),'```','',
            '## Full numerical evidence','',
            'MAE/RMSE/R² are reported in their physical units; classification accuracy/F1 do not apply to these numeric targets.',
            'No independent-site test is available for the Mandi grid. '+result['test_exposure_note'],'',
            '```json',json.dumps({k:result[k] for k in ['config_sha256','split','results','validation_selected_heads','hazard_results']},indent=2,allow_nan=False),'```','',
            'Attribution: Open-Meteo, ECMWF IFS and Copernicus Atmosphere Monitoring Service (CAMS).',
            'Source methods: https://open-meteo.com/en/docs/historical-weather-api and https://open-meteo.com/en/docs/air-quality-api.','']
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',default='ml/configs/mandi_modeled_forecast_v1.json')
    p.add_argument('--prepare',action='store_true');p.add_argument('--train',action='store_true');p.add_argument('--offline',action='store_true')
    p.add_argument('--export',action='store_true',help='Host-verify the India/Mandi compact C header; no board flashing')
    args=p.parse_args();cfg=load_config(args.config)
    if args.prepare:prepare(cfg,args.offline)
    if args.train:fit(cfg)
    result=evaluate(cfg);result['indian_transfer_tests']=indian_transfer_tests(cfg)
    result['original_indian_holdout_replayed']=any(r['split'] in ['future_test','geographic_test'] for r in result['indian_transfer_tests'])
    result['executed_at_utc']=datetime.now(timezone.utc).isoformat()
    export_root=ROOT/'ml/generated'/Path(cfg['models']).name
    if args.export:
        result['student_c_parity']=export(Path(cfg['models']),Path(cfg['data'])/'observations.csv',export_root)
    elif (export_root/'c_export_report.json').exists():
        receipt=json.loads((export_root/'c_export_report.json').read_text())
        if receipt['model_report_sha256']==sha256(Path(cfg['models'])/'training_report.json') and receipt['header_sha256']==sha256(export_root/'indra_six_sensor_forecast.h'):
            result['student_c_parity']=receipt
    output=Path(cfg['reports']);output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (output/'REPORT.md').write_text(render(result))
    print('INDIA-ONLY MANDI FORECAST BENCHMARK — modeled evidence, not field accuracy')
    for target,roles in result['results'].items():
        r=roles['future_test'];chosen=result['validation_selected_heads'][target]
        print(f"{target}: student MAE={r['student']['mae']:.4f}, persistence={r['persistence']['mae']:.4f}; validation-selected {chosen} MAE={r[chosen]['mae']:.4f}")
    print('Hazards: unavailable; no independent event labels. Chinese rows/weights used: 0.')
    print('Report:',output/'REPORT.md')


if __name__=='__main__':main()
