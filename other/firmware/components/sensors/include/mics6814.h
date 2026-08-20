#ifndef MICS6814_H
#define MICS6814_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MICS6814_ADC_CH_CO             ADC2_CHANNEL_3
#define MICS6814_ADC_CH_NO2            ADC2_CHANNEL_4
#define MICS6814_ADC_CH_NH3            ADC2_CHANNEL_5
#define MICS6814_SAMPLE_COUNT          16
#define MICS6814_WARMUP_MS             30000

typedef struct {
    int  adc_ch_co;
    int  adc_ch_no2;
    int  adc_ch_nh3;
    float voltage_ref;
    int  adc_resolution;
    bool warmed_up;
} mics6814_handle_t;

typedef struct {
    float co_ppm;
    float no2_ppm;
    float nh3_ppm;
} mics6814_data_t;

bool mics6814_init(int adc_ch_co, int adc_ch_no2, int adc_ch_nh3, mics6814_handle_t **handle);
bool mics6814_read(mics6814_handle_t *handle, mics6814_data_t *data);

#ifdef __cplusplus
}
#endif

#endif
