#pragma once
// INDRA slave -> master radio frame (ESP-NOW, <= 250 bytes).
//
// Layout (little-endian, 128 bytes):
//   0  'I','S'           magic
//   2  version (1)
//   3  flags             bit0 clock valid, bit1 location from GPS, bit2 location present
//   4  node_id[24]       NUL-padded, [A-Za-z0-9_-]
//  28  boot_id  u32      random per boot (replay protection across reboots)
//  32  sequence u32      increments every frame
//  36  weather  f32[6]   temperature_c, relative_humidity_pct, pressure_hpa, pm25, pm10, wind (NaN = missing)
//  60  battery_v f32
//  64  latitude  f64
//  72  longitude f64
//  80  elevation f32
//  84  utc[21]           "YYYY-MM-DDTHH:MM:SSZ" or empty
// 105  reserved[7]
// 112  tag[16]           HMAC-SHA256(key, bytes 0..111) truncated to 16 bytes
//
// Without a shared key, frames are only checked for shape (tag all zero) and the
// master marks them "unsigned". Set the same 32-byte key on every board to sign.
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#if defined(ARDUINO)
#include <mbedtls/md.h>
#elif defined(INDRA_HOST_OPENSSL)
#include <openssl/hmac.h>
#endif

#define INDRA_ESPNOW_FRAME_BYTES 128
#define INDRA_ESPNOW_SIGNED_BYTES 112
#define INDRA_ESPNOW_NODE_CHARS 24
#define INDRA_ESPNOW_MAX_NODES 16

struct IndraReading {
  char node_id[INDRA_ESPNOW_NODE_CHARS + 1] = {0};
  uint32_t boot_id = 0, sequence = 0;
  float weather[6] = {NAN, NAN, NAN, NAN, NAN, NAN};
  float battery_v = NAN, elevation_m = NAN;
  double latitude = NAN, longitude = NAN;
  char utc[21] = {0};
  bool clock_valid = false, location_from_gps = false;
};

static inline bool indra_valid_node_id(const char* s) {
  size_t n = strnlen(s, INDRA_ESPNOW_NODE_CHARS + 1);
  if (n == 0 || n > INDRA_ESPNOW_NODE_CHARS) return false;
  for (size_t i = 0; i < n; ++i) {
    char c = s[i];
    bool ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '-';
    if (!ok) return false;
  }
  return true;
}

static inline bool indra_hmac16(const uint8_t* key, size_t key_len, const uint8_t* data, size_t len, uint8_t out[16]) {
  if (!key || key_len < 32) return false;
  uint8_t digest[32];
#if defined(ARDUINO)
  const mbedtls_md_info_t* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  if (!info || mbedtls_md_hmac(info, key, key_len, data, len, digest) != 0) return false;
#elif defined(INDRA_HOST_OPENSSL)
  unsigned n = 32;
  if (!HMAC(EVP_sha256(), key, (int)key_len, data, len, digest, &n) || n != 32) return false;
#else
  (void)data; (void)len; (void)digest;
  return false;  // fail closed without a crypto backend
#endif
  memcpy(out, digest, 16);
  return true;
}

static inline bool indra_frame_pack(const IndraReading& r, const uint8_t* key, size_t key_len,
                                    uint8_t frame[INDRA_ESPNOW_FRAME_BYTES]) {
  if (!indra_valid_node_id(r.node_id)) return false;
  memset(frame, 0, INDRA_ESPNOW_FRAME_BYTES);
  frame[0] = 'I'; frame[1] = 'S'; frame[2] = 1;
  bool has_location = isfinite(r.latitude) && isfinite(r.longitude);
  frame[3] = (r.clock_valid ? 1 : 0) | (r.location_from_gps ? 2 : 0) | (has_location ? 4 : 0);
  strncpy(reinterpret_cast<char*>(frame + 4), r.node_id, INDRA_ESPNOW_NODE_CHARS);
  memcpy(frame + 28, &r.boot_id, 4);
  memcpy(frame + 32, &r.sequence, 4);
  memcpy(frame + 36, r.weather, 24);
  memcpy(frame + 60, &r.battery_v, 4);
  memcpy(frame + 64, &r.latitude, 8);
  memcpy(frame + 72, &r.longitude, 8);
  memcpy(frame + 80, &r.elevation_m, 4);
  if (r.clock_valid) strncpy(reinterpret_cast<char*>(frame + 84), r.utc, 20);
  if (key_len) return indra_hmac16(key, key_len, frame, INDRA_ESPNOW_SIGNED_BYTES, frame + INDRA_ESPNOW_SIGNED_BYTES);
  return true;  // unsigned: tag stays zero
}

enum IndraFrameStatus { INDRA_FRAME_OK = 0, INDRA_FRAME_UNSIGNED, INDRA_FRAME_BAD_SHAPE, INDRA_FRAME_BAD_TAG };

static inline IndraFrameStatus indra_frame_unpack(const uint8_t* frame, int len, const uint8_t* key, size_t key_len,
                                                  IndraReading& r) {
  if (len != INDRA_ESPNOW_FRAME_BYTES || frame[0] != 'I' || frame[1] != 'S' || frame[2] != 1) return INDRA_FRAME_BAD_SHAPE;
  // A master without a key accepts frames but reports them as unsigned (unverified).
  IndraFrameStatus status = INDRA_FRAME_UNSIGNED;
  if (key_len) {
    uint8_t expect[16];
    if (!indra_hmac16(key, key_len, frame, INDRA_ESPNOW_SIGNED_BYTES, expect)) return INDRA_FRAME_BAD_TAG;
    uint8_t diff = 0;
    for (int i = 0; i < 16; ++i) diff |= expect[i] ^ frame[INDRA_ESPNOW_SIGNED_BYTES + i];
    if (diff) return INDRA_FRAME_BAD_TAG;
    status = INDRA_FRAME_OK;
  }
  r = IndraReading();
  memcpy(r.node_id, frame + 4, INDRA_ESPNOW_NODE_CHARS);
  r.node_id[INDRA_ESPNOW_NODE_CHARS] = 0;
  if (!indra_valid_node_id(r.node_id)) return INDRA_FRAME_BAD_SHAPE;
  memcpy(&r.boot_id, frame + 28, 4);
  memcpy(&r.sequence, frame + 32, 4);
  memcpy(r.weather, frame + 36, 24);
  memcpy(&r.battery_v, frame + 60, 4);
  memcpy(&r.latitude, frame + 64, 8);
  memcpy(&r.longitude, frame + 72, 8);
  memcpy(&r.elevation_m, frame + 80, 4);
  r.clock_valid = frame[3] & 1;
  r.location_from_gps = frame[3] & 2;
  if (!(frame[3] & 4)) r.latitude = r.longitude = NAN;
  if (r.clock_valid) { memcpy(r.utc, frame + 84, 20); r.utc[20] = 0; }
  return status;
}

// Replay / duplicate guard on the master: accept only increasing sequence per boot.
struct IndraPeerTrack {
  char node_id[INDRA_ESPNOW_NODE_CHARS + 1];
  uint32_t boot_id, last_sequence, received, lost;
  bool used;
};

static inline bool indra_accept_sequence(IndraPeerTrack* table, int size, const IndraReading& r) {
  int slot = -1, free_slot = -1;
  for (int i = 0; i < size; ++i) {
    if (table[i].used && strcmp(table[i].node_id, r.node_id) == 0) { slot = i; break; }
    if (!table[i].used && free_slot < 0) free_slot = i;
  }
  if (slot < 0) {
    if (free_slot < 0) return false;  // table full
    IndraPeerTrack& t = table[free_slot];
    memset(&t, 0, sizeof(t));
    strncpy(t.node_id, r.node_id, INDRA_ESPNOW_NODE_CHARS);
    t.used = true; t.boot_id = r.boot_id; t.last_sequence = r.sequence; t.received = 1;
    return true;
  }
  IndraPeerTrack& t = table[slot];
  if (r.boot_id != t.boot_id) {  // peer rebooted
    t.boot_id = r.boot_id; t.last_sequence = r.sequence; t.received++;
    return true;
  }
  if (r.sequence <= t.last_sequence) return false;  // duplicate or replay
  t.lost += r.sequence - t.last_sequence - 1;
  t.last_sequence = r.sequence; t.received++;
  return true;
}

// indra_weather_records_v1 JSON for one relayed reading (what /api/ingest accepts).
static inline int indra_reading_json(const IndraReading& r, const char* relay, int rssi_dbm, bool signed_ok,
                                     char* out, size_t cap) {
  static const char* channels[6] = {"temperature_c", "relative_humidity_pct", "pressure_hpa",
                                    "pm25_ug_m3", "pm10_ug_m3", "wind_speed_mps"};
  char num[32], lat[32], lon[32], elev[32], bat[32], stamp[32], rssi[16];
  auto fmt = [](char* b, size_t n, double v, int d) { if (isfinite(v)) snprintf(b, n, "%.*f", d, v); else snprintf(b, n, "null"); };
  fmt(lat, sizeof lat, r.latitude, 7); fmt(lon, sizeof lon, r.longitude, 7);
  fmt(elev, sizeof elev, r.elevation_m, 2); fmt(bat, sizeof bat, r.battery_v, 3);
  if (r.clock_valid) snprintf(stamp, sizeof stamp, "\"%s\"", r.utc); else snprintf(stamp, sizeof stamp, "null");
  if (rssi_dbm < 0) snprintf(rssi, sizeof rssi, "%d", rssi_dbm); else snprintf(rssi, sizeof rssi, "null");
  size_t used = snprintf(out, cap, "{\"schema_version\":\"indra_weather_records_v1\",\"observations\":[");
  for (int i = 0; i < 6 && used < cap; ++i) {
    fmt(num, sizeof num, r.weather[i], 4);
    used += snprintf(out + used, cap - used,
      "%s{\"node_id\":\"%s\",\"timestamp_utc\":%s,\"latitude\":%s,\"longitude\":%s,\"elevation_m\":%s,"
      "\"channel\":\"%s\",\"value\":%s,\"quality_flag\":\"%s\",\"battery_v\":%s,\"rssi_dbm\":%s,"
      "\"transport\":\"espnow\",\"relay\":\"%s\",\"sequence\":%lu,\"signed\":%s}",
      i ? "," : "", r.node_id, stamp, lat, lon, elev, channels[i], num, isfinite(r.weather[i]) ? "valid" : "missing",
      bat, rssi, relay, (unsigned long)r.sequence, signed_ok ? "true" : "false");
  }
  if (used < cap) used += snprintf(out + used, cap - used, "]}");
  return used < cap ? (int)used : -1;
}
