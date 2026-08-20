#ifndef SEN0575_H
#define SEN0575_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SEN0575_ADC_CHANNEL            ADC2_CHANNEL_2
#define SEN0575_SAMPLE_COUNT           16
#define SEN0575_DRY_VOLTAGE            3.1f
#define SEN0575_LIGHT_THRESH_V         2.5f
#define SEN0575_MODERATE_THRESH_V      1.5f
#define SEN0575_HEAVY_THRESH_V         0.8f

typedef enum {
    RAIN_NONE    = 0,
    RAIN_LIGHT   = 1,
    RAIN_MODERATE = 2,
    RAIN_HEAVY   = 3
} rain_intensity_t;

typedef struct {
    int  adc_ch;
    float voltage_ref;
    int  adc_resolution;
} sen0575_handle_t;

bool sen0575_init(int adc_ch, sen0575_handle_t **handle);
bool sen0575_read_voltage(sen0575_handle_t *handle, float *voltage_mv);
bool sen0575_read_intensity(sen0575_handle_t *handle, rain_intensity_t *intensity);

#ifdef __cplusplus
}
#endif

#endif
