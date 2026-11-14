#pragma once
#include "sensor_hub.h"
// =============================================================================
// Per-board configuration.
//
//   cp include/device_config.example.h include/device_config.h   (git-ignored)
//
// then edit device_config.h for THIS board. Nothing here is assumed correct:
// with physical_mode=false the firmware only prints a status line and sends nothing.
// =============================================================================

// ---- Identity ---------------------------------------------------------------
// Unique per board: letters, digits, - and _. flash_esp32.py --node-id N sets
// INDRA_NODE_ID at build time; a value set here wins over that.
#ifndef INDRA_NODE_ID
#define INDRA_NODE_ID "UNCONFIGURED"
#endif
inline const char* device_node_id(){return INDRA_NODE_ID;}

// ---- Master/slave radio (ESP-NOW) ---------------------------------------------
// Used by the mesh-master and mesh-slave builds; ignored by the standalone build.
// Channel: identical on ALL boards. If the master also joins WiFi, set this to the
// router's channel (the master's radio must follow the router).
inline uint8_t indra_espnow_channel(){return 1;}
// Shared secret, identical on ALL boards: 64 hex characters (32 bytes). Generate with
//   python3 -c "import secrets; print(secrets.token_hex(32))"
// Empty = frames are sent unsigned and the master marks them "signed": false.
inline const char* indra_mesh_key_hex(){return "";}
// Slaves only: the master's MAC as printed at its boot ("mac=AA:BB:..."). Empty = broadcast
// (works, but without delivery acknowledgement/retries).
inline const char* indra_master_mac(){return "";}
inline uint32_t indra_slave_interval_ms(){return 10000;}

// ---- WiFi upload (optional; standalone or master only) ---------------------------
// Leave the SSID empty to use USB only (server/scripts/serial_bridge.py).
// The server URL must be reachable from the board: use your computer's LAN IP,
// not 127.0.0.1, and start the server with --host 0.0.0.0.
inline const char* indra_wifi_ssid(){return "";}
inline const char* indra_wifi_password(){return "";}
inline const char* indra_server_url(){return "";}      // e.g. "http://192.168.1.20:8080"
inline const char* indra_ingest_token(){return "";}    // must match server --ingest-token, if set
inline uint32_t indra_upload_interval_ms(){return 10000;}

// ---- Wiring --------------------------------------------------------------------
// The commented values are a COMMON ESP32-S3 DevKitC-1 layout, not your board.
// Check every pin against how you actually wired it. -1 = sensor not fitted.
inline NodeConfig make_device_config(){
  NodeConfig c;
  c.physical_mode=false;          // set true once the pins below match your wiring

  c.sda=-1;          // e.g. 8   BME280 + INA219 + DS3231 share this I2C bus (required)
  c.scl=-1;          // e.g. 9
  c.bme_address=0x76;             // 0x77 on some BME280 breakouts (SDO high)
  c.ina_address=0x40;

  c.pms_rx=-1;       // e.g. 18  ESP32 RX  <- PMS5003/7003 TX   (-1 = no PM sensor)
  c.pms_tx=-1;       // e.g. 17  ESP32 TX  -> PMS SET/RX (optional)

  c.gps_rx=-1;       // e.g. 16  ESP32 RX  <- GPS TX             (-1 = no GPS)
  c.gps_tx=-1;       // e.g. 15

  c.encoder_pin=-1;  // e.g. 4   anemometer pulse output         (-1 = no anemometer)
  c.counted_edges_per_revolution=600;
  c.wind_curve_provided=false;    // set true only with a real calibration:
  c.wind_mps_per_rps=NAN;         //   wind_mps = wind_mps_per_rps * rev_per_s + wind_intercept
  c.wind_intercept=NAN;

  c.rtc_configured_utc=false;     // true only if the DS3231 was set to UTC
  c.surveyed_egm96_m=NAN;         // site elevation in metres; enables lapse-rate maths
  c.fixed_latitude=NAN;           // site position for a board without GPS
  c.fixed_longitude=NAN;
  return c;
}
