#ifndef ANEMOMETER_H
#define ANEMOMETER_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ANEMOMETER_ADC_CH_WIND_SPEED   ADC2_CHANNEL_0
#define ANEMOMETER_ADC_CH_WIND_DIR     ADC2_CHANNEL_1
#define ANEMOMETER_SAMPLE_COUNT        8
#define ANEMOMETER_NUM_DIRECTIONS      16
#define ANEMOMETER_VOLTAGE_REF         3.3f
#define ANEMOMETER_ADC_RESOLUTION      4095

extern const float ANEMOMETER_DIR_DEG[ANEMOMETER_NUM_DIRECTIONS];

typedef struct {
    int   adc_speed_ch;
    int   adc_dir_ch;
    float voltage_ref;
    int   adc_resolution;
} anemometer_handle_t;

bool anemometer_init(int adc_speed_ch, int adc_dir_ch, anemometer_handle_t **handle);
bool anemometer_read_speed(anemometer_handle_t *handle, float *speed_ms);
bool anemometer_read_direction(anemometer_handle_t *handle, float *direction_deg);

#ifdef __cplusplus
}
#endif

#endif
