import json,tempfile,unittest,warnings
from pathlib import Path
import numpy as np,pandas as pd
from ml.spatial_ensemble.corridor import corridor,DEFAULT_LIMITS
from ml.spatial_ensemble.physics_serving import predict_two_nodes
from ml.spatial_ensemble.batched_physics import HourlyNetwork
from ml.spatial_ensemble.physics_residual import PhysicsResidualEnsemble
from ml.spatial_ensemble.residual_artifact import export,load

class TwoNodeTests(unittest.TestCase):
 def nodes(self):
  return [dict(node_id=id,latitude=0,longitude=lon,elevation_m=z,timestamp_utc='2024-01-01T00:00Z',temperature_c=15-.0065*z,relative_humidity_pct=60,pressure_hpa=1013.25*((288.15-.0065*z)/288.15)**(9.80665/(287.05*.0065)),wind_speed_mps=2) for id,lon,z in [('A',0,100),('B',.1,1000)]]
 def test_corridor_midpoint_off_axis_ends_and_degenerate(self):
  g=corridor([0,0],[0,.1],[0,.05]);self.assertTrue(g['allowed']);self.assertAlmostEqual(g['along_track_km'],5.559754,places=5)
  self.assertFalse(corridor([0,0],[0,.1],[.02,.05])['allowed']);self.assertFalse(corridor([0,0],[0,.1],[0,-.01])['allowed'])
  self.assertTrue(corridor([0,0],[0,.1],[0,-.001])['allowed']);self.assertFalse(corridor([0,0],[0,0],[0,0])['allowed'])
  self.assertFalse(corridor([0,0],[0,180],[0,90])['allowed'])
 def test_antimeridian_and_reverse_end_limits(self):
  config={**DEFAULT_LIMITS,'max_node_separation_km':30}
  self.assertTrue(corridor([0,179.9],[0,-179.9],[0,180],config)['allowed'])
  g=corridor([0,0],[0,.1],[0,-.003],{**DEFAULT_LIMITS,'max_beyond_a_km':.1,'max_beyond_b_km':1});self.assertIn('BEYOND_A',g['reason'])
  with self.assertRaises(ValueError):corridor([0,0],[0,.1],[0,.05],{'max_beyond_a_km':-1})
 def test_two_nodes_predict_no_hull_and_flag_policy(self):
  a,b=self.nodes();r=predict_two_nodes(a,b,0,.05,a['timestamp_utc'],500)
  from ml.spatial_ensemble.physics_serving import predict_snapshot
  auto=predict_snapshot([a,b],0,.05,a['timestamp_utc'],500);self.assertIsNotNone(auto['targets']['pressure_hpa']['prediction'])
  self.assertIsNotNone(r['targets']['pressure_hpa']['prediction']);self.assertAlmostEqual(r['targets']['temperature_c']['prediction'],11.75)
  outside=predict_two_nodes(a,b,.02,.05,a['timestamp_utc'],500);self.assertIsNone(outside['targets']['temperature_c']['prediction'])
  flagged=predict_two_nodes(a,b,.02,.05,a['timestamp_utc'],500,outside_policy='flag');self.assertEqual(flagged['targets']['temperature_c']['status'],'FLAGGED_OUTSIDE_CORRIDOR');self.assertTrue(all(v is None for v in flagged['targets']['temperature_c']['bands'].values()))
 def test_offline_colocated_identity_and_core_mask(self):
  a,b=self.nodes();r=predict_two_nodes(a,{**b,'timestamp_utc':'2023-01-01T00:00Z'},0,.05,a['timestamp_utc'],500);self.assertIsNone(r['targets']['temperature_c']['prediction'])
  with self.assertRaises(ValueError):predict_two_nodes(a,a,0,.05,a['timestamp_utc'],500)
  r=predict_two_nodes(a,{**b,'node_id':'B','longitude':0},0,0,a['timestamp_utc'],500);self.assertIsNone(r['targets']['temperature_c']['prediction'])
  r=predict_two_nodes(a,{**b,'pressure_hpa':np.nan},0,.05,a['timestamp_utc'],500);self.assertIsNone(r['targets']['pressure_hpa']['prediction']);self.assertIsNotNone(r['targets']['temperature_c']['prediction'])
  r=predict_two_nodes(a,{**b,'elevation_m':None},0,.05,a['timestamp_utc'],500,outside_policy='flag');self.assertIsNone(r['targets']['temperature_c']['prediction']);self.assertIsNone(r['targets']['relative_humidity_pct']['prediction']);self.assertIsNotNone(r['targets']['wind_speed_mps']['prediction'])
 def test_exact_count_no_query_or_third_sensor(self):
  nodes=self.nodes()+[dict(self.nodes()[1],node_id='D',longitude=.15),dict(self.nodes()[1],node_id='C',longitude=.05)]
  station=pd.DataFrame([dict(location_id=n['node_id'],physical_site_id=n['node_id'],geography_status='OK',slope_deg=0,elevation_m=n['elevation_m'],latitude=n['latitude'],longitude=n['longitude']) for n in nodes]);qc=pd.DataFrame({'location_id':station.location_id,'elevation_ok':True,'pressure_ok':True});frame=pd.DataFrame([{**n,'location_id':n['node_id'],'dewpoint_c':np.nan,'pm25_ug_m3':np.nan,'pm10_ug_m3':np.nan} for n in nodes])
  net=HourlyNetwork(frame,station,qc)
  with tempfile.TemporaryDirectory() as tmp:
   a,ids,_=net.examples({'C'},{'A','B','C','D'},net.parts['train2024'],tmp,neighbor_count=2);self.assertEqual(a['neighbor_ids'].shape,(1,2));self.assertNotIn(net.lookup['C'],a['neighbor_ids']);self.assertTrue(np.all(a['x'][:,[41,42,43,46]]==2));old=a['x'].copy()
   net.readings[:,net.lookup['D']]=999;net.readings[:,net.lookup['C']]=999
   a,_,_=net.examples({'C'},{'A','B','C','D'},net.parts['train2024'],Path(tmp)/'b',neighbor_count=2);np.testing.assert_allclose(a['x'],old,equal_nan=True)
 def test_json_export_roundtrip_and_bad_contract(self):
  rng=np.random.default_rng(42);x=rng.normal(size=(150,47));x[::3,0]=np.nan;base=np.tile([20,50,900,np.nan,np.nan,2],(150,1));y=base.copy();y[:,0]+=2*np.nan_to_num(x[:,0])+10*np.isnan(x[:,0])
  with warnings.catch_warnings():
   warnings.simplefilter('ignore');m=PhysicsResidualEnsemble(neighbor_count=2).fit(x[:100],y[:100],base[:100],x[100:],y[100:],base[100:])
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'model.json';export(m,p,corridor_limits=DEFAULT_LIMITS);r,_=load(p);expected,ef=m.predict(x[100:],base[100:]);actual,af=r.predict(x[100:],base[100:]);np.testing.assert_allclose(actual,expected,equal_nan=True,atol=2e-4);np.testing.assert_array_equal(af,ef)
   for i,h in m.heads.items():
    for kind,original in h['models'].items():np.testing.assert_allclose(original.predict(x[:,h['active']]),r.heads[i]['models'][kind].predict(x[:,h['active']]),rtol=1e-5,atol=2e-4)
   payload=json.loads(p.read_text());self.assertTrue(any(any(t['threshold_positive_infinity']) for t in payload['heads']['0']['models']['boosting']['trees']));payload['neighbor_count']=32;p.write_text(json.dumps(payload))
   with self.assertRaises(ValueError):load(p)

class FieldTests(unittest.TestCase):
 def fixture(self,root):
  from ml.field.two_node import calibrate
  records=[]
  for i in range(12):
   t=(pd.Timestamp('2024-01-01T00:00Z')+pd.Timedelta(minutes=i)).strftime('%Y-%m-%dT%H:%M:%SZ')
   for id in 'ABC':
    bias={'A':1,'B':-2,'C':0}[id]
    records.append(dict(timestamp_utc=t,node_id=id,latitude=31.7,longitude=76.9,elevation_m=600,pressure_reference='station',temperature_c=15+bias,relative_humidity_pct=60+bias,pressure_hpa=940+bias,wind_speed_mps=3+bias))
  calibration=Path(root)/'calibration.csv';pd.DataFrame(records).to_csv(calibration,index=False);offsets=Path(root)/'offsets.json';calibrate(calibration,offsets,minimum_pairs=10)
  records=[]
  for id,lon in [('A',76.90),('B',76.98),('C',76.94)]:
   bias={'A':1,'B':-2,'C':0}[id];records.append(dict(timestamp_utc='2024-01-02T00:00:00Z',node_id=id,latitude=31.7,longitude=lon,elevation_m=600,pressure_reference='station',temperature_c=15+bias,relative_humidity_pct=60+bias,pressure_hpa=940+bias,wind_speed_mps=3+bias))
  field=Path(root)/'field.csv';pd.DataFrame(records).to_csv(field,index=False);return calibration,offsets,field
 def test_offsets_and_hidden_truth_independence_rotation(self):
  from ml.field.two_node import score
  with tempfile.TemporaryDirectory() as tmp:
   _,offsets,field=self.fixture(tmp);payload=json.loads(offsets.read_text());self.assertEqual(payload['offsets']['A']['temperature_c']['additive_offset'],-1)
   out=Path(tmp)/'scores.csv';r=score(field,offsets,out);rows=pd.read_csv(out);c=rows[(rows.hidden_sensor=='C')&(rows.method=='prediction')];self.assertTrue(c.prediction.notna().all());self.assertTrue(rows[(rows.hidden_sensor=='A')&(rows.method=='prediction')].prediction.isna().all())
   frame=pd.read_csv(field);frame.loc[frame.node_id=='C','temperature_c']=40;frame.to_csv(field,index=False);score(field,offsets,out,rotation=False);after=pd.read_csv(out);np.testing.assert_allclose(c.prediction,after[after.method=='prediction'].prediction)
   self.assertTrue(all(s['checked_band_rows']==0 for s in r['scores']))
 def test_duplicates_naive_pressure_reference_and_calibration_overlap(self):
  from ml.field.two_node import read,score,calibrate
  with tempfile.TemporaryDirectory() as tmp:
   calibration,offsets,field=self.fixture(tmp)
   with self.assertRaises(ValueError):score(calibration,offsets,Path(tmp)/'scores.csv')
   frame=pd.read_csv(field);pd.concat([frame,frame.iloc[:1]]).to_csv(field,index=False)
   with self.assertRaises(ValueError):read(field)
   frame.timestamp_utc=frame.timestamp_utc.str.replace('Z','',regex=False);frame.to_csv(field,index=False)
   with self.assertRaises(ValueError):read(field)
   bad_reference=pd.read_csv(calibration);bad_reference.pressure_reference='sea_level';bad_reference.to_csv(field,index=False)
   with self.assertRaises(ValueError):read(field)
   bad=pd.read_csv(calibration);bad.loc[bad.node_id=='A','longitude']=77;bad.to_csv(calibration,index=False)
   with self.assertRaises(ValueError):calibrate(calibration,offsets,minimum_pairs=10)
 def test_demo_rejects_third_node_and_hidden_values(self):
  from reports.practicum.demo import example,run
  p=example();self.assertIsNotNone(run(p)['targets']['pressure_hpa']['prediction']);p['nodes']['C']=p['nodes']['A']
  with self.assertRaises(ValueError):run(p)
  p=example();p['query']['temperature_c']=20
  with self.assertRaises(ValueError):run(p)
 def test_mismatched_model_and_interval_cannot_authorize_band(self):
  a,b=TwoNodeTests().nodes()
  class WrongModel:
   neighbor_count=32
   def predict(self,x,b):raise AssertionError('must not be called')
  r=predict_two_nodes(a,b,0,.05,a['timestamp_utc'],500,model=WrongModel());self.assertFalse(r['model_neighbor_count_compatible']);self.assertIsNotNone(r['targets']['temperature_c']['prediction'])
  class Model:
   neighbor_count=2
   def predict(self,x,b):return b,np.zeros_like(b,dtype=bool)
  class Bands:
   corridor_limits=DEFAULT_LIMITS
   def interval(self,*args):return [0,1]
  r=predict_two_nodes(a,b,0,.05,a['timestamp_utc'],500,model=Model(),bands=Bands());self.assertFalse(r['input_aggregation_verified_for_archive_bands']);self.assertTrue(all(v is None for v in r['targets']['temperature_c']['bands'].values()))
  class Capture(Model):
   def predict(self,x,b):self.x=x.copy();return super().predict(x,b)
  capture=Capture();predict_two_nodes({**a,'pm25_ug_m3':10,'pm10_ug_m3':20},{**b,'pm25_ug_m3':15,'pm10_ug_m3':25},0,.05,a['timestamp_utc'],500,model=capture);self.assertTrue((capture.x[:,44:46]==0).all())

if __name__=='__main__':unittest.main()
