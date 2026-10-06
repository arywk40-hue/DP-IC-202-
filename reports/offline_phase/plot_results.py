"""Reproduce diagnostic figures from frozen report values; no model selection."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root=Path(__file__).resolve().parent
    data=json.loads((root/'results.json').read_text())
    target='near_saturation_measurement_at_6h'
    fig, axes=plt.subplots(1,4,figsize=(13,3.8),sharey=True)
    for ax,(scope,experiment) in zip(axes,data['experiment'].items()):
        methods=experiment['targets'][target]['strategies']
        for i,method in enumerate('ABCD'):
            r=methods[method]['overall']; value=r['brier']; ci=r.get('brier_station_bootstrap_95ci')
            ax.bar(i,value,width=.6,color=['#4c78a8','#f58518','#54a24b','#e45756'][i])
            if ci:
                # Quantiles need not bracket the original ratio statistic.
                ax.plot([i,i],ci,color='black',linewidth=1.2)
            ax.text(i,value+.004,f"{value:.4f}",ha='center',fontsize=8)
        ax.set_xticks(np.arange(4),list('ABCD'));ax.set_title(scope.replace('_','\n'),fontsize=10)
        ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Brier (lower better)')
    fig.suptitle('Real NOAA +6h RH ≥95% diagnostics; station-bootstrap 95% intervals')
    fig.text(.5,.01,'Within-protocol comparisons only; different held-out sites; Himalaya-only scores uncalibrated',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.07,1,.92]);fig.savefig(root/'rh_brier_comparison.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(5.5,4.5))
    for method in 'ABCD':
        bins=data['experiment']['national']['targets'][target]['strategies'][method]['overall']['reliability_bins']
        ax.plot([b['mean_probability'] for b in bins],[b['observed_fraction'] for b in bins],marker='o',label=method)
    ax.plot([0,1],[0,1],'k--',linewidth=1);ax.set(xlabel='Archive calibrated probability',ylabel='Observed positive fraction',title='National RH ≥95% test reliability')
    ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(root/'rh_reliability.png',dpi=160);plt.close(fig)


if __name__=='__main__':
    main()
