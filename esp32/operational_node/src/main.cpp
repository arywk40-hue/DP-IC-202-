// INDRA physical sensor node. One codebase, three build roles (platformio.ini):
//
//   operational-driver-preparation  standalone: USB serial JSON (+ optional WiFi upload)
//   mesh-slave   (INDRA_ROLE=2)      reads sensors, sends a signed 128-byte frame to the master over ESP-NOW
//   mesh-master  (INDRA_ROLE=1)      reads its own sensors, receives slave frames, prints every reading as
//                                    one JSON line on USB (server/scripts/serial_bridge.py forwards them),
//                                    and uploads over WiFi too if configured.
//
// Every board prints "INDRA node <id> role=<role> mac=<MAC>" at boot: put the master's MAC
// into each slave's device_config.h for acknowledged (unicast) delivery; otherwise slaves broadcast.
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_arduino_version.h>
#include <time.h>
#include "sensor_hub.h"
#include "weather_payload.h"
#include "indra_espnow.h"
#if __has_include("device_config.h")
#include "device_config.h"
#else
#include "device_config.example.h"
#endif

#ifndef INDRA_ROLE
#define INDRA_ROLE 0
#endif
#define ROLE_STANDALONE 0
#define ROLE_MASTER 1
#define ROLE_SLAVE 2
static const char* role_name(){return INDRA_ROLE==ROLE_MASTER?"master":INDRA_ROLE==ROLE_SLAVE?"slave":"standalone";}

static SensorHub hub;
static NodeConfig config=make_device_config();
static bool hardware_ready=false, ntp_started=false;
static uint32_t last_sample_ms=0, last_upload_ms=0, last_wifi_attempt_ms=0, last_status_ms=0, last_radio_ms=0;
static int last_http_code=0;
static uint32_t uploads_ok=0, uploads_failed=0;
static String latest_payload;

// ---- shared key (64 hex chars in device_config.h; empty = unsigned frames) ----
static uint8_t mesh_key[32];
static size_t mesh_key_len=0;
static void load_mesh_key(){
  const char* hex=indra_mesh_key_hex();
  if(strlen(hex)!=64){mesh_key_len=0;return;}
  for(int i=0;i<32;++i){
    char b[3]={hex[2*i],hex[2*i+1],0};char* end=nullptr;
    mesh_key[i]=(uint8_t)strtoul(b,&end,16);
    if(end!=b+2){mesh_key_len=0;return;}
  }
  mesh_key_len=32;
}

static bool parse_mac(const char* text,uint8_t mac[6]){
  unsigned v[6];
  if(sscanf(text,"%x:%x:%x:%x:%x:%x",&v[0],&v[1],&v[2],&v[3],&v[4],&v[5])!=6)return false;
  for(int i=0;i<6;++i){if(v[i]>255)return false;mac[i]=(uint8_t)v[i];}
  return true;
}

static void set_radio_channel(uint8_t channel){
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(channel,WIFI_SECOND_CHAN_NONE);
  esp_wifi_set_promiscuous(false);
}

// ---- WiFi upload (standalone or master) ----
static bool wifi_enabled(){return INDRA_ROLE!=ROLE_SLAVE&&strlen(indra_wifi_ssid())>0&&strlen(indra_server_url())>0;}

static void maintain_wifi(uint32_t now){
  if(!wifi_enabled())return;
  if(WiFi.status()==WL_CONNECTED){
    if(!ntp_started){configTime(0,0,"pool.ntp.org","time.google.com");ntp_started=true;}
    return;
  }
  if(now-last_wifi_attempt_ms<15000&&last_wifi_attempt_ms!=0)return;
  last_wifi_attempt_ms=now;
  WiFi.begin(indra_wifi_ssid(),indra_wifi_password());
}

static void upload(const String& payload){
  HTTPClient http;
  http.setTimeout(4000);
  String url=String(indra_server_url());
  if(url.endsWith("/"))url.remove(url.length()-1);
  if(!http.begin(url+"/api/ingest")){uploads_failed++;last_http_code=-1;return;}
  http.addHeader("Content-Type","application/json");
  if(strlen(indra_ingest_token())>0)http.addHeader("X-Indra-Token",indra_ingest_token());
  last_http_code=http.POST(payload);
  if(last_http_code==200)uploads_ok++;
  else{
    uploads_failed++;
    if(last_http_code>0)Serial.printf("upload rejected http=%d %s\n",last_http_code,http.getString().substring(0,160).c_str());
  }
  http.end();
}

static IndraReading reading_from(const NodeSnapshot& s){
  IndraReading r;
  strncpy(r.node_id,device_node_id(),INDRA_ESPNOW_NODE_CHARS);
  for(int i=0;i<6;++i)r.weather[i]=s.weather[i];
  r.battery_v=s.ina_ok?s.bus_voltage_v:NAN;
  r.latitude=s.latitude;r.longitude=s.longitude;r.elevation_m=s.elevation_m;
  r.clock_valid=s.clock_available;r.location_from_gps=s.location_from_gps;
  if(s.clock_available)strncpy(r.utc,s.utc,20);
  return r;
}

// =============================== SLAVE =======================================
#if INDRA_ROLE==ROLE_SLAVE
static uint8_t master_mac[6]={0xff,0xff,0xff,0xff,0xff,0xff};
static bool unicast=false;
static uint32_t boot_id=0, sequence=0, sent_ok=0, sent_failed=0;

static void radio_setup(){
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  set_radio_channel(indra_espnow_channel());
  if(esp_now_init()!=ESP_OK){Serial.println("ERROR: esp_now_init failed");return;}
  unicast=parse_mac(indra_master_mac(),master_mac);
  esp_now_peer_info_t peer={};
  memcpy(peer.peer_addr,master_mac,6);
  peer.channel=0;peer.encrypt=false;
  if(esp_now_add_peer(&peer)!=ESP_OK)Serial.println("ERROR: could not add master peer");
  boot_id=esp_random();
}

static void radio_send(const NodeSnapshot& s){
  if(!s.hardware_configured)return;
  IndraReading r=reading_from(s);
  r.boot_id=boot_id;r.sequence=++sequence;
  uint8_t frame[INDRA_ESPNOW_FRAME_BYTES];
  if(!indra_frame_pack(r,mesh_key,mesh_key_len,frame)){sent_failed++;return;}
  if(esp_now_send(master_mac,frame,sizeof frame)==ESP_OK)sent_ok++;else sent_failed++;
}
#endif

// =============================== MASTER ======================================
#if INDRA_ROLE==ROLE_MASTER
struct RxSlot{uint8_t data[INDRA_ESPNOW_FRAME_BYTES];int len;int rssi;bool full;};
static RxSlot rx_ring[8];
static volatile uint8_t rx_head=0, rx_tail=0;
static portMUX_TYPE rx_lock=portMUX_INITIALIZER_UNLOCKED;
static IndraPeerTrack peers[INDRA_ESPNOW_MAX_NODES];
static uint32_t rx_dropped=0, rx_bad=0, rx_unsigned=0, rx_replayed=0;
static char relay_json[2600];
static String upload_queue[8];
static uint8_t upload_count=0;

static void store_frame(const uint8_t* data,int len,int rssi){
  portENTER_CRITICAL(&rx_lock);
  uint8_t next=(rx_head+1)%8;
  if(next==rx_tail||len!=INDRA_ESPNOW_FRAME_BYTES){rx_dropped++;portEXIT_CRITICAL(&rx_lock);return;}
  memcpy(rx_ring[rx_head].data,data,len);rx_ring[rx_head].len=len;rx_ring[rx_head].rssi=rssi;
  rx_head=next;
  portEXIT_CRITICAL(&rx_lock);
}
#if ESP_ARDUINO_VERSION_MAJOR>=3
static void on_receive(const esp_now_recv_info_t* info,const uint8_t* data,int len){
  store_frame(data,len,info&&info->rx_ctrl?info->rx_ctrl->rssi:0);
}
#else
static void on_receive(const uint8_t* mac,const uint8_t* data,int len){(void)mac;store_frame(data,len,0);}
#endif

static void radio_setup(){
  WiFi.mode(WIFI_STA);
  if(!wifi_enabled()){WiFi.disconnect();set_radio_channel(indra_espnow_channel());}
  if(esp_now_init()!=ESP_OK){Serial.println("ERROR: esp_now_init failed");return;}
  esp_now_register_recv_cb(on_receive);
  memset(peers,0,sizeof peers);
}

static void queue_upload(const char* json){
  if(!wifi_enabled())return;
  if(upload_count<8)upload_queue[upload_count++]=String(json);
}

static void radio_drain(){
  while(true){
    RxSlot slot;
    portENTER_CRITICAL(&rx_lock);
    if(rx_tail==rx_head){portEXIT_CRITICAL(&rx_lock);break;}
    slot=rx_ring[rx_tail];rx_tail=(rx_tail+1)%8;
    portEXIT_CRITICAL(&rx_lock);
    IndraReading r;
    IndraFrameStatus status=indra_frame_unpack(slot.data,slot.len,mesh_key,mesh_key_len,r);
    if(status==INDRA_FRAME_BAD_SHAPE||status==INDRA_FRAME_BAD_TAG){rx_bad++;continue;}
    if(status==INDRA_FRAME_UNSIGNED)rx_unsigned++;
    if(!indra_accept_sequence(peers,INDRA_ESPNOW_MAX_NODES,r)){rx_replayed++;continue;}
    if(indra_reading_json(r,device_node_id(),slot.rssi,status==INDRA_FRAME_OK,relay_json,sizeof relay_json)>0){
      Serial.println(relay_json);
      queue_upload(relay_json);
    }
  }
}

static void print_peers(){
  for(int i=0;i<INDRA_ESPNOW_MAX_NODES;++i)if(peers[i].used)
    Serial.printf("peer %s received=%lu lost=%lu last_seq=%lu\n",peers[i].node_id,
      (unsigned long)peers[i].received,(unsigned long)peers[i].lost,(unsigned long)peers[i].last_sequence);
}
#endif

// ================================ COMMON =====================================
void setup(){
  Serial.begin(115200);
  delay(200);
  load_mesh_key();
  hardware_ready=hub.begin(config);
#if INDRA_ROLE!=ROLE_STANDALONE
  radio_setup();
#else
  WiFi.mode(WIFI_STA);
#endif
  Serial.printf("INDRA node %s role=%s mac=%s hardware=%s channel=%u key=%s wifi=%s\n",device_node_id(),role_name(),
                WiFi.macAddress().c_str(),hardware_ready?"configured":"NOT CONFIGURED (edit include/device_config.h)",
                (unsigned)indra_espnow_channel(),mesh_key_len?"set":"none (unsigned frames)",
                wifi_enabled()?indra_wifi_ssid():"off");
  if(strcmp(device_node_id(),"UNCONFIGURED")==0)
    Serial.println("WARNING: node id is UNCONFIGURED; the server will reject readings until INDRA_NODE_ID is set");
#if INDRA_ROLE==ROLE_SLAVE
  Serial.printf("sending to %s\n",unicast?indra_master_mac():"broadcast (set indra_master_mac() for acknowledged delivery)");
#endif
}

void loop(){
  const uint32_t now=millis();
  hub.poll();
  maintain_wifi(now);
#if INDRA_ROLE==ROLE_MASTER
  radio_drain();
#endif

  if(now-last_sample_ms>=1000){
    last_sample_ms=now;
    NodeSnapshot s=hub.sample();
    String payload;
    if(indra_weather_payload(device_node_id(),s,payload)){
#if INDRA_ROLE!=ROLE_SLAVE
      Serial.println(payload);  // slaves stay quiet on USB unless debugging, see status line
#endif
      latest_payload=payload;
    }
#if INDRA_ROLE==ROLE_SLAVE
    if(now-last_radio_ms>=indra_slave_interval_ms()){last_radio_ms=now;radio_send(s);}
#endif
    if(now-last_status_ms>=10000){
      last_status_ms=now;
      Serial.printf("status node=%s role=%s configured=%d bme=%d pms=%d gps_fix=%d ina=%d clock=%s",
        device_node_id(),role_name(),s.hardware_configured,s.bme_ok,s.pms_ok,s.gps_fix,s.ina_ok,
        !s.clock_available?"none":s.clock_from_ntp?"ntp":s.rtc_ok?"rtc":"gps");
#if INDRA_ROLE==ROLE_SLAVE
      Serial.printf(" radio_sent=%lu radio_failed=%lu seq=%lu\n",(unsigned long)sent_ok,(unsigned long)sent_failed,(unsigned long)sequence);
#elif INDRA_ROLE==ROLE_MASTER
      Serial.printf(" rx_bad=%lu rx_unsigned=%lu rx_replayed=%lu rx_dropped=%lu http=%d\n",(unsigned long)rx_bad,
        (unsigned long)rx_unsigned,(unsigned long)rx_replayed,(unsigned long)rx_dropped,last_http_code);
      print_peers();
#else
      Serial.printf(" wifi=%s http=%d ok=%lu failed=%lu\n",
        !wifi_enabled()?"off":WiFi.status()==WL_CONNECTED?WiFi.localIP().toString().c_str():"connecting",
        last_http_code,(unsigned long)uploads_ok,(unsigned long)uploads_failed);
#endif
    }
  }

  if(wifi_enabled()&&WiFi.status()==WL_CONNECTED&&now-last_upload_ms>=indra_upload_interval_ms()){
    last_upload_ms=now;
    if(latest_payload.length())upload(latest_payload);
#if INDRA_ROLE==ROLE_MASTER
    for(uint8_t i=0;i<upload_count;++i)upload(upload_queue[i]);
    upload_count=0;
#endif
  }
  yield();
}
