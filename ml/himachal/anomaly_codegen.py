"""Generate bounded C diagnostics and verify compiled stateful Python parity."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np

from ml.himachal.anomaly import CONFIG, Detector, PACKET_STATES, STATES, load
from ml.operational.contracts import canonical_bytes
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS


def render(config):
    digest = hashlib.sha256(canonical_bytes(config)).hexdigest()
    def numbers(values):
        return ",".join(format(v, ".17g") for v in values)
    return r'''/* Generated research diagnostics; no hazard probability or physical validation. */
#ifndef INDRA_HIMACHAL_ANOMALY_H
#define INDRA_HIMACHAL_ANOMALY_H
#include <math.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define INDRA_ANOMALY_VERSION "indra_himachal_anomaly_v1"
#define INDRA_ANOMALY_CONFIG_SHA256 "CONFIG_HASH"
enum {INDRA_UNAVAILABLE=0,INDRA_WARMUP=1,INDRA_WITHIN_BASELINE=2,INDRA_ENVIRONMENTAL_ANOMALY=3,INDRA_SENSOR_FAULT=4};
enum {INDRA_ACCEPTED=0,INDRA_CRC_REJECTED=1,INDRA_TIME_REJECTED=2,INDRA_CLOCK_UNVERIFIED=3};
typedef struct {float ring[6][16],ewma[6];uint8_t count[6],cursor[6];uint32_t last;} indra_anomaly_state;
typedef struct {uint8_t packet,state[6],valid_mask,environmental_mask,fault_mask;float residual[6],scale[6];} indra_anomaly_result;
static inline double indra_median16(const double *values,unsigned n){
 double x[16];for(unsigned i=0;i<n;++i){x[i]=values[i];for(unsigned j=i;j>0&&x[j]<x[j-1];--j){double v=x[j];x[j]=x[j-1];x[j-1]=v;}}
 return n%2?x[n/2]:(x[n/2-1]+x[n/2])/2.;
}
static inline void indra_anomaly_reset(indra_anomaly_state *s){if(s)memset(s,0,sizeof(*s));}
/* No heap or I/O. Caller supplies explicit native cadence and verified clock/QC. */
static inline int indra_anomaly_push(indra_anomaly_state *s,uint32_t stamp,uint32_t cadence,
 const float *raw,int crc_ok,float clock_uncertainty,uint8_t self_test_faults,indra_anomaly_result *r){
 if(!s||!raw||!r||!cadence||3600%cadence||self_test_faults>63)return 0;
 for(int i=0;i<6;++i)if(s->count[i]>16||s->cursor[i]>15)return 0;
 memset(r,0,sizeof(*r));for(int i=0;i<6;++i){r->residual[i]=r->scale[i]=NAN;}
 if(crc_ok!=1)r->packet=INDRA_CRC_REJECTED;
 else if(stamp<TIME_LO||stamp>TIME_HI||stamp%cadence||(s->last&&stamp<=s->last))r->packet=INDRA_TIME_REJECTED;
 else if(!isfinite(clock_uncertainty)||clock_uncertainty<0||clock_uncertainty>CLOCK_LIMIT)r->packet=INDRA_CLOCK_UNVERIFIED;
 if(r->packet!=INDRA_ACCEPTED){if(r->packet==INDRA_CRC_REJECTED){r->fault_mask=63;for(int i=0;i<6;++i)r->state[i]=INDRA_SENSOR_FAULT;}return 1;}
 if(s->last&&stamp-s->last>GAP_INTERVALS*cadence)indra_anomaly_reset(s);
 s->last=stamp;
 const double lo[6]={LOWER},hi[6]={UPPER},floor_scale[6]={FLOORS};
 for(int i=0;i<6;++i){float v=raw[i];
  if((self_test_faults&(1u<<i))||isinf(v)||(isfinite(v)&&(v<lo[i]||v>hi[i]))){r->state[i]=INDRA_SENSOR_FAULT;r->fault_mask|=1u<<i;s->count[i]=s->cursor[i]=0;s->ewma[i]=NAN;continue;}
  if(isnan(v)){s->count[i]=s->cursor[i]=0;s->ewma[i]=NAN;continue;}
  r->valid_mask|=1u<<i;
  if(s->count[i]<WARMUP_SAMPLES)r->state[i]=INDRA_WARMUP;
  else {double values[16],deviation[16];for(unsigned j=0;j<s->count[i];++j)values[j]=s->ring[i][j];
   double median=indra_median16(values,s->count[i]);for(unsigned j=0;j<s->count[i];++j)deviation[j]=fabs(values[j]-median);
   double scale=fmax(floor_scale[i],MAD_FACTOR*indra_median16(deviation,s->count[i]));
   r->residual[i]=(float)(v-median);r->scale[i]=(float)scale;
   if(fabs(v-median)>THRESHOLD_SCALE*scale){r->state[i]=INDRA_ENVIRONMENTAL_ANOMALY;r->environmental_mask|=1u<<i;}
   else r->state[i]=INDRA_WITHIN_BASELINE;
  }
  s->ewma[i]=s->count[i]?(float)(s->ewma[i]+EWMA_ALPHA*((double)v-s->ewma[i])):v;
  s->ring[i][s->cursor[i]]=v;s->cursor[i]=(s->cursor[i]+1)%16;if(s->count[i]<16)++s->count[i];
 }
 return 1;
}
#endif
'''.replace("CONFIG_HASH", digest).replace("TIME_LO", str(config["unix_time_bounds"][0])+"u").replace("TIME_HI", str(config["unix_time_bounds"][1])+"u").replace("CLOCK_LIMIT", str(config["maximum_clock_uncertainty_seconds"])).replace("GAP_INTERVALS", str(config["maximum_gap_intervals"])).replace("LOWER", numbers([PHYSICAL_RANGES[c][0] for c in RAW_SENSOR_COLUMNS])).replace("UPPER", numbers([PHYSICAL_RANGES[c][1] for c in RAW_SENSOR_COLUMNS])).replace("FLOORS", numbers(config["noise_floors"])).replace("WARMUP_SAMPLES", str(config["warmup_valid_samples"])).replace("MAD_FACTOR", format(config["mad_consistency_factor"], ".17g")).replace("THRESHOLD_SCALE", format(config["threshold_scale"], ".17g")).replace("EWMA_ALPHA", format(config["ewma_alpha"], ".17g"))


def corpus():
    rng = np.random.default_rng(20261014)
    rows = []
    stamp = 1767225600
    for i in range(220):
        x = np.array([20,60,900,25,50,0.],dtype="float32")
        if 30<=i<60:
            x[:5] += rng.normal(0,[.2,1,.1,2,3]).astype("float32")
        if 60<=i<75:
            x[0], x[1], x[2], x[5] = 10,95,895,12
        if 80<=i<115:
            x[0] += (i-80)*.05
        if i in (120,121):
            x[3] = np.nan
        if i == 130:
            x[2] = np.inf
        if i == 140:
            x[1] = 101
        if i == 150:
            stamp += 600
        time = stamp if i != 155 else stamp-60
        crc = i != 160
        uncertainty = 80. if i == 165 else 2.
        fault_mask = 32 if i == 170 else 0
        if i == 185:
            x[0] = 21.
        if i == 186:
            x[0] = np.nextafter(np.float32(21),np.float32(np.inf))
        rows.append((time,x.tolist(),crc,uncertainty,fault_mask))
        stamp += 60
    return rows


def verify(header, config):
    compiler = shutil.which("cc")
    if not compiler:
        raise RuntimeError("C compiler required")
    sequence = corpus()
    detector = Detector(config)
    expected = []
    for timestamp, values, crc, uncertainty, fault in sequence:
        r = detector.push(timestamp,values,crc_ok=crc,clock_uncertainty_seconds=uncertainty,self_test_fault_mask=fault)
        expected.append([PACKET_STATES.index(r["packet_state"]),r["valid_mask"],r["environmental_mask"],r["fault_mask"],
            *[STATES.index(s) for s in r["channel_states"]], *r["baseline_counts"],
            *[math_value(v) for v in r["residuals"]], *[math_value(v) for v in r["scales"]],
            *[math_value(v) for v in r["ewma"]]])
    source = r'''#include <stdio.h>
#include "indra_anomaly.h"
static indra_anomaly_state state;
int indra_object_probe(uint32_t t,const float *x,indra_anomaly_result *r){return indra_anomaly_push(&state,t,60,x,1,2,0,r);}
int main(void){unsigned t,crc,fault;float uncertainty,x[6];indra_anomaly_result r;
printf("%zu\n",sizeof(state));
while(scanf("%u %u %f %u",&t,&crc,&uncertainty,&fault)==4){for(int i=0;i<6;++i)if(scanf("%f",x+i)!=1)return 1;
if(!indra_anomaly_push(&state,t,60,x,crc,uncertainty,fault,&r))return 2;
printf("%u %u %u %u",r.packet,r.valid_mask,r.environmental_mask,r.fault_mask);
for(int i=0;i<6;++i)printf(" %u",r.state[i]);for(int i=0;i<6;++i)printf(" %u",state.count[i]);
for(int i=0;i<6;++i)printf(" %.9g",r.residual[i]);for(int i=0;i<6;++i)printf(" %.9g",r.scale[i]);
for(int i=0;i<6;++i)printf(" %.9g",state.count[i]?state.ewma[i]:NAN);puts("");}
if(indra_anomaly_push(NULL,1767225600,60,x,1,0,0,&r)||indra_anomaly_push(&state,1767225600,0,x,1,0,0,&r))return 3;
return 0;}'''
    with tempfile.TemporaryDirectory(prefix="indra-anomaly-") as tmp:
        folder=Path(tmp)
        shutil.copyfile(header,folder/"indra_anomaly.h")
        path=folder/"runner.c"
        path.write_text(source)
        binary=folder/"runner"
        flags=[compiler,"-std=c99","-O2","-Wall","-Wextra","-Werror"]
        subprocess.run([*flags,str(path),"-lm","-o",str(binary)],check=True,capture_output=True)
        obj=folder/"anomaly.o"
        subprocess.run([*flags,"-c",str(path),"-o",str(obj)],check=True,capture_output=True)
        text="".join(f"{t} {int(c)} {u} {f} "+" ".join(f"{v:.9g}" for v in x)+"\n" for t,x,c,u,f in sequence)
        result=subprocess.run([str(binary)],input=text,text=True,capture_output=True,check=True).stdout.splitlines()
        ram=int(result[0])
        actual=np.array([[float(v) for v in line.split()] for line in result[1:]])
        expected=np.array(expected,dtype=float)
        np.testing.assert_array_equal(actual[:,:16],expected[:,:16])
        np.testing.assert_allclose(actual[:,16:],expected[:,16:],rtol=1e-6,atol=2e-6,equal_nan=True)
        error=float(np.nanmax(np.abs(actual[:,16:]-expected[:,16:])))
        object_bytes=obj.stat().st_size
        if ram>config["anomaly_state_budget_bytes"] or object_bytes>config["anomaly_flash_budget_bytes"]:
            raise ValueError("Measured host anomaly object/state exceeds proposed budget")
        size=subprocess.run(["size",str(obj)],capture_output=True,text=True,check=True).stdout
    return dict(schema_version="indra_himachal_anomaly_parity_v1",status="HOST_PARITY_PASSED",rows=len(sequence),
        max_absolute_error=error,absolute_tolerance=2e-6,relative_tolerance=1e-6,
        config_sha256=hashlib.sha256(canonical_bytes(config)).hexdigest(),header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
        measured_host_state_bytes=ram,measured_host_object_file_bytes=object_bytes,host_object_size_command=size,
        budget_scope="Host object includes runner; board section/flash sizes measured by separate cross-build. State excludes call stack scratch; board peak stack/latency remain unmeasured.",
        evidence_kind="SYNTHETIC_SOFTWARE_CONTRACT_ONLY",heap_in_inference=False,hardware_execution="NOT_TESTED")


def math_value(value):
    return np.nan if value is None else value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",type=Path,default=CONFIG)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--verify",action="store_true")
    a=p.parse_args()
    config=load(a.config)
    # Generate/test before replacing an existing verified header.
    with tempfile.TemporaryDirectory() as tmp:
        header=Path(tmp)/"indra_anomaly.h"
        header.write_text(render(config))
        receipt=verify(header,config) if a.verify else None
        a.output.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(header,a.output)
        from ml.himachal.edge_rules import render as render_rules
        local_header=a.output.parent/"indra_local_rules.h"
        local_header.write_text(render_rules())
        if receipt:
            receipt["local_rule_header_sha256"]=hashlib.sha256(local_header.read_bytes()).hexdigest()
    if receipt:
        a.output.with_suffix(".parity.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
        print(json.dumps(receipt,indent=2,allow_nan=False))


if __name__=="__main__":
    main()
