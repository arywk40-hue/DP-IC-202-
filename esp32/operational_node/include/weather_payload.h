#pragma once
#include "sensor_hub.h"
// Engineering readings for the host HMAC client or packet_auth helper.
// Emits no secret or client-side authenticated claim; receiver derives trust.
static inline String indra_numeric(float value){return isfinite(value)?String(value,6):String("null");}
static inline bool indra_weather_payload(const String& node,const NodeSnapshot& s,String& payload){
  if(node.length()==0||node.length()>64||!s.clock_available||!isfinite(s.latitude)||!isfinite(s.longitude))return false;
  for(size_t i=0;i<node.length();++i){char c=node[i];if(!isalnum(c)&&c!='_'&&c!='-')return false;}
  const char* channels[]={"temperature_c","relative_humidity_pct","pressure_hpa","pm25_ug_m3","pm10_ug_m3","wind_speed_mps"};
  const char* units[]={"degC","%","hPa","ug/m3","ug/m3","m/s"};
  payload="{\"schema_version\":\"indra_weather_records_v1\",\"observations\":[";
  for(int i=0;i<6;++i){
    if(i)payload+=',';
    payload+="{\"node_id\":\""+node+"\",\"timestamp_utc\":\""+String(s.utc)+"\",\"latitude\":"+String(s.latitude,7)+",\"longitude\":"+String(s.longitude,7);
    payload+=",\"elevation_m\":"+indra_numeric(s.elevation_m)+",\"elevation_datum\":\""+(isfinite(s.elevation_m)?String("EGM96"):String("unknown"))+"\"";
    payload+=",\"channel\":\""+String(channels[i])+"\",\"value\":"+indra_numeric(s.weather[i])+",\"unit\":\""+String(units[i])+"\",\"quality_flag\":\""+(isfinite(s.weather[i])?String("valid"):String("missing"))+"\"";
    payload+=",\"source\":\"INDRA_NODE_LIVE_NOT_FIELD_VALIDATED\",\"sensor_model\":\""+String(i<3?"BME280":i<5?"PMS7003":"encoder_600PPR")+"\",\"pressure_reference\":\"station\",\"sample_interval_seconds\":1}";
  }
  payload+="]}";return true;
}
