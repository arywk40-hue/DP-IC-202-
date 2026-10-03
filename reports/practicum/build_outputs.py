"""Regenerate tables and standalone figures from final measured JSON only."""
import json,math
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path('reports/practicum')
CORE=['temperature_c','relative_humidity_pct','pressure_hpa','wind_speed_mps']
METHODS=['physics_residual','physics_baseline','idw','nearest_node','node_mean','neighbor_idw_persistence_1h']

def wilson(p,n):
    if p is None or not n:return None
    z=1.96;den=1+z*z/n;c=(p+z*z/(2*n))/den;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0,c-h),min(1,c+h)]

def main():
    report=json.loads(Path('reports/physics_phase/results.json').read_text());ROOT.mkdir(exist_ok=True)
    rows=[];cover=[];text=['# Practicum measured results','', 'NOAA-only completed-hour interpolation. All results below use whole held-out stations and a spatial buffer. December 2024 is untouched for fitting, shrinkage and interval widths. **Archive diagnostic distances often exceed the 20 km serving limit**; these tables do not demonstrate deployable 1–20 km mesh skill. CIs resample whole stations (200 bootstrap repetitions), not individual hours; they do not quantify all spatial/temporal dependence.','', '| Scope / training | Target | Rows | Residual MAE | Physics MAE | IDW MAE | Nearest MAE | Mean MAE | Residual loses to |','|---|---|---:|---:|---:|---:|---:|---:|---|']
    for e in report['experiments']:
        for target in CORE:
            m=e['metrics'][target];scores=m['paired_methods'];ens=scores['physics_residual']['mae'];loss=[k for k in METHODS[1:5] if ens is not None and scores[k]['mae'] is not None and ens>scores[k]['mae']+1e-6]
            for method,s in scores.items():
                ci=s['mae_station_bootstrap_95ci'];rows.append(dict(scope=e['scope'],training=e['configuration'],target=target,method=method,paired_rows=m['paired_rows'],rows=s['rows'],stations=s.get('stations',0),mae=s['mae'],rmse=s['rmse'],mae_ci_lower=ci[0] if ci else None,mae_ci_upper=ci[1] if ci else None,residual_loses_to_method=method in loss,truth_rows=m['truth_rows'],available_rows=m['availability'][method]))
            s=m['lagged_physics_persistence_3h_available'];ci=s['mae_station_bootstrap_95ci']
            rows.append(dict(scope=e['scope'],training=e['configuration'],target=target,method='neighbor_physics_persistence_3h_SEPARATE_SUBSET',paired_rows=None,rows=s['rows'],stations=s.get('stations',0),mae=s['mae'],rmse=s['rmse'],mae_ci_lower=ci[0] if ci else None,mae_ci_upper=ci[1] if ci else None,residual_loses_to_method=None,truth_rows=m['truth_rows'],available_rows=s['rows']))
            fmt=lambda v:'—' if v is None else f'{v:.3f}'
            text.append('| '+e['scope']+' / '+e['configuration']+' | '+target+' | '+str(m['paired_rows'])+' | '+' | '.join(fmt(scores[k]['mae']) for k in METHODS[:5])+' | '+(', '.join(loss) or 'none')+' |')
        for c in e['untouched_test_coverage']:
            cover.append(dict(scope=e['scope'],training=e['configuration'],**c,episode_coverage_95ci=wilson(c['episode_coverage'],c['episodes'])))
    pd.DataFrame(rows).to_csv(ROOT/'results.csv',index=False);pd.DataFrame(cover).to_csv(ROOT/'coverage_by_distance.csv',index=False)
    text+=['','RMSE, station-bootstrap MAE intervals, sample counts and unavailable persistence are in [results.csv](results.csv). Per-climate/elevation metrics and station IDs are in [results.json](../physics_phase/results.json). PM heads have no training observations and remain unavailable.','', '## Interpretation and limitations','', '- Pressure physics uses 0 m EGM96 reference pressure, log-space IDW and query-height restoration. Station/QC filtering changes the population; compare only the paired rows here, not the previous unfiltered pressure score.', '- T uses a fixed 6.5 K/km lapse. Inversions, valleys and seasonal lapse changes remain unresolved. RH uses dewpoint interpolation followed by query-temperature reconstruction; raw RH IDW can win. Wind retains IDW as its physics baseline.', '- The residual shrinkage is non-inferior only on July–August selection aggregate MAE. December losses are listed explicitly. No future/pointwise “never worse” claim.', '- Global 72-hour UTC blocks keep all stations in the same temporal role. They approximate weather episodes; storms can cross block boundaries. Train: 2023 plus Jan–Jun 2024; select: Jul–Aug; calibrate: Sep–Oct; independent check: Nov; final audit: Dec. Episode **start** assigns the fold, so an episode can cross a month/year boundary.', '- The block-max conformal width targets simultaneous coverage of all observed rows in each target/distance bin per episode. Calibration/check weather may differ from test weather; finite-episode evidence is weak and widths can be large. Both point and episode coverage, widths and approximate binomial episode intervals are in [coverage_by_distance.csv](coverage_by_distance.csv). These intervals assume independent episodes and are descriptive only.', '- A failed November check or December audit revokes interval authorization without retuning widths on December. Sparse bins have no interval. Archived coverages remain visible as diagnostics, including failures. Geometry refusal and OOD/failure fallback never expose a checked serving band in the demo.', '- All 375 source-station files are screened; exact coordinate aliases and suspect P/elevation channels are excluded. Not every station reports every hour or pressure. No missing hours are manufactured. Hourly means are not instantaneous sensor truth, and archive publication latency is unverified.', '- ERA5-Land was absent; no background contribution was measured. [Exact downloads](../physics_phase/ERA5_DOWNLOAD.md). NWIC/Kala Amb remain quarantined. These runs do not train PM heads or establish the national versus Himalaya-specialist Mandi comparison anew.', '- The new full ensemble is a Python server experiment. No deployable model artifact, ESP32 distillation, device memory/latency/energy or field outage test is established.','', '## Demonstration','', 'From the repository root, run `python -m reports.practicum.demo`. The synthetic physics-only demo shows an in-hull prediction, far-query refusal, one-node-offline hull refusal, missing-elevation pressure refusal and suspect-pressure quarantine. Missing PM remains unavailable; no invented confidence band is displayed. [Recorded demo](demo_output.json).','', 'Reproduce: `python -m ml.datasets.hourly_noaa --acquire-year 2023` (unsigned public NOAA download), `python -m ml.datasets.hourly_noaa`, `python -m ml.spatial_ensemble.evaluate_physics`, `python -m ml.spatial_ensemble.finalize_physics`, `python -m reports.practicum.build_outputs`. Use an isolated Python 3.11.8 environment with `requirements-physics.txt` (the root pins differ from this tested phase) and the same raw-file hashes. The capped/full-test comparison uses identical final test rows.','', '## Figures','', '![Core-target MAE; losses remain visible](mae_comparison.png)','', '![Calibration coverage by distance](coverage_by_distance.png)','']
    (ROOT/'RESULTS.md').write_text('\n'.join(text))
    df=pd.DataFrame(rows);selected=[('national20km','all_hours2023_2024'),('himalaya20km','all_hours2023_2024')]
    fig,axes=plt.subplots(2,4,figsize=(16,8))
    colors=['#516da6','#36867b','#a5a5a5','#ca9a5b','#b887a8']
    for r,(scope,training) in enumerate(selected):
        for j,target in enumerate(CORE):
            ax=axes[r,j];q=df[(df.scope==scope)&(df.training==training)&(df.target==target)].set_index('method').reindex(METHODS[:5]);v=q.mae.to_numpy(float);ci=q[['mae_ci_lower','mae_ci_upper']].to_numpy(float)
            error=np.stack([np.maximum(0,v-ci[:,0]),np.maximum(0,ci[:,1]-v)])
            ax.bar(np.arange(5),v,color=colors,yerr=error,capsize=2);ax.set_xticks(np.arange(5),['Residual','Physics','IDW','Nearest','Mean'],rotation=45,ha='right');ax.set_title(scope+'\n'+target);ax.set_ylabel('MAE (target units)');ax.grid(axis='y',alpha=.2)
    fig.suptitle('Untouched December: paired rows, station-bootstrap 95% intervals; archive distances');fig.tight_layout();fig.savefig(ROOT/'mae_comparison.png',dpi=180);fig.savefig(ROOT/'mae_comparison.pdf');plt.close(fig)
    bins=['0–1','1–5','5–20','20–50','50–100','100–250','250+'];fig,axes=plt.subplots(3,4,figsize=(16,12))
    coverage_selected=[selected[0],('national5km','all_hours2023_2024'),selected[1]]
    for r,(scope,training) in enumerate(coverage_selected):
        for j,target in enumerate(CORE):
            ax=axes[r,j]
            for level,color in [(.8,'#36867b'),(.9,'#516da6')]:
                cs=[next(c for c in cover if c['scope']==scope and c['training']==training and c['head']==target and c['distance_bin_km']==b and c['nominal']==level) for b in bins]
                p=[np.nan if c['point_coverage'] is None else c['point_coverage'] for c in cs];ep=[np.nan if c['episode_coverage'] is None else c['episode_coverage'] for c in cs]
                ax.plot(np.arange(7),p,':',color=color,label=f'{int(level*100)}% point');ax.plot(np.arange(7),ep,'o-',color=color,label=f'{int(level*100)}% episode');ax.axhline(level,color=color,alpha=.3)
                for k,c in enumerate(cs):
                    if c['episode_coverage'] is not None and not c['serving_authorized_after_test_audit']:ax.scatter(k,c['episode_coverage'],marker='x',s=70,color='red',zorder=5)
            ax.set_ylim(0,1.05);ax.set_xticks(np.arange(7),bins,rotation=45);ax.set_title(scope+'\n'+target);ax.set_ylabel('Observed coverage');ax.set_xlabel('Nearest valid contributor (km)');ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8);fig.suptitle('Nominal levels are diagnostic: red × = unauthorized after checks/audit; missing = insufficient evidence');fig.tight_layout();fig.savefig(ROOT/'coverage_by_distance.png',dpi=180);fig.savefig(ROOT/'coverage_by_distance.pdf');plt.close(fig)
if __name__=='__main__':main()
