"""Reproducible synthetic fixture exercise; no real events or fitted hazard heads."""
import argparse
import json

import numpy as np
import pandas as pd

from ml.hazard_context.era5 import normalize_files,join_context
from ml.hazard_context.events import normalize,admit
from ml.hazard_context.matching import match
from ml.hazard_context.output import fresh_directory
from ml.india_sensor.features import METADATA
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


def run(output):
    import xarray as xr
    p=fresh_directory(output);times=pd.date_range('2024-01-01',periods=300,freq='h',tz='UTC')
    row=dict(location_id='fixture_node',physical_site_id='fixture_site',source_id='noaa_ghcnh',country_code='IN',
             latitude=31.,longitude=77.,elevation_m=1200.,elevation_datum='EGM96',pressure_reference='station',climate_zone='unknown',interval_seconds=3600,
             temperature_c=20.,relative_humidity_pct=60.,pressure_hpa=900.,pm25_ug_m3=np.nan,pm10_ug_m3=np.nan,wind_speed_mps=3.)
    f=pd.DataFrame([{**row,'timestamp_utc':t,'available_at_utc':t} for t in times])
    f=f[[*METADATA,*RAW_SENSOR_COLUMNS]];f.to_csv(p/'sensor_fixture.csv',index=False)
    stations=f[['location_id','physical_site_id','latitude','longitude','elevation_m']].iloc[:1];stations.to_csv(p/'stations.csv',index=False)
    fields={k:(('time','latitude','longitude'),np.full((300,2,2),value),{'units':unit}) for k,value,unit in [('t2m',293.15,'K'),('d2m',285.,'K'),('sp',90000.,'Pa'),('u10',3.,'m s**-1'),('v10',4.,'m s**-1')]}
    ds=xr.Dataset(fields,coords=dict(time=times.tz_localize(None),latitude=[32.,30.],longitude=[76.,78.]))
    ds.to_netcdf(p/'fixture.nc')
    metadata=dict(provider='ECMWF/Copernicus',dataset='era5_land',country='IN',version='fixture_v1',retrieved_at='2026-10-06T00:00:00Z',
                  license='SYNTHETIC_TEST_ONLY',rights_status='approved_open',rights_evidence_uri='fixture://generated',evidence='SYNTHETIC_CONTRACT_ONLY')
    b,manifest=normalize_files([p/'fixture.nc'],stations,metadata,p/'background.parquet')
    joined=join_context(f,b)
    s=dict(source_provider='fixture',source_dataset='synthetic',status='admitted_for_training',independent_observed=True,country='IN',targets=['cloudburst'],
           rights_status='approved_open',provider_license='SYNTHETIC_TEST_ONLY',rights_evidence_uri='fixture://generated',reviewed_by='unit_fixture',event_identity_reviewed=True,evidence='SYNTHETIC_CONTRACT_ONLY')
    e=normalize(dict(event_group_id='physical_fixture_one',source_provider='fixture',source_dataset='synthetic',source_record_id='one',event_type='cloudburst',event_start_utc='2024-01-03T00:00:00Z',
                     event_end_utc='2024-01-03T01:00:00Z',country='IN',latitude=31.,longitude=77.,spatial_uncertainty_km=.1,temporal_uncertainty_hours=.1,
                     measurement_value=120.,measurement_unit='mm/h',threshold_definition='SYNTHETIC_TEST_ONLY',quality_flag='verified',label_provenance='SYNTHETIC_CONTRACT_ONLY',
                     evidence_kind='observed_gauge',provider_license='SYNTHETIC_TEST_ONLY',provider_rights_status='approved_open',source_version='fixture_v1',source_hash='a'*64,
                     retrieved_at='2026-10-06T00:00:00Z',cloudburst_evidence_verified=True))
    # Explicit unit-contract override; normal admission rejects synthetic sources.
    e=admit(e,s,allow_fixture=True)
    (p/'events.jsonl').write_text(json.dumps(e)+'\n');(p/'sources.json').write_text(json.dumps({'sources':[s]})+'\n')
    m=dict(source_provider='fixture',source_version='fixture_v1',provider_license='SYNTHETIC_TEST_ONLY',rights_evidence_uri='fixture://generated',reviewed_by='unit_fixture',retrieved_at='2026-10-06T00:00:00Z',monitoring_admission_status='admitted_for_training',spatial_coverage_radius_km=20.,monitoring_id='synthetic_monitor',physical_site_id='fixture_site',event_type='cloudburst',source_dataset='synthetic',country='IN',independent_observed=True,
           complete_coverage_verified=True,negative_category='monitored_no_event',rights_status='approved_open',definition='SYNTHETIC_TEST_ONLY',source_hash='b'*64,
           start_utc='2024-01-01T00:00:00Z',end_utc='2024-01-14T00:00:00Z')
    (p/'monitoring.json').write_text(json.dumps([m])+'\n')
    matched=match([e],stations,f,[m]);matched.to_csv(p/'matched.csv',index=False)
    result=dict(evidence='SYNTHETIC_CONTRACT_ONLY',sensor_rows=len(f),normalized_fixture_era5_rows=len(b),joined_nonmissing_rows=int(joined.era5_temperature_c.notna().sum()),
                synthetic_positive_hours=int(matched.label.eq(1).sum()),synthetic_monitored_negative_hours=int(matched.label.eq(0).sum()),
                unknown_hours=int(matched.label.isna().sum()),real_events=0,real_era5_rows=0,hazard_models_fitted=0,disaster_outputs='DISABLED',
                normal_admission_status=admit(e,s)['admission_status'],background_manifest=manifest)
    (p/'demo.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    print(json.dumps(run(a.output),indent=2))
