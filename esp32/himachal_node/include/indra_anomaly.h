/* Generated research diagnostics; no hazard probability or physical validation. */
#ifndef INDRA_HIMACHAL_ANOMALY_H
#define INDRA_HIMACHAL_ANOMALY_H
#include <math.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define INDRA_ANOMALY_VERSION "indra_himachal_anomaly_v1"
#define INDRA_ANOMALY_CONFIG_SHA256 "aed660538746232f49536624d7328b3e3d6d745778603170063d81656ec94726"
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
 else if(stamp<1577836800u||stamp>2145916800u||stamp%cadence||(s->last&&stamp<=s->last))r->packet=INDRA_TIME_REJECTED;
 else if(!isfinite(clock_uncertainty)||clock_uncertainty<0||clock_uncertainty>30)r->packet=INDRA_CLOCK_UNVERIFIED;
 if(r->packet!=INDRA_ACCEPTED){if(r->packet==INDRA_CRC_REJECTED){r->fault_mask=63;for(int i=0;i<6;++i)r->state[i]=INDRA_SENSOR_FAULT;}return 1;}
 if(s->last&&stamp-s->last>3*cadence)indra_anomaly_reset(s);
 s->last=stamp;
 const double lo[6]={-60,0,300,0,0,0},hi[6]={85,100,1100,5000,5000,100},floor_scale[6]={0.20000000000000001,1,0.10000000000000001,2,3,0.29999999999999999};
 for(int i=0;i<6;++i){float v=raw[i];
  if((self_test_faults&(1u<<i))||isinf(v)||(isfinite(v)&&(v<lo[i]||v>hi[i]))){r->state[i]=INDRA_SENSOR_FAULT;r->fault_mask|=1u<<i;s->count[i]=s->cursor[i]=0;s->ewma[i]=NAN;continue;}
  if(isnan(v)){s->count[i]=s->cursor[i]=0;s->ewma[i]=NAN;continue;}
  r->valid_mask|=1u<<i;
  if(s->count[i]<8)r->state[i]=INDRA_WARMUP;
  else {double values[16],deviation[16];for(unsigned j=0;j<s->count[i];++j)values[j]=s->ring[i][j];
   double median=indra_median16(values,s->count[i]);for(unsigned j=0;j<s->count[i];++j)deviation[j]=fabs(values[j]-median);
   double scale=fmax(floor_scale[i],1.4825999999999999*indra_median16(deviation,s->count[i]));
   r->residual[i]=(float)(v-median);r->scale[i]=(float)scale;
   if(fabs(v-median)>5*scale){r->state[i]=INDRA_ENVIRONMENTAL_ANOMALY;r->environmental_mask|=1u<<i;}
   else r->state[i]=INDRA_WITHIN_BASELINE;
  }
  s->ewma[i]=s->count[i]?(float)(s->ewma[i]+0.125*((double)v-s->ewma[i])):v;
  s->ring[i][s->cursor[i]]=v;s->cursor[i]=(s->cursor[i]+1)%16;if(s->count[i]<16)++s->count[i];
 }
 return 1;
}
#endif
