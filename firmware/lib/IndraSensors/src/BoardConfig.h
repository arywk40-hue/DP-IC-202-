#pragma once

#include <stdint.h>

namespace indra::board {
constexpr int kI2cSdaPin = 8;
constexpr int kI2cSclPin = 9;
constexpr int kPmsRxPin = 17;
constexpr int kPmsTxPin = 18;
constexpr int kGpsRxPin = 15;
constexpr int kGpsTxPin = 16;
constexpr int kWindEncoderPin = 4;
constexpr uint32_t kBmeIntervalMs = 2000;
constexpr uint32_t kPowerIntervalMs = 5000;
constexpr uint32_t kWindWindowMs = 5000;
constexpr uint32_t kTelemetryIntervalMs = 5000;
constexpr uint32_t kStaleAfterMs = 15000;
constexpr float kEncoderPulsesPerRevolution = 600.0f;
constexpr float kWindMetersPerRevolution = 2.40f;  // Calibrate against the installed rotor.
}  // namespace indra::board
