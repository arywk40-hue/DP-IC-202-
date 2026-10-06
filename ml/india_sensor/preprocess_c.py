"""Generate bounded native-hour preprocessing; unknown feature names fail closed."""
import re
from pathlib import Path

from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS

BASE = r'''#ifndef INDRA_INDIA_PREPROCESS_H
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
'''


def expression(name):
    if name in RAW_SENSOR_COLUMNS:
        return f'indra_lag(s,{RAW_SENSOR_COLUMNS.index(name)},0)'
    for c, channel in enumerate(RAW_SENSOR_COLUMNS):
        if not name.startswith(channel+'_'):
            continue
        tail = name[len(channel)+1:]
        match = re.fullmatch(r'lag_(\d+)h', tail)
        if match:
            return f'indra_lag(s,{c},{match[1]})'
        match = re.fullmatch(r'(mean|std|min|max)_(\d+)(h|min)', tail)
        if match:
            n = int(match[2]) if match[3] == 'h' else int(match[2])//60
            if n < 1 or n > 24:
                raise ValueError('Unsupported hour window')
            return f'indra_roll(s,{c},{n},{["mean","std","min","max"].index(match[1])},0)'
        match = re.fullmatch(r'delta_(\d+)(h|min)', tail)
        if match:
            n = int(match[1]) if match[2] == 'h' else int(match[1])//60
            if n < 1 or n > 24:
                raise ValueError('Sub-hour feature cannot be exported from hours')
            return f'indra_delta(s,{c},{n})'
    fixed = {'dewpoint_c': 'dew', 'dewpoint_depression_c': 't-dew', 'heat_index_c': 'heat',
             'vapor_pressure_deficit_kpa': 'vpd', 'absolute_humidity_estimate_g_m3': 'absolute',
             'pm25_pm10_ratio': 'ratio', 'hour_sin': 'sin(hour_angle)', 'hour_cos': 'cos(hour_angle)',
             'month_sin': 'sin(month_angle)', 'month_cos': 'cos(month_angle)',
             'calendar_jjas_proxy': '(utc.tm_mon>=5&&utc.tm_mon<=8)',
             'latitude': 'lat', 'longitude': 'lon', 'elevation_m': 'height',
             'pressure_anomaly_prior24h_hpa': 'indra_lag(s,2,0)-indra_roll(s,2,24,0,1)',
             'pressure_tendency_hpa_per_min_60min': 'indra_delta(s,2,1)/60.'}
    if name not in fixed:
        raise ValueError('Unsupported preprocessing feature: '+name)
    return fixed[name]


def generate(names, output):
    lines = [BASE]
    for i, name in enumerate(names):
        lines.append(f' out[{i}]=(float)({expression(name)}); /* {name} */')
        lines.append(f' if(!isfinite(out[{i}]))out[{i}]=NAN;')
    lines += [' return stamp-s->time[0]>=24*3600?1:2;', '}', '#endif', '']
    path = Path(output)/'indra_india_preprocess.h'
    path.write_text('\n'.join(lines))
    return {'header': str(path), 'history_bytes_upper_bound': 26*6*4+26*8+16,
            'native_cadence_seconds': 3600, 'raw_order': RAW_SENSOR_COLUMNS,
            'float_precision': 'float32 telemetry, double derived intermediates',
            'units': ['degC','percent','station_hPa','ug/m3','ug/m3','m/s'],
            'latitude_longitude': 'Fixed surveyed WGS84 degrees', 'height': 'Verified EGM96 sensor elevation or NAN; never raw GNSS ellipsoid altitude',
            'time': 'Explicit UTC completed hour 2020–2037; DS3231/GNSS synchronization not hardware verified',
            'hardware_validated': False}
