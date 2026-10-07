"""Paired continuous-weather diagnostics; no fitting or test-label calibration."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.operational.contracts import UNITS,utc


def metrics(truth,prediction,lower=None,upper=None,nominal=None):
    y,p=np.asarray(truth,float),np.asarray(prediction,float);good=np.isfinite(y)&np.isfinite(p);error=p[good]-y[good]
    result=dict(rows=int(good.sum()),mae=float(np.abs(error).mean()) if len(error) else None,rmse=float(np.sqrt((error**2).mean())) if len(error) else None,
                bias=float(error.mean()) if len(error) else None,correlation=float(np.corrcoef(y[good],p[good])[0,1]) if len(error)>2 and np.std(y[good])>0 and np.std(p[good])>0 else None)
    if lower is None or upper is None:result['intervals']={'rows':0,'status':'UNAVAILABLE'};return result
    lo,hi=np.asarray(lower,float),np.asarray(upper,float)
    valid=good&np.isfinite(lo)&np.isfinite(hi)
    if np.any(lo[valid]>hi[valid]) or nominal is None or not 0<nominal<1:raise ValueError('Valid interval and explicit nominal level required')
    alpha=1-nominal;width=hi[valid]-lo[valid];truth=y[valid]
    score=width+2/alpha*(lo[valid]-truth)*(truth<lo[valid])+2/alpha*(truth-hi[valid])*(truth>hi[valid])
    coverage=float(((lo[valid]<=truth)&(truth<=hi[valid])).mean()) if valid.any() else None
    result['intervals']={'rows':int(valid.sum()),'nominal':nominal,'empirical_coverage':coverage,'mean_width':float(width.mean()) if len(width) else None,
                         'interval_score':float(score.mean()) if len(score) else None,'status':'POORLY_CALIBRATED' if coverage is not None and coverage<nominal else 'ARCHIVE_DIAGNOSTIC_NOT_FIELD_RELEASED'}
    return result


def paired(s,sb,metadata,seed=42):
    s,sb=s.copy(),sb.copy()
    keys=['physical_site_id','valid_time_utc','channel','split']
    required=set(keys)|{'truth','prediction','unit','country','elevation_m','wind_speed_mps'}
    if not required<=set(s) or not required<=set(sb):raise ValueError('Paired diagnostic schema incomplete')
    if not metadata.get('dataset_sha256') or not metadata.get('split_manifest_sha256') or metadata.get('forecast_horizon_seconds') is None:
        raise ValueError('Frozen dataset/split/horizon provenance required')
    for frame in [s,sb]:
        if not frame.country.eq('IN').all():raise ValueError('China/non-India excluded')
        if frame.duplicated(keys).any():raise ValueError('Duplicate paired keys')
        for channel,rows in frame.groupby('channel'):
            if channel not in UNITS or not rows.unit.eq(UNITS[channel]).all():raise ValueError('Canonical channel/units required')
        frame.loc[:,'valid_time_utc']=[utc(t).isoformat() for t in frame.valid_time_utc]
    a,b=s.sort_values(keys).reset_index(drop=True),sb.sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(a[keys],b[keys])
    for column in ['truth','unit','country','elevation_m','wind_speed_mps']:pd.testing.assert_series_equal(a[column],b[column])
    common=np.isfinite(a.prediction)&np.isfinite(b.prediction)&np.isfinite(a.truth)&a.split.eq('test')
    result={'metadata':metadata,'paired_rows':int(common.sum()),'total_rows':len(a),'unavailable_S':int(a.prediction.isna().sum()),'unavailable_SB':int(b.prediction.isna().sum()),'channels':{},'evaluation_scope':'test_only_on_exact_paired_keys','independent_event_metrics_status':'NO_ADMITTED_EVENT_WINDOWS','disaster_outputs':'DISABLED'}
    for channel,indices in a.groupby('channel').groups.items():
        indices=np.asarray(list(indices));ix=indices[common.iloc[indices]];truth=a.iloc[ix].truth.to_numpy();p=a.iloc[ix].prediction.to_numpy();q=b.iloc[ix].prediction.to_numpy()
        def report(frame,selection):
            f=frame.iloc[selection]
            return metrics(f.truth,f.prediction,f.lower if 'lower' in f else None,f.upper if 'upper' in f else None,metadata.get('nominal_interval_level'))
        out={'S':report(a,ix),'SB':report(b,ix),'by_elevation_band':{},'by_wind_bin':{}}
        bands=pd.cut(a.iloc[ix].elevation_m,[-500,500,1500,3000,9000],labels=['below500','500to1500','1500to3000','3000plus'])
        wind=pd.cut(a.iloc[ix].wind_speed_mps,[-.001,1.5,5,10,100],labels=['calm','moderate','strong','high_measured_mean'])
        for group,name in [(bands,'by_elevation_band'),(wind,'by_wind_bin')]:
            for category in group.cat.categories:
                selected=ix[np.asarray(group==category)];out[name][str(category)]={'S':report(a,selected),'SB':report(b,selected)}
        sites=a.iloc[ix].physical_site_id.to_numpy();unique=np.unique(sites)
        if len(unique)>=2:
            totals=np.array([((np.abs(q[sites==site]-truth[sites==site])-np.abs(p[sites==site]-truth[sites==site])).sum(),int((sites==site).sum())) for site in unique])
            sums=totals[np.random.default_rng(seed).integers(0,len(unique),size=(200,len(unique)))].sum(axis=1)
            out['paired_MAE_delta_SB_minus_S_95ci']=np.quantile(sums[:,0]/sums[:,1],[.025,.975]).tolist()
        else:out['paired_MAE_delta_SB_minus_S_95ci']=None
        result['channels'][channel]=out
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sensor-only',required=True);p.add_argument('--sensor-background',required=True);p.add_argument('--metadata',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    result=paired(pd.read_csv(a.sensor_only),pd.read_csv(a.sensor_background),json.loads(Path(a.metadata).read_text()))
    Path(a.output).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
