#include <Arduino.h>
#include <cerrno>
#include <cstdlib>
#include <cmath>
#include <cstring>
#include "indra_mandi_v2_runtime.h"
#include "mandi_v2_selftest.h"
#include "build_identity.h"

mandi_v2::Runtime runtime;
char line[256];
size_t used = 0;
bool overflow = false;
bool self_test_passed = false;
uint32_t boot_id = 0;
uint32_t sequence = 0;

void array_json(const double* values, int count) {
  Serial.print('[');
  for (int i=0;i<count;++i) {
    if (i) Serial.print(',');
    if (std::isfinite(values[i])) Serial.print(values[i], 8);
    else Serial.print("null");
  }
  Serial.print(']');
}
void print_info() {
  Serial.printf("{\"info\":true,\"protocol_version\":2,\"model_id\":\"india_mandi_tabular_v2\","
    "\"boot_id\":%lu,\"self_test_passed\":%s,\"research_only\":true,"
    "\"field_validated\":false,\"calibrated\":false,"
    "\"pattern_model_id\":\"%s\",\"pattern_profile_sha256\":\"%s\",\"scenario_model_id\":\"%s\",\"scenario_config_sha256\":\"%s\",\"scenario_rng\":\"indra_xorshift64star_boxmuller_v1\","
    "\"build_sha256\":\"%s\",\"model_sha256\":\"%s\"}\n",
    static_cast<unsigned long>(boot_id),self_test_passed?"true":"false",
    mandi_v2::kPatternModelId,mandi_v2::kPatternProfileSha256,mandi_v2::kScenarioModelId,mandi_v2::kScenarioConfigSha256,INDRA_BUILD_SHA256,INDRA_MODEL_SHA256);
}
void print_result(uint32_t timestamp,const mandi_v2::Result& result,uint32_t latency,const double* raw) {
  Serial.printf("{\"protocol_version\":2,\"boot_id\":%lu,\"sequence\":%lu,\"build_sha256\":\"%s\",",
    static_cast<unsigned long>(boot_id),static_cast<unsigned long>(++sequence),INDRA_BUILD_SHA256);
  Serial.print("\"model_id\":\"india_mandi_tabular_v2\",\"measurements\":"); array_json(raw,6);
  Serial.printf(",\"timestamp_utc\":%lu,\"forecast_timestamp_utc\":%llu,\"status\":\"%s\","
    "\"research_only\":true,\"field_validated\":false,\"calibrated\":false,"
    "\"history_rows\":%u,\"history_required\":25,\"latency_us\":%lu,\"forecast_6h\":",
    static_cast<unsigned long>(timestamp),static_cast<unsigned long long>(timestamp)+21600ULL,
    mandi_v2::status_name(result.status),result.history_rows,static_cast<unsigned long>(latency));
  array_json(result.forecast,6);
  Serial.print(",\"weather_patterns\":{\"model_id\":\"");Serial.print(mandi_v2::kPatternModelId);Serial.print("\",\"profile_sha256\":\"");Serial.print(mandi_v2::kPatternProfileSha256);Serial.print("\",\"score_kind\":\"synthetic_pattern_score_not_event_probability\",\"field_validated\":false,\"calibrated\":false,\"probability\":null,\"status\":");
  if(!result.patterns.available) Serial.print("\"UNAVAILABLE\",\"scores\":null,\"matched\":[]}");
  else {
    Serial.print("\"SYNTHETIC_PATTERN_SCORES_ONLY\",\"scores\":{");
    for(int j=0;j<mandi_v2::kPatternCount;++j){if(j)Serial.print(',');Serial.printf("\"%s\":%.8f",mandi_v2::kPatternNames[j],result.patterns.scores[j]);}
    Serial.print("},\"matched\":["); bool first=true;
    for(int j=0;j<mandi_v2::kPatternCount;++j)if(result.patterns.matched[j]){if(!first)Serial.print(',');Serial.printf("\"%s\"",mandi_v2::kPatternNames[j]);first=false;}
    Serial.print("]}");
  }
  Serial.print(",\"hazard_scenarios\":{\"score_kind\":\"conditional_simulation_fraction\",\"horizon_hours\":6,\"field_validated\":false,\"calibrated\":false,\"probability\":null,\"public_alerts_enabled\":false,\"model_id\":\"");
  Serial.print(mandi_v2::kScenarioModelId);Serial.print("\",\"config_sha256\":\"");Serial.print(mandi_v2::kScenarioConfigSha256);Serial.print("\",\"rng\":\"indra_xorshift64star_boxmuller_v1\",\"seed\":");
  if(!result.scenarios.available) Serial.print("null,\"status\":\"UNAVAILABLE\",\"targets\":[]}");
  else {
    Serial.printf("%llu,\"status\":\"SYNTHETIC_SCENARIOS_ONLY\",\"draws_per_family\":%u,\"targets\":[",static_cast<unsigned long long>(result.scenarios.seed),mandi_v2::kScenarioDraws);
    const char* targets[3]={"cloudburst","flash_flood","landslide"};const char* families[3]={"drier","central","wetter"};
    for(int j=0;j<3;++j){if(j)Serial.print(',');Serial.printf("{\"id\":\"%s\",\"scenario_fraction\":%.8f,\"assumption_cases\":{",targets[j],result.scenarios.fraction[1][j]);for(int f=0;f<3;++f){if(f)Serial.print(',');Serial.printf("\"%s\":%.8f",families[f],result.scenarios.fraction[f][j]);}Serial.print("}}");}
    Serial.print("],\"unknown_drivers\":[\"observed_rainfall\",\"rainfall_footprint\",\"soil_wetness\",\"terrain_susceptibility\",\"catchment_area\",\"drainage_capacity\"]}");
  }
  Serial.println('}');
}
bool close_to(const double* actual,const double* expected,int count,double tolerance) {
  for(int i=0;i<count;++i) if(!std::isfinite(actual[i]) || std::abs(actual[i]-expected[i])>tolerance) return false;
  return true;
}
void self_test() {
  mandi_v2::Runtime test;
  mandi_v2::Result result;
  for(int i=0;i<25;++i) result=test.push(1767225600UL+i*3600UL,mandi_v2::kSelfTestRows[i]);
  bool pattern_ok=result.patterns.available;
  if(pattern_ok)for(int i=0;i<10;++i)if(std::abs(result.patterns.scores[i]-mandi_v2::kSelfTestPatternExpected[i])>0.002)pattern_ok=false;
  bool scenarios_ok=result.scenarios.available;
  if(scenarios_ok)for(int f=0;f<3;++f)for(int j=0;j<3;++j)if(result.scenarios.fraction[f][j]<0||result.scenarios.fraction[f][j]>1)scenarios_ok=false;
  self_test_passed=result.status==mandi_v2::Status::Ready && close_to(result.forecast,mandi_v2::kSelfTestExpected,6,0.03) && pattern_ok && scenarios_ok;
  Serial.printf("{\"self_test\":\"%s\",\"model_id\":\"india_mandi_tabular_v2\",\"fixture\":\"synthetic_software_vector\",\"free_heap\":%u}\n",
    self_test_passed?"PASS":"FAIL",ESP.getFreeHeap());
}
bool parse(char* text,uint32_t& timestamp,double* raw) {
  if(*text<'0'||*text>'9') return false;
  char* end; errno=0; unsigned long ts=strtoul(text,&end,10);
  if(errno||!ts||ts>UINT32_MAX||*end!=',') return false;
  timestamp=static_cast<uint32_t>(ts); text=end+1;
  for(int i=0;i<6;++i) {
    errno=0; raw[i]=strtod(text,&end);
    if(errno||end==text||!std::isfinite(raw[i])) return false;
    if(i<5) { if(*end!=',') return false; text=end+1; }
    else if(*end!='\0') return false;
  }
  return true;
}
void handle() {
  if(!strcmp(line,"INFO")) { print_info(); return; }
  if(!strcmp(line,"SELFTEST")) { self_test(); print_info(); return; }
  if(!strcmp(line,"RESET")) { runtime.reset(); Serial.println("{\"reset\":true}"); return; }
  if(!self_test_passed) { Serial.println("{\"error\":\"SELF_TEST_FAILED\"}"); return; }
  uint32_t timestamp; double raw[6];
  if(!parse(line,timestamp,raw)) { Serial.println("{\"error\":\"INVALID_CSV\"}"); return; }
  uint32_t start=micros(); auto result=runtime.push(timestamp,raw);
  print_result(timestamp,result,micros()-start,raw);
}
void setup() {
  boot_id=esp_random(); Serial.begin(115200); delay(1200);
  Serial.println("INDRA Mandi v2 forecast + synthetic pattern/scenario firmware; research only");
  self_test(); print_info();
  Serial.println("Send INFO, SELFTEST, RESET or unix_seconds,T,RH,P,PM2.5,PM10,W (hourly)");
}
void loop() {
  unsigned budget=256;
  while(budget--&&Serial.available()) {
    const char c=static_cast<char>(Serial.read());
    if(c=='\r') continue;
    if(c=='\n') { line[used]=0; if(overflow) Serial.println("{\"error\":\"LINE_TOO_LONG\"}"); else if(used) handle(); used=0; overflow=false; }
    else if(static_cast<unsigned char>(c)<32||static_cast<unsigned char>(c)>126) overflow=true;
    else if(used+1<sizeof(line)&&!overflow) line[used++]=c;
    else overflow=true;
  }
  delay(1);
}
