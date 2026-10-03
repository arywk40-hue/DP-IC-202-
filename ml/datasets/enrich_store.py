"""Join sampled terrain into long-form artifacts, preserving source lineage."""
import json,sqlite3
from pathlib import Path
import pandas as pd
from ml.datasets.registry import digest


def enrich_sqlite(path,stations_path):
    db=sqlite3.connect(path);s=pd.read_csv(stations_path)
    for r in s.itertuples():
        if r.terrain_status!='VERIFIED_ASSET_SAMPLED':continue
        db.execute('UPDATE observations SET elevation_m=?,elevation_datum=?,elevation_source_id=?,elevation_asset_sha256=? WHERE station_id=?',
            (r.elevation_m,'EGM96','srtm_gl1',r.elevation_asset_sha256,r.location_id))
    db.commit();db.close()


def enrich_parquet(path,stations_path):
    import pyarrow as pa,pyarrow.parquet as pq
    stations=pd.read_csv(stations_path).set_index('location_id');path=Path(path);out=path.with_suffix('.terrain.building.parquet');writer=None
    try:
        for batch in pq.ParquetFile(path).iter_batches(batch_size=10000):
            f=batch.to_pandas();s=stations.reindex(f.station_id)
            wind_2007=f.variable.eq('wind_speed_mps') & f.source_timestamp.str.contains(r'-2007 ',regex=True)
            f.loc[wind_2007,'qc_flags']=f.loc[wind_2007,'qc_flags'].apply(lambda v:json.dumps(sorted(set(json.loads(v)+['WIND_2007_UNCORROBORATED']))))
            f['elevation_m']=s.elevation_m.to_numpy();f['elevation_datum']=s.elevation_datum.to_numpy();f['elevation_source_id']='srtm_gl1';f['elevation_asset_sha256']=s.elevation_asset_sha256.to_numpy()
            table=pa.Table.from_pandas(f,schema=batch.schema,preserve_index=False)
            if writer is None:writer=pq.ParquetWriter(out,batch.schema,compression='zstd')
            writer.write_table(table)
        if writer:writer.close();writer=None
        out.replace(path)
    finally:
        if writer:writer.close()
        out.unlink(missing_ok=True)

if __name__=='__main__':
    enrich_sqlite('data/india_training/sample.sqlite','data/registry/india_stations.csv')
    enrich_parquet('data/nwic_himachal/observations.parquet','data/registry/nwic_stations.csv')
    for report,artifact,stations in [('data/nwic_himachal/build_report.json','data/nwic_himachal/observations.parquet','data/registry/nwic_stations.csv'),('data/india_training/manifest.json','data/india_training/sample.sqlite','data/registry/india_stations.csv')]:
        p=Path(report);r=json.loads(p.read_text())
        if 'sources' in r and 'wind_speed_mps' in r['sources']:
            r['sources']['wind_speed_mps']['flag_counts']['WIND_2007_UNCORROBORATED']=r['sources']['wind_speed_mps']['wind_rows_by_year'].get('2007',0)
        r.update(terrain_registry_sha256=digest(stations),terrain_enriched_artifact_sha256=digest(artifact),terrain_enriched_artifact=artifact);p.write_text(json.dumps(r,indent=2)+'\n')
