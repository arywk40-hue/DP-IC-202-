#pragma once
// Six measured channels; hourly history matches ml/event_classifier/features.py.
#include <cmath>
#include <cstdint>
#include <cstring>
#include "indra_six_sensor_forecast.h"
#include "indra_event_classifier.h"

namespace indra {
static_assert(INDRA_FORECAST_INPUTS == 6 && INDRA_FORECAST_OUTPUTS == 6,
              "This runtime requires the complete six-channel forecast");
static_assert(INDRA_EVENT_INPUTS == 17 && INDRA_EVENT_OUTPUTS == 12,
              "Event feature contract changed");
constexpr uint16_t kTrainedEventMask = 0x0ff9;  // Heads 1 and 2 were not trained.
enum class Status { Invalid, OutOfOrder, WarmingUp, Ready, FeaturesUnavailable };
struct Result {
  Status status = Status::Invalid;
  uint8_t history_rows = 0;
  uint16_t event_valid_mask = 0;
  float forecast[6];
  float features[17];
  float events[12];
  Result() {
    for (float &x : forecast) x = NAN;
    for (float &x : features) x = NAN;
    for (float &x : events) x = NAN;
  }
};
inline const char* status_name(Status s) {
  switch (s) {
    case Status::Invalid: return "INVALID_INPUT";
    case Status::OutOfOrder: return "OUT_OF_ORDER";
    case Status::WarmingUp: return "WARMING_UP";
    case Status::Ready: return "READY";
    case Status::FeaturesUnavailable: return "FEATURES_UNAVAILABLE";
  }
  return "INVALID_INPUT";
}
class Runtime {
 public:
  void reset() { count_ = 0; last_ = 0; }
  Result push(uint32_t timestamp, const float* raw) {
    Result out;
    const float lo[6] = {-60, 0, 300, 0, 0, 0};
    const float hi[6] = {85, 100, 1100, 5000, 5000, 100};
    if (!raw || timestamp == 0) return out;
    for (int i = 0; i < 6; ++i)
      if (!std::isfinite(raw[i]) || raw[i] < lo[i] || raw[i] > hi[i]) return out;
    if (count_ && timestamp <= last_) {
      out.status = Status::OutOfOrder;
      out.history_rows = count_;
      return out;
    }
    // A missing/off-grid hour starts a new history; never invent temporal inputs.
    if (count_ && timestamp - last_ != 3600) reset();
    if (count_ == 7) {
      std::memmove(rows_, rows_ + 1, 6 * sizeof(rows_[0]));
      count_ = 6;
    }
    std::memcpy(rows_[count_++], raw, sizeof(rows_[0]));
    last_ = timestamp;
    out.history_rows = count_;
    if (!indra_forecast_predict(raw, out.forecast)) return out;
    out.status = Status::WarmingUp;
    if (count_ != 7) return out;
    if (raw[4] <= 0) { out.status = Status::FeaturesUnavailable; return out; }
    for (int i = 0; i < 6; ++i) out.features[i] = raw[i];
    // Double intermediates reproduce the Python feature calculations before float32 export.
    const double t = raw[0], rh = raw[1];
    const double fraction = rh / 100.0 < 1e-6 ? 1e-6 : rh / 100.0;
    const double gamma = std::log(fraction) + 17.625 * t / (243.04 + t);
    out.features[6] = 243.04 * gamma / (17.625 - gamma);
    out.features[7] = 0.6108 * std::exp(17.27 * t / (t + 237.3)) * (1.0 - rh / 100.0);
    const double tf = t * 9.0 / 5.0 + 32.0;
    const double hi_f = -42.379 + 2.04901523 * tf + 10.14333127 * rh
        - 0.22475541 * tf * rh - 6.83783e-3 * tf * tf - 5.481717e-2 * rh * rh
        + 1.22874e-3 * tf * tf * rh + 8.5282e-4 * tf * rh * rh
        - 1.99e-6 * tf * tf * rh * rh;
    out.features[8] = tf >= 80.0 ? (hi_f - 32.0) * 5.0 / 9.0 : t;
    out.features[9] = static_cast<double>(raw[3]) / raw[4];
    out.features[10] = static_cast<double>(raw[2]) - rows_[5][2];
    out.features[11] = static_cast<double>(raw[2]) - rows_[0][2];
    out.features[12] = static_cast<double>(raw[0]) - rows_[5][0];
    out.features[13] = static_cast<double>(raw[3]) - rows_[5][3];
    out.features[14] = static_cast<double>(raw[4]) - rows_[5][4];
    out.features[15] = static_cast<double>(raw[1]) - rows_[5][1];
    out.features[16] = 1;
    for (int i = 1; i < 7; ++i)
      if (rows_[i][3] <= rows_[i-1][3]) out.features[16] = 0;
    if (!indra_event_predict(out.features, out.events)) return out;
    out.event_valid_mask = kTrainedEventMask;
    // Preserve the distinction between an untrained head and a negative score.
    out.events[1] = out.events[2] = NAN;
    out.status = Status::Ready;
    return out;
  }
 private:
  float rows_[7][6]{};
  uint32_t last_ = 0;
  uint8_t count_ = 0;
};
}  // namespace indra
