/* Generated current-condition risk only; no empirical event model. */
#ifndef INDRA_HIMACHAL_LOCAL_RULES_H
#define INDRA_HIMACHAL_LOCAL_RULES_H
#include <math.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#define INDRA_LOCAL_RULE_HASH "657f9fdf6896d78d95b4ff9624f83079ba3d78bce94cb1792abb544134a22491"
#define INDRA_LOCAL_FEATURE_HASH "83f613ad23eaafb5772c0bd3720fbb65f3eca2a26a239341b38ba4d2ef52ac71"
typedef struct {float raw[6],dp6,dp,dt,wind_increase,wash_hour,wash_native,month,terrain;int hourly;} indra_rule_view;
typedef struct {float score[3],coverage[3],probability[3];uint8_t abstain_mask,local_candidate_mask,trained_model_valid_mask;} indra_rule_result;
/* Pure deterministic indicator. Caller must preserve source/reference checks. */
static inline void indra_local_rules(const indra_rule_view *v,int station_source,indra_rule_result *r){
 memset(r,0,sizeof(*r));for(int j=0;j<3;++j)r->score[j]=r->probability[j]=NAN;
 if(!station_source){r->abstain_mask=7;return;}
 float a[4]={v->raw[1],v->dp6,v->raw[0],v->wash_hour};int present=0;
 for(int i=0;i<4;++i)present+=isfinite(a[i]);r->coverage[0]=present/4.f;
 if(present<4)r->abstain_mask|=1;else{r->score[0]=(a[0]>=85&&a[1]<=-1.5&&a[2]>3&&a[3]==1)?1.f:0.f;if(r->score[0])r->local_candidate_mask|=1;}
 float b[5]={v->raw[0],v->raw[1],v->raw[5],v->dp6,v->wash_hour};present=0;
 for(int i=0;i<5;++i)present+=isfinite(b[i]);r->coverage[1]=present/5.f;
 if(present<5)r->abstain_mask|=2;else{r->score[1]=(b[0]<=1&&b[1]>=85&&b[2]>=9&&b[3]<=-3&&b[4]==1)?1.f:0.f;if(r->score[1])r->local_candidate_mask|=2;}
 const double native_weights[7]={0.20000000000000001,0.20000000000000001,0.20000000000000001,0.14999999999999999,0.14999999999999999,0.050000000000000003,0.050000000000000003},hourly_weights[7]={0.20000000000000001,0.20000000000000001,0.20000000000000001,0.14999999999999999,0.14999999999999999,0.050000000000000003,0.050000000000000003};
 const double *weights=v->hourly?hourly_weights:native_weights;
 float values[7]={v->raw[1],v->dp,v->dt,v->wind_increase,v->hourly?v->wash_hour:v->wash_native,v->month,v->terrain};
 int matched[7]={values[0]>=(v->hourly?90:90),values[1]<=(v->hourly?-1.5:-1),values[2]<=(v->hourly?-2:-2),values[3]==1,values[4]==1,values[5]==1,values[6]==1};
 double score=0,available=0;unsigned dynamic=0,dynamic_available=0;
 for(int i=0;i<7;++i)if(isfinite(values[i])){available+=weights[i];if(i<5)++dynamic_available;if(matched[i]){score+=weights[i];if(i<5)++dynamic;}}
 r->coverage[2]=(float)available;if(available>0)r->score[2]=(float)score;
 if(available+1e-9<0.9||dynamic_available<3)r->abstain_mask|=4;
 else if(score+1e-9>=0.7&&dynamic>=3)r->local_candidate_mask|=4;
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
  if(baselines[c]<(c?20:10)||!isfinite(indra_local_at(s,c+3,0)))return NAN;
 }
 for(int c=0;c<2;++c)if(baselines[c]-indra_local_at(s,c+3,0)<fmax(c?10:5,0.2*baselines[c]))return 0;
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
 float dw=indra_local_delta(s,5,span);v->wind_increase=wind_calibrated&&isfinite(dw)?(dw>=3&&v->raw[5]>=8?1.f:0.f):NAN;
 v->wash_hour=indra_local_washout(s,1);v->wash_native=indra_local_washout(s,0);v->terrain=terrain;
 time_t local=(time_t)stamp+19800;struct tm *calendar=gmtime(&local);v->month=calendar?(calendar->tm_mon>=5&&calendar->tm_mon<=8?1.f:0.f):NAN;
 return 1;
}
#endif
