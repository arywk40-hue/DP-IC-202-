#pragma once
#include "sensor_hub.h"
// Copy to ignored device_config.h. No physical pin/calibration/clock assumptions.
struct HimachalConfig {
  NodeConfig sensors;
  bool native_cadence_verified=false,calibration_verified=false,site_verified=false;
  bool terrain_reviewed=false,terrain_exposed=false;
  uint32_t cadence_seconds=60; // SERIAL SYNTHETIC DEMO only until verified.
  float clock_uncertainty_seconds=NAN;
};
inline HimachalConfig himachal_device_config(){
  HimachalConfig c;
  c.sensors.physical_mode=false;
  c.sensors.sda=c.sensors.scl=c.sensors.gps_rx=c.sensors.gps_tx=-1;
  c.sensors.pms_rx=c.sensors.pms_tx=c.sensors.encoder_pin=-1;
  return c;
}
