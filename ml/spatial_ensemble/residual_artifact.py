"""Bounded JSON export/inference for this server ensemble; no executable loading.
Private sklearn tree representation is version-dependent: export parity is checked.
"""
import json
from pathlib import Path
import numpy as np
from ml.spatial_ensemble.physics_residual import PhysicsResidualEnsemble
from ml.spatial_ensemble.episodes import DISTANCE_EDGES

FORMAT='indra_residual_json_v1'

def export(model,path,bands=None,corridor_limits=None):
    heads={}
    for i,h in model.heads.items():
        record={k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in h.items() if k!='models'};record['models']={}
        for kind,m in h['models'].items():
            if kind=='boosting':
                trees=[]
                for stage in m._predictors:
                    n=stage[0].nodes
                    tree={k:n[k].tolist() for k in ['value','feature_idx','num_threshold','missing_go_to_left','left','right','is_leaf']}
                    # HGB uses +inf for a missing-only split; JSON cannot encode it.
                    tree['threshold_positive_infinity']=np.isposinf(n['num_threshold']).tolist()
                    tree['num_threshold']=np.where(np.isposinf(n['num_threshold']),0,n['num_threshold']).tolist()
                    trees.append(tree)
                record['models'][kind]={'base':float(m._baseline_prediction[0,0]),'trees':trees}
            else:
                imputer,scaler,nn=m.steps[0][1],m.steps[1][1],m.steps[2][1]
                record['models'][kind]={'impute':imputer.statistics_.tolist(),'mean':scaler.mean_.tolist(),'std':scaler.scale_.tolist(),'coefs':[c.tolist() for c in nn.coefs_],'intercepts':[c.tolist() for c in nn.intercepts_],'activation':nn.activation,'output_activation':nn.out_activation_}
        heads[str(i)]=record
    payload={'format':FORMAT,'neighbor_count':model.neighbor_count,'feature_width':47,'heads':heads,'bands':bands.report() if bands is not None else [],'corridor_limits':corridor_limits,'warning':'Archive-only checked uncertainty; server JSON artifact, not ESP32 validated'}
    Path(path).write_text(json.dumps(payload,allow_nan=False)+'\n')

class Tree:
    def __init__(self,record,width):
        self.base=float(record['base']);self.trees=[]
        if not np.isfinite(self.base) or len(record['trees'])>200:raise ValueError('Invalid tree count/base')
        for tree in record['trees']:
            n=len(tree['value'])
            if not 1<=n<=255 or any(len(v)!=n for v in tree.values()):raise ValueError('Invalid tree size')
            t={k:np.asarray(v,dtype=float if k in ['value','num_threshold'] else int) for k,v in tree.items()}
            if not np.isfinite(t['value']).all() or not np.isfinite(t['num_threshold']).all():raise ValueError('Nonfinite tree')
            t['num_threshold']=np.where(t['threshold_positive_infinity'].astype(bool),np.inf,t['num_threshold'])
            for j in range(n):
                if t['is_leaf'][j]:continue
                if not 0<=t['feature_idx'][j]<width or not j<t['left'][j]<n or not j<t['right'][j]<n:raise ValueError('Invalid/cyclic tree edges')
            self.trees.append(t)
    def predict(self,x):
        out=np.full(len(x),self.base)
        for t in self.trees:
            idx=np.zeros(len(x),dtype=int)
            for _ in range(len(t['value'])):
                rows=np.where(~t['is_leaf'][idx].astype(bool))[0]
                if not len(rows):break
                ni=idx[rows];v=x[rows,t['feature_idx'][ni]];left=np.where(np.isnan(v),t['missing_go_to_left'][ni].astype(bool),v<=t['num_threshold'][ni]);idx[rows]=np.where(left,t['left'][ni],t['right'][ni])
            out+=t['value'][idx]
        return out

class Neural:
    def __init__(self,r,width):
        self.r=r
        if r['activation']!='relu' or r['output_activation']!='identity':raise ValueError('Unsupported NN activation')
        self.impute=np.asarray(r['impute'],float);self.mean=np.asarray(r['mean'],float);self.std=np.asarray(r['std'],float)
        self.coefs=[np.asarray(v,float) for v in r['coefs']];self.intercepts=[np.asarray(v,float) for v in r['intercepts']]
        if any(v.shape!=(width,) for v in [self.impute,self.mean,self.std]) or (self.std<=0).any():raise ValueError('Invalid scaler')
        if len(self.coefs)!=2 or len(self.intercepts)!=2 or self.coefs[0].shape!=(width,12) or self.coefs[1].shape!=(12,1) or self.intercepts[0].shape!=(12,) or self.intercepts[1].shape!=(1,):raise ValueError('Invalid NN shape')
        if not all(np.isfinite(v).all() for v in [self.impute,self.mean,self.std,*self.coefs,*self.intercepts]):raise ValueError('Nonfinite NN')
    def predict(self,x):
        a=(np.where(np.isnan(x),self.impute,x)-self.mean)/self.std
        return (np.maximum(0,a@self.coefs[0]+self.intercepts[0])@self.coefs[1]+self.intercepts[1])[:,0]

class Bands:
    def __init__(self,records,corridor_limits):self.records=records;self.corridor_limits=corridor_limits
    def interval(self,prediction,head,distance,level=.9):
        from ml.spatial_ensemble.episodes import DISTANCE_NAMES
        b=int(np.searchsorted(DISTANCE_EDGES,distance,side='right')-1)
        if not 0<=b<len(DISTANCE_NAMES):return None
        for r in self.records:
            proof=r.get('independent_check') or {};audit=r.get('later_audit') or {}
            verified=r.get('calibration_episodes',0)>=10 and proof.get('episodes',0)>=5 and audit.get('episodes',0)>=5 and (proof.get('episode_coverage') or 0)>=level and (audit.get('episode_coverage') or 0)>=level
            if r['head_index']==head and r['nominal']==level and r['distance_bin_km']==DISTANCE_NAMES[b] and r['checked'] and verified:
                width=r['half_width']
                if width is not None and np.isfinite(width) and width>=0:return [float(prediction-width),float(prediction+width)]
        return None

def load(path):
    path=Path(path)
    if path.stat().st_size>20_000_000:raise ValueError('Model file too large')
    r=json.loads(path.read_text())
    if r['format']!=FORMAT or r['feature_width']!=47 or r['neighbor_count'] not in [2,3,4,5] or len(r['heads'])>6:raise ValueError('Invalid model contract')
    m=PhysicsResidualEnsemble(neighbor_count=r['neighbor_count'])
    for key,h in r['heads'].items():
        i=int(key)
        if not 0<=i<6:raise ValueError('Invalid head')
        active=np.asarray(h['active'],int)
        if not len(active) or len(active)>47 or len(set(active))!=len(active) or (active<0).any() or (active>=47).any():raise ValueError('Invalid features')
        h['active']=active;h['lower']=np.asarray(h['lower'],float);h['upper']=np.asarray(h['upper'],float)
        if h['lower'].shape!=active.shape or h['upper'].shape!=active.shape or not np.isfinite(h['lower']).all() or not np.isfinite(h['upper']).all() or (h['lower']>h['upper']).any():raise ValueError('Invalid envelope')
        if not 0<=h['alpha']<=1 or not np.isfinite(h['scale']) or h['scale']<=0:raise ValueError('Invalid residual scale')
        if set(h['models'])!=set(h['weights']) or not h['models'] or any(not np.isfinite(w) or w<0 for w in h['weights'].values()) or abs(sum(h['weights'].values())-1)>1e-6:raise ValueError('Invalid model weights')
        models={}
        for kind,record in h['models'].items():
            if kind not in ['boosting','small_nn']:raise ValueError('Unknown model')
            models[kind]=Tree(record,len(active)) if kind=='boosting' else Neural(record,len(active))
        h['models']=models;m.heads[i]=h
    return m,Bands(r['bands'],r['corridor_limits'])
