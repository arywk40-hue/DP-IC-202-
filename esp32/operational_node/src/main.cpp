// Compile/readout harness only. No credentials, pin assumptions or live radio.
#include <Arduino.h>
#include "sensor_hub.h"
#include "packet_auth.h"
#include "weather_payload.h"

static SensorHub hub;
#if __has_include("device_config.h")
#include "device_config.h"
static NodeConfig config=make_device_config();
#else
#include "device_config.example.h"
static NodeConfig config=make_device_config();
#endif
void setup(){Serial.begin(115200);hub.begin(config);Serial.println("INDRA driver preparation: NOT HARDWARE VALIDATED; physical IO/network disabled until explicit configuration");}
void loop(){
  hub.poll();static uint32_t last_ms=0;uint32_t now=millis();if(now-last_ms<1000)return;last_ms=now;
  NodeSnapshot s=hub.sample();
  Serial.printf("configured=%d clock=%d bme=%d pms=%d gps=%d ina=%d wind_available=%d\n",s.hardware_configured,s.clock_available,s.bme_ok,s.pms_ok,s.gps_fix,s.ina_ok,isfinite(s.weather[5]));
  String payload;if(indra_weather_payload(device_node_id(),s,payload))Serial.println(payload);
  // Exercise signing entry point with no key: it must refuse, never invent auth.
  String output;indra_signed_packet("A","unconfigured_nonce","",nullptr,0,"{}",output);
  yield();
}
