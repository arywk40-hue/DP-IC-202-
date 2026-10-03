"""Reproducible QC-approved India sample in the common long-form store.

Public raw station-year files remain intact. This first experiment selects
00/06/12/18 UTC on days 1/8/15/22 each month, exact minute zero. No random
selection of favorable weather; manifest describes all exclusions.
"""
import argparse,json
from pathlib import Path
import pandas as pd
from ml.datasets.registry import connect,digest
from ml.datasets.adapters import ingest_frame
from ml.datasets.noaa import VARIABLES,qc_good


def build(stations_path,raw_dir,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    stations=pd.read_csv(stations_path)
    staging=output/'sample.building.sqlite'
    staging.unlink(missing_ok=True)
    db=connect(staging)
    reports=[]
    for n,path in enumerate(sorted(Path(raw_dir).glob('*_2024.parquet')),1):
        frame=pd.read_parquet(path);times=pd.to_datetime(frame.DATE,utc=True,errors='coerce')
        selected=times.dt.day.isin([1,8,15,22]) & times.dt.hour.isin([0,6,12,18]) & times.dt.minute.eq(0)
        frame=frame.loc[selected].reset_index(drop=True);frame['location_id']=frame.STATION
        # Preserve original zero-based row number before deterministic sampling.
        frame['raw_record_index']=selected[selected].index.to_numpy()
        counts=ingest_frame(db,frame,path,'noaa_ghcnh',VARIABLES,stations,time_column='DATE',pressure_reference='station',qc={v:qc_good(frame,v) for v in VARIABLES})
        reports.append({'path':str(path),'sha256':digest(path),'selected_reports':len(frame),'status_counts':counts})
        if n%50==0:print('long schema stations',n,flush=True)
    approved=pd.read_sql_query('SELECT station_id,interval_end_utc,variable,value,source_id,raw_sha256,source_metadata_json FROM training_open',db)
    # Duplicate source reports at identical instant are averaged AFTER per-report QC.
    wide=approved.pivot_table(index=['station_id','interval_end_utc'],columns='variable',values='value',aggfunc='mean').reset_index().rename(columns={'station_id':'location_id','interval_end_utc':'timestamp_utc'})
    for name in ['pm25_ug_m3','pm10_ug_m3']:
        if name not in wide:wide[name]=float('nan')
    wide.to_csv(output/'weather_sample.csv',index=False)
    manifest={'sampling':'exact minute zero, UTC hours 0/6/12/18, month days 1/8/15/22, 2024',
        'registry_sha256':digest(stations_path),'source_registry_sha256':digest('data/registry/sources.json'),
        'source_reports':reports,'approved_long_rows':len(approved),'wide_rows':len(wide),
        'training_open_only':True,'pm_heads':'masked; no PM observations in NOAA core sample',
        'live_latency':'not verified; archive publication is retrospective','wide_sha256':digest(output/'weather_sample.csv')}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');db.close();staging.replace(output/'sample.sqlite')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stations',default='data/registry/india_stations.csv');p.add_argument('--raw',default='data/noaa_ghcnh/raw');p.add_argument('--output',default='data/india_training');a=p.parse_args();build(a.stations,a.raw,a.output)
