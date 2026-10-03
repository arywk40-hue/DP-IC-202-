"""Local CSV side-by-side offsets and hidden A/B/C scoring; no network writes."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS,PHYSICAL_RANGES
from ml.spatial_ensemble.physics_serving import predict_two_nodes
from ml.spatial_ensemble.model import coordinates
from ml.spatial_ensemble.network import distances_km
from ml.spatial_ensemble.physics import weighted
from ml.spatial_ensemble.residual_artifact import load
from ml.spatial_ensemble.corridor import DEFAULT_LIMITS

CORE=[RAW_SENSOR_COLUMNS[i] for i in [0,1,2,5]]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    frame=pd.read_csv(path).rename(columns={'latitude_deg':'latitude','longitude_deg':'longitude','interval_end_utc':'timestamp_utc'})
    required=['timestamp_utc','node_id','latitude','longitude','elevation_m','pressure_reference',*CORE]
    if not len(frame) or any(k not in frame for k in required):raise ValueError('Empty data or missing field columns')
    if not frame.timestamp_utc.astype(str).str.endswith('Z').all():raise ValueError('Explicit UTC timestamps ending Z required')
    frame.timestamp_utc=pd.to_datetime(frame.timestamp_utc,utc=True,errors='raise')
    if frame[['timestamp_utc','node_id']].duplicated().any():raise ValueError('Duplicate sensor/time records')
    if not set(frame.node_id)<=set('ABC'):raise ValueError('Use physical instrument identities A, B, C')
    for _,g in frame.groupby('node_id'):
        if not g.timestamp_utc.is_monotonic_increasing:raise ValueError('Out-of-order records')
    for row in frame.itertuples():
        coordinates(row.latitude,row.longitude)
        if not np.isfinite(row.elevation_m) or not -450<=row.elevation_m<=9000:raise ValueError('Invalid orthometric sensor elevation')
    if not frame.pressure_reference.eq('station').all():raise ValueError('Station absolute pressure required')
    for target in RAW_SENSOR_COLUMNS:
        value=pd.to_numeric(frame.get(target,pd.Series(np.nan,index=frame.index)),errors='coerce');lo,hi=PHYSICAL_RANGES[target]
        good=value.between(lo,hi)&np.isfinite(value)
        if target+'_valid' in frame:good &= frame[target+'_valid'].astype(str).str.lower().isin(['true','1'])
        frame[target]=value.where(good)
    return frame

def calibrate(path,output,reference='C',minimum_pairs=60):
    if minimum_pairs<10 or reference not in 'ABC':raise ValueError('Invalid calibration policy')
    frame=read(path)
    if set(frame.node_id)!=set('ABC'):raise ValueError('All three physical sensors required for calibration')
    for _,group in frame.groupby('timestamp_utc'):
        if len(group)!=3:raise ValueError('Calibration requires aligned A/B/C intervals')
        p=group[['latitude','longitude']].to_numpy()
        if max(distances_km(*p[0],p))>.020 or np.ptp(group.elevation_m.to_numpy())>.5:raise ValueError('Calibration must be colocated within 20m horizontally and 0.5m in sensor elevation')
    offsets={}
    for sensor in 'ABC':
        offsets[sensor]={}
        for target in CORE:
            table=frame.pivot(index='timestamp_utc',columns='node_id',values=target);delta=(table[reference]-table[sensor]).dropna()
            if len(delta)<minimum_pairs:raise ValueError(f'Insufficient valid paired calibration samples: {sensor}/{target}')
            correction=float(delta.median());mad=float(np.median(np.abs(delta-correction)))
            offsets[sensor][target]={'additive_offset':correction,'pairs':len(delta),'median_absolute_deviation':mad,'raw_range':[float(table[sensor].min()),float(table[sensor].max())]}
    receipt={'format':'indra_offsets_v1','reference_instrument':reference,'calibration_start_utc':frame.timestamp_utc.min().isoformat(),'calibration_end_utc':frame.timestamp_utc.max().isoformat(),'raw_file_sha256':sha(path),'offsets':offsets,'warning':'Relative side-by-side offsets, not traceable absolute calibration; validity beyond observed range and drift unverified'}
    Path(output).write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n');return receipt

def correct(row,offsets):
    result=row.copy()
    for target in CORE:
        raw=float(row[target]);v=raw+offsets[row['node_id']][target]['additive_offset'];lo,hi=PHYSICAL_RANGES[target]
        result[target]=v if np.isfinite(v) and lo<=v<=hi else np.nan
    return result

def score(path,offset_path,output,model_path=None,rotation=True,corridor_limits=None):
    frame=read(path);receipt=json.loads(Path(offset_path).read_text())
    if receipt['format']!='indra_offsets_v1' or set(receipt['offsets'])!=set('ABC'):raise ValueError('Invalid offset artifact')
    if pd.Timestamp(receipt['calibration_end_utc'])>=frame.timestamp_utc.min():raise ValueError('Calibration overlaps evaluation; offsets must be frozen beforehand')
    if model_path:model,bands=load(model_path)
    else:model,bands=None,None
    if model is not None and model.neighbor_count!=2:raise ValueError('Field scoring requires a 2-neighbor model')
    records=[]
    for stamp,group in frame.groupby('timestamp_utc',sort=True):
        raw={r['node_id']:r for r in group.to_dict('records')};corrected={id:correct(r,receipt['offsets']) for id,r in raw.items()}
        for hidden in ('ABC' if rotation else 'C'):
            if hidden not in raw:continue
            context=[id for id in 'ABC' if id!=hidden];a,b=[corrected.get(id,{}) for id in context]
            q=raw[hidden];kwargs=dict(corridor_limits=corridor_limits)
            # Only query metadata, never hidden sensor values, enter inference.
            physics=predict_two_nodes(a,b,q['latitude'],q['longitude'],stamp,q['elevation_m'],**kwargs)
            result=predict_two_nodes(a,b,q['latitude'],q['longitude'],stamp,q['elevation_m'],model=model,bands=bands,**kwargs) if model is not None else physics
            nodes=[n for n in [a,b] if n];d=distances_km(q['latitude'],q['longitude'],[[n['latitude'],n['longitude']] for n in nodes])
            for target in CORE:
                t=result['targets'][target];value=np.array([n[target] for n in nodes]);valid=np.isfinite(value)
                for method,pred in [('prediction',t['prediction']),('two_node_physics',physics['targets'][target]['prediction']),('idw',float(weighted(value,d)) if valid.any() else None),('nearest',float(value[np.where(valid)[0][np.argmin(d[valid])]]) if valid.any() else None),('node_mean',float(value[valid].mean()) if valid.any() else None)]:
                    band=t['bands'].get('0.9') if method=='prediction' else None
                    records.append(dict(timestamp_utc=stamp.isoformat(),hidden_sensor=hidden,node_a=context[0],node_b=context[1],target=target,method=method,truth_raw=q[target],truth_corrected=corrected[hidden][target],prediction=pred,status=t['status'] if method=='prediction' else ('DIAGNOSTIC_UNGUARDED' if method in ['idw','nearest','node_mean'] else physics['targets'][target]['status']),band90_lower=band[0] if band else None,band90_upper=band[1] if band else None,calibration_status=t['calibration_status'] if method=='prediction' else None))
    scored=pd.DataFrame(records)
    if not len(scored):raise ValueError('No hidden sensor observations')
    Path(output).parent.mkdir(parents=True,exist_ok=True);scored.to_csv(output,index=False);summary=[]
    for (hidden,target,method),g in scored.groupby(['hidden_sensor','target','method']):
        valid=np.isfinite(g.truth_corrected)&np.isfinite(g.prediction);error=(g.loc[valid,'prediction']-g.loc[valid,'truth_corrected']).to_numpy();covered=valid&g.band90_lower.notna()&g.band90_upper.notna()
        summary.append({'hidden_sensor':hidden,'target':target,'method':method,'truth_rows':int(g.truth_corrected.notna().sum()),'predicted_rows':int(valid.sum()),'mae':float(np.abs(error).mean()) if len(error) else None,'rmse':float(np.sqrt(np.mean(error**2))) if len(error) else None,'checked_band_rows':int(covered.sum()),'checked_band_point_coverage':float(((g.loc[covered,'truth_corrected']>=g.loc[covered,'band90_lower'])&(g.loc[covered,'truth_corrected']<=g.loc[covered,'band90_upper'])).mean()) if covered.any() else None})
    report={'input_sha256':sha(path),'offset_sha256':sha(offset_path),'model_sha256':sha(model_path) if model_path else None,'geometry_limits':corridor_limits or DEFAULT_LIMITS,'scores':summary,'warning':'Coverage conditional on emitted predictions; refusal counts remain visible. Role rotations share episodes/instruments, not independent tests. This does not calibrate new bands.'}
    Path(str(output)+'.summary.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report

def main():
    p=argparse.ArgumentParser();subs=p.add_subparsers(dest='command',required=True);c=subs.add_parser('calibrate');c.add_argument('csv');c.add_argument('--output',required=True);c.add_argument('--minimum-pairs',type=int,default=60);s=subs.add_parser('score');s.add_argument('csv');s.add_argument('--offsets',required=True);s.add_argument('--output',required=True);s.add_argument('--model');s.add_argument('--hide-c-only',action='store_true')
    for key,default in DEFAULT_LIMITS.items():s.add_argument('--'+key.replace('_','-'),type=float,default=default)
    args=p.parse_args()
    result=calibrate(args.csv,args.output,minimum_pairs=args.minimum_pairs) if args.command=='calibrate' else score(args.csv,args.offsets,args.output,args.model,not args.hide_c_only,{key:getattr(args,key) for key in DEFAULT_LIMITS})
    print(json.dumps(result,indent=2,allow_nan=False))
if __name__=='__main__':main()
