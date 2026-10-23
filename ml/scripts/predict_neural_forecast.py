"""Run a saved six-channel history neural model; no fitting or live updates."""
import argparse
import json
from pathlib import Path
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from ml.india_mandi.neural import load_artifact, predict_observations  # noqa: E402
from ml.six_sensor_forecast.data import sha256  # noqa: E402


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--model",type=Path,default=ROOT/"ml/models/india_mandi_neural_history_v1/residual_mlp_64_32")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    receipt=args.output.with_suffix(args.output.suffix+'.metadata.json')
    if args.output.exists() or receipt.exists() or args.output.resolve()==args.input.resolve():
        p.error("Choose new output and metadata paths")
    result=predict_observations(pd.read_csv(args.input),args.model)
    _,report=load_artifact(args.model)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result.to_csv(args.output,index=False)
    receipt.write_text(json.dumps(dict(model=str(args.model),model_artifact_sha256=report['artifact_sha256'],
        input_sha256=sha256(args.input),input_provenance='USER_SUPPLIED_UNVERIFIED',rows=len(result),
        status_counts=result.status.value_counts().to_dict(),model_training_evidence=report['evidence'],
        online_learning=False,field_validated=False,hazard_prediction=False),indent=2)+'\n')
    print(result.tail(3).to_string(index=False))
    print('Research forecasts saved:',args.output)


if __name__=='__main__':
    main()
