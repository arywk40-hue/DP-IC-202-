"""Vectorized all-hour neighbor features, no query labels among inputs.
Nearest 32 CURRENT available context sites; excluded physical-site aliases.
Data are processed in 96-hour chunks to bound temporary memory.
"""
from pathlib import Path
import json
import numpy as np,pandas as pd
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.spatial_ensemble.physics import interpolate,weighted
from ml.spatial_ensemble.episodes import episode_ids
from ml.spatial_ensemble.network import distances_km

WIDTH=47  # old 33 + physics 8 + per-channel neighbor counts 6


class HourlyNetwork:
    def __init__(self,frame,stations,qc):
        self.raw_station_count=frame.location_id.nunique()
        stations=stations[stations.location_id.isin(frame.location_id)].copy().sort_values('location_id')
        stations=stations[stations.geography_status.ne('COUNTRY_LOCATION_CONFLICT')]
        self.aliases=stations[stations.physical_site_id.duplicated()].location_id.tolist()
        # Same policy across all experiments; no test-score-based alias choice.
        self.stations=stations.drop_duplicates('physical_site_id').reset_index(drop=True)
        self.ids=self.stations.location_id.tolist();self.lookup={s:i for i,s in enumerate(self.ids)}
        qc=qc.set_index('location_id').reindex(self.ids);self.qc=qc.reset_index()
        self.elevation=self.stations.elevation_m.to_numpy(float);self.elevation=np.where(qc.elevation_ok.to_numpy(bool),self.elevation,np.nan)
        self.slope=self.stations.slope_deg.to_numpy(float)
        self.pressure_ok=qc.pressure_ok.to_numpy(bool)
        frame=frame[frame.location_id.isin(self.ids)].copy();frame.timestamp_utc=pd.to_datetime(frame.timestamp_utc,utc=True)
        self.times=pd.DatetimeIndex(frame.timestamp_utc.unique()).sort_values();time_lookup=pd.Series(np.arange(len(self.times)),index=self.times)
        self.readings=np.full((len(self.times),len(self.ids),6),np.nan,dtype=np.float32);self.dewpoints=np.full((len(self.times),len(self.ids)),np.nan,dtype=np.float32)
        ti=frame.timestamp_utc.map(time_lookup).to_numpy(int);si=frame.location_id.map(self.lookup).to_numpy(int)
        self.readings[ti,si]=frame[RAW_SENSOR_COLUMNS].to_numpy(np.float32);self.dewpoints[ti,si]=frame.dewpoint_c.to_numpy(np.float32)
        self.readings[:,~self.pressure_ok,2]=np.nan
        positions=self.stations[['latitude','longitude']].to_numpy(float)
        self.distance=np.array([distances_km(a,b,positions) for a,b in positions])
        self.episodes=episode_ids(self.times)
        self.episode_starts=pd.Timestamp('2024-01-01',tz='UTC')+pd.to_timedelta(self.episodes*72,unit='h')
        self.parts={}
        y=self.episode_starts.year;m=self.episode_starts.month
        self.parts['train2023']=(y==2023);self.parts['train2024']=(y==2024)&(m<=6)
        self.parts['select']=(y==2024)&(m>=7)&(m<=8);self.parts['calibrate']=(y==2024)&(m>=9)&(m<=10)
        self.parts['check']=(y==2024)&(m==11);self.parts['test']=(y==2024)&(m==12)

    def examples(self,queries,context,part,cache,limit=None):
        queries=np.array([self.lookup[s] for s in sorted(queries) if s in self.lookup]);context=np.array([self.lookup[s] for s in sorted(context) if s in self.lookup])
        if not len(context) or not len(queries):raise ValueError('No query/context sites')
        tm=np.where(part)[0];valid_query=np.isfinite(self.readings[tm][:,queries]).any(axis=2)
        total=int(valid_query.sum());n=min(total,limit) if limit is not None else total
        selected=None
        if limit is not None and total>limit:selected=set(np.random.default_rng(42).choice(total,n,replace=False).tolist())
        path=Path(cache);path.mkdir(parents=True,exist_ok=True)
        arrays={name:np.lib.format.open_memmap(path/(name+'.npy'),mode='w+',dtype=dtype,shape=(n,width)) for name,width,dtype in [('x',WIDTH,np.float32),('y',6,np.float32),('physics',6,np.float32),('idw',6,np.float32),('nearest',6,np.float32),('mean',6,np.float32),('persistence',6,np.float32),('distance',6,np.float32)]}
        ids=np.lib.format.open_memmap(path/'ids.npy',mode='w+',dtype=np.int32,shape=(n,3)) # station,time,episode
        offset=0;candidate_index=0;k=min(32,len(context));dist=self.distance[np.ix_(queries,context)].copy()
        # Physical aliases were removed; also exclude query site in training.
        dist[queries[:,None]==context[None,:]]=np.inf
        for start in range(0,len(tm),96):
            chunk=tm[start:start+96];a=self.readings[chunk][:,context];dp=self.dewpoints[chunk][:,context]
            available=np.isfinite(a).any(axis=2)|np.isfinite(dp)
            scores=np.where(available[:,None,:],dist[None,:,:],np.inf)
            order=np.argsort(scores,axis=2)[:,:,:k];d=np.take_along_axis(scores,order,axis=2)
            values=np.take_along_axis(np.broadcast_to(a[:,None,:,:],(len(chunk),len(queries),len(context),6)),order[:,:,:,None],axis=2)
            neighbor_ids=context[order];z=self.elevation[neighbor_ids];dew=np.take_along_axis(np.broadcast_to(dp[:,None,:],(len(chunk),len(queries),len(context))),order,axis=2)
            pressure_ok=self.pressure_ok[neighbor_ids]
            physics,idw,extra,pc=interpolate(values,z,d,self.elevation[queries][None,:],pressure_ok=pressure_ok,dewpoints=dew)
            count=np.sum(np.isfinite(values)&np.isfinite(d[:,:,:,None]),axis=2)
            nearest=np.stack([np.min(np.where(np.isfinite(values[...,i]),d,np.inf),axis=2) for i in range(6)],axis=2)
            nearest=np.where(np.isfinite(nearest),nearest,np.nan)
            # Pressure nearest uses the same physical plausibility gate as baseline.
            from ml.spatial_ensemble.physics import pressure_log_reference
            lp=pressure_log_reference(values[...,2],z,values[...,0],values[...,1]);pvalid=np.isfinite(lp)&pressure_ok&(lp>=np.log(870))&(lp<=np.log(1085))
            pn=np.min(np.where(pvalid,d,np.inf),axis=2);nearest[...,2]=np.where(np.isfinite(pn),pn,np.nan)
            sums=np.sum(np.where(np.isfinite(values)&np.isfinite(d[...,None]),values,0),axis=2)
            means=np.divide(sums,count,out=np.full_like(sums,np.nan),where=count>0)
            nearest_values=np.stack([np.take_along_axis(values[...,i],np.argmin(np.where(np.isfinite(values[...,i]),d,np.inf),axis=2)[:,:,None],axis=2)[...,0] for i in range(6)],axis=2)
            nearest_values=np.where(count>0,nearest_values,np.nan)
            spread=np.stack([np.sqrt(weighted((values[...,i]-idw[...,i,None])**2,d)) for i in range(6)],axis=2)
            lat=np.radians(self.stations.latitude.to_numpy()[queries]);lon=np.radians(self.stations.longitude.to_numpy()[queries]);geo=np.stack([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)],axis=1)
            hour=self.times[chunk].hour.to_numpy();day=self.times[chunk].dayofyear.to_numpy();cyclic=np.stack([np.sin(2*np.pi*hour/24),np.cos(2*np.pi*hour/24),np.sin(2*np.pi*day/365.25),np.cos(2*np.pi*day/365.25)],axis=1)
            node_z=weighted(z,d);qz=np.broadcast_to(self.elevation[queries][None,:],node_z.shape);slope=np.broadcast_to(self.slope[queries][None,:],node_z.shape)
            terrain=np.stack([qz,slope,node_z,qz-node_z],axis=2)
            background=np.full((*qz.shape,4),np.nan) # no ERA5 file obtained; explicit missing view
            x=np.concatenate([idw,spread,nearest,np.broadcast_to(geo[None,:,:],(*qz.shape,3)),np.broadcast_to(cyclic[:,None,:],(*qz.shape,4)),terrain,background,extra,count],axis=2)
            truth=self.readings[chunk][:,queries]
            previous=np.full_like(idw,np.nan)
            prior=chunk-1;good=(prior>=0)&((self.times[chunk]-self.times[np.maximum(prior,0)])==pd.Timedelta(hours=1))
            if good.any():
                old=self.readings[prior[good]][:,context];old_available=np.isfinite(old).any(axis=2)
                od=np.where(old_available[:,None,:],dist[None,:,:],np.inf);oi=np.argsort(od,axis=2)[:,:,:k];od=np.take_along_axis(od,oi,axis=2)
                ov=np.take_along_axis(np.broadcast_to(old[:,None,:,:],(len(old),len(queries),len(context),6)),oi[:,:,:,None],axis=2)
                previous[good]=np.stack([weighted(ov[...,i],od) for i in range(6)],axis=2)
            keep=np.isfinite(truth).any(axis=2);h,q=np.where(keep)
            if selected is not None:
                chosen=np.array([candidate_index+j in selected for j in range(len(h))]);h,q=h[chosen],q[chosen]
            candidate_index+=int(keep.sum());end=offset+len(h)
            for name,data in [('x',x),('y',truth),('physics',physics),('idw',idw),('nearest',nearest_values),('mean',means),('persistence',previous),('distance',nearest)]:arrays[name][offset:end]=data[h,q]
            ids[offset:end]=np.stack([queries[q],chunk[h],self.episodes[chunk[h]]],axis=1);offset=end
        if offset!=n:raise ValueError('Feature row accounting mismatch')
        for a in arrays.values():a.flush()
        ids.flush();return arrays,ids,{'rows':n,'candidate_rows':total,'caps':limit,'context_sites':len(context),'query_sites':len(queries)}

    def lagged_physics(self,ids,context,lag_hours=3):
        """Exact earlier completed hour, no held-out query history or fill."""
        context=np.array([self.lookup[s] for s in sorted(context)]);out=np.full((len(ids),6),np.nan)
        lookup={t:i for i,t in enumerate(self.times)}
        for time_index in np.unique(ids[:,1]):
            previous=lookup.get(self.times[time_index]-pd.Timedelta(hours=lag_hours))
            if previous is None:continue
            indices=np.where(ids[:,1]==time_index)[0];query=ids[indices,0]
            a=self.readings[previous,context];dp=self.dewpoints[previous,context]
            available=np.isfinite(a).any(axis=1)|np.isfinite(dp)
            d=self.distance[np.ix_(query,context)].copy();d[:,~available]=np.inf;d[query[:,None]==context[None,:]]=np.inf
            order=np.argsort(d,axis=1)[:,:min(32,len(context))];d=np.take_along_axis(d,order,axis=1);ni=context[order]
            out[indices]=interpolate(a[order],self.elevation[ni],d,self.elevation[query],pressure_ok=self.pressure_ok[ni],dewpoints=dp[order])[0]
        return out
