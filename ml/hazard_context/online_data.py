"""Explicit ERA5 research inputs and delayed binary labels; no sensor substitution."""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path

import numpy as np
import pandas as pd

from ml.six_sensor_forecast.data import sha256

FEATURES = ["cape_j_kg", "cin_j_kg", "tcwv_kg_m2", "temperature_c", "dewpoint_depression_k",
            "surface_pressure_hpa", "u10_mps", "v10_mps", "gust_mps", "boundary_layer_height_m"]
VARIABLES = {
    "cape": (["cape", "convective_available_potential_energy"], {"J kg**-1", "J kg-1", "J/kg"}),
    "cin": (["cin", "convective_inhibition"], {"J kg**-1", "J kg-1", "J/kg"}),
    "tcwv": (["tcwv", "total_column_water_vapour"], {"kg m**-2", "kg m-2", "kg/m2"}),
    "t2m": (["t2m", "2m_temperature"], {"K"}),
    "d2m": (["d2m", "2m_dewpoint_temperature"], {"K"}),
    "sp": (["sp", "surface_pressure"], {"Pa"}),
    "u10": (["u10", "10m_u_component_of_wind"], {"m s**-1", "m s-1", "m/s"}),
    "v10": (["v10", "10m_v_component_of_wind"], {"m s**-1", "m s-1", "m/s"}),
    "gust": (["fg10", "i10fg", "10fg", "10m_wind_gust_since_previous_post_processing", "instantaneous_10m_wind_gust"], {"m s**-1", "m s-1", "m/s"}),
    "blh": (["blh", "boundary_layer_height"], {"m"}),
}
MAX_ROWS = 200_000


def utc(value):
    """Require an explicitly timezone-aware clock in CSV/user input."""
    result = pd.Timestamp(value)
    if pd.isna(result) or result.tzinfo is None:
        raise ValueError("Timezone-aware UTC timestamps required")
    return result.tz_convert("UTC")


def key(time, lat, lon):
    """Use exact timestamp/location identity; never approximate label times."""
    return f"{utc(time).isoformat()}|{float(lat):.8f}|{float(lon):.8f}"


def read_labels(path, *, target, label_role, assumed_delay_hours=None):
    """Keep unknowns unknown and preserve actual/explicitly assumed availability."""
    path = Path(path)
    if path.stat().st_size > 64*1024*1024:
        raise ValueError("Label CSV exceeds 64 MiB")
    frame = pd.read_csv(path)
    if not {"time", "lat", "lon", "label"} <= set(frame) or not 1 <= len(frame) <= MAX_ROWS:
        raise ValueError("Bounded label CSV requires time, lat, lon, label")
    if target not in {"cloudburst", "snowstorm"} or label_role not in {"satellite_proxy", "observed_event_unverified", "synthetic_test"}:
        raise ValueError("Explicit target/evidence role required")
    if target == "snowstorm" and label_role == "satellite_proxy":
        raise ValueError("Rain-rate proxies are not snowstorm labels")
    if "target" in frame and not frame.target.eq(target).all():
        raise ValueError("Separate label streams/models required for each target")
    frame["time"] = [utc(v) for v in frame.time]
    if not frame.time.eq(frame.time.dt.floor("h")).all():
        raise ValueError("Exact hourly label times required")
    frame["label"] = pd.to_numeric(frame.label, errors="raise")
    if not frame.label.dropna().isin([0,1]).all():
        raise ValueError("Labels must be binary or unknown; missing is never zero")
    for col, limit in (("lat",90),("lon",180)):
        frame[col] = pd.to_numeric(frame[col],errors="raise")
        if not np.isfinite(frame[col]).all() or not frame[col].between(-limit,limit).all():
            raise ValueError("Finite WGS84 label coordinates required")
    if "available_at" in frame:
        frame["available_at"] = pd.to_datetime([utc(v) if not pd.isna(v) else pd.NaT for v in frame.available_at],utc=True)
        if frame.loc[frame.label.isin([0,1]),"available_at"].isna().any():
            raise ValueError("Known labels require their availability timestamp")
        availability = "CSV_DECLARED_AVAILABILITY_NOT_EXTERNALLY_VERIFIED"
    else:
        if assumed_delay_hours is None or not np.isfinite(assumed_delay_hours) or not 1 <= assumed_delay_hours <= 24*366:
            raise ValueError("Supply available_at or an explicit label delay of at least one hour")
        frame["available_at"] = frame.time+pd.Timedelta(hours=assumed_delay_hours)
        availability = "ASSUMED_DELAY_NOT_VERIFIED_PUBLICATION_TIME"
    if (frame.available_at < frame.time+pd.Timedelta(hours=1)).any():
        raise ValueError("An hourly outcome cannot be known before its hour ends")
    frame["key"] = [key(*r) for r in frame[["time","lat","lon"]].itertuples(index=False,name=None)]
    if frame.key.duplicated().any():
        raise ValueError("Duplicate/conflicting label identities")
    return frame.sort_values(["time","lat","lon"]).reset_index(drop=True), dict(
        sha256=sha256(path), label_role=label_role, availability=availability, target=target,
        positives=int(frame.label.eq(1).sum()), negatives=int(frame.label.eq(0).sum()), unknowns=int(frame.label.isna().sum()),
        independent_observed_admission=False, monitored_negatives_verified=False)


def load_era5(paths, sites, *, feature_delay_hours, max_distance_km=25):
    """Read bounded selected cells, strict units and explicit assumed availability.

    Monthly complete files or disjoint variable files on exact coordinates are
    supported; overlapping time/cell exports and ambiguous ensemble dimensions
    are rejected. This is retrospective context, not as-issued live ERA5.
    """
    import xarray as xr

    paths = [Path(p) for p in paths]
    if not paths or not np.isfinite(feature_delay_hours) or not 0 <= feature_delay_hours <= 24*366:
        raise ValueError("NetCDF files and an explicit bounded feature delay required")
    if not 0 < max_distance_km <= 100 or not 1 <= len(sites) <= 200:
        raise ValueError("Bounded cell matching/site count required")
    receipts, frames = [], []
    with ExitStack() as stack:
        datasets=[]
        for path in paths:
            ds=stack.enter_context(xr.open_dataset(path,decode_times=True,mask_and_scale=True))
            rename={}
            for canonical,aliases in {"time":["time","valid_time"],"lat":["lat","latitude"],"lon":["lon","longitude"]}.items():
                found=[v for v in aliases if v in ds.dims]
                if len(found)!=1:
                    raise ValueError("Unambiguous rectilinear ERA5 dimensions required")
                if found[0]!=canonical:
                    rename[found[0]]=canonical
            ds=ds.rename(rename)
            for dim in list(ds.dims):
                if dim not in {"time","lat","lon"}:
                    if ds.sizes[dim]!=1:
                        raise ValueError("Select an explicit ensemble/version before import")
                    ds=ds.isel({dim:0},drop=True)
            t=pd.DatetimeIndex(ds.time.values)
            if (t.hasnans or t.tz is not None or not t.is_unique or not (t==t.floor("h")).all()
                    or any(not pd.Index(ds[c].values).is_unique for c in ("lat","lon"))):
                raise ValueError("Unique CF-decoded exact hourly UTC/grid coordinates required")
            ds=ds.assign_coords(lon=((ds.lon+180)%360)-180).sortby("time").sortby("lat").sortby("lon")
            names={}
            for name,(aliases,units) in VARIABLES.items():
                found=[a for a in aliases if a in ds.data_vars]
                if len(found)>1:
                    raise ValueError("Ambiguous ERA5 variable: "+name)
                if found:
                    a=found[0]
                    if ds[a].attrs.get("units") not in units or set(ds[a].dims)!={"time","lat","lon"}:
                        raise ValueError("Unverified ERA5 units/dimensions: "+a)
                    names[a]=name
            ds=ds[list(names)].rename(names)
            datasets.append(ds)
            receipts.append(dict(path=str(path),sha256=sha256(path)))
        if any(set(ds.data_vars)!=set(VARIABLES) for ds in datasets):
            owned=[n for ds in datasets for n in ds.data_vars]
            if len(owned)!=len(set(owned)):
                raise ValueError("Partial variables must have disjoint names and identical coordinates")
            datasets=[xr.merge(datasets,join="exact",compat="no_conflicts")]
        if any(set(ds.data_vars)!=set(VARIABLES) for ds in datasets):
            raise ValueError("Missing required ERA5 variables; nothing is synthesized")
        for ds in datasets:
            if len(ds.time)*len(sites)+sum(len(f) for f in frames)>MAX_ROWS:
                raise ValueError("Selected ERA5 row budget exceeded")
            for lat,lon in sites:
                tile=ds.sel(lat=lat,lon=lon,method="nearest")
                actual_lat,actual_lon=float(tile.lat),float(tile.lon)
                if not np.isfinite([actual_lat,actual_lon]).all() or not -90<=actual_lat<=90:
                    raise ValueError("Invalid ERA5 grid coordinates")
                dlat,dlon=np.radians([actual_lat-lat,actual_lon-lon])
                a=np.sin(dlat/2)**2+np.cos(np.radians(lat))*np.cos(np.radians(actual_lat))*np.sin(dlon/2)**2
                distance=6371.*2*np.arcsin(np.sqrt(np.clip(a,0,1)))
                if distance>max_distance_km:
                    raise ValueError("Label location is outside permitted ERA5 cell matching distance")
                values={name:np.asarray(tile[name].values,dtype=float) for name in VARIABLES}
                frame=pd.DataFrame(dict(zip(FEATURES,[values["cape"],values["cin"],values["tcwv"],values["t2m"]-273.15,
                    values["t2m"]-values["d2m"],values["sp"]/100,values["u10"],values["v10"],values["gust"],values["blh"]])))
                frame["time"]=pd.to_datetime(ds.time.values,utc=True)
                frame["lat"],frame["lon"]=lat,lon
                frame["era5_lat"],frame["era5_lon"]=actual_lat,actual_lon
                frame["matching_distance_km"]=distance
                frame["feature_available_at"]=frame.time+pd.Timedelta(hours=feature_delay_hours)
                frame["key"]=[key(t,lat,lon) for t in frame.time]
                frames.append(frame)
    result=pd.concat(frames,ignore_index=True).sort_values(["time","lat","lon"]).reset_index(drop=True)
    if result.key.duplicated().any():
        raise ValueError("Duplicate ERA5 time/location across exports")
    return result,dict(files=receipts,features=FEATURES,rows=len(result),feature_availability="EXPLICIT_ASSUMED_DELAY_RETROSPECTIVE_ONLY",
        feature_delay_hours=feature_delay_hours,unique_era5_cells=len(result[["era5_lat","era5_lon"]].drop_duplicates()),
        context_only=True,physical_sensor_channels_added=0,as_issued_feature_availability_verified=False)
