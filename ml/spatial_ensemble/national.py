"""Buffered whole-station and whole-region experiments, never query sensors.

Deterministic bounded experiment; held-out nodes never provide context.
Persistence is previous AVAILABLE neighbor-IDW (<=6h), not hidden query truth.
Intervals are station-bootstrap MAE confidence intervals, not independent-row CI.
"""
from __future__ import annotations
import argparse,json,warnings
from pathlib import Path
import numpy as np,pandas as pd
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.spatial_ensemble.model import SpatialEnsemble
from ml.spatial_ensemble.network import named_features,distances_km,distance_distribution,guard


def region(stations):
    # Predeclared broad mountain geography proxy, not an administrative boundary.
    return (stations.latitude.between(28,37) & stations.longitude.between(72,90) & (pd.to_numeric(stations.elevation_m,errors='coerce')>=500))


def splits(stations,heldout,seed=42,buffer_km=20):
    test=set(heldout);remaining=stations[~stations.location_id.isin(test)].copy()
    # Remove entire physical sites and all stations within buffer from model AND context.
    held=stations[stations.location_id.isin(test)]
    aliases=set(held.physical_site_id)
    def clear(row):
        return row.physical_site_id not in aliases and np.all(distances_km(row.latitude,row.longitude,held[['latitude','longitude']])>=buffer_km)
    remaining=remaining.loc[[clear(row) for row in remaining.itertuples()]]
    if len(remaining)<4:return set(),set(),test
    rng=np.random.default_rng(seed);ids=rng.permutation(remaining.location_id.to_numpy());n=max(3,len(ids)//5)
    validation=set(ids[:n]);train=set(ids[n:])
    # Validation site aliases are excluded; buffer validation independently too.
    valpos=stations[stations.location_id.isin(validation)]
    train={sid for sid in train if sid not in set(valpos.location_id) and stations.set_index('location_id').loc[sid,'physical_site_id'] not in set(valpos.physical_site_id)
        and np.all(distances_km(*stations.set_index('location_id').loc[sid,['latitude','longitude']],valpos[['latitude','longitude']])>=buffer_km)}
    return train,validation,test


def examples(frame,queries,context,limit,seed=42):
    rng=np.random.default_rng(seed);candidates=frame[frame.location_id.isin(queries)]
    if len(candidates)>limit:candidates=candidates.iloc[np.sort(rng.choice(len(candidates),limit,replace=False))]
    groups={t:g[g.location_id.isin(context)] for t,g in frame.groupby('timestamp_utc')}
    times=sorted(groups);prev={t:times[i-1] if i else None for i,t in enumerate(times)}
    rows=[];xs=[];ys=[];bases=[];pers=[];pair_distances=[]
    for query in candidates.itertuples(index=False):
        t=query.timestamp_utc;neighbors=groups[t];neighbors=neighbors[neighbors.physical_site_id!=query.physical_site_id]
        d=distances_km(query.latitude,query.longitude,neighbors[['latitude','longitude']])
        order=np.argsort(d)[:32];neighbors=neighbors.iloc[order];pair_distances.extend(d[order].tolist())
        nodes=neighbors.to_dict('records')
        x,b,c=named_features(nodes,query.latitude,query.longitude,t,query.elevation_m,query.slope_deg)
        previous=np.full(6,np.nan);pt=prev[t]
        if pt is not None and (t-pt)<=pd.Timedelta(hours=6):
            ng=groups[pt];ng=ng[ng.physical_site_id!=query.physical_site_id]
            nd=distances_km(query.latitude,query.longitude,ng[['latitude','longitude']]);ng=ng.iloc[np.argsort(nd)[:32]]
            _,previous,_=named_features(ng.to_dict('records'),query.latitude,query.longitude,pt,query.elevation_m,query.slope_deg)
        rows.append(dict(nodes=nodes,latitude=query.latitude,longitude=query.longitude,timestamp=t,query_elevation_m=query.elevation_m,query_slope_deg=query.slope_deg,
            location_id=query.location_id,climate_zone=query.climate_zone,elevation_band=('0–500' if query.elevation_m<500 else '500–1500' if query.elevation_m<1500 else '1500–3000' if query.elevation_m<3000 else '3000+')))
        xs.append(x);ys.append([getattr(query,c) for c in RAW_SENSOR_COLUMNS]);bases.append(b);pers.append(previous)
    return rows,np.asarray(xs).reshape(-1,33),np.asarray(ys).reshape(-1,6),np.asarray(bases).reshape(-1,6),np.asarray(pers).reshape(-1,6),pair_distances


def stats(truth,pred,station_ids,seed=42):
    valid=np.isfinite(truth)&np.isfinite(pred);error=np.abs(truth[valid]-pred[valid]);ids=np.asarray(station_ids)[valid]
    if not len(error):return dict(rows=0,mae=None,rmse=None,mae_station_bootstrap_95ci=None)
    unique=np.unique(ids);rng=np.random.default_rng(seed);samples=[]
    grouped={s:error[ids==s] for s in unique}
    if len(unique)>=2:
        for _ in range(200):samples.append(float(np.concatenate([grouped[s] for s in rng.choice(unique,len(unique),replace=True)]).mean()))
    return dict(rows=len(error),stations=len(unique),mae=float(error.mean()),rmse=float(np.sqrt((error**2).mean())),
        mae_station_bootstrap_95ci=np.quantile(samples,[.025,.975]).tolist() if samples else None)


def experiment(frame,stations,heldout,scope,buffer_km=20,min_train_stations=10,test_context=None):
    train,val,test=splits(stations,heldout,buffer_km=buffer_km)
    if len(train)<min_train_stations or len(val)<3 or len(test)<3:return {'scope':scope,'status':'INSUFFICIENT_DISJOINT_STATIONS','counts':dict(train=len(train),validation=len(val),test=len(test))}
    _,x,y,_,_,distances=examples(frame[frame.timestamp_utc.dt.month<=8],train,train,2500)
    _,vx,vy,_,_,_=examples(frame[frame.timestamp_utc.dt.month.isin([9,10])],val,train,600)
    query_context=train if test_context is None else set(test_context)
    if query_context & (test|val):raise ValueError('Held-out site in inference context')
    rows,tx,ty,idw,persistence,_=examples(frame[frame.timestamp_utc.dt.month>=11],test,query_context,1000)
    if not len(x) or not len(vx) or not rows:return {'scope':scope,'status':'EMPTY_TIME_PARTITION'}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore');model=SpatialEnsemble(extended_features=True).fit(x,y,vx,vy)
    predictions=[];bands=[];flags=[];nearest=np.full_like(idw,np.nan);mean=nearest.copy()
    for j,row in enumerate(rows):
        args={k:v for k,v in row.items() if k not in ['location_id','climate_zone','elevation_band']}
        result=model.predict(**args);targets=result['targets'];predictions.append([targets[c]['prediction'] if targets[c]['prediction'] is not None else np.nan for c in RAW_SENSOR_COLUMNS]);bands.append([targets[c]['absolute_error_p90'] if targets[c]['absolute_error_p90'] is not None else np.nan for c in RAW_SENSOR_COLUMNS])
        flags.append(guard(row['nodes'],row['latitude'],row['longitude'],row['timestamp'],20))
        for i,c in enumerate(RAW_SENSOR_COLUMNS):
            values=np.array([n.get(c,np.nan) for n in row['nodes']],dtype=float);good=np.isfinite(values)
            if good.any():nearest[j,i]=values[good][0];mean[j,i]=values[good].mean()
    predictions=np.asarray(predictions);bands=np.asarray(bands);ids=[r['location_id'] for r in rows]
    def report(indices):
        metrics={}
        for i,c in enumerate(RAW_SENSOR_COLUMNS):
            truth=ty[indices,i];methods={'ensemble':predictions[indices,i],'idw':idw[indices,i],'nearest_node':nearest[indices,i],'node_mean':mean[indices,i],'neighbor_idw_persistence_6h':persistence[indices,i]}
            paired=np.isfinite(truth)
            for values in methods.values():paired &= np.isfinite(values)
            selected_ids=np.array(ids)[indices];b=bands[indices,i];cal=np.isfinite(b)&np.isfinite(truth)&np.isfinite(methods['ensemble'])
            metrics[c]={'paired_methods':{k:stats(truth[paired],v[paired],selected_ids[paired]) for k,v in methods.items()},
                'each_method_available':{k:int((np.isfinite(truth)&np.isfinite(v)).sum()) for k,v in methods.items()},
                'truth_rows':int(np.isfinite(truth).sum()),'band_rows':int(cal.sum()),
                'band_coverage':float((np.abs(truth[cal]-methods['ensemble'][cal])<=b[cal]).mean()) if cal.any() else None,
                'mean_p90_absolute_error_band':float(b[cal].mean()) if cal.any() else None,
                'diagnostic_validation_p90':model.heads[c]['p90'] if c in model.heads else None,
                'diagnostic_band_coverage_all_test':float((np.abs(truth[paired]-methods['ensemble'][paired])<=model.heads[c]['p90']).mean()) if c in model.heads and paired.any() else None,
                'diagnostic_band_warning':'Offline validation residual band outside deployment domain is not a calibrated serving uncertainty'}
        return metrics
    edges=[0,1,5,20,50,100,250,500,1000,np.inf]
    return {'scope':scope,'status':'EVALUATED_EXPERIMENTAL','split':dict(training_stations=sorted(train),validation_stations=sorted(val),test_stations=sorted(test),spatial_buffer_km=buffer_km,query_context='training sites only; nearest 32 current nodes',inference_context_stations=sorted(query_context)),
        'examples':dict(train=len(x),validation=len(vx),test=len(rows)),'metrics':report(np.ones(len(rows),dtype=bool)),
        'per_station':{z:report(np.array([r['location_id']==z for r in rows])) for z in sorted(set(ids))} if 'comparison' in scope else {},
        'per_climate_zone':{z:report(np.array([r['climate_zone']==z for r in rows])) for z in sorted({r['climate_zone'] for r in rows})},
        'per_elevation_band':{z:report(np.array([r['elevation_band']==z for r in rows])) for z in sorted({r['elevation_band'] for r in rows})},
        'training_context_pair_distance_counts':np.histogram(distances,bins=edges)[0].tolist(),'distance_bins_km':['0–1','1–5','5–20','20–50','50–100','100–250','250–500','500–1000','1000+'],
        'mesh_20km_geometry_allowed_rows':sum(f['allowed'] for f in flags),'geometry_note':'Diagnostic large-distance experiment bypasses refusal; deployment guard defaults 20km. These are not claimed mesh-valid predictions.',
        'heads':{k:{'weights':v['weights'],'p90':v['p90'],'active_feature_indices':v['active'].tolist()} for k,v in model.heads.items()}}


def run(observations,station_path,output):
    stations=pd.read_csv(station_path);frame=pd.read_csv(observations);frame.timestamp_utc=pd.to_datetime(frame.timestamp_utc,utc=True)
    good=stations.terrain_status.eq('VERIFIED_ASSET_SAMPLED') & stations.climate_zone.notna() & stations.geography_status.ne('COUNTRY_LOCATION_CONFLICT')
    stations=stations[good & stations.location_id.isin(frame.location_id)].reset_index(drop=True)
    # Physical aliases never count as separate mesh nodes.
    stations=stations.drop_duplicates('physical_site_id');frame=frame.merge(stations,on='location_id',validate='many_to_one')
    rng=np.random.default_rng(42);held=rng.permutation(stations.location_id.to_numpy())[:max(3,len(stations)//5)]
    results=[]
    for scope,buffer in [('whole-station',20),('whole-station-5km-buffer',5)]:
        print('evaluating',scope,flush=True);results.append(experiment(frame,stations,held,scope,buffer_km=buffer))
    for zone in sorted(stations.climate_zone.unique()):
        ids=stations.loc[stations.climate_zone.eq(zone),'location_id']
        print('evaluating climate',zone,flush=True)
        results.append(experiment(frame,stations,ids,'leave-climate-zone-out:'+zone))
    mountain=stations[region(stations)]
    results.append(experiment(frame,stations,mountain.location_id,'Himalaya-geography-proxy-holdout'))
    # Identical Himalayan held-out stations for national versus local proxy training.
    if len(mountain)>=15:
        mandi=mountain[mountain.station_name.str.strip().str.upper().eq('MANDI')].location_id.tolist()
        target=list(dict.fromkeys(mandi+list(np.random.default_rng(42).permutation(mountain.location_id.to_numpy()))))[:max(3,len(mountain)//5)]
        common_context=splits(stations,target)[0]&splits(mountain,target)[0]
        results.append(experiment(frame,stations,target,'national-Mandi-comparison',test_context=common_context))
        results.append(experiment(frame[frame.location_id.isin(mountain.location_id)],mountain,target,'Himalaya-only-Mandi-comparison',min_train_stations=3,test_context=common_context))
    else:results.append({'scope':'Mandi-model-comparison','status':'INSUFFICIENT_HIMALAYAN_STATIONS','stations':len(mountain),'Mandi_truth_available':bool(stations.station_name.str.strip().str.upper().eq('MANDI').any())})
    report={'seed':42,'station_candidates':len(stations),'static_distances':distance_distribution(stations.reset_index(drop=True)),
        'experiments':results,'era5_status':'not obtained; no background feature trained','pm_status':'no PM labels; masked heads inactive',
        'Himalaya_definition':'predeclared proxy: 28–37 N,72–90 E,SRTM>=500m; not verified administrative/ecological boundary',
        'Mandi_claim':'NOAA Mandi station is an archive proxy; site position and own mesh-node truth remain unverified',
        'calibration_limitation':'validation examples split by deterministic station/time row order in half; no shared calibration rows; station-bootstrap CI; bands need independent network calibration',
        'sampling':'bounded deterministic sample, max 2500 train / 600 validation / 1000 test per experiment; one year only'}
    from ml.datasets.registry import digest
    report['input_sha256']={str(path):digest(path) for path in [observations,station_path]}
    Path(output).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--observations',default='data/india_training/weather_sample.csv');p.add_argument('--stations',default='data/registry/india_stations.csv');p.add_argument('--output',default='reports/nwic_pipeline/india_evaluation.json');a=p.parse_args();run(a.observations,a.stations,a.output)
