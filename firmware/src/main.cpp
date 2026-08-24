#include <Arduino.h>
#include <Wire.h>

#include "BoardConfig.h"
#include "IndraCore.h"
#include "IndraSensors.h"

namespace {
indra::SensorSnapshot snapshot{};
indra::FeatureBuilder feature_builder;
indra::Bme280Driver bme;
indra::Ina219Driver ina219;
indra::RtcDriver rtc;
indra::Pms7003Driver pms;
indra::GpsDriver gps;
indra::WindEncoder wind;
HardwareSerial pms_serial(1);
HardwareSerial gps_serial(2);
uint32_t last_environment = 0, last_power = 0, last_telemetry = 0;

void initialize_snapshot() {
  const indra::Reading missing{NAN, indra::SensorStatus::Missing, 0};
  snapshot.temperature_c = snapshot.relative_humidity_pct = snapshot.pressure_hpa = missing;
  snapshot.wind_speed_mps = snapshot.pm1_ug_m3 = snapshot.pm25_ug_m3 = snapshot.pm10_ug_m3 = missing;
  snapshot.latitude_deg = snapshot.longitude_deg = snapshot.altitude_m = missing;
  snapshot.battery_voltage_v = snapshot.battery_current_ma = snapshot.battery_power_mw = missing;
  snapshot.time = {0, 0, 0, indra::SensorStatus::Missing};
  snapshot.gps_time = {0, 0, 0, indra::SensorStatus::Missing};
}

void mark_stale(indra::Reading* r, uint32_t now) {
  if (r->status == indra::SensorStatus::Valid && now - r->sampled_at_ms > indra::board::kStaleAfterMs) r->status = indra::SensorStatus::Stale;
}

void refresh_staleness(uint32_t now) {
  mark_stale(&snapshot.temperature_c, now); mark_stale(&snapshot.relative_humidity_pct, now); mark_stale(&snapshot.pressure_hpa, now); mark_stale(&snapshot.wind_speed_mps, now);
  mark_stale(&snapshot.pm1_ug_m3, now); mark_stale(&snapshot.pm25_ug_m3, now); mark_stale(&snapshot.pm10_ug_m3, now); mark_stale(&snapshot.latitude_deg, now); mark_stale(&snapshot.longitude_deg, now); mark_stale(&snapshot.altitude_m, now);
  mark_stale(&snapshot.battery_voltage_v, now); mark_stale(&snapshot.battery_current_ma, now); mark_stale(&snapshot.battery_power_mw, now);
}

void print_reading(const char* name, const indra::Reading& r) {
  Serial.printf("\"%s\":{\"value\":", name);
  if (isfinite(r.value)) Serial.printf("%.3f", r.value); else Serial.print("null");
  Serial.printf(",\"status\":\"%s\"}", indra::status_name(r.status));
}

void print_telemetry() {
  indra::FeatureVector features{};
  indra::ModelResult result{};
  const bool features_ready = feature_builder.build(snapshot, &features, &result);
  Serial.print("{\"schema_version\":\"sensor_only_v1\",\"readings\":{");
  print_reading("temperature_c", snapshot.temperature_c); Serial.print(','); print_reading("relative_humidity_pct", snapshot.relative_humidity_pct); Serial.print(','); print_reading("pressure_hpa", snapshot.pressure_hpa); Serial.print(','); print_reading("wind_speed_mps", snapshot.wind_speed_mps); Serial.print(','); print_reading("pm1_ug_m3", snapshot.pm1_ug_m3); Serial.print(','); print_reading("pm25_ug_m3", snapshot.pm25_ug_m3); Serial.print(','); print_reading("pm10_ug_m3", snapshot.pm10_ug_m3);
  Serial.print("},\"gps\":{"); print_reading("latitude_deg", snapshot.latitude_deg); Serial.print(','); print_reading("longitude_deg", snapshot.longitude_deg); Serial.print(','); print_reading("altitude_m", snapshot.altitude_m);
  Serial.print("},\"power\":{"); print_reading("voltage_v", snapshot.battery_voltage_v); Serial.print(','); print_reading("current_ma", snapshot.battery_current_ma); Serial.print(','); print_reading("power_mw", snapshot.battery_power_mw);
  Serial.printf("},\"time\":{\"rtc\":{\"year\":%u,\"day_of_year\":%u,\"hour\":%u,\"status\":\"%s\"},\"gps\":{\"year\":%u,\"day_of_year\":%u,\"hour\":%u,\"status\":\"%s\"}},\"model\":{\"status\":\"%s\",\"schema_checksum\":\"%s\",\"checksum\":\"%s\",\"features_ready\":%s", snapshot.time.year, snapshot.time.day_of_year, snapshot.time.hour, indra::status_name(snapshot.time.status), snapshot.gps_time.year, snapshot.gps_time.day_of_year, snapshot.gps_time.hour, indra::status_name(snapshot.gps_time.status), indra::model_status_name(result.status), result.schema_checksum, result.model_checksum, features_ready ? "true" : "false");
  if (result.missing_feature != nullptr) Serial.printf(",\"missing_feature\":\"%s\"", result.missing_feature);
  Serial.println("}}");
}
}  // namespace

void setup() {
  Serial.begin(115200); delay(500);
  initialize_snapshot();
  Wire.begin(indra::board::kI2cSdaPin, indra::board::kI2cSclPin);
  bme.begin(Wire); ina219.begin(Wire); rtc.begin(Wire);
  pms.begin(pms_serial); gps.begin(gps_serial); wind.begin(indra::board::kWindEncoderPin);
}

void loop() {
  const uint32_t now = millis();
  pms.poll(&snapshot, now); gps.poll(&snapshot, now); wind.sample(&snapshot, now);
  if (now - last_environment >= indra::board::kBmeIntervalMs) { bme.sample(&snapshot, now); rtc.sample(&snapshot); last_environment = now; }
  if (now - last_power >= indra::board::kPowerIntervalMs) { ina219.sample(&snapshot, now); last_power = now; }
  refresh_staleness(now);
  if (now - last_telemetry >= indra::board::kTelemetryIntervalMs) { print_telemetry(); last_telemetry = now; }
}
