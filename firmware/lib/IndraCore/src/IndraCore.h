#pragma once

#include <stddef.h>
#include <stdint.h>

namespace indra {

constexpr size_t kSensorOnlyFeatureCount = 14;
constexpr const char* kSchemaVersion = "sensor_only_v1";
constexpr const char* kModelChecksum = "NOT_READY-no-trained-model";

enum class SensorStatus : uint8_t { Valid, Missing, Stale, Invalid, OutOfRange };
enum class ModelStatus : uint8_t { NotReady, MissingRequiredFeature };

struct Reading {
  float value;
  SensorStatus status;
  uint32_t sampled_at_ms;
};

struct ClockTime {
  uint16_t year;
  uint16_t day_of_year;
  uint8_t hour;
  SensorStatus status;
};

struct SensorSnapshot {
  Reading temperature_c;
  Reading relative_humidity_pct;
  Reading pressure_hpa;
  Reading wind_speed_mps;
  Reading pm1_ug_m3;
  Reading pm25_ug_m3;
  Reading pm10_ug_m3;
  Reading latitude_deg;
  Reading longitude_deg;
  Reading altitude_m;
  Reading battery_voltage_v;
  Reading battery_current_ma;
  Reading battery_power_mw;
  ClockTime time;
};

struct FeatureVector {
  float values[kSensorOnlyFeatureCount];
};

struct ModelResult {
  ModelStatus status;
  const char* missing_feature;
  const char* schema_version;
  const char* model_checksum;
};

class FeatureBuilder {
 public:
  bool build(const SensorSnapshot& snapshot, FeatureVector* output, ModelResult* result);

 private:
  bool has_pressure_history_ = false;
  float previous_pressure_hpa_ = 0.0f;
  uint32_t previous_pressure_ms_ = 0;
};

bool is_valid(SensorStatus status);
const char* status_name(SensorStatus status);
const char* model_status_name(ModelStatus status);

}  // namespace indra
