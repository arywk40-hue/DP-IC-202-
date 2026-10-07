#pragma once
// Hardware backends are prepared, never calibrated/validated by compilation.
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_BME280.h>
#include <Adafruit_INA219.h>
#include <RTClib.h>
#include <TinyGPSPlus.h>
#include <math.h>

struct NodeConfig {
  int sda=-1, scl=-1, gps_rx=-1, gps_tx=-1, pms_rx=-1, pms_tx=-1, encoder_pin=-1;
  uint8_t bme_address=0x76, ina_address=0x40;
  uint32_t gps_baud=9600, pms_baud=9600, counted_edges_per_revolution=600;
  bool physical_mode=false, rtc_configured_utc=false, wind_curve_provided=false;
  float wind_mps_per_rps=NAN, wind_intercept=NAN, surveyed_egm96_m=NAN;
};
struct NodeSnapshot {
  float weather[6]={NAN,NAN,NAN,NAN,NAN,NAN};
  double latitude=NAN,longitude=NAN;
  float elevation_m=NAN,bus_voltage_v=NAN,current_ma=NAN,power_mw=NAN;
  char utc[25]={0}; bool clock_available=false,hardware_configured=false;
  bool bme_ok=false,pms_ok=false,rtc_ok=false,gps_fix=false,ina_ok=false;
};
class SensorHub {
 public:
  bool begin(const NodeConfig& c) {
    config=c;
    if (!c.physical_mode) return false;
    int pins[]={c.sda,c.scl,c.gps_rx,c.gps_tx,c.pms_rx,c.pms_tx,c.encoder_pin};
    for(int i=0;i<7;++i){if(pins[i]<0||pins[i]>48)return false;for(int j=0;j<i;++j)if(pins[i]==pins[j])return false;}
    Wire.begin(c.sda,c.scl);Wire.setTimeOut(50);
    gps_serial.begin(c.gps_baud,SERIAL_8N1,c.gps_rx,c.gps_tx);
    pms_serial.begin(c.pms_baud,SERIAL_8N1,c.pms_rx,c.pms_tx);
    bme_ready=bme.begin(c.bme_address,&Wire);rtc_ready=rtc.begin(&Wire);
    ina=Adafruit_INA219(c.ina_address);ina_ready=ina.begin(&Wire);
    pinMode(c.encoder_pin,INPUT_PULLUP);attachInterrupt(c.encoder_pin,pulse,RISING);
    configured=true;last_counter_ms=millis();return true;
  }
  void poll() {
    if(!configured)return;
    // Bounded UART consumption; no blocking readBytes or delay loops.
    for(int i=0;i<256&&gps_serial.available();++i)gps.encode(gps_serial.read());
    for(int i=0;i<128&&pms_serial.available();++i)consume_pm(pms_serial.read());
  }
  NodeSnapshot sample() {
    NodeSnapshot s;s.hardware_configured=configured;
    if(!configured)return s;
    s.bme_ok=bme_ready;
    if(bme_ready){s.weather[0]=bme.readTemperature();s.weather[1]=bme.readHumidity();s.weather[2]=bme.readPressure()/100.f;}
    s.pms_ok=pm_valid && uint32_t(millis()-pm_ms)<10000;
    if(s.pms_ok){s.weather[3]=pm25;s.weather[4]=pm10;}
    uint32_t now=millis(),elapsed=now-last_counter_ms,count=encoder_counter,delta=count-last_counter;
    last_counter=count;last_counter_ms=now;
    if(elapsed&&config.counted_edges_per_revolution&&config.wind_curve_provided&&isfinite(config.wind_mps_per_rps)&&config.wind_mps_per_rps>0&&isfinite(config.wind_intercept)){
      const float rps=double(delta)*1000.0/(double(elapsed)*config.counted_edges_per_revolution);
      const float wind=config.wind_mps_per_rps*rps+config.wind_intercept;
      if(wind>=0&&wind<=100)s.weather[5]=wind;
    }
    s.gps_fix=gps.location.isValid()&&gps.location.age()<5000;
    if(s.gps_fix){s.latitude=gps.location.lat();s.longitude=gps.location.lng();}
    // Receiver GGA/MSL/ellipsoid height is never silently tagged EGM96.
    if(isfinite(config.surveyed_egm96_m))s.elevation_m=config.surveyed_egm96_m;
    if(gps.date.isValid()&&gps.time.isValid()&&gps.time.age()<5000){
      snprintf(s.utc,sizeof(s.utc),"%04d-%02d-%02dT%02d:%02d:%02dZ",gps.date.year(),gps.date.month(),gps.date.day(),gps.time.hour(),gps.time.minute(),gps.time.second());s.clock_available=true;
    } else if(rtc_ready&&config.rtc_configured_utc&&!rtc.lostPower()){
      DateTime t=rtc.now();snprintf(s.utc,sizeof(s.utc),"%04d-%02d-%02dT%02d:%02d:%02dZ",t.year(),t.month(),t.day(),t.hour(),t.minute(),t.second());s.clock_available=true;s.rtc_ok=true;
    }
    s.ina_ok=ina_ready;
    if(ina_ready){s.bus_voltage_v=ina.getBusVoltage_V();s.current_ma=ina.getCurrent_mA();s.power_mw=ina.getPower_mW();}
    return s;
  }
 private:
  NodeConfig config;bool configured=false,bme_ready=false,rtc_ready=false,ina_ready=false;
  Adafruit_BME280 bme;Adafruit_INA219 ina;RTC_DS3231 rtc;TinyGPSPlus gps;
  HardwareSerial gps_serial{1},pms_serial{2};uint8_t pm_frame[32]={0};uint8_t pm_used=0;
  bool pm_valid=false;float pm25=NAN,pm10=NAN;uint32_t pm_ms=0,last_counter=0,last_counter_ms=0;
  static volatile uint32_t encoder_counter;
  static void IRAM_ATTR pulse();
  void consume_pm(uint8_t value){
    if(pm_used==0&&value!=0x42)return;
    if(pm_used==1&&value!=0x4d){pm_used=value==0x42?1:0;return;}
    pm_frame[pm_used++]=value;
    if(pm_used!=32)return;
    pm_used=0;uint16_t sum=0;for(int i=0;i<30;++i)sum+=pm_frame[i];
    if(pm_frame[2]!=0||pm_frame[3]!=28||sum!=uint16_t(pm_frame[30]*256+pm_frame[31])){pm_valid=false;return;}
    pm25=pm_frame[12]*256+pm_frame[13];pm10=pm_frame[14]*256+pm_frame[15];pm_valid=true;pm_ms=millis();
  }
};
DRAM_ATTR volatile uint32_t SensorHub::encoder_counter=0;
void IRAM_ATTR SensorHub::pulse(){++encoder_counter;}
