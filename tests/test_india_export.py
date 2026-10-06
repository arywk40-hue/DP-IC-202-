"""Compiled export and raw-preprocessing contracts; no physical device test."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np

from ml.india_sensor.config import load
from ml.india_sensor.features import build
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from tests.test_india_sensor import observations

EXPORT = Path(__file__).resolve().parents[1]/'esp32/india_sensor/export'


@unittest.skipUnless(shutil.which('cc'), 'C compiler unavailable')
class IndiaExportTests(unittest.TestCase):
    def compile_run(self, source, data=''):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'test.c'; path.write_text(source)
            exe=Path(tmp)/'test'
            subprocess.run(['cc','-std=c99','-D_POSIX_C_SOURCE=200809L','-O2','-Wall','-Wextra','-Werror',str(path),'-I'+str(EXPORT),'-lm','-o',str(exe)],check=True,capture_output=True)
            return subprocess.run([str(exe)],input=data,text=True,capture_output=True,check=True).stdout

    def test_raw_hourly_features_missing_gap_and_calendar_parity(self):
        names=json.loads((EXPORT/'export_manifest.json').read_text())['feature_order']
        frame=observations(70).drop(index=32).reset_index(drop=True)
        frame.loc[20,'relative_humidity_pct']=np.nan
        frame.loc[45,'pressure_reference']='sea_level'
        frame.loc[55,'wind_speed_mps']=np.inf
        frame.loc[56,'pm25_ug_m3']=25.; frame.loc[56,'pm10_ug_m3']=50.
        # Deployment telemetry quantization is explicit, before either producer.
        frame[RAW_SENSOR_COLUMNS]=frame[RAW_SENSOR_COLUMNS].astype('float32').astype('float64')
        expected=build(frame,load('configs/india_sensor_offline.json'))[names].to_numpy('float32')
        rows=[]
        for r in frame.to_dict('records'):
            values=' '.join(str(r[c]) for c in RAW_SENSOR_COLUMNS)
            rows.append(f"{int(r['timestamp_utc'].timestamp())} {int(r['pressure_reference']=='station')} {values}")
        source='''#include <stdio.h>
#include <inttypes.h>
#include "indra_india_preprocess.h"
int main(void){indra_hour_history s={0};uint64_t t;int station;float raw[6],x[INDRA_INDIA_FEATURES];
while(scanf("%" SCNu64 " %d",&t,&station)==2){for(int i=0;i<6;++i)if(scanf("%f",&raw[i])!=1)return 2;
if(!indra_hour_push(&s,t,t,raw,station,31,77,1200,x))return 3;
for(int i=0;i<INDRA_INDIA_FEATURES;++i)printf("%.9g ",(double)x[i]);puts("");}return 0;}'''
        actual=np.array([[float(v) for v in line.split()] for line in self.compile_run(source,'\n'.join(rows)+'\n').splitlines()])
        np.testing.assert_array_equal(np.isnan(actual),np.isnan(expected))
        np.testing.assert_allclose(actual,expected,rtol=1e-5,atol=2e-3,equal_nan=True)

    def test_serving_safety_and_payload_time_gates(self):
        names=json.loads((EXPORT/'export_manifest.json').read_text())['feature_order']
        wind=names.index('wind_speed_mps'); temp=names.index('temperature_c');rh=names.index('relative_humidity_pct')
        source='''#include "indra_india_preprocess.h"
int main(void){indra_hour_history s={0};float r[6]={20,60,900,NAN,NAN,3};float x[INDRA_INDIA_FEATURES],a[3],p[3];int f[3];uint8_t status[3];
uint64_t t=1704067200ULL;
if(!indra_hour_push(&s,t,t,r,1,31,77,1200,x))return 1;
if(indra_hour_push(&s,t,t,r,1,31,77,1200,x))return 2;
if(indra_hour_push(&s,t+3600,t+3601,r,1,31,77,1200,x))return 3;
if(indra_hour_push(&s,t+3601,t+3601,r,1,31,77,1200,x))return 4;
if(indra_hour_push(&s,t+3600,t+3600,r,1,91,77,1200,x))return 5;
for(int i=0;i<INDRA_INDIA_FEATURES;++i)x[i]=NAN;
REPLACE
if(indra_india_predict(x,a,p,f,status))return 6;
if(status[0]!=INDRA_INVALID_CORE)return 7;
x[WIND]=3;x[TEMP]=10000;x[RH]=60;
if(!indra_india_predict(x,a,p,f,status))return 8;
for(int j=0;j<3;++j)if(status[j]!=INDRA_OOD||!isnan(a[j])||f[j]!=-1)return 9;
x[TEMP]=20;x[WIND]=INFINITY;
if(indra_india_predict(x,a,p,f,status))return 10;
if(INDRA_DISASTER_OUTPUTS_ENABLED||INDRA_INDIA_HARDWARE_VALIDATED)return 11;
return 0;}'''.replace('REPLACE',f'x[{temp}]=20;x[{rh}]=60;').replace('WIND',str(wind)).replace('TEMP',str(temp)).replace('RH',str(rh))
        self.compile_run(source)
