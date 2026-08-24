#include "IndraCore.h"

#include <math.h>

namespace indra {
namespace {

float dew_point_c(float temperature_c, float humidity_pct) {
  constexpr float kA = 17.27f;
  constexpr float kB = 237.7f;
  const float gamma = (kA * temperature_c) / (kB + temperature_c) + logf(humidity_pct / 100.0f);
  return (kB * gamma) / (kA - gamma);
}

float heat_index_c(float temperature_c, float humidity_pct) {
  if (temperature_c < 26.7f || humidity_pct < 40.0f) return temperature_c;
  const float f = temperature_c * 9.0f / 5.0f + 32.0f;
  const float hi_f = -42.379f + 2.04901523f * f + 10.14333127f * humidity_pct
      - 0.22475541f * f * humidity_pct - 0.00683783f * f * f
      - 0.05481717f * humidity_pct * humidity_pct + 0.00122874f * f * f * humidity_pct
      + 0.00085282f * f * humidity_pct * humidity_pct - 0.00000199f * f * f * humidity_pct * humidity_pct;
  return (hi_f - 32.0f) * 5.0f / 9.0f;
}

bool required(const Reading& reading, const char** missing, const char* name) {
  if (is_valid(reading.status) && isfinite(reading.value)) return true;
  *missing = name;
  return false;
}

}  // namespace

bool is_valid(SensorStatus status) { return status == SensorStatus::Valid; }

const char* status_name(SensorStatus status) {
  switch (status) {
    case SensorStatus::Valid: return "valid";
    case SensorStatus::Missing: return "missing";
    case SensorStatus::Stale: return "stale";
    case SensorStatus::Invalid: return "invalid";
    case SensorStatus::OutOfRange: return "out_of_range";
  }
  return "invalid";
}

const char* model_status_name(ModelStatus status) {
  return status == ModelStatus::NotReady ? "NOT_READY" : "missing_required_feature";
}

bool FeatureBuilder::build(const SensorSnapshot& s, FeatureVector* output, ModelResult* result) {
  if (output == nullptr || result == nullptr) return false;
  result->schema_version = kSchemaVersion;
  result->schema_checksum = kSchemaChecksum;
  result->model_checksum = kModelChecksum;
  result->missing_feature = nullptr;
  const char* missing = nullptr;
  if (!required(s.temperature_c, &missing, "temperature_c") ||
      !required(s.relative_humidity_pct, &missing, "relative_humidity_pct") ||
      !required(s.pressure_hpa, &missing, "pressure_hpa") ||
      !required(s.wind_speed_mps, &missing, "wind_speed_mps") ||
      !required(s.pm25_ug_m3, &missing, "pm25_ug_m3") ||
      !required(s.latitude_deg, &missing, "latitude_deg") ||
      !required(s.longitude_deg, &missing, "longitude_deg") ||
      !is_valid(s.time.status) || s.time.hour > 23 || s.time.day_of_year == 0 || s.time.day_of_year > 366) {
    result->status = ModelStatus::MissingRequiredFeature;
    result->missing_feature = missing != nullptr ? missing : "time";
    return false;
  }
  if (!has_pressure_history_) {
    previous_pressure_hpa_ = s.pressure_hpa.value;
    previous_pressure_ms_ = s.pressure_hpa.sampled_at_ms;
    has_pressure_history_ = true;
    result->status = ModelStatus::MissingRequiredFeature;
    result->missing_feature = "pressure_trend_hpa_per_hour";
    return false;
  }
  const uint32_t elapsed_ms = s.pressure_hpa.sampled_at_ms - previous_pressure_ms_;
  if (elapsed_ms == 0) {
    result->status = ModelStatus::MissingRequiredFeature;
    result->missing_feature = "pressure_trend_hpa_per_hour";
    return false;
  }
  const float pressure_trend = (s.pressure_hpa.value - previous_pressure_hpa_) * 3600000.0f / elapsed_ms;
  previous_pressure_hpa_ = s.pressure_hpa.value;
  previous_pressure_ms_ = s.pressure_hpa.sampled_at_ms;
  constexpr float kTau = 6.28318530718f;
  const float hour_angle = kTau * static_cast<float>(s.time.hour) / 24.0f;
  const float day_angle = kTau * static_cast<float>(s.time.day_of_year - 1) / 365.0f;
  const float t = s.temperature_c.value;
  const float h = s.relative_humidity_pct.value;
  output->values[0] = t;
  output->values[1] = h;
  output->values[2] = s.pressure_hpa.value;
  output->values[3] = s.wind_speed_mps.value;
  output->values[4] = s.pm25_ug_m3.value;
  output->values[5] = pressure_trend;
  output->values[6] = dew_point_c(t, h);
  output->values[7] = heat_index_c(t, h);
  output->values[8] = sinf(hour_angle);
  output->values[9] = cosf(hour_angle);
  output->values[10] = sinf(day_angle);
  output->values[11] = cosf(day_angle);
  output->values[12] = s.latitude_deg.value;
  output->values[13] = s.longitude_deg.value;
  result->status = ModelStatus::NotReady;
  return true;
}

}  // namespace indra
