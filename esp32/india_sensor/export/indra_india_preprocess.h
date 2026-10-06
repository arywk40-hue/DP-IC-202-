#ifndef INDRA_INDIA_PREPROCESS_H
#define INDRA_INDIA_PREPROCESS_H
#include <math.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include "indra_india_model.h"
/* Fixed surveyed WGS84 position and orthometric sensor height. No raw GNSS datum conversion. */
typedef struct { float raw[26][6]; uint64_t time[26]; int n; } indra_hour_history;
static inline double indra_lag(const indra_hour_history *s,int c,int h) {
  uint64_t t=s->time[s->n-1]; if(t<(uint64_t)h*3600)return NAN;
  for(int i=s->n-1;i>=0;--i) if(s->time[i]==t-(uint64_t)h*3600)return s->raw[i][c];
  return NAN;
}
static inline double indra_roll(const indra_hour_history *s,int c,int n,int kind,int skip) {
  double sum=0,lo=INFINITY,hi=-INFINITY;
  for(int h=skip;h<n+skip;++h){double v=indra_lag(s,c,h);if(!isfinite(v))return NAN;sum+=v;lo=fmin(lo,v);hi=fmax(hi,v);}
  double mean=sum/n;if(kind==0)return mean;if(kind==2)return lo;if(kind==3)return hi;
  double var=0;for(int h=skip;h<n+skip;++h){double d=indra_lag(s,c,h)-mean;var+=d*d;}return sqrt(var/n);
}
static inline double indra_delta(const indra_hour_history *s,int c,int h) {
  for(int k=0;k<=h;++k)if(!isfinite(indra_lag(s,c,k)))return NAN;
  return indra_lag(s,c,0)-indra_lag(s,c,h);
}
/* Store invalid channels as NAN, not zero. Late/out-of-order/off-grid rows refuse.
 * Returns 1 after 24h span, 2 warming up, 0 invalid packet. No allocation/I/O. */
static inline int indra_hour_push(indra_hour_history *s,uint64_t stamp,uint64_t available,
 const float *raw,int station_pressure,float lat,float lon,float height,float *out){
 if(!s||!raw||!out||s->n<0||s->n>26)return 0;
 for(int i=0;i<INDRA_INDIA_FEATURES;++i)out[i]=NAN;
 if(stamp<1577836800ULL||stamp>2145916800ULL||stamp%3600||available!=stamp||
    !isfinite(lat)||!isfinite(lon)||lat< -90||lat>90||lon< -180||lon>180)return 0;
 if(s->n&&stamp<=s->time[s->n-1])return 0;
 if(s->n==26){memmove(s->raw,s->raw+1,25*sizeof(s->raw[0]));memmove(s->time,s->time+1,25*sizeof(s->time[0]));s->n=25;}
 const float lo[6]={-60,0,300,0,0,0},hi[6]={85,100,1100,5000,5000,100};
 for(int i=0;i<6;++i)s->raw[s->n][i]=(isfinite(raw[i])&&raw[i]>=lo[i]&&raw[i]<=hi[i])?raw[i]:NAN;
 if(!station_pressure)s->raw[s->n][2]=NAN;
 s->time[s->n++]=stamp;
 double t=indra_lag(s,0,0),rh=indra_lag(s,1,0);
 double frac=fmax(1e-6,fmin(1.,rh/100.));
 double gamma=log(frac)+17.625*t/(243.04+t),dew=rh>0?243.04*gamma/(17.625-gamma):NAN;
 double tf=t*1.8+32;
 double hi_f=-42.379+2.04901523*tf+10.14333127*rh-.22475541*tf*rh-.00683783*tf*tf-.05481717*rh*rh+.00122874*tf*tf*rh+.00085282*tf*rh*rh-.00000199*tf*tf*rh*rh;
 double heat=tf>=80?(hi_f-32)/1.8:t;
 double vpd=isfinite(t)&&isfinite(rh)?fmax(0.,.6108*exp(17.27*t/(t+237.3))*(1-rh/100.)):NAN;
 double absolute=216.7*(6.112*exp(17.625*t/(243.04+t))*rh/100.)/(t+273.15);
 double ratio=indra_lag(s,4,0)>0?indra_lag(s,3,0)/indra_lag(s,4,0):NAN;
 time_t tick=(time_t)stamp;struct tm utc;
 if(!gmtime_r(&tick,&utc))return 0;
 double hour_angle=6.283185307179586*utc.tm_hour/24.,month_angle=6.283185307179586*utc.tm_mon/12.;
 (void)dew;(void)heat;(void)vpd;(void)absolute;(void)ratio;(void)hour_angle;(void)month_angle;
 if(!isfinite(height)||height< -500||height>9000)height=NAN;

 out[0]=(float)(indra_lag(s,0,0)); /* temperature_c */
 if(!isfinite(out[0]))out[0]=NAN;
 out[1]=(float)(indra_lag(s,1,0)); /* relative_humidity_pct */
 if(!isfinite(out[1]))out[1]=NAN;
 out[2]=(float)(indra_lag(s,2,0)); /* pressure_hpa */
 if(!isfinite(out[2]))out[2]=NAN;
 out[3]=(float)(indra_lag(s,5,0)); /* wind_speed_mps */
 if(!isfinite(out[3]))out[3]=NAN;
 out[4]=(float)(indra_lag(s,0,1)); /* temperature_c_lag_1h */
 if(!isfinite(out[4]))out[4]=NAN;
 out[5]=(float)(indra_lag(s,0,3)); /* temperature_c_lag_3h */
 if(!isfinite(out[5]))out[5]=NAN;
 out[6]=(float)(indra_lag(s,0,6)); /* temperature_c_lag_6h */
 if(!isfinite(out[6]))out[6]=NAN;
 out[7]=(float)(indra_lag(s,0,12)); /* temperature_c_lag_12h */
 if(!isfinite(out[7]))out[7]=NAN;
 out[8]=(float)(indra_lag(s,0,24)); /* temperature_c_lag_24h */
 if(!isfinite(out[8]))out[8]=NAN;
 out[9]=(float)(indra_delta(s,0,1)); /* temperature_c_delta_1h */
 if(!isfinite(out[9]))out[9]=NAN;
 out[10]=(float)(indra_roll(s,0,6,0,0)); /* temperature_c_mean_6h */
 if(!isfinite(out[10]))out[10]=NAN;
 out[11]=(float)(indra_roll(s,0,6,1,0)); /* temperature_c_std_6h */
 if(!isfinite(out[11]))out[11]=NAN;
 out[12]=(float)(indra_roll(s,0,24,0,0)); /* temperature_c_mean_24h */
 if(!isfinite(out[12]))out[12]=NAN;
 out[13]=(float)(indra_roll(s,0,24,1,0)); /* temperature_c_std_24h */
 if(!isfinite(out[13]))out[13]=NAN;
 out[14]=(float)(indra_lag(s,1,1)); /* relative_humidity_pct_lag_1h */
 if(!isfinite(out[14]))out[14]=NAN;
 out[15]=(float)(indra_lag(s,1,3)); /* relative_humidity_pct_lag_3h */
 if(!isfinite(out[15]))out[15]=NAN;
 out[16]=(float)(indra_lag(s,1,6)); /* relative_humidity_pct_lag_6h */
 if(!isfinite(out[16]))out[16]=NAN;
 out[17]=(float)(indra_lag(s,1,12)); /* relative_humidity_pct_lag_12h */
 if(!isfinite(out[17]))out[17]=NAN;
 out[18]=(float)(indra_lag(s,1,24)); /* relative_humidity_pct_lag_24h */
 if(!isfinite(out[18]))out[18]=NAN;
 out[19]=(float)(indra_delta(s,1,1)); /* relative_humidity_pct_delta_1h */
 if(!isfinite(out[19]))out[19]=NAN;
 out[20]=(float)(indra_roll(s,1,6,0,0)); /* relative_humidity_pct_mean_6h */
 if(!isfinite(out[20]))out[20]=NAN;
 out[21]=(float)(indra_roll(s,1,6,1,0)); /* relative_humidity_pct_std_6h */
 if(!isfinite(out[21]))out[21]=NAN;
 out[22]=(float)(indra_roll(s,1,24,0,0)); /* relative_humidity_pct_mean_24h */
 if(!isfinite(out[22]))out[22]=NAN;
 out[23]=(float)(indra_roll(s,1,24,1,0)); /* relative_humidity_pct_std_24h */
 if(!isfinite(out[23]))out[23]=NAN;
 out[24]=(float)(indra_lag(s,2,1)); /* pressure_hpa_lag_1h */
 if(!isfinite(out[24]))out[24]=NAN;
 out[25]=(float)(indra_lag(s,2,3)); /* pressure_hpa_lag_3h */
 if(!isfinite(out[25]))out[25]=NAN;
 out[26]=(float)(indra_lag(s,2,6)); /* pressure_hpa_lag_6h */
 if(!isfinite(out[26]))out[26]=NAN;
 out[27]=(float)(indra_lag(s,2,12)); /* pressure_hpa_lag_12h */
 if(!isfinite(out[27]))out[27]=NAN;
 out[28]=(float)(indra_lag(s,2,24)); /* pressure_hpa_lag_24h */
 if(!isfinite(out[28]))out[28]=NAN;
 out[29]=(float)(indra_delta(s,2,1)); /* pressure_hpa_delta_1h */
 if(!isfinite(out[29]))out[29]=NAN;
 out[30]=(float)(indra_lag(s,5,1)); /* wind_speed_mps_lag_1h */
 if(!isfinite(out[30]))out[30]=NAN;
 out[31]=(float)(indra_lag(s,5,3)); /* wind_speed_mps_lag_3h */
 if(!isfinite(out[31]))out[31]=NAN;
 out[32]=(float)(indra_lag(s,5,6)); /* wind_speed_mps_lag_6h */
 if(!isfinite(out[32]))out[32]=NAN;
 out[33]=(float)(indra_lag(s,5,12)); /* wind_speed_mps_lag_12h */
 if(!isfinite(out[33]))out[33]=NAN;
 out[34]=(float)(indra_lag(s,5,24)); /* wind_speed_mps_lag_24h */
 if(!isfinite(out[34]))out[34]=NAN;
 out[35]=(float)(indra_delta(s,5,1)); /* wind_speed_mps_delta_1h */
 if(!isfinite(out[35]))out[35]=NAN;
 out[36]=(float)(indra_roll(s,5,6,0,0)); /* wind_speed_mps_mean_6h */
 if(!isfinite(out[36]))out[36]=NAN;
 out[37]=(float)(indra_roll(s,5,6,1,0)); /* wind_speed_mps_std_6h */
 if(!isfinite(out[37]))out[37]=NAN;
 out[38]=(float)(indra_roll(s,5,24,0,0)); /* wind_speed_mps_mean_24h */
 if(!isfinite(out[38]))out[38]=NAN;
 out[39]=(float)(indra_roll(s,5,24,1,0)); /* wind_speed_mps_std_24h */
 if(!isfinite(out[39]))out[39]=NAN;
 out[40]=(float)(indra_delta(s,0,6)); /* temperature_c_delta_360min */
 if(!isfinite(out[40]))out[40]=NAN;
 out[41]=(float)(indra_roll(s,0,6,2,0)); /* temperature_c_min_360min */
 if(!isfinite(out[41]))out[41]=NAN;
 out[42]=(float)(indra_roll(s,0,6,3,0)); /* temperature_c_max_360min */
 if(!isfinite(out[42]))out[42]=NAN;
 out[43]=(float)(indra_delta(s,1,6)); /* relative_humidity_pct_delta_360min */
 if(!isfinite(out[43]))out[43]=NAN;
 out[44]=(float)(indra_roll(s,1,6,2,0)); /* relative_humidity_pct_min_360min */
 if(!isfinite(out[44]))out[44]=NAN;
 out[45]=(float)(indra_roll(s,1,6,3,0)); /* relative_humidity_pct_max_360min */
 if(!isfinite(out[45]))out[45]=NAN;
 out[46]=(float)(indra_delta(s,5,6)); /* wind_speed_mps_delta_360min */
 if(!isfinite(out[46]))out[46]=NAN;
 out[47]=(float)(indra_roll(s,5,6,2,0)); /* wind_speed_mps_min_360min */
 if(!isfinite(out[47]))out[47]=NAN;
 out[48]=(float)(indra_roll(s,5,6,3,0)); /* wind_speed_mps_max_360min */
 if(!isfinite(out[48]))out[48]=NAN;
 out[49]=(float)(indra_delta(s,0,24)); /* temperature_c_delta_1440min */
 if(!isfinite(out[49]))out[49]=NAN;
 out[50]=(float)(indra_roll(s,0,24,2,0)); /* temperature_c_min_1440min */
 if(!isfinite(out[50]))out[50]=NAN;
 out[51]=(float)(indra_roll(s,0,24,3,0)); /* temperature_c_max_1440min */
 if(!isfinite(out[51]))out[51]=NAN;
 out[52]=(float)(indra_delta(s,1,24)); /* relative_humidity_pct_delta_1440min */
 if(!isfinite(out[52]))out[52]=NAN;
 out[53]=(float)(indra_roll(s,1,24,2,0)); /* relative_humidity_pct_min_1440min */
 if(!isfinite(out[53]))out[53]=NAN;
 out[54]=(float)(indra_roll(s,1,24,3,0)); /* relative_humidity_pct_max_1440min */
 if(!isfinite(out[54]))out[54]=NAN;
 out[55]=(float)(indra_delta(s,5,24)); /* wind_speed_mps_delta_1440min */
 if(!isfinite(out[55]))out[55]=NAN;
 out[56]=(float)(indra_roll(s,5,24,2,0)); /* wind_speed_mps_min_1440min */
 if(!isfinite(out[56]))out[56]=NAN;
 out[57]=(float)(indra_roll(s,5,24,3,0)); /* wind_speed_mps_max_1440min */
 if(!isfinite(out[57]))out[57]=NAN;
 out[58]=(float)(indra_delta(s,2,1)/60.); /* pressure_tendency_hpa_per_min_60min */
 if(!isfinite(out[58]))out[58]=NAN;
 out[59]=(float)(dew); /* dewpoint_c */
 if(!isfinite(out[59]))out[59]=NAN;
 out[60]=(float)(t-dew); /* dewpoint_depression_c */
 if(!isfinite(out[60]))out[60]=NAN;
 out[61]=(float)(vpd); /* vapor_pressure_deficit_kpa */
 if(!isfinite(out[61]))out[61]=NAN;
 out[62]=(float)(heat); /* heat_index_c */
 if(!isfinite(out[62]))out[62]=NAN;
 out[63]=(float)(absolute); /* absolute_humidity_estimate_g_m3 */
 if(!isfinite(out[63]))out[63]=NAN;
 out[64]=(float)(sin(hour_angle)); /* hour_sin */
 if(!isfinite(out[64]))out[64]=NAN;
 out[65]=(float)(cos(hour_angle)); /* hour_cos */
 if(!isfinite(out[65]))out[65]=NAN;
 out[66]=(float)(sin(month_angle)); /* month_sin */
 if(!isfinite(out[66]))out[66]=NAN;
 out[67]=(float)(cos(month_angle)); /* month_cos */
 if(!isfinite(out[67]))out[67]=NAN;
 out[68]=(float)((utc.tm_mon>=5&&utc.tm_mon<=8)); /* calendar_jjas_proxy */
 if(!isfinite(out[68]))out[68]=NAN;
 out[69]=(float)(lat); /* latitude */
 if(!isfinite(out[69]))out[69]=NAN;
 out[70]=(float)(lon); /* longitude */
 if(!isfinite(out[70]))out[70]=NAN;
 out[71]=(float)(height); /* elevation_m */
 if(!isfinite(out[71]))out[71]=NAN;
 return stamp-s->time[0]>=24*3600?1:2;
}
#endif
