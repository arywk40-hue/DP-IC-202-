"""Fit/evaluate isolated neural alternatives on the frozen India/Mandi dataset."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from ml.india_mandi.neural import run  # noqa: E402


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",type=Path,default=ROOT/"ml/configs/mandi_neural_forecast_v1.json")
    p.add_argument("--train",action="store_true",help="Fit new candidates once; refuses existing versioned output")
    args=p.parse_args()
    result=run(args.config,train=args.train)
    print("MODELED MANDI NUMERICAL BENCHMARK — no measured field/hazard accuracy")
    for target,choice in result["validation_selected_heads"].items():
        r=result["results"][target]["future_test"]
        print(f"{target}: validation choice {choice}; test MAE={r[choice]['mae']:.4f}; saved student={r['student']['mae']:.4f}")
    print("Report: ml/reports/india_mandi_neural_history_v1/REPORT.md")


if __name__=="__main__":
    main()
