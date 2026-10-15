// Local research interface: no Internet, LoRa, notification or empirical hazard head.
#include <Arduino.h>
#include "sensor_hub.h"
#include "indra_anomaly.h"
#include "indra_local_rules.h"
#include "indra_peer_protocol.h"
#include "indra_consensus_policy.h"
#if __has_include("device_config.h")
#include "device_config.h"
#else
#include "device_config.example.h"
#endif

static SensorHub hub;
static HimachalConfig config=himachal_device_config();
static indra_anomaly_state anomaly={};
static indra_local_history history={};
static bool physical_ready=false;
static char line[224];
static unsigned line_used=0;
static bool line_overflow=false;

static void number(float value){if(isfinite(value))Serial.print(value,6);else Serial.print("null");}
static void info(){
  Serial.printf("{\"schema_version\":\"indra_himachal_edge_v1\",\"kind\":\"INFO\",\"research_only\":true,\"hardware_validated\":false,\"physical_ready\":%s,\"anomaly_state_bytes\":%u,\"local_history_bytes\":%u,\"trained_event_model\":null,\"radio_enabled\":false,\"anomaly_hash\":\"%s\",\"rule_hash\":\"%s\"}\n",
      physical_ready?"true":"false",unsigned(sizeof(anomaly)),unsigned(sizeof(history)),INDRA_ANOMALY_CONFIG_SHA256,INDRA_LOCAL_RULE_HASH);
}
static void process(uint32_t stamp,const float *raw,int crc_ok,float uncertainty,bool physical){
  uint32_t started=micros();
  indra_anomaly_result diagnostic;
  const uint32_t cadence=physical?config.cadence_seconds:60;
  if(!indra_anomaly_push(&anomaly,stamp,cadence,raw,crc_ok,uncertainty,0,&diagnostic))return;
  indra_rule_result result={};
  for(int i=0;i<3;++i)result.score[i]=result.probability[i]=NAN;
  result.abstain_mask=7;
  indra_rule_view view;
  float terrain=config.terrain_reviewed?(config.terrain_exposed?1.f:0.f):NAN;
  if(diagnostic.packet==INDRA_ACCEPTED&&indra_local_push(&history,stamp,cadence,raw,diagnostic.valid_mask,
        physical?config.calibration_verified:true,terrain,&view))indra_local_rules(&view,1,&result);
  uint32_t latency_us=micros()-started;
  Serial.printf("{\"schema_version\":\"indra_himachal_edge_v1\",\"timestamp_utc\":%u,\"source_class\":\"%s\",\"research_only\":true,\"packet_state\":%u,\"fault_mask\":%u,\"environmental_mask\":%u,\"valid_channel_mask\":%u,\"inference_latency_us\":%u,\"native_interval_seconds\":%u,\"measurements\":[",
      stamp,physical?"physical_indra":"synthetic_demo",diagnostic.packet,diagnostic.fault_mask,diagnostic.environmental_mask,diagnostic.valid_mask,latency_us,cadence);
  for(int i=0;i<6;++i){if(i)Serial.print(',');number(raw[i]);}
  Serial.print("],\"channel_states\":[");for(int i=0;i<6;++i){if(i)Serial.print(',');Serial.print(diagnostic.state[i]);}
  Serial.print("],\"rule_scores\":[");
  for(int i=0;i<3;++i){if(i)Serial.print(',');number(result.score[i]);}
  Serial.print("],\"rule_coverage\":[");for(int i=0;i<3;++i){if(i)Serial.print(',');number(result.coverage[i]);}
  Serial.printf("],\"abstain_mask\":%u,\"local_candidate_mask\":%u,\"probabilities\":[null,null,null],\"trained_event_model_valid_mask\":0,\"target_order\":[\"rain\",\"snowstorm\",\"cloudburst_risk\"],\"profile\":\"%s\",\"risk_only\":true,\"lead_time_h\":null,\"consensus\":\"LOCAL_ONLY\",\"dispatch\":\"DISABLED\"}\n",result.abstain_mask,result.local_candidate_mask,cadence==3600?"hourly_companion":"native_75min_cloudburst_only");
}
void setup(){
  Serial.begin(115200);
  bool declared=config.native_cadence_verified&&config.calibration_verified&&config.site_verified
      &&isfinite(config.clock_uncertainty_seconds)&&config.clock_uncertainty_seconds>=0&&config.clock_uncertainty_seconds<=30
      &&isfinite(config.sensors.surveyed_egm96_m)&&config.sensors.wind_curve_provided
      &&(config.cadence_seconds==60||config.cadence_seconds==3600);
  physical_ready=config.sensors.physical_mode&&declared&&hub.begin(config.sensors);
  info();
}
void loop(){
  if(physical_ready){
    hub.poll();static uint32_t last_stamp=0;static uint32_t last_poll_ms=0;
    static double wind_integral=0;static uint32_t wind_duration_ms=0;
    static bool wind_window_complete=true;
    if(uint32_t(millis()-last_poll_ms)>=200){
      uint32_t now_ms=millis(),elapsed=now_ms-last_poll_ms;
      last_poll_ms=now_ms;NodeSnapshot sample=hub.sample();
      if(isfinite(sample.weather[5])){wind_integral+=sample.weather[5]*double(elapsed);wind_duration_ms+=elapsed;}
      else wind_window_complete=false;
      unsigned yr,mo,day,hour,minute,second;
      if(sample.clock_available&&sscanf(sample.utc,"%u-%u-%uT%u:%u:%uZ",&yr,&mo,&day,&hour,&minute,&second)==6){
        uint32_t stamp=DateTime(yr,mo,day,hour,minute,second).unixtime();
        if(stamp!=last_stamp&&stamp%config.cadence_seconds==0){
          uint32_t expected=config.cadence_seconds*1000;
          bool complete=last_stamp&&stamp-last_stamp==config.cadence_seconds&&wind_window_complete
              &&wind_duration_ms>=expected-1000&&wind_duration_ms<=expected+1000;
          sample.weather[5]=complete?float(wind_integral/wind_duration_ms):NAN;
          last_stamp=stamp;process(stamp,sample.weather,1,config.clock_uncertainty_seconds,true);
          wind_integral=0;wind_duration_ms=0;wind_window_complete=true;
        }
      }
    }
  }
  for(int budget=0;budget<256&&Serial.available();++budget){
    char c=char(Serial.read());
    if(c=='\r')continue;
    if(c!='\n'){if(line_used<sizeof(line)-1&&!line_overflow)line[line_used++]=c;else line_overflow=true;continue;}
    line[line_used]=0;
    if(line_overflow){Serial.println("{\"error\":\"INPUT_TOO_LONG\"}");}
    else if(!strcmp(line,"INFO"))info();
    else if(!strcmp(line,"RESET")){indra_anomaly_reset(&anomaly);indra_local_reset(&history);Serial.println("{\"reset\":true}");}
    else if(!physical_ready){
      unsigned timestamp,crc;float raw[6],uncertainty;int used=0;
      int got=sscanf(line,"%u,%f,%f,%f,%f,%f,%f,%u,%f%n",&timestamp,raw,raw+1,raw+2,raw+3,raw+4,raw+5,&crc,&uncertainty,&used);
      if(got==9&&line[used]==0&&crc<=1)process(timestamp,raw,int(crc),uncertainty,false);
      else Serial.println("{\"error\":\"INVALID_SERIAL_DEMO_RECORD\"}");
    }
    line_used=0;line_overflow=false;
  }
  yield();
}
