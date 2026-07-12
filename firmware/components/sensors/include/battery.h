#ifndef BATTERY_H
#define BATTERY_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define BATTERY_ADC_CHANNEL            ADC1_CHANNEL_3
#define BATTERY_DIVIDER_RATIO          2.0f
#define BATTERY_ADC_ATTEN              ADC_ATTEN_DB_12
#define BATTERY_FULLY_CHARGED_V        4.2f
#define BATTERY_EMPTY_V                3.0f
#define BATTERY_CRITICAL_V             3.2f
#define BATTERY_LOW_V                  3.3f
#define BATTERY_SAMPLE_COUNT           32

typedef enum {
    BATTERY_OK         = 0,
    BATTERY_LOW        = 1,
    BATTERY_CRITICAL   = 2,
    BATTERY_EMPTY      = 3
} battery_level_t;

typedef struct {
    int  adc_ch;
    float divider_ratio;
    float voltage_ref;
    int  adc_resolution;
} battery_handle_t;

typedef struct {
    float voltage;
    float percent;
    battery_level_t level;
} battery_status_t;

bool battery_init(int adc_ch, float divider_ratio, battery_handle_t **handle);
bool battery_read(battery_handle_t *handle, battery_status_t *status);

#ifdef __cplusplus
}
#endif

#endif
