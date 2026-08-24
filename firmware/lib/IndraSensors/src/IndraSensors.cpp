#include "IndraSensors.h"

#include <Wire.h>

namespace indra {
namespace {
Reading reading(float value, SensorStatus status, uint32_t now) { return {value, status, now}; }
SensorStatus range(float value, float low, float high) { return isfinite(value) && value >= low && value <= high ? SensorStatus::Valid : SensorStatus::OutOfRange; }
uint16_t u16(const uint8_t* p) { return (static_cast<uint16_t>(p[0]) << 8) | p[1]; }
uint16_t day_of_year(uint16_t year, uint8_t month, uint8_t day) {
  static constexpr uint16_t kDaysBeforeMonth[] = {0, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334};
  const bool leap = (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;
  return kDaysBeforeMonth[month] + day + (leap && month > 2 ? 1 : 0);
}
}
bool Bme280Driver::begin(TwoWire& bus) { ready_ = sensor_.begin(0x76, &bus) || sensor_.begin(0x77, &bus); return ready_; }
void Bme280Driver::sample(SensorSnapshot* s, uint32_t now) { if (!ready_) { s->temperature_c = s->relative_humidity_pct = s->pressure_hpa = reading(NAN, SensorStatus::Missing, now); return; } const float t = sensor_.readTemperature(), h = sensor_.readHumidity(), p = sensor_.readPressure() / 100.0f; s->temperature_c = reading(t, range(t, -40, 85), now); s->relative_humidity_pct = reading(h, range(h, 0, 100), now); s->pressure_hpa = reading(p, range(p, 300, 1100), now); }
bool Ina219Driver::begin(TwoWire& bus) { ready_ = sensor_.begin(&bus); return ready_; }
void Ina219Driver::sample(SensorSnapshot* s, uint32_t now) { if (!ready_) { s->battery_voltage_v = s->battery_current_ma = s->battery_power_mw = reading(NAN, SensorStatus::Missing, now); return; } const float v = sensor_.getBusVoltage_V(), i = sensor_.getCurrent_mA(), p = sensor_.getPower_mW(); s->battery_voltage_v = reading(v, range(v, 0, 32), now); s->battery_current_ma = reading(i, range(i, -3200, 3200), now); s->battery_power_mw = reading(p, range(p, -100000, 100000), now); }
bool RtcDriver::begin(TwoWire& bus) { ready_ = rtc_.begin(&bus); return ready_; }
void RtcDriver::sample(SensorSnapshot* s) { if (!ready_) { s->time = {0, 0, 0, SensorStatus::Missing}; return; } const DateTime now = rtc_.now(); s->time = indra::ClockTime{static_cast<uint16_t>(now.year()), day_of_year(now.year(), now.month(), now.day()), now.hour(), SensorStatus::Valid}; }
void Pms7003Driver::begin(HardwareSerial& serial) { serial_ = &serial; serial.begin(9600, SERIAL_8N1, board::kPmsRxPin, board::kPmsTxPin); }
void Pms7003Driver::poll(SensorSnapshot* s, uint32_t now) { if (serial_ == nullptr) return; while (serial_->available()) { const uint8_t byte = static_cast<uint8_t>(serial_->read()); if (index_ == 0 && byte != 0x42) continue; if (index_ == 1 && byte != 0x4d) { index_ = 0; continue; } frame_[index_++] = byte; if (index_ != sizeof(frame_)) continue; index_ = 0; uint16_t sum = 0; for (size_t i = 0; i < 30; ++i) sum += frame_[i]; if (sum != u16(&frame_[30])) { s->pm25_ug_m3.status = SensorStatus::Invalid; continue; } const float pm1 = u16(&frame_[10]), pm25 = u16(&frame_[12]), pm10 = u16(&frame_[14]); s->pm1_ug_m3 = reading(pm1, range(pm1, 0, 1000), now); s->pm25_ug_m3 = reading(pm25, range(pm25, 0, 1000), now); s->pm10_ug_m3 = reading(pm10, range(pm10, 0, 1000), now); } }
void GpsDriver::begin(HardwareSerial& serial) { serial_ = &serial; serial.begin(9600, SERIAL_8N1, board::kGpsRxPin, board::kGpsTxPin); }
void GpsDriver::poll(SensorSnapshot* s, uint32_t now) { if (serial_ == nullptr) return; while (serial_->available()) parser_.encode(static_cast<char>(serial_->read())); if (!parser_.location.isValid()) return; const float lat = parser_.location.lat(), lon = parser_.location.lng(); s->latitude_deg = reading(lat, range(lat, -90, 90), now); s->longitude_deg = reading(lon, range(lon, -180, 180), now); if (parser_.altitude.isValid()) s->altitude_m = reading(parser_.altitude.meters(), SensorStatus::Valid, now); }
volatile uint32_t WindEncoder::pulses_ = 0;
void IRAM_ATTR WindEncoder::on_pulse() { ++pulses_; }
void WindEncoder::begin(uint8_t pin) { pinMode(pin, INPUT_PULLUP); attachInterrupt(digitalPinToInterrupt(pin), on_pulse, RISING); }
void WindEncoder::sample(SensorSnapshot* s, uint32_t now) { if (previous_ms_ == 0) { previous_ms_ = now; previous_pulses_ = pulses_; s->wind_speed_mps = reading(NAN, SensorStatus::Stale, now); return; } const uint32_t elapsed = now - previous_ms_; if (elapsed < board::kWindWindowMs) return; noInterrupts(); const uint32_t total = pulses_; interrupts(); const uint32_t delta = total - previous_pulses_; const float speed = (delta / board::kEncoderPulsesPerRevolution) * board::kWindMetersPerRevolution * 1000.0f / elapsed; s->wind_speed_mps = reading(speed, range(speed, 0, 80), now); previous_pulses_ = total; previous_ms_ = now; }
}  // namespace indra
