// Isolated synthetic smoke harness. No sensor drivers, network, or field alerts.
#include <Arduino.h>
#include "indra_india_preprocess.h"

static indra_hour_history history = {};
static float features[INDRA_INDIA_FEATURES], raw_scores[3], probabilities[3];
static int flags[3];
static uint8_t statuses[3];
static uint64_t timestamp_utc = 1730419200ULL;

void setup() {
  Serial.begin(115200);
  Serial.println("INDRA synthetic hourly smoke; NOT HARDWARE VALIDATED; alerts disabled");
}
void loop() {
  // One bounded synthetic packet per second, simulating completed UTC hours.
  static uint32_t last_ms = 0;
  const uint32_t now = millis();
  if (now - last_ms < 1000) return;
  last_ms = now;
  const float sensors[6] = {22, 65, 1000, NAN, NAN, 3};
  const int ready = indra_hour_push(&history, timestamp_utc, timestamp_utc,
                                  sensors, 1, 28.6f, 77.2f, 220, features);
  timestamp_utc += 3600;
  if (ready == 1) {
    indra_india_predict(features, raw_scores, probabilities, flags, statuses);
    for (int h = 0; h < 3; ++h)
      Serial.printf("head=%d raw=%.8f probability=%.8f research_flag=%d status=%u\n",
                    h, raw_scores[h], probabilities[h], flags[h], statuses[h]);
  }
}
