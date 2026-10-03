"""Residual ensemble over physics; selection-only non-inferiority safety gate.
No guarantee on future/test error. OOD/model failure falls back to physics.
"""
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS,PHYSICAL_RANGES


class PhysicsResidualEnsemble:
    def __init__(self,seed=42):self.seed=seed;self.heads={}

    def fit(self,x,y,base,sx,sy,sbase):
        self.heads={}
        for i,name in enumerate(RAW_SENSOR_COLUMNS):
            valid=np.isfinite(y[:,i])&np.isfinite(base[:,i]);sv=np.isfinite(sy[:,i])&np.isfinite(sbase[:,i])
            if valid.sum()<30 or sv.sum()<30:continue
            candidates=[j for j in range(x.shape[1]) if j not in [3,4,9,10,15,16] or i in [3,4]]
            active=np.array([j for j in candidates if np.isfinite(x[valid,j]).mean()>.5])
            scale=max(float(np.std((y-base)[valid,i])),.01);r=(y-base)[valid,i]/scale
            models={'boosting':HistGradientBoostingRegressor(max_iter=70,max_leaf_nodes=15,l2_regularization=1,random_state=self.seed,early_stopping=False),
                'small_nn':make_pipeline(SimpleImputer(),StandardScaler(),MLPRegressor(hidden_layer_sizes=(12,),batch_size=1024,max_iter=25,random_state=self.seed,tol=1e-3,n_iter_no_change=5,early_stopping=False))}
            residuals={};failed={}
            for kind,model in list(models.items()):
                try:
                    model.fit(x[valid][:,active],r);p=model.predict(sx[sv][:,active])*scale
                    if not np.isfinite(p).all():raise ValueError('Nonfinite residual')
                    residuals[kind]=p
                except Exception as exc:failed[kind]=type(exc).__name__;del models[kind]
            if not residuals:continue
            errs={k:float(np.abs(sbase[sv,i]+v-sy[sv,i]).mean()) for k,v in residuals.items()};w={k:1/max(v,1e-6) for k,v in errs.items()};total=sum(w.values());w={k:v/total for k,v in w.items()}
            correction=sum(w[k]*v for k,v in residuals.items());lo,hi=PHYSICAL_RANGES[name]
            lower=np.nanmin(x[valid][:,active],axis=0);upper=np.nanmax(x[valid][:,active],axis=0)
            checked=(active<21)|(active>=25);lower_check=(active<6)|((active>=18)&(active<21))|(active>=25)
            aselect=sx[sv][:,active]
            safe=np.isfinite(aselect).all(axis=1)&~np.any(aselect[:,checked]>upper[checked],axis=1)&~np.any(aselect[:,lower_check]<lower[lower_check],axis=1)
            correction=np.where(safe,correction,0.)
            baseline_error=float(np.abs(sbase[sv,i]-sy[sv,i]).mean());alpha=0.;best=baseline_error
            for a in [.25,.5,.75,1.]:
                err=float(np.abs(np.clip(sbase[sv,i]+a*correction,lo,hi)-sy[sv,i]).mean())
                if err<best-1e-10:alpha,best=a,err
            self.heads[i]={'models':models,'scale':scale,'weights':w,'alpha':alpha,'active':active,'lower':lower,'upper':upper,'selection_physics_mae':baseline_error,'selection_gated_mae':best,'failures':failed}
        return self

    def predict(self,x,base):
        out=base.copy();fallback=np.ones_like(base,dtype=bool)
        for i,h in self.heads.items():
            if h['alpha']==0:continue
            active=h['active'];a=x[:,active];good=np.isfinite(base[:,i])&np.isfinite(a).all(axis=1)
            # Envelope ignores lower distance/spread (closer/less disagreement)
            # and bounded time cycles. It is a guard, not OOD probability.
            checked=(active<21)|(active>=25);lower_check=(active<6)|((active>=18)&(active<21))|(active>=25)
            good &= ~np.any((a[:,checked]>h['upper'][checked]),axis=1)
            good &= ~np.any((a[:,lower_check]<h['lower'][lower_check]),axis=1)
            if not good.any():continue
            try:
                residual=sum(h['weights'][k]*m.predict(a[good])*h['scale'] for k,m in h['models'].items())
                p=np.clip(base[good,i]+h['alpha']*residual,*PHYSICAL_RANGES[RAW_SENSOR_COLUMNS[i]])
                finite=np.isfinite(p);idx=np.where(good)[0][finite];out[idx,i]=p[finite];fallback[idx,i]=False
            except Exception:pass
        return out,fallback

    def report(self):
        return {RAW_SENSOR_COLUMNS[i]:{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in h.items() if k not in ['models','lower','upper']} for i,h in self.heads.items()}
