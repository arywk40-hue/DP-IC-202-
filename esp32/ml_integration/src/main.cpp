#include <Arduino.h>
#include <cerrno>
#include <cstdlib>
#include <climits>
#include "indra_ml_runtime.h"
#include "self_test_fixture.h"
#include "build_identity.h"

indra::Runtime runtime;
char line[192];
size_t used = 0;
bool overflow = false;
bool self_test_passed = false;
uint32_t boot_id = 0;
uint32_t sequence = 0;

void print_info() {
  Serial.printf("{\"info\":true,\"protocol_version\":1,\"node_id\":\"%012llx\","
                "\"boot_id\":%lu,\"self_test_passed\":%s,\"research_only\":true,"
                "\"build_sha256\":\"%s\",\"forecast_sha256\":\"%s\",\"events_sha256\":\"%s\"}\n",
                static_cast<unsigned long long>(ESP.getEfuseMac()),
                static_cast<unsigned long>(boot_id), self_test_passed ? "true" : "false",
                INDRA_BUILD_SHA256, INDRA_FORECAST_SHA256, INDRA_EVENTS_SHA256);
}

void array_json(const float* values, int count) {
  Serial.print('[');
  for (int i = 0; i < count; ++i) {
    if (i) Serial.print(',');
    if (std::isfinite(values[i])) Serial.print(values[i], 7);
    else Serial.print("null");
  }
  Serial.print(']');
}
void print_result(uint32_t timestamp, const indra::Result& r, uint32_t latency, const float* raw) {
  Serial.printf("{\"protocol_version\":1,\"boot_id\":%lu,\"sequence\":%lu,\"build_sha256\":\"%s\",",
                static_cast<unsigned long>(boot_id), static_cast<unsigned long>(++sequence), INDRA_BUILD_SHA256);
  Serial.print("\"measurements\":");
  array_json(raw, 6);
  Serial.printf(",\"forecast_timestamp_utc\":%llu,",
                static_cast<unsigned long long>(timestamp) + 21600ULL);
  Serial.printf("\"timestamp_utc\":%lu,\"status\":\"%s\",\"research_only\":true,"
                "\"history_rows\":%u,\"latency_us\":%lu,\"forecast_6h\":",
                static_cast<unsigned long>(timestamp), indra::status_name(r.status),
                r.history_rows, static_cast<unsigned long>(latency));
  array_json(r.forecast, 6);
  Serial.printf(",\"event_valid_mask\":%u,\"event_scores\":", r.event_valid_mask);
  array_json(r.events, 12);
  Serial.println('}');
}
bool close_to(const float* actual, const float* expected, int count, float tolerance) {
  for (int i = 0; i < count; ++i) {
    if (std::isnan(expected[i])) { if (!std::isnan(actual[i])) return false; }
    else if (!std::isfinite(actual[i]) || std::fabs(actual[i] - expected[i]) > tolerance) return false;
  }
  return true;
}
void self_test() {
  indra::Runtime test;
  indra::Result r;
  bool ok = true;
  for (int i = 0; i < 7; ++i) {
    r = test.push(1767225600UL + i * 3600UL, kTestRows[i]);
    if (i < 6) ok = ok && r.status == indra::Status::WarmingUp && !r.event_valid_mask;
  }
  ok = ok && r.status == indra::Status::Ready && r.event_valid_mask == indra::kTrainedEventMask;
  ok = ok && close_to(r.forecast, kExpectedForecast, 6, 5e-4f);
  ok = ok && close_to(r.events, kExpectedEvents, 12, 5e-4f);
  float invalid[6] = {20, 50, 1013, NAN, 60, 2};
  ok = ok && test.push(1767250800UL, invalid).status == indra::Status::Invalid;
  self_test_passed = ok;
  Serial.printf("{\"self_test\":\"%s\",\"fixture\":\"synthetic\",\"free_heap\":%u}\n", ok ? "PASS" : "FAIL", ESP.getFreeHeap());
}
// Strict CSV: unix_seconds,T,RH,P,PM2.5,PM10,W. No invented measurements.
bool parse(char* text, uint32_t& timestamp, float* raw) {
  if (*text < '0' || *text > '9') return false;
  char* end;
  errno = 0;
  const unsigned long ts = strtoul(text, &end, 10);
  if (errno || ts == 0 || ts > UINT32_MAX || *end != ',') return false;
  timestamp = static_cast<uint32_t>(ts);
  text = end + 1;
  for (int i = 0; i < 6; ++i) {
    errno = 0;
    raw[i] = strtof(text, &end);
    if (errno || end == text || !std::isfinite(raw[i])) return false;
    if (i < 5) { if (*end != ',') return false; text = end + 1; }
    else if (*end != '\0') return false;
  }
  return true;
}
void handle() {
  if (!strcmp(line, "INFO")) { print_info(); return; }
  if (!strcmp(line, "SELFTEST")) { self_test(); return; }
  if (!strcmp(line, "RESET")) { runtime.reset(); Serial.println("{\"reset\":true}"); return; }
  if (!self_test_passed) { Serial.println("{\"error\":\"SELF_TEST_FAILED\"}"); return; }
  uint32_t timestamp;
  float raw[6];
  if (!parse(line, timestamp, raw)) { Serial.println("{\"error\":\"INVALID_CSV\"}"); return; }
  const uint32_t start = micros();
  const auto result = runtime.push(timestamp, raw);
  print_result(timestamp, result, micros() - start, raw);
}
void setup() {
  boot_id = esp_random();
  Serial.begin(115200);
  delay(1500);
  Serial.println("INDRA ESP32-S3 ML integration: six-channel forecast + event rules");
  self_test();
  print_info();
  Serial.println("Send INFO, SELFTEST, RESET or unix_seconds,T,RH,P,PM2.5,PM10,W (hourly)");
}
void loop() {
  // Bound each drain so continuous input cannot starve scheduler/watchdog.
  unsigned budget = 256;
  while (budget-- && Serial.available()) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\r') continue;
    if (c == '\n') {
      line[used] = 0;
      if (overflow) Serial.println("{\"error\":\"LINE_TOO_LONG\"}");
      else if (used) handle();
      used = 0; overflow = false;
    } else if (static_cast<unsigned char>(c) < 32 || static_cast<unsigned char>(c) > 126) overflow = true;
    else if (used + 1 < sizeof(line) && !overflow) line[used++] = c;
    else overflow = true;
  }
  delay(1);
}
