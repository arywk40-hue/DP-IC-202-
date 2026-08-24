#include <cstdio>

#include "IndraCore.h"

namespace {
indra::Reading valid(float value, unsigned long at) { return {value, indra::SensorStatus::Valid, static_cast<uint32_t>(at)}; }
indra::SensorSnapshot sample(unsigned long at, float pressure) {
  indra::SensorSnapshot s{};
  s.temperature_c = valid(30.0f, at); s.relative_humidity_pct = valid(65.0f, at);
  s.pressure_hpa = valid(pressure, at); s.wind_speed_mps = valid(4.0f, at);
  s.pm25_ug_m3 = valid(25.0f, at); s.latitude_deg = valid(22.5726f, at);
  s.longitude_deg = valid(88.3639f, at); s.time = {2026, 236, 12, indra::SensorStatus::Valid};
  return s;
}
}  // namespace

int main() {
  indra::FeatureBuilder builder; indra::FeatureVector vector{}; indra::ModelResult result{};
  if (builder.build(sample(1000, 1008.0f), &vector, &result)) return 1;
  if (!builder.build(sample(3601000, 1009.0f), &vector, &result)) return 2;
  for (size_t i = 0; i < indra::kSensorOnlyFeatureCount; ++i) std::printf("%.9g\n", vector.values[i]);
  return 0;
}
