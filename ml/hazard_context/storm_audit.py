"""Read observed Himachal NOAA weather reports as storm candidates, never onset labels."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timezone
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from ml.datasets.noaa import qc_good
from ml.datasets.registry import digest
from ml.hazard_context.events import admit
from ml.hazard_context.output import fresh_directory,new_file

STATIONS=['INM00042078','INM00042079','INM00042081','INM00042083','INI0000VISM','INI0000VIGG']
CODE_URI='https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh-present-weather-elements.pdf'


def classification(column,value):
    """Use manual and automatic WMO code families separately; AU needs separate review."""
    if not isinstance(value,str):return None
    m=re.fullmatch(r'(?:([A-Z+\-]+):)?(\d{2})',value.strip())
    if not m:return None
    prefix=m.group(1);code=int(m.group(2))
    if re.fullmatch(r'pres_wx_MW[123]',column):
        if code in {17,95,96,97,98,99} and prefix in [None,'TS']:return 'thunderstorm_at_observation'
        if code==18 and prefix in [None,'SQ']:return 'squall_current_or_previous_hour'
        if code in {29,91,92,93,94} and prefix in [None,'RA','TS']:return 'thunderstorm_previous_hour'
    if re.fullmatch(r'pres_wx_AW[123]',column):
        if code in {90,91,92,93,94,95,96} and prefix in [None,'TS','TS-HAIL','TS+HAIL']:return 'thunderstorm_at_observation'
        if code==18 and prefix in [None,'SQ']:return 'squall_report'
        if code==26 and prefix in [None,'TS']:return 'thunderstorm_previous_hour'
    return None


def source_descriptor():
    return dict(source_provider='NOAA NCEI GHCNh',source_dataset='ghcnh_himachal_weather_reports',
                source_uri='https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly',
                targets=['storm'],country='IN',status='candidate',independent_observed=True,
                event_identity_reviewed=False,rights_status='unresolved',provider_license=None,
                rights_evidence_uri=None,reviewed_by=None,used_for_training=False,used_for_validation=False,
                used_for_labels=False,reason='Observed present-weather report times are not adjudicated episode onsets; location/time uncertainty, monitored negatives, rights and matched PM require review')


def run(raw_root,registry,output,audit_output,code_receipt):
    folder=fresh_directory(output)
    if Path(audit_output).exists():raise ValueError('Choose a new audit output path')
    station_table=pd.read_csv(registry).set_index('location_id')
    source=source_descriptor();receipts=[];summaries=[];candidates=[]
    retrieved=datetime.now(timezone.utc).isoformat()
    for station in STATIONS:
        if station not in station_table.index:raise ValueError('Expected station absent from reviewed registry')
        site=station_table.loc[station]
        for year in [2023,2024]:
            path=Path(raw_root)/f'GHCNh_{station}_{year}.parquet'
            if not path.exists() or getattr(path.stat(),'st_flags',0)&0x40000000:
                summaries.append(dict(station=station,year=year,status='RAW_FILE_NOT_LOCAL'));continue
            names=pq.read_schema(path).names
            variables=[c for c in names if re.fullmatch(r'pres_wx_(MW|AW)[123]',c)]
            selected=['DATE']
            for var in [*variables,'wind_gust']:
                selected.extend(n for n in [var,var+'_Quality_Code',var+'_Source_Code'] if n in names)
            f=pq.read_table(path,columns=selected).to_pandas()
            dates=pd.to_datetime(f.DATE,utc=True,errors='coerce')
            positive=np.zeros(len(f),bool);kinds=Counter();entries={}
            for var in variables:
                good=qc_good(f,var).to_numpy() & dates.dt.year.eq(year).to_numpy()
                for index,value in enumerate(f[var]):
                    kind=classification(var,value)
                    if not good[index] or kind is None:continue
                    positive[index]=True;kinds[kind]+=1
                    key=dates.iloc[index].isoformat()
                    entries.setdefault(key,set()).add((var,value,kind))
            gust=pd.to_numeric(f.get('wind_gust',pd.Series(np.nan,index=f.index)),errors='coerce')
            gust_ok=gust.between(0,100)&qc_good(f,'wind_gust')&dates.dt.year.eq(year)
            sha=digest(path);receipts.append(dict(file=path.as_posix(),sha256=sha))
            delta=dates.dropna().sort_values().drop_duplicates().diff().dt.total_seconds()/3600
            summaries.append(dict(station=station,station_name=str(site.station_name),year=year,
                                  raw_reports=len(f),distinct_report_hours=int(dates.dropna().dt.floor('h').nunique()),
                                  median_report_gap_hours=float(delta.median()) if len(delta.dropna()) else None,
                                  reports_with_qc_accepted_storm_code=int(positive.sum()),distinct_storm_report_times=len(entries),
                                  storm_code_entry_counts=dict(kinds),qc_accepted_gust_reports=int(gust_ok.sum()),
                                  maximum_observed_gust_mps=float(gust[gust_ok].max()) if gust_ok.any() else None,
                                  complete_six_channel_matches=0,monitored_non_event_windows=0,
                                  pm_columns_present=[n for n in names if n in ['pm25_ug_m3','pm10_ug_m3']],status='OBSERVED_REPORT_CANDIDATES_ONLY'))
            for stamp,details in sorted(entries.items()):
                r=dict(source_provider=source['source_provider'],source_dataset=source['source_dataset'],
                       source_record_id=f'{station}|{year}|{stamp}',event_type='storm',country='IN',
                       state='Himachal Pradesh',latitude=float(site.latitude),longitude=float(site.longitude),
                       source_uri=f'https://noaa-ghcnh-pds.s3.amazonaws.com/hourly/access/by-year/{year}/parquet/GHCNh_{station}_{year}.parquet',
                       source_version='Locally retained GHCNh station-year snapshot',source_hash=sha,retrieved_at=retrieved,
                       provider_license=None,provider_rights_status='unresolved',quality_flag='event_unreviewed',
                       evidence_kind='confirmed_occurrence',label_provenance='Independent station weather report; episode identity and onset not adjudicated',
                       reported_date=stamp,reported_time_text='UTC observation/report time; not event onset',
                       reported_location=f'{site.station_name} / {station}',
                       threshold_definition='Observed weather-report discovery: '+json.dumps(sorted(details)))
                candidates.append(admit(r,source))
    (folder/'candidates.jsonl').write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in candidates))
    (folder/'sources.json').write_text(json.dumps({'sources':[source]},indent=2)+'\n')
    report=dict(source=source,weather_code_specification=json.loads(Path(code_receipt).read_text()),
                code_interpretation={'MW_current':[17,95,96,97,98,99],'MW_squall':[18],'MW_recent':[29,91,92,93,94],
                                     'AW_current':[90,91,92,93,94,95,96],'AW_squall':[18],'AW_recent':[26],
                                     'AU':'Not decoded; code/measurement combinations require separate review'},
                reviewed_pdf_tables='5(a) manual MW and 5(b) automated AW; pages visually reviewed',
                station_years=summaries,source_files=receipts,unique_candidate_report_times=len(candidates),
                independent_admitted_episodes=0,verified_event_onsets=0,monitored_non_event_windows=0,
                matched_complete_six_channel_windows=0,models_trained=0,china_data_used=False,
                raw_candidates_path=(folder/'candidates.jsonl').as_posix(),
                blockers=['Report time differs from onset; adjudicate independent episodes',
                          'No matched measured PM2.5/PM10 in this archive',
                          'Sparse weather reports do not prove continuous event-free coverage',
                          'Source rights, definitions and uncertainty review still needed'])
    new_file(audit_output).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw-root',default='ml/data/noaa_ghcnh/raw');p.add_argument('--registry',default='ml/data/registry/india_stations.csv')
    p.add_argument('--output',required=True);p.add_argument('--audit-output',required=True)
    p.add_argument('--code-receipt',required=True)
    args=p.parse_args();r=run(args.raw_root,args.registry,args.output,args.audit_output,args.code_receipt)
    print(json.dumps({'unique_candidate_report_times':r['unique_candidate_report_times'],'admitted_episodes':0,'models_trained':0,'station_years':r['station_years']},indent=2))


if __name__=='__main__':main()
