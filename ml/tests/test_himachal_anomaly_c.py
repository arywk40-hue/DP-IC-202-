"""Host C parity is a software receipt, never physical ESP32 validation."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import numpy as np

from ml.himachal.anomaly import load
from ml.himachal.anomaly_codegen import render, verify
from ml.himachal.edge_rules import render as render_rules
from ml.himachal.rules import evaluate
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.tests.test_himachal_features import native_records, packet

ROOT=Path(__file__).resolve().parents[2]
INCLUDE=ROOT/"esp32/himachal_node/include"


class AnomalyCTests(unittest.TestCase):
    def test_committed_header_reproduces_and_stateful_c_parity(self):
        self.assertEqual((INCLUDE/"indra_anomaly.h").read_text(),render(load()))
        self.assertEqual((INCLUDE/"indra_local_rules.h").read_text(),render_rules())
        receipt=verify(INCLUDE/"indra_anomaly.h",load())
        self.assertEqual(receipt["status"],"HOST_PARITY_PASSED")
        self.assertEqual(receipt["rows"],220)
        self.assertLessEqual(receipt["measured_host_state_bytes"],4096)
        self.assertFalse(receipt["heap_in_inference"])
        self.assertEqual(receipt["hardware_execution"],"NOT_TESTED")

    def test_supported_local_indicators_match_python_and_probabilities_unavailable(self):
        source=r'''#include <stdio.h>
#include "indra_local_rules.h"
int main(void){unsigned t,cadence;float x[6];indra_local_history h={0};indra_rule_view v;indra_rule_result r;
while(scanf("%u %u",&t,&cadence)==2){for(int i=0;i<6;++i)if(scanf("%f",x+i)!=1)return 2;
if(!indra_local_push(&h,t,cadence,x,63,1,NAN,&v))return 3;indra_local_rules(&v,1,&r);
for(int i=0;i<3;++i)printf("%.9g ",r.score[i]);for(int i=0;i<3;++i)printf("%.9g ",r.coverage[i]);
printf("%u %u %u",r.abstain_mask,r.local_candidate_mask,r.trained_model_valid_mask);
for(int i=0;i<3;++i)printf(" %.9g",r.probability[i]);puts("");}return 0;}'''
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"rules.c"
            path.write_text(source)
            binary=Path(tmp)/"rules"
            subprocess.run([shutil.which("cc"),"-std=c99","-O2","-Wall","-Wextra","-Werror",str(path),"-I"+str(INCLUDE),"-lm","-o",str(binary)],check=True,capture_output=True)
            for cadence,hours in ((60,2),(3600,8)):
                with self.subTest(cadence=cadence):
                    rows=copy.deepcopy(native_records(cadence=cadence,hours=hours))
                    rows[-1]["measurements"].update(temperature_c=18.,relative_humidity_pct=95.,wind_speed_mps=8.,pm25_ug_m3=20.,pm10_ug_m3=40.)
                    if cadence==60:
                        rows[-1]["measurements"]["pressure_hpa"]-=1.
                    # Quantized telemetry is identical for both producers.
                    for row in rows:
                        row["measurements"]={c:float(np.float32(v)) for c,v in row["measurements"].items()}
                    data="".join(str(int(__import__('pandas').Timestamp(r["timestamp_utc"]).timestamp()))+f" {cadence} "+" ".join(str(r["measurements"][c]) for c in RAW_SENSOR_COLUMNS)+"\n" for r in rows)
                    actual=np.array([[float(v) for v in l.split()] for l in subprocess.run([str(binary)],input=data,text=True,capture_output=True,check=True).stdout.splitlines()])[-1]
                    result=evaluate(packet(rows),profile="hourly_companion" if cadence==3600 else "native_15min")["outputs"]
                    heads=list(result.values())
                    expected=[np.nan if r["score"] is None else r["score"] for r in heads]+[r["coverage"] for r in heads]
                    np.testing.assert_allclose(actual[:6],expected,atol=1e-6,equal_nan=True)
                    self.assertEqual(actual[6],sum((1<<i) for i,r in enumerate(heads) if r["abstain"]))
                    self.assertEqual(actual[7],sum((1<<i) for i,r in enumerate(heads) if r["level"]=="local_warning_candidate"))
                    self.assertEqual(actual[8],0)
                    self.assertTrue(np.isnan(actual[9:]).all())

    def test_physical_defaults_do_not_supply_pins_or_validation(self):
        text=(INCLUDE/"device_config.example.h").read_text()
        self.assertIn("physical_mode=false",text)
        self.assertIn("native_cadence_verified=false",text)
        self.assertIn("clock_uncertainty_seconds=NAN",text)
        self.assertIn("=-1",text)
        receipt=json.loads((INCLUDE/"indra_anomaly.parity.json").read_text())
        self.assertEqual(receipt["hardware_execution"],"NOT_TESTED")
