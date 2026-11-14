#pragma once
#include "sensor_hub.h"
// Builds the indra_weather_records_v1 JSON the INDRA server accepts at POST /api/ingest.
// The same line is printed on USB serial (for server/scripts/serial_bridge.py) and,
// when WiFi is configured, POSTed directly by main.cpp.
// A missing clock or location is sent as null (never invented): the server then stamps
// receive time and uses the location registered for the node.
static inline String indra_numeric(float value){return isfinite(value)?String(value,6):String("null");}
static inline String indra_coord(double value){return isfinite(value)?String(value,7):String("null");}
static inline bool indra_weather_payload(const String& node,const NodeSnapshot& s,String& payload){
  if(node.length()==0||node.length()>64||!s.hardware_configured)return false;
  for(size_t i=0;i<node.length();++i){char c=node[i];if(!isalnum(c)&&c!='_'&&c!='-')return false;}
  bool any=false;for(int i=0;i<6;++i)any|=isfinite(s.weather[i]);
  if(!any)return false;
  const char* channels[]={"temperature_c","relative_humidity_pct","pressure_hpa","pm25_ug_m3","pm10_ug_m3","wind_speed_mps"};
  const char* units[]={"degC","%","hPa","ug/m3","ug/m3","m/s"};
  const String stamp=s.clock_available?("\""+String(s.utc)+"\""):String("null");
  const String battery=s.ina_ok?indra_numeric(s.bus_voltage_v):String("null");
  payload="{\"schema_version\":\"indra_weather_records_v1\",\"observations\":[";
  for(int i=0;i<6;++i){
    if(i)payload+=',';
    payload+="{\"node_id\":\""+node+"\",\"timestamp_utc\":"+stamp+",\"latitude\":"+indra_coord(s.latitude)+",\"longitude\":"+indra_coord(s.longitude);
    payload+=",\"elevation_m\":"+indra_numeric(s.elevation_m)+",\"elevation_datum\":\""+(isfinite(s.elevation_m)?String("EGM96"):String("unknown"))+"\"";
    payload+=",\"channel\":\""+String(channels[i])+"\",\"value\":"+indra_numeric(s.weather[i])+",\"unit\":\""+String(units[i])+"\",\"quality_flag\":\""+(isfinite(s.weather[i])?String("valid"):String("missing"))+"\"";
    payload+=",\"battery_v\":"+battery;
    payload+=",\"source\":\"INDRA_NODE_LIVE_NOT_FIELD_VALIDATED\",\"sensor_model\":\""+String(i<3?"BME280":i<5?"PMS7003":"encoder_600PPR")+"\",\"pressure_reference\":\"station\",\"sample_interval_seconds\":1}";
  }
  payload+="]}";return true;
}
