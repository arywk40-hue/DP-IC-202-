"""Chronological neural training/inference contracts, not field accuracy tests."""
import copy
import json

import numpy as np
import pandas as pd
import pytest
from threadpoolctl import threadpool_limits

from ml.india_mandi.neural import SCHEMA, fit_candidate, load_artifact, predict, scale_fit
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import sha256


def fixture():
    rng=np.random.default_rng(42)
    x=rng.normal(size=(140,66))
    current=np.tile([20.,60.,900.,40.,80.,3.],(140,1))
    residual=np.tile(x[:,0,None],(1,6))*.1
    train=np.arange(140)<80
    val=(np.arange(140)>=80)&(np.arange(140)<110)
    cfg=dict(alpha=.01,batch_size=32,learning_rate=.001,seed=42,max_epochs=3,
             minimum_improvement=.0001,patience=2,residual_blend_candidates=[0,.5,1])
    return x,current,residual,train,val,cfg


def test_training_normalization_and_predictions_do_not_read_future_test_values():
    x,current,residual,train,val,cfg=fixture()
    with threadpool_limits(limits=1):
        a,meta=fit_candidate(x,residual,current,current+residual,train,val,cfg,[8])
        poisoned=copy.deepcopy(x)
        poisoned[~(train|val)]=1e9
        future_residual=residual.copy()
        future_residual[~(train|val)]=-1e9
        b,other=fit_candidate(poisoned,future_residual,current,current+future_residual,train,val,cfg,[8])
    assert meta==other
    for key in a:
        np.testing.assert_array_equal(a[key],b[key])
    np.testing.assert_allclose(a['x_mean'],x[train].mean(axis=0))
    assert a['x_mean'].shape==(66,)
    assert meta['parameter_count']==66*8+8+8*6+6
    with pytest.raises(ValueError,match='Distinct'):
        fit_candidate(x,residual,current,current+residual,train,train,cfg,[8])


@pytest.fixture
def artifact(tmp_path):
    x,current,residual,train,val,cfg=fixture()
    with threadpool_limits(limits=1):
        state,architecture=fit_candidate(x,residual,current,current+residual,train,val,cfg,[8])
    path=tmp_path/'weights.npz'
    np.savez_compressed(path,**state)
    columns=['f'+str(i) for i in range(66)]
    report=dict(schema_version=SCHEMA, artifact=path.name, artifact_sha256=sha256(path),
                targets=RAW_SENSOR_COLUMNS,features=columns,architecture=architecture)
    (tmp_path/'model.json').write_text(json.dumps(report))
    return tmp_path,pd.DataFrame(x,columns=columns),pd.DataFrame(current,columns=RAW_SENSOR_COLUMNS)


def test_saved_neural_model_preserves_missing_history_and_target_order(artifact):
    path,features,current=artifact
    values=predict(path,features,current)
    assert values.shape==(140,6) and np.isfinite(values).all()
    features.loc[0,'f0']=np.nan
    values=predict(path,features,current)
    assert np.isnan(values[0]).all()
    assert np.isfinite(values[1:]).all()
    with pytest.raises(ValueError,match='column order'):
        predict(path,features[features.columns[::-1]],current)
    with pytest.raises(ValueError,match='column order'):
        predict(path,features,current[current.columns[::-1]])


def test_neural_tamper_and_out_of_root_paths_rejected(artifact):
    path,_,_=artifact
    with (path/'weights.npz').open('ab') as handle:
        handle.write(b'tamper')
    with pytest.raises(ValueError,match='hash mismatch'):
        load_artifact(path)
    report=json.loads((path/'model.json').read_text())
    report['artifact']='../outside.npz'
    (path/'model.json').write_text(json.dumps(report))
    with pytest.raises(ValueError,match='hash mismatch'):
        load_artifact(path)


def test_constant_training_features_and_bad_targets():
    state=scale_fit(np.ones((4,66)),np.zeros((4,6)))
    assert np.equal(state['x_std'],1).all()
    assert np.equal(state['y_std'],1).all()
    with pytest.raises(ValueError,match='Complete'):
        scale_fit(np.full((4,66),np.nan),np.zeros((4,6)))
    with pytest.raises(ValueError,match='matching'):
        scale_fit(np.ones((4,66)),np.zeros((4,5)))
