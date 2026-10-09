"""Explicit phase commands; no default download, training or deployment side effects."""
import argparse
import json
import os
from pathlib import Path

import pandas as pd

from ml.datasets.registry import digest
from ml.hazard_context.acquire import audit,download
from ml.hazard_context.era5 import normalize_files,verify_requests
from ml.hazard_context.events import DEFAULT_TRAINING_TARGETS,TARGETS,read_events,schema
from ml.hazard_context.matching import match
from ml.hazard_context.output import new_file


def write(path,value):
    p=Path(path);text=json.dumps(value,indent=2,allow_nan=False)+'\n'
    if p.exists() and p.read_text()==text:return
    p=new_file(p);p.write_text(text)


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('audit-era5');a.add_argument('--requests',default='data/registry/cds_physics_requests.json');a.add_argument('--data-root',default='data');a.add_argument('--output',default='reports/hazard_context_phase/era5_audit.json')
    a=sub.add_parser('download-era5');a.add_argument('--requests',default='data/registry/cds_physics_requests.json');a.add_argument('--output',default='data/backgrounds/raw/era5_land');a.add_argument('--execute',action='store_true');a.add_argument('--accepted-terms',action='store_true')
    a=sub.add_parser('schema');a.add_argument('--output',default='configs/hazard_event_schema.json')
    for name in ['normalize-events','match','warning-labels','train-hazards']:
        a=sub.add_parser(name);a.add_argument('--events',required=True);a.add_argument('--sources',default='configs/hazard_sources.json');a.add_argument('--output',required=True);a.add_argument('--restricted',action='store_true')
        if name in ['train-hazards','warning-labels']:
            a.add_argument('--targets',nargs='+',choices=sorted(TARGETS),
                           help='Independent event heads to evaluate for research training; admission checks still apply')
            a.add_argument('--warning-protocol',default='configs/himalayan_warning_v1.json')
        if name=='train-hazards':
            a.add_argument('--label-mode',choices=['exact_future_window','next_h_hours'],default='exact_future_window')
        if name!='normalize-events':
            a.add_argument('--matching-config');a.add_argument('--stations',required=True);a.add_argument('--observations',required=True);a.add_argument('--monitoring',required=True);a.add_argument('--config',default='configs/india_sensor_offline.json')
    a=sub.add_parser('prepare-era5');a.add_argument('--input',nargs='+',required=True);a.add_argument('--stations',required=True);a.add_argument('--metadata',required=True);a.add_argument('--output',required=True)
    a=sub.add_parser('compare');a.add_argument('--observations',required=True);a.add_argument('--background',required=True);a.add_argument('--manifest',required=True);a.add_argument('--output',required=True);a.add_argument('--config',default='configs/india_sensor_offline.json');a.add_argument('--scope',default='national',choices=['national','temporal','himalaya_only','himalaya_holdout'])
    a=sub.add_parser('episodes');a.add_argument('--input',required=True);a.add_argument('--threshold',required=True,type=float);a.add_argument('--output',required=True)
    a=p.parse_args()
    if a.command=='audit-era5':result=audit(a.requests,a.data_root);write(a.output,result)
    elif a.command=='schema':result=schema();write(a.output,result)
    elif a.command=='download-era5':
        result=verify_requests(a.requests)
        if a.execute:
            if not a.accepted_terms:raise ValueError('Manual accepted terms required')
            if not Path.home().joinpath('.cdsapirc').is_file() and not os.environ.get('CDSAPI_KEY'):
                result.update(ERA5_DOWNLOAD_STATUS='BLOCKED_BY_ACCESS',authenticated_submission_verified=False)
            else:
                import cdsapi  # Normal authentication only after explicit execution/terms.
                result=download(cdsapi.Client(),json.loads(Path(a.requests).read_text())['requests'],a.output,True)
        else:result.update(status='DRY_RUN_NO_AUTHENTICATION',manual='Accept terms and own token; then --execute --accepted-terms')
    elif a.command in ['normalize-events','match','warning-labels','train-hazards']:
        sources={s['source_dataset']:s for s in json.loads(Path(a.sources).read_text())['sources']}
        quarantine=[] if a.command=='normalize-events' else None
        events=read_events(a.events,sources,a.restricted,quarantine)
        if a.command=='normalize-events':
            output=new_file(a.output)
            output.write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in events))
            quarantine_path=new_file(output.with_suffix('.quarantine.jsonl'))
            quarantine_path.write_text(''.join(json.dumps(r)+'\n' for r in quarantine))
            result={'quarantined_rows':len(quarantine),'quarantine_sha256':digest(quarantine_path),'normalized_events':len(events),'input_sha256':digest(a.events),'source_registry_sha256':digest(a.sources),'output_sha256':digest(output),'used_for_training':False}
            write(output.with_suffix('.manifest.json'),result)
        else:
            stations=pd.read_csv(a.stations);observations=pd.read_csv(a.observations)
            monitoring=json.loads(Path(a.monitoring).read_text())
            if a.command=='match':
                matching=json.loads(Path(a.matching_config).read_text()) if a.matching_config else None
                matched=match(events,stations,observations,monitoring,cfg=matching,restricted=a.restricted)
                output=new_file(a.output);matched.to_csv(output,index=False)
                result={'association_rows':len(matched),'label_semantics':'Nearby event association; pre/post periods remain unlabeled'}
            elif a.command=='warning-labels':
                from ml.hazard_context.warning import load_protocol, mask_incomplete_history, warning_targets
                from ml.india_sensor.config import load
                from ml.india_sensor.features import build
                protocol=load_protocol(a.warning_protocol);config=load(a.config)
                if (config['forecast_hours'],config['history_minutes'],config['cadence_seconds'])!=(protocol['horizon_hours'],protocol['history_minutes'],protocol['cadence_seconds']):raise ValueError('Sensor configuration differs from warning protocol')
                if a.matching_config:raise ValueError('Warning matching limits come from the versioned protocol')
                selected=list(dict.fromkeys(a.targets or protocol['targets']))
                if set(selected)-set(protocol['targets']):raise ValueError('Target absent from warning protocol')
                frame=build(observations,config)
                labels=pd.concat([mask_incomplete_history(warning_targets(frame,events,stations,monitoring,t,protocol['horizon_hours'],protocol['matching'],a.restricted),frame,protocol['history_minutes'],protocol['cadence_seconds']) for t in selected],ignore_index=True)
                output=new_file(a.output);labels.to_csv(output,index=False)
                result={'label_mode':'next_h_hours','protocol_sha256':protocol['_sha256'],'protocol':protocol,'rows':len(labels),
                        'positive_rows':int(labels.label.eq(1).sum()),'negative_rows':int(labels.label.eq(0).sum()),'unknown_rows':int(labels.label.isna().sum()),
                        'events_sha256':digest(a.events),'sources_sha256':digest(a.sources),'stations_sha256':digest(a.stations),'observations_sha256':digest(a.observations),'monitoring_sha256':digest(a.monitoring),
                        'config_sha256':digest(a.config),'output_sha256':digest(output),'used_for_training':False}
                write(output.with_suffix('.manifest.json'),result)
            else:
                from ml.india_sensor.config import load
                from ml.hazard_context.train import run
                from ml.hazard_context.warning import load_protocol
                defaults=load_protocol(a.warning_protocol)['targets'] if a.label_mode=='next_h_hours' else DEFAULT_TRAINING_TARGETS
                provenance={name:digest(getattr(a,name)) for name in ['events','sources','stations','observations','monitoring','config']}
                result=run(events,sources,stations,observations,monitoring,load(a.config),a.output,list(dict.fromkeys(a.targets or defaults)),restricted=a.restricted,matching_cfg=json.loads(Path(a.matching_config).read_text()) if a.matching_config else None,label_mode=a.label_mode,warning_protocol=a.warning_protocol if a.label_mode=='next_h_hours' else None,input_provenance=provenance)
    elif a.command=='prepare-era5':
        _,result=normalize_files(a.input,pd.read_csv(a.stations),json.loads(Path(a.metadata).read_text()),a.output)
    elif a.command=='compare':
        from ml.india_sensor.config import load
        from ml.hazard_context.compare import run
        manifest=json.loads(Path(a.manifest).read_text())
        if manifest.get('normalized_sha256')!=digest(a.background):raise ValueError('Background provenance hash differs')
        result=run(pd.read_csv(a.observations),pd.read_parquet(a.background),load(a.config),manifest,a.output,a.scope)
    else:
        from ml.hazard_context.episodes import evaluate
        result=evaluate(pd.read_csv(a.input),a.threshold);write(a.output,result)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
