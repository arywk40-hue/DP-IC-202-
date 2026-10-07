"""GPS grids through existing guarded spatial inference; no hazard interpretation."""
import hashlib
from pathlib import Path

import numpy as np

from ml.operational.contracts import RAW_SENSOR_COLUMNS, CORE, observation, prediction, utc
from ml.spatial_ensemble.physics_serving import predict_snapshot
from ml.spatial_ensemble.residual_artifact import load
from ml.spatial_ensemble.corridor import DEFAULT_LIMITS
from ml.spatial_ensemble.network import guard


def fixture(count=2,terrain=None):
    time='2026-10-06T00:00:00Z';points=[('A',31.7,76.9),('B',31.7,76.98),('D',31.74,76.94)]
    rows=[]
    for i,(identity,lat,lon) in enumerate(points[:count]):
        sampled,proof=terrain.sample(lat,lon) if terrain else (None,{})
        z=sampled if sampled is not None else [600.,1000.,850.][i]
        temp=20.-.0065*z;pressure=1013.25*np.exp(-9.80665*z/(287.05*(temp+273.15+.00325*z)))
        values=[temp,65.+i*2,pressure,12.+i*3,25.+i*4,2.+i*.5]
        for channel,value in zip(RAW_SENSOR_COLUMNS,values):
            rows.append(dict(node_id=identity,timestamp_utc=time,latitude=lat,longitude=lon,elevation_m=z,elevation_datum='EGM96',
                             channel=channel,value=float(value),unit={'temperature_c':'degC','relative_humidity_pct':'%','pressure_hpa':'hPa','pm25_ug_m3':'ug/m3','pm10_ug_m3':'ug/m3','wind_speed_mps':'m/s'}[channel],
                             quality_flag='valid',source='SYNTHETIC_FIXTURE_REAL_CACHED_TERRAIN' if proof else 'SYNTHETIC_FIXTURE',sensor_model='SYNTHETIC_NOT_HARDWARE',
                             pressure_reference='station',sample_interval_seconds=3600))
    return dict(schema_version='indra_weather_records_v1',mode='fixture',roles={r['node_id']:'transmitter' for r in rows},reference_time_utc=time,observations=rows)


def build(payload,terrain=None,model_path=None,grid_shape=(17,25),max_age_seconds=300,verified_ingestion=False):
    if payload.get('mode') not in ['fixture','recorded','live_verified']:raise ValueError('Explicit demo/source mode required')
    if payload['mode']=='live_verified' and not verified_ingestion:raise ValueError('Live mode requires server-verified ingestion, not JSON auth claims')
    if len(grid_shape)!=2 or any(type(v) is not int or not 2<=v<=100 for v in grid_shape) or np.prod(grid_shape)>2500:raise ValueError('Grid budget exceeded')
    reference=utc(payload['reference_time_utc']);records=[]
    roles=payload.get('roles',{})
    if payload['mode']!='fixture' and not roles:raise ValueError('Explicit transmitter/hidden-test role registry required')
    if any(role not in ['transmitter','hidden_test'] for role in roles.values()):raise ValueError('Unknown node role')
    hidden={node for node,role in roles.items() if role=='hidden_test'}
    if not isinstance(payload['observations'],list) or len(payload['observations'])>4096:raise ValueError('Bounded observation list required')
    for raw in payload['observations']:
        if raw.get('node_id') in hidden:continue
        source=raw.get('source','').lower().removeprefix('completed_window:')
        if source.startswith(('nwic','india_cpcb','uci_beijing','delhi_opencity')):raise ValueError('Quarantined/restricted/China sources cannot enter the operational map export')
        if payload['mode']=='fixture' and not raw.get('source','').startswith('SYNTHETIC'):raise ValueError('Fixture mode accepts explicit synthetic readings only')
        if roles and raw.get('node_id') not in roles:raise ValueError('Node missing from role registry')
        records.append(observation(raw,authenticated=verified_ingestion and raw.get('authenticated') is True))
    duplicate={(r['node_id'],r['timestamp_utc'],r['channel']) for r in records}
    if len(duplicate)!=len(records):raise ValueError('Duplicate node/channel/time')
    registry={s['node_id']:s for s in payload.get('sites',[]) if s['node_id'] not in hidden}
    by_node={identity:[] for identity in registry}
    for r in records:by_node.setdefault(r['node_id'],[]).append(r)
    if not 2<=len(by_node)<=5:raise ValueError('Two to five nodes required')
    model=bands=None;model_status='physics_baseline_only';version='physics_elevation_v1'
    if model_path:
        try:
            model,bands=load(model_path)
            if model.neighbor_count!=len(by_node):raise ValueError('Model neighbor count differs from map')
            version='spatial_residual_json_v1:'+hashlib.sha256(Path(model_path).read_bytes()).hexdigest()[:16]
            model_status='loaded_with_per_cell_OOD_and_fallback'
        except (OSError,ValueError,KeyError,TypeError):model=bands=None;model_status='model_unavailable_physics_fallback'
    nodes=[];rendered=[]
    for identity,rows in sorted(by_node.items()):
        positions={(r['latitude'],r['longitude'],r['elevation_m']) for r in rows}
        if rows and len(positions)!=1:raise ValueError('One fixed position/elevation per node snapshot')
        latest={}
        for r in sorted(rows,key=lambda r:r['timestamp_utc']):latest[r['channel']]=r
        anchor=rows[0] if rows else registry[identity];node=dict(node_id=identity,latitude=anchor['latitude'],longitude=anchor['longitude'],elevation_m=anchor['elevation_m'],timestamp_utc=reference.isoformat(),
                               elevation_ok=anchor['elevation_m'] is not None,pressure_ok=True,interval_seconds=anchor.get('sample_interval_seconds',3600))
        channel_states={}
        for c in RAW_SENSOR_COLUMNS:
            r=latest.get(c);age=None if r is None else (reference-utc(r['timestamp_utc'])).total_seconds()
            value=None if r is None else r['value'];state='missing' if value is None else 'healthy'
            if r and r['quality_flag'].startswith(('rejected','provider_')):state='rejected'
            elif age is not None and age<0:state='rejected_future_time'
            elif age is not None and age>max_age_seconds:state='stale'
            elif r and not r['authenticated']:state='fixture' if payload['mode']=='fixture' else 'unauthenticated'
            aligned=r is not None and utc(r['timestamp_utc'])==reference
            usable=value is not None and aligned and age is not None and 0<=age<=max_age_seconds and (r['authenticated'] or payload['mode']=='fixture')
            node[c]=value if usable else None
            channel_states[c]=dict(value=value,unit=None if r is None else r['unit'],status=state,age_seconds=age,
                                   timestamp_utc=None if r is None else r['timestamp_utc'],authenticated=False if r is None else r['authenticated'],
                                   aligned_for_snapshot=aligned,quality_flag='missing' if r is None else r['quality_flag'],source='none' if r is None else r['source'],raw_value=None if r is None else r['raw_value'])
        health='healthy' if all(channel_states[c]['status']=='healthy' and channel_states[c]['aligned_for_snapshot'] for c in CORE) else 'degraded'
        rendered.append(dict(node_id=identity,latitude=node['latitude'],longitude=node['longitude'],elevation_m=node['elevation_m'],health=health,channels=channel_states))
        nodes.append(node)
    lat=np.array([n['latitude'] for n in nodes]);lon=np.array([n['longitude'] for n in nodes])
    if np.ptp(lat)>1 or np.ptp(lon)>1:raise ValueError('Local demo extent budget exceeded; not an India-wide rendering projection')
    lat_margin=max(np.ptp(lat)*.12,.006);lon_margin=max(np.ptp(lon)*.12,.003)
    north,south=min(90.,lat.max()+lat_margin),max(-90.,lat.min()-lat_margin);west,east=max(-180.,lon.min()-lon_margin),min(180.,lon.max()+lon_margin)
    warnings=set()
    if model is not None and (any(n['interval_seconds']!=3600 for n in nodes) or reference.minute or reference.second or reference.microsecond):
        model=bands=None;model_status='archive_model_aggregation_mismatch_physics_fallback';version='physics_elevation_v1'
        warnings.add('hourly_archive_model_requires_verified_completed_hour_means')
    cells=[];compatible=None if model is None else model.neighbor_count==len(nodes)
    for j,y in enumerate(np.linspace(north,south,grid_shape[0])):
        for i,x in enumerate(np.linspace(west,east,grid_shape[1])):
            z,terrain_proof=terrain.sample(float(y),float(x)) if terrain else (None,{'status':'terrain_unavailable','source':'none'})
            if z is None:warnings.add('query_elevation_unavailable')
            result=predict_snapshot(nodes,float(y),float(x),reference.isoformat(),query_elevation_m=z,model=model,bands=bands,
                                    max_distance_km=20,corridor_limits=DEFAULT_LIMITS)
            features=[{'node_id':n['node_id'],'timestamp_utc':n['timestamp_utc'] if any(n.get(c) is not None for c in RAW_SENSOR_COLUMNS) else None,'source':('static_site_registry_only' if not any(n.get(c) is not None for c in RAW_SENSOR_COLUMNS) else 'synthetic' if payload['mode']=='fixture' else 'verified_ingestion' if verified_ingestion else 'unverified_replay')} for n in nodes]
            records_for_cell={}
            supported=False
            for c,target in result['targets'].items():
                band=target['bands'].get('0.9');status=target['status']
                if target['prediction'] is not None:supported=True
                rec=prediction(f'{j}:{i}',c,reference.isoformat(),target['prediction'],version,features,status,band,'checked_archive_90_not_field_validated' if band else None)
                rec.update(contributing_nodes=target['contributing_nodes'],elevation_adjustment_available=target['elevation_adjustment_available'],residual_fallback=target['residual_fallback'])
                records_for_cell[c]=rec
            if len(nodes)==2:
                from ml.spatial_ensemble.corridor import corridor
                geometrically_supported=corridor([lat[0],lon[0]],[lat[1],lon[1]],[float(y),float(x)])['allowed']
            else:geometrically_supported=guard(nodes,float(y),float(x),reference.isoformat(),20)['allowed']
            cells.append(dict(grid_id=f'{j}:{i}',row=j,col=i,latitude=float(y),longitude=float(x),elevation_m=z,terrain=terrain_proof,
                              geometry_supported=bool(geometrically_supported),prediction_available=supported,channels=records_for_cell))
    return dict(schema_version='indra_weather_map_v1',mode=payload['mode'],reference_time_utc=reference.isoformat(),
                generated_at_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                hidden_test_nodes_excluded=sorted(hidden),grid_shape=list(grid_shape),bounds=dict(north=float(north),south=float(south),west=float(west),east=float(east)),nodes=rendered,cells=cells,
                model_version=version,model_status=model_status,neighbor_count_compatible=compatible,corridor_limits=DEFAULT_LIMITS,
                warnings=sorted(warnings),disaster_outputs='DISABLED',source_accuracy='NOT_FIELD_VALIDATED',authentication_semantics='server-derived only; fixture and replay JSON cannot authenticate a node',
                uncertainty_note='Only already-checked archive bands may be displayed; absent bands stay null; no field coverage claim')
