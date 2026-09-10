// Isolated model test: no sensor drivers or application changes.
#include <Arduino.h>
#include "indra_six_sensor_forecast.h"

void setup() {
  Serial.begin(115200);
  delay(1000);
  // Test vector only, not a claimed live sensor reading.
  // Volatile prevents constant folding from removing the model in this test build.
  static volatile float test_input[6] = {20.0f, 50.0f, 1013.0f, 35.0f, 60.0f, 2.0f};
  float input[6];
  for (int i = 0; i < 6; ++i) input[i] = test_input[i];
  float output[6];
  const uint32_t start = micros();
  int ok = indra_forecast_predict(input, output);
  const uint32_t elapsed = micros() - start;
  Serial.printf("six_sensor_forecast status=%s ok=%d horizon_h=%d latency_us=%lu\n",
                INDRA_FORECAST_STATUS, ok, INDRA_FORECAST_HORIZON_HOURS,
                static_cast<unsigned long>(elapsed));
  for (int i = 0; i < 6; ++i) Serial.printf("output[%d]=%.6f\n", i, output[i]);
}

void loop() { delay(1000); }
