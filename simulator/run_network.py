"""Run seeded actual-runtime transport stress; synthetic engineering only."""
import argparse
import json
from pathlib import Path
import platform
import time

import numpy as np

from ml.himachal.nodes import CONFIG, load_config
from ml.himachal.radio import FRAME_BYTES, airtime, load_profile
from simulator.network import NetworkSimulation, SCENARIOS


def run(config,node_counts,scenarios,seeds,*,output,rounds=None,topology=None):
    if type(seeds) is not int or not 1<=seeds<=100 or not node_counts or not scenarios:
        raise ValueError("Explicit bounded simulation counts required")
    results=[]
    started=time.perf_counter()
    for count in node_counts:
        for scenario in scenarios:
            cases=[]
            for seed in range(seeds):
                cases.append(NetworkSimulation(count,scenario,seed,config,rounds=rounds,topology=topology).run())
            positive=sum(c["positive_synthetic_queries"] for c in cases)
            negative=sum(c["negative_synthetic_queries"] for c in cases)
            false=sum(c["false_corrob_episodes"] for c in cases)
            misses=sum(c["missed_positive_queries"] for c in cases)
            result=dict(nodes=count,scenario=scenario,seeds=seeds,rounds_per_seed=rounds or config["simulation"]["rounds"],
                topology=topology or config["simulation"]["topology"],positive_synthetic_queries=positive,negative_synthetic_queries=negative,
                false_corrob_episodes=false,missed_positive_queries=misses,
                false_corrob_fraction=false/negative if negative else None,missed_positive_fraction=misses/positive if positive else None,
                p95_of_seed_all_query_latency_p95_s=float(np.quantile([c["all_query_latency_p95_s"] for c in cases],.95)),
                p95_seed_cpu_seconds=float(np.quantile([c["cpu_seconds"] for c in cases],.95)),
                maximum_python_tracemalloc_peak_bytes=max(c["python_tracemalloc_peak_bytes"] for c in cases),
                frame_count=sum(c["scheduler"]["frames"] for c in cases),per_seed=cases)
            results.append(result)
            print(json.dumps({k:v for k,v in result.items() if k!="per_seed"}),flush=True)
    receipt=dict(schema_version="indra_himachal_network_scale_v1",evidence_kind="SYNTHETIC_NETWORK_ENGINEERING_ONLY",
        frame_bytes=FRAME_BYTES,airtime_per_frame_s=airtime(profile=load_profile(config["radio_profile"])),
        runtime=dict(python=platform.python_version(),numpy=np.__version__),wall_seconds=time.perf_counter()-started,
        configuration=config,results=results,
        assumptions=["All nodes are synthetic physical-role protocol fixtures, not empirical observations",
            "Injected local flags test transport; no learned hazard accuracy is measured",
            "One local-indication query per minute across the simulated network",
            "Direct raw-LoRa star via offline pairwise-key coordinator; no multi-hop relay path in this scenario",
            "Three actual radio warm-up minutes before measurement; warm-up airtime still counts toward duty",
            "Same-channel overlaps and receiver half-duplex drop packets; no terrain/capture/inter-SF model",
            "Independent link loss, clock uncertainty, offline actors and shared self-test/hidden faults are explicit synthetic fixtures",
            "Unresolved client rounds run their actual local 30-second timer; zero false corroborations under saturation is not success",
            "Tracemalloc covers Python planning/runtime allocations, including initial lazy imports; it is not total process RSS"],
        thresholds_tuned_on_stress_seeds=False,field_accuracy="NOT_EVALUATED",physical_rf="NOT_TESTED",rf_enabled=False,public_dispatch=False)
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",type=Path,default=CONFIG)
    p.add_argument("--nodes",type=int,nargs="+",default=[3,10,50,200])
    p.add_argument("--scenarios",nargs="+",choices=SCENARIOS,default=list(SCENARIOS))
    p.add_argument("--seeds",type=int,default=30)
    p.add_argument("--rounds",type=int)
    p.add_argument("--topology",choices=["dense","multi_valley"])
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    run(load_config(a.config),a.nodes,a.scenarios,a.seeds,output=a.output,rounds=a.rounds,topology=a.topology)


if __name__=="__main__":
    main()
