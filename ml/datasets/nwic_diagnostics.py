import json,hashlib,sys
from pathlib import Path
import numpy as np,pandas as pd
from ml.datasets.terrain import sample
from ml.datasets.registry import digest
root=Path('himachal 4-sensor dataset');out=Path('reports/nwic_pipeline')
powerpath=out/'source_evidence/power_mandi_202401.json';p=json.loads(powerpath.read_text());bg=p['properties']['parameter'];pt=pd.to_datetime(list(bg['T2M']),format='%Y%m%d%H',utc=True);power=pd.Series(list(bg['T2M'].values()),index=pt)
tfile=root/'6b64941e-8646-4020-b7e8-a8024d86fae2.csv';t=pd.read_csv(tfile);stamp=pd.to_datetime(t['Data Acquisition Time'],format='%d-%m-%Y %H:%M',errors='coerce');name=t['Station'];distance=(t.Latitude-31.708)**2+(t.Longitude-76.932)**2;site=t.loc[distance.idxmin(),'Station'];mask=name.eq(site)&stamp.between('2024-01-01','2024-01-31 23:59');ts=pd.Series(pd.to_numeric(t.loc[mask,'Air Temperature Telemetry Hourly (AoC)'],errors='coerce').to_numpy(),index=stamp[mask]);ts=ts[(ts>=-60)&(ts<=60)].groupby(level=0).mean();cycle=ts.groupby(ts.index.hour).mean();scores={}
for zone in ['UTC','Asia/Kolkata']:
 idx=ts.index.tz_localize(zone).tz_convert('UTC');sourcecycle=pd.Series(ts.to_numpy(),index=idx).groupby(idx.hour).mean();powercycle=power.groupby(power.index.hour).mean();joint=pd.concat([sourcecycle,powercycle],axis=1).dropna();scores[zone]={'daily_cycle_correlation':float(joint.iloc[:,0].corr(joint.iloc[:,1])) if len(joint)>=12 else None,'hours':len(joint),'source_utc_peak_hour':int(sourcecycle.idxmax()) if len(sourcecycle) else None}
pressure=pd.read_csv(root/'bbb7d941-de74-438c-a19a-bfe9e42a5fad.csv');pv='Telemetry_Hourly_Atmospheric Pressure (mb)';by=[]
for (name,lat,lon),g in pressure.groupby(['Station','Latitude','Longitude']):
 values=pd.to_numeric(g[pv],errors='coerce');z=sample(lat,lon,cache='data/terrain_diagnostics',climate=False)
 # Standard-atmosphere diagnostic only, never a proof of pressure reference.
 standard=1013.25*(1-2.25577e-5*z['elevation_m'])**5.25588
 by.append({'station':name,'latitude':lat,'longitude':lon,'srtm_elevation_m':z['elevation_m'],'srtm_asset_sha256':z['elevation_asset_sha256'],'rows':len(g),'exact_925_rows':int(values.eq(925).sum()),'pressure_median_hpa':float(values.median()),'standard_atmosphere_hpa':float(standard)})
w=pd.read_csv(root/'22ef7020-904b-4ef8-a975-d6baa5701988.csv');wt=pd.to_datetime(w['Data Acquisition Time'],format='%d-%m-%Y %H:%M',errors='coerce');old=w[wt.dt.year.eq(2007)]
report={'temperature_comparison':{'station':site,'sample_rows':len(ts),'period':'January 2024','power_uri':'https://power.larc.nasa.gov/api/temporal/hourly/point?parameters=T2M,RH2M,PS,WS10M&community=AG&longitude=76.932&latitude=31.708&start=20240101&end=20240131&format=JSON&time-standard=UTC','power_sha256':digest(powerpath),'timezone_hypotheses':scores,'decision':'UNRESOLVED: coarse background/one month cannot establish provider clock semantics'},'pressure_stations':by,'power_mandi_surface_pressure_median_hpa':float(np.median(list(bg['PS'].values())))*10,'pressure_decision':'UNRESOLVED: POWER grid-surface pressure is not station pressure; ERA5 unavailable; plateau remains suspect', 'wind_2007_rows':old.to_dict('records'),'wind_period_evidence':'NWIC resource officially spans 1970–2025; no provider correction record obtained','wind_decision':'UNRESOLVED: no overlapping 2007 T/RH/pressure evidence; quarantine','era5_comparison_status':'not performed: CDS download unavailable'}
(out/'nwic_diagnostics.json').write_text(json.dumps(report,indent=2,default=str,allow_nan=False)+'\n')
print('NWIC diagnostics written',scores,flush=True)
