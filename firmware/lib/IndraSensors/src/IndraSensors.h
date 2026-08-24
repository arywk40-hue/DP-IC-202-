#pragma once

#include <Arduino.h>
#include <Adafruit_BME280.h>
#include <Adafruit_INA219.h>
#include <RTClib.h>
#include <TinyGPS++.h>

#include "BoardConfig.h"
#include "IndraCore.h"

namespace indra {

class Bme280Driver { public: bool begin(TwoWire& bus); void sample(SensorSnapshot* snapshot, uint32_t now); private: Adafruit_BME280 sensor_; bool ready_ = false; };
class Ina219Driver { public: bool begin(TwoWire& bus); void sample(SensorSnapshot* snapshot, uint32_t now); private: Adafruit_INA219 sensor_; bool ready_ = false; };
class RtcDriver { public: bool begin(TwoWire& bus); void sample(SensorSnapshot* snapshot); private: RTC_DS3231 rtc_; bool ready_ = false; };
class Pms7003Driver { public: void begin(HardwareSerial& serial); void poll(SensorSnapshot* snapshot, uint32_t now); private: HardwareSerial* serial_ = nullptr; uint8_t frame_[32]{}; uint8_t index_ = 0; };
class GpsDriver { public: void begin(HardwareSerial& serial); void poll(SensorSnapshot* snapshot, uint32_t now); private: HardwareSerial* serial_ = nullptr; TinyGPSPlus parser_; };
class WindEncoder { public: void begin(uint8_t pin); void sample(SensorSnapshot* snapshot, uint32_t now); private: static void IRAM_ATTR on_pulse(); static volatile uint32_t pulses_; uint32_t previous_pulses_ = 0; uint32_t previous_ms_ = 0; };

}  // namespace indra
