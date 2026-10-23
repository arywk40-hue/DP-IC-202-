import unittest,tempfile
from pathlib import Path
import numpy as np,pandas as pd
from ml.spatial_ensemble.physics import pressure_log_reference,pressure_from_reference,interpolate,temperature_reference,dewpoint,relative_humidity
from ml.spatial_ensemble.episodes import EpisodeBands,episode_ids,quantile
from ml.spatial_ensemble.physics_residual import PhysicsResidualEnsemble

class PhysicsTests(unittest.TestCase):
 def test_pressure_roundtrip_with_moisture(self):
  z=np.array([0,763,2510,4000]);p=np.array([1010,920,745,620]);t=np.array([25,15,3,-10]);rh=np.array([70,60,40,50]);ref=pressure_log_reference(p,z,t,rh)
  np.testing.assert_allclose(pressure_from_reference(ref,z,t,rh),p,atol=.005)
 def test_standard_atmosphere_common_reference(self):
  z=np.array([100,1000,2500]);t=15-.0065*z;p=1013.25*((t+273.15)/288.15)**(9.80665/(287.05*.0065));read=np.full((3,6),np.nan);read[:,0]=t;read[:,1]=50;read[:,2]=p
  b,idw,_,_=interpolate(read,z,[1,2,3],1500)
  self.assertLess(abs(b[2]-1013.25*((288.15-.0065*1500)/288.15)**(9.80665/(287.05*.0065))),2)
  self.assertAlmostEqual(b[0],5.25)
  self.assertGreater(abs(idw[2]-b[2]),20)
 def test_humidity_dewpoint_identity(self):
  np.testing.assert_allclose(relative_humidity([20,5],dewpoint([20,5],[50,80])),[50,80],atol=1e-9)
 def test_suspect_high_pressure_and_missing_height_refuse(self):
  a=np.full((1,6),np.nan);a[0,[0,1,2]]=[20,50,964.6]
  b,_,_,n=interpolate(a,[5069],[1],763);self.assertTrue(np.isnan(b[2]));self.assertEqual(n,0)
  b,_,_,_=interpolate(a,[100],[1],np.nan);self.assertTrue(np.isnan(b[2]))
 def test_episode_partition_timezone_and_finite_sample(self):
  e=episode_ids(pd.to_datetime(['2024-01-01T00:00Z','2024-01-03T23:00Z','2024-01-04T00:00Z']))
  self.assertEqual(e.tolist(),[0,0,1]);self.assertIsNone(quantile([1,2],.9))
  with self.assertRaises(ValueError):episode_ids(['2024-01-01'])
 def test_band_requires_disjoint_check_and_distance_evidence(self):
  y=np.tile(np.arange(20)[:,None],(1,6));pred=np.zeros_like(y);ep=np.arange(20);d=np.full_like(y,10,dtype=float)
  b=EpisodeBands().fit(y,pred,ep,d);self.assertIsNone(b.interval(0,0,10))
  with self.assertRaises(ValueError):b.check(y,pred,ep,d)
  b.check(np.ones((10,6)),np.zeros((10,6)),np.arange(30,40),np.full((10,6),10))
  self.assertIsNotNone(b.interval(0,0,10));self.assertIsNone(b.interval(0,0,100))
 def test_failed_coverage_suppresses_nominal_band(self):
  b=EpisodeBands().fit(np.ones((20,6)),np.zeros((20,6)),np.arange(20),np.full((20,6),10))
  b.check(np.full((10,6),100),np.zeros((10,6)),np.arange(30,40),np.full((10,6),10));self.assertIsNone(b.interval(0,0,10))
 def test_residual_gate_and_failure_fallback(self):
  rng=np.random.default_rng(42);x=rng.normal(size=(100,47));base=np.tile([20,50,900,np.nan,np.nan,2],(100,1));y=base.copy()
  import warnings
  with warnings.catch_warnings():
   warnings.simplefilter('ignore');m=PhysicsResidualEnsemble().fit(x[:60],y[:60],base[:60],x[60:],y[60:],base[60:])
  for h in m.heads.values():self.assertLessEqual(h['selection_gated_mae'],h['selection_physics_mae']+1e-9)
  p,_=m.predict(x[60:],base[60:]);np.testing.assert_allclose(p,base[60:],equal_nan=True)

class ServingTests(unittest.TestCase):
 def nodes(self):
  return [dict(latitude=a,longitude=b,elevation_m=z,timestamp_utc='2024-01-01T00:00Z',temperature_c=15-.0065*z,relative_humidity_pct=60,pressure_hpa=1013.25*((288.15-.0065*z)/288.15)**(9.80665/(287.05*.0065)),wind_speed_mps=2) for a,b,z in [(31.68,76.89,600),(31.75,76.89,1000),(31.71,76.98,1200)]]
 def predict(self,nodes,**kw):
  from ml.spatial_ensemble.physics_serving import predict_snapshot
  return predict_snapshot(nodes,31.71,76.93,'2024-01-01T00:00Z',**kw)
 def test_core_only_and_missing_elevation(self):
  r=self.predict(self.nodes(),query_elevation_m=763);self.assertIsNotNone(r['targets']['pressure_hpa']['prediction']);self.assertIsNone(r['targets']['pm25_ug_m3']['prediction']);self.assertTrue(all(v is None for v in r['targets']['pressure_hpa']['bands'].values()))
  r=self.predict(self.nodes());self.assertIsNone(r['targets']['pressure_hpa']['prediction'])
 def test_offline_empty_invalid_and_suspect_pressure(self):
  for nodes in [[],[None,{}, {'latitude':float('nan')}],self.nodes()[:-1]]:
   r=self.predict(nodes,query_elevation_m=763);self.assertIsNone(r['targets']['pressure_hpa']['prediction'])
  r=self.predict([{**n,'pressure_ok':False} for n in self.nodes()],query_elevation_m=763);self.assertIsNone(r['targets']['pressure_hpa']['prediction'])
  with self.assertRaises(ValueError):self.predict({})
 def test_quarantined_dewpoint_not_used(self):
  from ml.datasets.hourly_noaa import valid_dewpoint
  raw=pd.DataFrame({'dew_point_temperature':[20,900,10],'dew_point_temperature_Quality_Code':['','','BAD']})
  self.assertTrue(valid_dewpoint(raw,pd.Series([False,True,True])).isna().all())
 def test_excluded_pressure_neighbor_count(self):
  a=np.full((2,6),np.nan);a[:,[0,1,2]]=[20,50,1000]
  _,_,_,count=interpolate(a,[100,100],[np.inf,1],100);self.assertEqual(count,1)
 def test_query_truth_never_in_features(self):
  from ml.spatial_ensemble.batched_physics import HourlyNetwork
  nodes=self.nodes();stations=pd.DataFrame([dict(location_id=str(i),physical_site_id=str(i),geography_status='OK',slope_deg=0,elevation_m=n['elevation_m'],latitude=n['latitude'],longitude=n['longitude']) for i,n in enumerate(nodes)])
  qc=pd.DataFrame({'location_id':['0','1','2'],'elevation_ok':True,'pressure_ok':True})
  frame=pd.DataFrame([dict(location_id=str(i),dewpoint_c=np.nan,pm25_ug_m3=np.nan,pm10_ug_m3=np.nan,**n) for i,n in enumerate(nodes)])
  with tempfile.TemporaryDirectory() as tmp:
   net=HourlyNetwork(frame,stations,qc);a,_,_=net.examples({'0'},{'0','1','2'},net.parts['train2024'],Path(tmp)/'a');old=a['x'].copy()
   net.readings[:,0,[0,1,2,5]]=[50,90,500,20]
   b,_,_=net.examples({'0'},{'0','1','2'},net.parts['train2024'],Path(tmp)/'b');np.testing.assert_allclose(old,b['x'],equal_nan=True)
 def test_model_failure_and_ood_return_physics(self):
  class Broken:
   def predict(self,x):raise ValueError('failed')
  m=PhysicsResidualEnsemble();m.heads[0]={'alpha':1,'active':np.array([0]),'lower':np.array([0]),'upper':np.array([1]),'models':{'broken':Broken()},'weights':{'broken':1},'scale':1}
  base=np.tile([20,50,900,np.nan,np.nan,2],(2,1));x=np.zeros((2,47));x[1,0]=10
  out,fall=m.predict(x,base);np.testing.assert_allclose(out,base,equal_nan=True);self.assertTrue(fall.all())

class AuditTests(unittest.TestCase):
 nodes=ServingTests.nodes
 def test_later_audit_revokes_checked_band(self):
  b=EpisodeBands().fit(np.ones((20,6)),np.zeros((20,6)),np.arange(20),np.full((20,6),10))
  b.check(np.ones((10,6)),np.zeros((10,6)),np.arange(30,40),np.full((10,6),10));self.assertIsNotNone(b.interval(0,0,10))
  b.audit(np.full((10,6),100),np.zeros((10,6)),np.arange(40,50),np.full((10,6),10));self.assertIsNone(b.interval(0,0,10))
 def test_legacy_p90_never_exposed(self):
  from ml.spatial_ensemble.model import SpatialEnsemble,snapshot_features
  class Zero:
   def predict(self,x):return np.zeros(len(x))
  nodes=self.nodes();x,_,_=snapshot_features(nodes,31.71,76.93,'2024-01-01T00:00Z');m=SpatialEnsemble(max_distance_km=20)
  m.heads['temperature_c']={'models':{'boosting':Zero(),'neural_net':Zero()},'scale':1,'weights':{'idw':1/3,'boosting':1/3,'neural_net':1/3},'p90':100,'lower':np.full(25,-np.inf),'upper':np.full(25,np.inf),'active':np.where(np.isfinite(x))[0]}
  r=m.predict(nodes,31.71,76.93,'2024-01-01T00:00Z')['targets']['temperature_c'];self.assertEqual(r['status'],'ENSEMBLE');self.assertIsNone(r['absolute_error_p90'])
 def test_invalid_query_height(self):
  from ml.spatial_ensemble.physics_serving import predict_snapshot
  with self.assertRaises(ValueError):predict_snapshot(self.nodes(),31.71,76.93,'2024-01-01T00:00Z',90000)
 def test_serving_model_boundary_failure(self):
  from ml.spatial_ensemble.physics_serving import predict_snapshot
  class Broken:
   def predict(self,x,b):raise ValueError('broken wrapper')
  class Invalid:
   def predict(self,x,b):return np.full((1,6),9999.),np.zeros((1,6),dtype=bool)
  for model in [Broken(),Invalid()]:
   r=predict_snapshot(self.nodes(),31.71,76.93,'2024-01-01T00:00Z',763,model=model)
   self.assertIsNotNone(r['targets']['pressure_hpa']['prediction']);self.assertTrue(r['targets']['pressure_hpa']['residual_fallback']);self.assertTrue(all(v is None for v in r['targets']['pressure_hpa']['bands'].values()))
  class Valid:
   def predict(self,x,b):return b,np.zeros_like(b,dtype=bool)
  class BadBands:
   def interval(self,*args):raise ValueError('corrupt bands')
  r=predict_snapshot(self.nodes(),31.71,76.93,'2024-01-01T00:00Z',763,model=Valid(),bands=BadBands());self.assertIsNotNone(r['targets']['pressure_hpa']['prediction']);self.assertTrue(all(v is None for v in r['targets']['pressure_hpa']['bands'].values()))
 def test_three_hour_persistence_does_not_use_current_or_query_truth(self):
  from ml.spatial_ensemble.batched_physics import HourlyNetwork
  nodes=self.nodes();stations=pd.DataFrame([dict(location_id=str(i),physical_site_id=str(i),geography_status='OK',slope_deg=0,elevation_m=n['elevation_m'],latitude=n['latitude'],longitude=n['longitude']) for i,n in enumerate(nodes)])
  qc=pd.DataFrame({'location_id':['0','1','2'],'elevation_ok':True,'pressure_ok':True});frame=pd.DataFrame([dict(location_id=str(i),dewpoint_c=np.nan,pm25_ug_m3=np.nan,pm10_ug_m3=np.nan,**{**n,'timestamp_utc':t}) for t in ['2024-01-01T00:00Z','2024-01-01T03:00Z'] for i,n in enumerate(nodes)])
  net=HourlyNetwork(frame,stations,qc);ids=np.array([[0,1,0]]);old=net.lagged_physics(ids,{'0','1','2'})
  net.readings[1,:,:]=999;net.readings[0,0,:]=999
  np.testing.assert_allclose(old,net.lagged_physics(ids,{'0','1','2'}),equal_nan=True)

 def test_snapshot_batch_feature_parity(self):
  from ml.spatial_ensemble.batched_physics import HourlyNetwork
  from ml.spatial_ensemble.physics_serving import predict_snapshot
  nodes=self.nodes();query=dict(latitude=31.71,longitude=76.93,elevation_m=763,timestamp_utc='2024-01-01T00:00Z',temperature_c=10,relative_humidity_pct=50,pressure_hpa=900,wind_speed_mps=2)
  allnodes=nodes+[query];stations=pd.DataFrame([dict(location_id=str(i),physical_site_id=str(i),geography_status='OK',slope_deg=0,elevation_m=n['elevation_m'],latitude=n['latitude'],longitude=n['longitude']) for i,n in enumerate(allnodes)])
  qc=pd.DataFrame({'location_id':['0','1','2','3'],'elevation_ok':True,'pressure_ok':True});frame=pd.DataFrame([dict(location_id=str(i),dewpoint_c=np.nan,pm25_ug_m3=np.nan,pm10_ug_m3=np.nan,**n) for i,n in enumerate(allnodes)])
  class Capture:
   def predict(self,x,b):self.x=x.copy();return b,np.ones_like(b,dtype=bool)
  capture=Capture();predict_snapshot(nodes,31.71,76.93,'2024-01-01T00:00Z',763,0,model=capture)
  with tempfile.TemporaryDirectory() as tmp:
   net=HourlyNetwork(frame,stations,qc);a,_,_=net.examples({'3'},{'0','1','2'},net.parts['train2024'],tmp)
   np.testing.assert_allclose(capture.x,a['x'],equal_nan=True,rtol=1e-5,atol=1e-4)

if __name__=='__main__':unittest.main()
