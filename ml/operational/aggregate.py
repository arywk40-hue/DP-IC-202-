"""Causal completed windows from actual native samples; no forward fill/upsampling."""
import pandas as pd
import hashlib
from ml.operational.contracts import canonical_bytes

from ml.operational.contracts import utc,UNITS,RAW_SENSOR_COLUMNS


def completed_windows(records,window_seconds=3600,as_of=None):
    if not records or type(window_seconds) is not int or window_seconds<=0:raise ValueError('Nonempty native records and window required')
    cutoff=utc(as_of) if as_of else max(utc(r['available_at_utc']) for r in records)
    by_node={}
    for r in records:by_node.setdefault(r['node_id'],[]).append(r)
    result=[]
    for node,rows in by_node.items():
        cadences={r['sample_interval_seconds'] for r in rows}
        positions={(r['latitude'],r['longitude'],r['elevation_m']) for r in rows}
        if len(cadences)!=1 or len(positions)!=1:raise ValueError('One fixed surveyed site and native cadence required')
        cadence=next(iter(cadences))
        if cadence>window_seconds or window_seconds%cadence:raise ValueError('Cannot manufacture finer-resolution data')
        seen=set();groups={}
        for r in rows:
            t=utc(r['timestamp_utc']);key=(t,r['channel'])
            if key in seen:raise ValueError('Duplicate native sample')
            seen.add(key)
            if t.value%(cadence*1_000_000_000):raise ValueError('Native samples off exact UTC grid')
            # Raw instantaneous native samples belong to [start,end); sample at H starts next window.
            end=t.floor(pd.Timedelta(seconds=window_seconds))+pd.Timedelta(seconds=window_seconds)
            if end>cutoff or utc(r['available_at_utc'])>end:continue
            groups.setdefault(end,[]).append(r)
        for end,samples in sorted(groups.items()):
            for channel in RAW_SENSOR_COLUMNS:
                selected=[r for r in samples if r['channel']==channel and r['value'] is not None and r['quality_flag']=='valid']
                expected=window_seconds//cadence;complete=len(selected)==expected
                anchor=samples[0]
                result.append({**anchor,'node_id':node,'channel':channel,'timestamp_utc':end.isoformat(),'available_at_utc':end.isoformat(),
                               'value':sum(r['value'] for r in selected)/expected if complete else None,'raw_value':None,'raw_unit':UNITS[channel],
                               'quality_flag':'valid' if complete else 'missing_incomplete_window','authenticated':complete and all(r['authenticated'] for r in selected),
                               'source':'completed_window:'+anchor['source'],'sample_interval_seconds':window_seconds,
                               'aggregation':{'method':'complete_native_arithmetic_mean','native_samples':len(selected),'expected_samples':expected,
                                              'raw_sample_sha256':hashlib.sha256(canonical_bytes(selected)).hexdigest(),'publication_assumption':'window end with all native values available by end; actual transport latency tracked separately'}})
    return result
