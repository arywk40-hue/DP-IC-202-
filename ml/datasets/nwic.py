"""Build all supplied NWIC observations with traceable quarantine, never guessed UTC."""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
from ml.datasets.registry import connect, digest, insert_rows
from ml.deployment.audit_himachal import SOURCES, KEYS
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES

UNITS = {'temperature_c':'degC','relative_humidity_pct':'%','pressure_hpa':'hPa','wind_speed_mps':'m/s'}
SOURCE_IDS = {'temperature_c':'nwic_hp_temperature','relative_humidity_pct':'nwic_hp_humidity',
              'pressure_hpa':'nwic_hp_pressure','wind_speed_mps':'nwic_hp_wind'}


def site_id(name, lat, lon):
    identity = f'{name.strip()}|{float(lat):.6f}|{float(lon):.6f}'
    return 'nwic_hp_' + hashlib.sha256(identity.encode()).hexdigest()[:16]


def build(directory, output, registry='data/registry/sources.json', compact=False):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    destination = output/'observations.sqlite'
    staging = output/'observations.building.sqlite'
    if staging.exists():
        staging.unlink()  # Only a generated staging artifact, never raw source data.
    db = connect(':memory:' if compact else staging, registry)
    writer = None
    compact_path = output/'observations.building.parquet'
    def flush(batch):
        nonlocal writer
        if not batch:return
        insert_rows(db,batch);db.commit()
        if compact:
            import pyarrow as pa, pyarrow.parquet as pq
            columns={row[1]:row[2] for row in db.execute('PRAGMA table_info(observations)')}
            types={'TEXT':pa.string(),'REAL':pa.float64()}
            schema=pa.schema([(name,types[kind]) for name,kind in columns.items()])
            data=pd.read_sql_query('SELECT * FROM observations',db)
            table=pa.Table.from_pandas(data,schema=schema,preserve_index=False)
            if writer is None:writer=pq.ParquetWriter(compact_path,schema,compression='zstd')
            writer.write_table(table);db.execute('DELETE FROM observations');db.commit()
    report = dict(schema_version='indra_observations_v1', registry_sha256=digest(registry), sources={})
    station_rows = {}
    for path in sorted(Path(directory).glob('*.csv')):
        header = pd.read_csv(path, nrows=0).columns
        found = [column for column in SOURCES if column in header]
        if len(found) != 1:
            continue
        column = found[0]
        variable, factor = SOURCES[column]
        sid = SOURCE_IDS[variable]
        source = dict(zip([c[0] for c in db.execute('SELECT * FROM sources LIMIT 0').description],
                         db.execute('SELECT * FROM sources WHERE source_id=?', (sid,)).fetchone()))
        checksum = digest(path)
        db.execute('INSERT INTO raw_files VALUES (?,?,?,?,?)',(checksum,sid,str(path),path.stat().st_size,None))
        frame = pd.read_csv(path, usecols=KEYS+[column])
        duplicate = frame.duplicated(KEYS, keep=False).to_numpy()
        times = pd.to_datetime(frame['Data Acquisition Time'],format='%d-%m-%Y %H:%M',errors='coerce')
        values = pd.to_numeric(frame[column],errors='coerce')*factor
        lo,hi = PHYSICAL_RANGES[variable]
        valid_values = np.isfinite(values) & values.between(lo,hi)
        coordinates = frame[['Latitude','Longitude']].apply(pd.to_numeric,errors='coerce')
        coordinate_array=coordinates.to_numpy()
        flags_count = Counter()
        wind_years = Counter()
        batches = []
        source_counts = Counter()
        for index, row in enumerate(frame.itertuples(index=False,name=None)):
            # Use column names rather than tuple positions because pandas source order varies.
            original = dict(zip(frame.columns,row))
            lat,lon = coordinate_array[index]
            flags = []
            if not np.isfinite(lat+lon) or not -90<=lat<=90 or not -180<=lon<=180:
                flags.append('INVALID_COORDINATES')
                identity = 'unresolved_'+hashlib.sha256(f'{sid}:{index}'.encode()).hexdigest()[:16]
                lat=lon=None
            else:
                identity=site_id(str(original['Station']),lat,lon)
                station_rows[identity]=dict(location_id=identity,physical_site_id=identity,station_name=original['Station'],
                    latitude=float(lat),longitude=float(lon),source='nwic_hp',elevation_m=None,elevation_datum=None,
                    climate_zone=None,climate_zone_source=None)
            time=times.iloc[index]
            if pd.isna(time): flags.append('INVALID_SOURCE_TIMESTAMP')
            if duplicate[index]: flags.append('DUPLICATE_STATION_TIME')
            if not valid_values.iloc[index]: flags.append('INVALID_PHYSICAL_VALUE')
            if not source['timezone_verified']: flags.append('TIMEZONE_UNVERIFIED')
            if source['interval_semantics']=='unknown': flags.append('INTERVAL_SEMANTICS_UNVERIFIED')
            if source['license_class']=='unresolved': flags.append('LICENSE_UNRESOLVED')
            pressure_ref = 'not_applicable'
            if variable=='pressure_hpa':
                pressure_ref=source['pressure_reference']
                if not source['pressure_verified'] or pressure_ref!='station': flags.append('PRESSURE_REFERENCE_UNVERIFIED')
                if values.iloc[index]==925: flags.append('REPEATED_925_SUSPECT')
            if variable=='wind_speed_mps' and not pd.isna(time):
                wind_years[int(time.year)] += 1
                if time.year==2007 and not json.loads(source['approval_evidence']).get('wind_2007_verified',False):
                    flags.append('WIND_2007_UNCORROBORATED')
                # Provider resource spans 1970–2025: 2007 is not itself out of period.
                if not 1970<=time.year<=2025: flags.append('OUTSIDE_DOCUMENTED_RESOURCE_PERIOD')
            utc=None
            if source['timezone_verified'] and not pd.isna(time):
                utc=time.tz_localize(source['timezone'],ambiguous='raise',nonexistent='raise').tz_convert('UTC').isoformat()
            # Hourly cadence does not establish whether each row is instant/start/end.
            start=end=available=None
            if utc is not None and source['interval_semantics'] in ('instant','hour_end','hour_start'):
                ts=pd.Timestamp(utc)
                start=(ts-pd.Timedelta(hours=1)).isoformat() if source['interval_semantics']=='hour_end' else utc
                end=(ts+pd.Timedelta(hours=1)).isoformat() if source['interval_semantics']=='hour_start' else utc
                available=end
            flags=sorted(set(flags))
            flags_count.update(flags)
            status='quarantined' if flags else 'approved'
            source_counts[status]+=1
            record=hashlib.sha256(f'{sid}:{checksum}:{index+2}:{variable}'.encode()).hexdigest()
            batches.append(dict(record_id=record,source_id=sid,raw_sha256=checksum,source_row_id=str(index+2),
                station_id=identity,physical_site_id=identity,instrument_id=None,latitude_deg=lat,longitude_deg=lon,
                elevation_m=None,elevation_datum=None,elevation_source_id=None,elevation_asset_sha256=None,
                source_timestamp=str(original['Data Acquisition Time']),interval_start_utc=start,
                interval_end_utc=end,available_at_utc=available,variable=variable,
                value=float(values.iloc[index]) if valid_values.iloc[index] else None,unit=UNITS[variable],
                original_value=str(original[column]),original_unit='km/h' if variable=='wind_speed_mps' else ('mb' if variable=='pressure_hpa' else UNITS[variable]),
                pressure_reference=pressure_ref,measurement_height_m=None,qc_flags=json.dumps(flags),
                observed_or_modeled='observed',uncertainty=None,status=status))
            if len(batches)==10000:
                flush(batches);batches=[]
        flush(batches)
        report['sources'][variable]=dict(source_id=sid,raw_sha256=checksum,raw_rows=len(frame),
            status_counts=dict(source_counts),flag_counts=dict(flags_count),wind_rows_by_year=dict(wind_years),
            source_timezone=source['timezone'],pressure_reference=source['pressure_reference'])
        print(variable,source_counts,flush=True)
    if set(report['sources'])!=set(SOURCE_IDS):
        raise ValueError('Require all four source files')
    report['views']={view:db.execute(f'SELECT count(*) FROM {view}').fetchone()[0] for view in ['training_open','training_restricted','quarantine']}
    if compact:
        if writer is not None:writer.close()
        report['views']={'training_open':sum(r['status_counts'].get('approved',0) for r in report['sources'].values()),'training_restricted':0,'quarantine':sum(r['status_counts'].get('quarantined',0) for r in report['sources'].values())}
        report['storage']='compressed long-form Parquet; SQL views require materialization into canonical store'
    pd.DataFrame(station_rows.values()).sort_values('location_id').to_csv(output/'stations.csv',index=False)
    report['stations']=len(station_rows)
    db.close()
    if not compact:staging.replace(destination)
    else:
        destination=output/'observations.parquet'
        compact_path.replace(destination)
    report['database_sha256']=digest(destination)
    (output/'build_report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,default=Path('himachal 4-sensor dataset'))
    p.add_argument('--output',type=Path,default=Path('data/nwic_himachal'))
    p.add_argument('--compact',action='store_true',help='Compressed long-form artifact for low-disk environments')
    p.add_argument('--registry',type=Path,default=Path('data/registry/sources.json'))
    a=p.parse_args();build(a.data,a.output,a.registry,a.compact)


if __name__=='__main__':main()
