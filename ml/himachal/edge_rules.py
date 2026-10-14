"""C rendering of the same versioned rule defaults; finite view or abstention.

The collector supports native-minute cloudburst pattern and hourly three-target
companion mode. It never invents six hours of pressure from a 75-minute buffer.
"""
import hashlib
import json

from ml.himachal.rules import CONFIG
from ml.operational.contracts import canonical_bytes
from ml.himachal.features import load_config


def render():
    config=json.loads(CONFIG.read_text())
    r,s=config["rain"],config["snowstorm"]
    feature_config=load_config()
    pm=feature_config["hourly_washout"]
    replacements={"RULE_HASH_VALUE":hashlib.sha256(canonical_bytes(config)).hexdigest(),
                  "FEATURE_HASH_VALUE":hashlib.sha256(canonical_bytes(feature_config)).hexdigest(),
                  "WIND_DELTA":feature_config["wind_increase_15min_mps"],"WIND_MIN":feature_config["wind_current_minimum_mps"],
                  "PM25_BASE":pm["minimum_baselines_ug_m3"][0],"PM10_BASE":pm["minimum_baselines_ug_m3"][1],
                  "PM25_DROP":pm["minimum_declines_ug_m3"][0],"PM10_DROP":pm["minimum_declines_ug_m3"][1],"PM_FRACTION":pm["relative_decline"],
                  "RAIN_RH":r["rh_min_pct"],"RAIN_DP":r["pressure_delta_6h_max_hpa"],"RAIN_T":r["temperature_min_exclusive_c"],
                  "SNOW_RH":s["rh_min_pct"],"SNOW_T":s["temperature_max_c"],"SNOW_DP":s["pressure_delta_6h_max_hpa"],"SNOW_W":s["wind_min_mps"],
                  "WATCH":config["watch_threshold"],"CANDIDATE":config["warning_candidate_threshold"],
                  "COVERAGE":config["minimum_warning_available_weight"],"DYNAMIC":config["minimum_warning_dynamic_matches"]}
    # Field order: RH, pressure change, temperature change, calibrated wind
    # increase, PM proxy, Indian month, reviewed terrain. Read weights/thresholds
    # from the same config rather than independently copied numerical constants.
    for name, key in (("NATIVE","cloudburst_native"),("HOURLY","cloudburst_hourly")):
        items=config[key]["criteria"]
        replacements[name+"_WEIGHTS"]=",".join(format(x["weight"],".17g") for x in items)
        replacements[name+"_RH"]=items[0]["threshold"]
        replacements[name+"_DP"]=items[1]["threshold"]
        replacements[name+"_DT"]=items[2]["threshold"]
    source=r'''/* Generated current-condition risk only; no empirical event model. */
#ifndef INDRA_HIMACHAL_LOCAL_RULES_H
#define INDRA_HIMACHAL_LOCAL_RULES_H
#include <math.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#define INDRA_LOCAL_RULE_HASH "RULE_HASH_VALUE"
#define INDRA_LOCAL_FEATURE_HASH "FEATURE_HASH_VALUE"
typedef struct {float raw[6],dp6,dp,dt,wind_increase,wash_hour,wash_native,month,terrain;int hourly;} indra_rule_view;
typedef struct {float score[3],coverage[3],probability[3];uint8_t abstain_mask,local_candidate_mask,trained_model_valid_mask;} indra_rule_result;
/* Pure deterministic indicator. Caller must preserve source/reference checks. */
static inline void indra_local_rules(const indra_rule_view *v,int station_source,indra_rule_result *r){
 memset(r,0,sizeof(*r));for(int j=0;j<3;++j)r->score[j]=r->probability[j]=NAN;
 if(!station_source){r->abstain_mask=7;return;}
 float a[4]={v->raw[1],v->dp6,v->raw[0],v->wash_hour};int present=0;
 for(int i=0;i<4;++i)present+=isfinite(a[i]);r->coverage[0]=present/4.f;
 if(present<4)r->abstain_mask|=1;else{r->score[0]=(a[0]>=RAIN_RH&&a[1]<=RAIN_DP&&a[2]>RAIN_T&&a[3]==1)?1.f:0.f;if(r->score[0])r->local_candidate_mask|=1;}
 float b[5]={v->raw[0],v->raw[1],v->raw[5],v->dp6,v->wash_hour};present=0;
 for(int i=0;i<5;++i)present+=isfinite(b[i]);r->coverage[1]=present/5.f;
 if(present<5)r->abstain_mask|=2;else{r->score[1]=(b[0]<=SNOW_T&&b[1]>=SNOW_RH&&b[2]>=SNOW_W&&b[3]<=SNOW_DP&&b[4]==1)?1.f:0.f;if(r->score[1])r->local_candidate_mask|=2;}
 const double native_weights[7]={NATIVE_WEIGHTS},hourly_weights[7]={HOURLY_WEIGHTS};
 const double *weights=v->hourly?hourly_weights:native_weights;
 float values[7]={v->raw[1],v->dp,v->dt,v->wind_increase,v->hourly?v->wash_hour:v->wash_native,v->month,v->terrain};
 int matched[7]={values[0]>=(v->hourly?HOURLY_RH:NATIVE_RH),values[1]<=(v->hourly?HOURLY_DP:NATIVE_DP),values[2]<=(v->hourly?HOURLY_DT:NATIVE_DT),values[3]==1,values[4]==1,values[5]==1,values[6]==1};
 double score=0,available=0;unsigned dynamic=0,dynamic_available=0;
 for(int i=0;i<7;++i)if(isfinite(values[i])){available+=weights[i];if(i<5)++dynamic_available;if(matched[i]){score+=weights[i];if(i<5)++dynamic;}}
 r->coverage[2]=(float)available;if(available>0)r->score[2]=(float)score;
 if(available+1e-9<COVERAGE||dynamic_available<3)r->abstain_mask|=4;
 else if(score+1e-9>=CANDIDATE&&dynamic>=DYNAMIC)r->local_candidate_mask|=4;
 /* No quorum/public dispatch or calibrated probability is generated here. */
}
typedef struct {uint32_t stamp[76];float raw[76][6];unsigned count;uint32_t last,cadence;} indra_local_history;
static inline void indra_local_reset(indra_local_history *s){memset(s,0,sizeof(*s));}
static inline float indra_local_at(const indra_local_history *s,int channel,uint32_t age){
 if(!s->count||!s->cadence||age%s->cadence)return NAN;
 unsigned back=age/s->cadence;if(back>=s->count)return NAN;return s->raw[s->count-1-back][channel];
}
static inline float indra_local_delta(const indra_local_history *s,int c,uint32_t seconds){
 if(!s->cadence||seconds%s->cadence)return NAN;
 for(uint32_t age=0;age<=seconds;age+=s->cadence)if(!isfinite(indra_local_at(s,c,age)))return NAN;
 return indra_local_at(s,c,0)-indra_local_at(s,c,seconds);
}
static inline float indra_local_washout(const indra_local_history *s,int hourly){
 double baselines[2];
 for(int c=0;c<2;++c){double values[60];unsigned n=0;
  if(hourly){if(s->cadence!=3600)return NAN;for(int h=1;h<=3;++h){float v=indra_local_at(s,c+3,h*3600);if(!isfinite(v))return NAN;values[n++]=v;}}
  else{if(s->cadence!=60)return NAN;for(int m=16;m<=75;++m){float v=indra_local_at(s,c+3,m*60);if(!isfinite(v))return NAN;values[n++]=v;}}
  for(unsigned i=1;i<n;++i)for(unsigned j=i;j>0&&values[j]<values[j-1];--j){double v=values[j];values[j]=values[j-1];values[j-1]=v;}
  baselines[c]=n%2?values[n/2]:(values[n/2-1]+values[n/2])/2;
  if(baselines[c]<(c?PM10_BASE:PM25_BASE)||!isfinite(indra_local_at(s,c+3,0)))return NAN;
 }
 for(int c=0;c<2;++c)if(baselines[c]-indra_local_at(s,c+3,0)<fmax(c?PM10_DROP:PM25_DROP,PM_FRACTION*baselines[c]))return 0;
 return 1;
}
/* Bounded supported collector: 60s native or 3600s hourly, exact steps only.
 * Native mode returns no 6h rain/snow evidence: buffer spans only 75 minutes.
 * Hourly mode cannot fabricate native 15-minute conditions. */
static inline int indra_local_push(indra_local_history *s,uint32_t stamp,uint32_t cadence,const float *raw,
 uint8_t valid_mask,int wind_calibrated,float terrain,indra_rule_view *v){
 if(!s||!raw||!v||(cadence!=60&&cadence!=3600)||stamp%cadence||(s->last&&stamp<=s->last))return 0;
 if(s->count>76)return 0;
 if(s->last&&(cadence!=s->cadence||stamp-s->last!=cadence))indra_local_reset(s);
 if(s->count==76){memmove(s->stamp,s->stamp+1,75*sizeof(s->stamp[0]));memmove(s->raw,s->raw+1,75*sizeof(s->raw[0]));--s->count;}
 s->cadence=cadence;s->last=stamp;s->stamp[s->count]=stamp;
 for(int i=0;i<6;++i)s->raw[s->count][i]=(valid_mask&(1u<<i))&&isfinite(raw[i])?raw[i]:NAN;++s->count;
 for(int i=0;i<6;++i)v->raw[i]=indra_local_at(s,i,0);
 v->hourly=cadence==3600;v->dp6=indra_local_delta(s,2,21600);
 uint32_t span=v->hourly?3600:900;v->dp=indra_local_delta(s,2,span);v->dt=indra_local_delta(s,0,span);
 float dw=indra_local_delta(s,5,span);v->wind_increase=wind_calibrated&&isfinite(dw)?(dw>=WIND_DELTA&&v->raw[5]>=WIND_MIN?1.f:0.f):NAN;
 v->wash_hour=indra_local_washout(s,1);v->wash_native=indra_local_washout(s,0);v->terrain=terrain;
 time_t local=(time_t)stamp+19800;struct tm *calendar=gmtime(&local);v->month=calendar?(calendar->tm_mon>=5&&calendar->tm_mon<=8?1.f:0.f):NAN;
 return 1;
}
#endif
'''
    for key,value in sorted(replacements.items(),key=lambda x:len(x[0]),reverse=True):
        source=source.replace(key,str(value))
    return source
