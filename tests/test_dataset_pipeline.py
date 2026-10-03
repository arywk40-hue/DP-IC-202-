import json,sqlite3,tempfile,unittest
from pathlib import Path
import numpy as np,pandas as pd
from ml.datasets.registry import connect,validate_long_row
from ml.datasets.noaa import coverage,qc_good
from ml.datasets.terrain import tile
from ml.datasets.era5_land import request
from ml.spatial_ensemble.network import guard,named_features,distance_distribution
from ml.spatial_ensemble.model import SpatialEnsemble
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS

class PipelineTests(unittest.TestCase):
 def test_registry_views_and_identifier_validation(self):
  with tempfile.TemporaryDirectory() as d:
   db=connect(Path(d)/'obs.sqlite')
   self.assertEqual(db.execute('SELECT count(*) FROM training_open').fetchone()[0],0)
   self.assertEqual(db.execute("SELECT license_class FROM sources WHERE source_id='india_cpcb_kaggle_v2'").fetchone()[0],'restricted')
   registry=json.loads(Path('data/registry/sources.json').read_text());registry['sources'][0]['evil); DROP TABLE sources; --']=1
   p=Path(d)/'bad.json';p.write_text(json.dumps(registry))
   with self.assertRaises(ValueError):connect(Path(d)/'bad.sqlite',p)
 def test_noaa_real_hour_completeness(self):
  f=pd.DataFrame({'DATE':['2024-01-01T00:00:00','2024-01-01T00:30:00','2024-01-01T01:00:00'],
   'temperature':[20,21,22],'temperature_Quality_Code':['1','1','2'],'temperature_Source_Code':['220']*3})
  c=coverage(f,2024);self.assertEqual(c['distinct_hours'],2)
  self.assertEqual(c['variables']['temperature']['distinct_hours'],1)
  self.assertEqual(c['variables']['temperature']['calendar_hour_completeness'],1/8784)
 def test_unknown_qc_fails_closed(self):
  f=pd.DataFrame({'temperature_Quality_Code':['1','q',''],'temperature_Source_Code':['999']*3})
  self.assertEqual(qc_good(f,'temperature').tolist(),[False,False,True])
 def test_terrain_names_and_cds_bounds(self):
  self.assertEqual(tile(31.7,76.9),'N31E076.tif')
  self.assertEqual(tile(-1.1,-2.1),'S02W003.tif')
  self.assertEqual(len(request(2024,2,[38,68,6,99])['request']['day']),29)
  with self.assertRaises(ValueError):request(2024,1,[6,68,38,99])
 def nodes(self):
  return [dict(latitude=a,longitude=b,timestamp_utc='2024-01-01T00:00:00Z',elevation_m=100,
   temperature_c=20,relative_humidity_pct=50,pressure_hpa=1000,wind_speed_mps=2) for a,b in [(30,75),(30,75.1),(30.1,75)]]
 def test_network_and_optional_features(self):
  nodes=self.nodes();self.assertTrue(guard(nodes,30.02,75.02,'2024-01-01T00:00:00Z')['allowed'])
  self.assertFalse(guard(nodes,31,76,'2024-01-01T00:00:00Z')['allowed'])
  x,b,c=named_features(nodes,30.02,75.02,'2024-01-01T00:00:00Z',110,2)
  self.assertEqual(x.shape,(33,));self.assertAlmostEqual(x[28],10)
  self.assertTrue(np.isnan(x[3]));self.assertEqual(c[3],0)
  result=SpatialEnsemble(max_distance_km=20).predict(nodes,31,76,'2024-01-01T00:00:00Z')
  self.assertEqual(result['status'],'REFUSED_NETWORK_GEOMETRY')
 def test_channel_distance_uses_only_valid_nodes(self):
  nodes=self.nodes();nodes.append(dict(latitude=32,longitude=77,timestamp_utc='2024-01-01T00:00:00Z',pressure_hpa=900))
  for node in nodes[:3]:node['pressure_hpa']=None
  result=SpatialEnsemble(max_distance_km=20).predict(nodes,30.02,75.02,'2024-01-01T00:00:00Z')
  self.assertIsNone(result['targets']['pressure_hpa']['prediction'])
  self.assertEqual(result['targets']['pressure_hpa']['geometry']['reason'],'MAXIMUM_DISTANCE')
 def test_invalid_distance_configuration(self):
  for value in [0,-1,float('nan'),float('inf')]:
   with self.assertRaises(ValueError):SpatialEnsemble(max_distance_km=value)
 def test_malformed_node_does_not_crash_valid_fallback(self):
  result=SpatialEnsemble().predict(self.nodes()+['invalid',None],30.02,75.02,'2024-01-01T00:00:00Z')
  self.assertEqual(result['targets']['temperature_c']['prediction'],20)
 def test_nan_long_row_rejected(self):
  r={'variable':'temperature_c','unit':'degC','status':'quarantined','qc_flags':'[]','value':float('nan')}
  with self.assertRaises(ValueError):validate_long_row(r)
 def test_metadata_nan_and_modeled_view(self):
  from ml.datasets.adapters import power_json,ingest_frame
  with tempfile.TemporaryDirectory() as d:
   db=connect(Path(d)/'obs.sqlite');p=Path('reports/nwic_pipeline/source_evidence/power_mandi_202401.json')
   # Synthetic approval of interval semantics isolates background-view behavior;
   # production registry keeps POWER's interval semantics unresolved.
   db.execute("UPDATE sources SET interval_semantics='instant' WHERE source_id='nasa_power'")
   counts=power_json(db,p,'power_mandi',31.708,76.932)
   self.assertGreater(counts['approved'],0)
   self.assertEqual(db.execute('SELECT count(*) FROM training_open').fetchone()[0],0)
   self.assertGreater(db.execute('SELECT count(*) FROM background_open').fetchone()[0],0)
   db.execute("UPDATE sources SET interval_semantics='unknown' WHERE source_id='nasa_power'")
   self.assertEqual(db.execute('SELECT count(*) FROM background_open').fetchone()[0],0)
   with self.assertRaises(ValueError):ingest_frame(db,pd.DataFrame(),p,'unknown',{'T2M':'temperature_c'},pd.DataFrame())
 def test_core_mask_head(self):
  # Fits actual core heads while both PM labels/features are entirely missing.
  rng=np.random.default_rng(7);x=rng.normal(size=(100,25));x[:,[3,4,9,10,15,16]]=np.nan
  y=np.tile([20,50,950,np.nan,np.nan,3],(100,1));x[:,[0,1,2,5]]=y[:,[0,1,2,5]]+rng.normal(size=(100,4))
  with __import__('warnings').catch_warnings():
   __import__('warnings').simplefilter('ignore');m=SpatialEnsemble().fit(x[:60],y[:60][:,[0,1,2,5]],x[60:],y[60:][:,[0,1,2,5]])
  self.assertEqual(set(m.heads),{'temperature_c','relative_humidity_pct','pressure_hpa','wind_speed_mps'})
  for h in m.heads.values():self.assertFalse(set(h['active'])&{3,4,9,10,15,16})

if __name__=='__main__':unittest.main()
