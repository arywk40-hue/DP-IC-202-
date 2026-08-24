#pragma once

#include <stddef.h>
#include <stdint.h>
#include <math.h>

namespace indra {

constexpr size_t kSensorOnlyFeatureCount = 14;
constexpr const char* kSchemaVersion = "sensor_only_v1";
constexpr const char* kSchemaChecksum = "a85fd11ea784026b6b27a0157a4498567102e71c82b9e689ddcbbb5698c2c441";
constexpr const char* kModelChecksum = "NOT_READY-no-trained-model";

enum class SensorStatus : uint8_t { Valid, Missing, Stale, Invalid, OutOfRange };
enum class ModelStatus : uint8_t { NotReady, MissingRequiredFeature };

struct Reading {
  float value;
  SensorStatus status;
  uint32_t sampled_at_ms;
  Reading() : value(NAN), status(SensorStatus::Missing), sampled_at_ms(0) {}
  Reading(float reading_value, SensorStatus reading_status, uint32_t sampled_at)
      : value(reading_value), status(reading_status), sampled_at_ms(sampled_at) {}
};

struct ClockTime {
  uint16_t year;
  uint16_t day_of_year;
  uint8_t hour;
  SensorStatus status;
  ClockTime() : year(0), day_of_year(0), hour(0), status(SensorStatus::Missing) {}
  ClockTime(uint16_t clock_year, uint16_t clock_day, uint8_t clock_hour, SensorStatus clock_status)
      : year(clock_year), day_of_year(clock_day), hour(clock_hour), status(clock_status) {}
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
  ClockTime gps_time;
};

struct FeatureVector {
  float values[kSensorOnlyFeatureCount];
};

struct ModelResult {
  ModelStatus status;
  const char* missing_feature;
  const char* schema_version;
  const char* schema_checksum;
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
