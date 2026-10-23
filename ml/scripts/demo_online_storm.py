"""Run the real online loop on labelled synthetic engineering fixtures only."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from ml.hazard_context.online_demo import create_inputs  # noqa: E402
from ml.scripts.online_storm_risk import run_replay  # noqa: E402


def main():
    """Generate source fixtures locally and replay both independent target heads."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():
        p.error("Choose a new demo folder")
    args.output.mkdir(parents=True)
    nc,labels=create_inputs(args.output/"inputs")
    for target,path in labels.items():
        run_replay([nc],path,args.output/target,target=target,label_role="synthetic_test",feature_delay_hours=.5,
            until="2024-04-12T00:00:00Z")
    print("SYNTHETIC ENGINEERING TEST ONLY — no real hazard accuracy or calibrated probabilities")


if __name__=="__main__":
    main()
