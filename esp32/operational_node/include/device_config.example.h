#pragma once
#include "sensor_hub.h"
// Copy to ignored device_config.h and fill the actual wiring/profile privately.
// No GPIO, calibration, credential or RTC timezone is assumed correct.
inline NodeConfig make_device_config(){
  NodeConfig c;
  c.physical_mode=false;
  c.sda=c.scl=c.gps_rx=c.gps_tx=c.pms_rx=c.pms_tx=c.encoder_pin=-1;
  c.rtc_configured_utc=false;
  c.wind_curve_provided=false;
  c.surveyed_egm96_m=NAN;
  return c;
}
inline const char* device_node_id(){return "UNCONFIGURED";}
