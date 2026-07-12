#include <stdlib.h>
#include <math.h>
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "driver/adc.h"
#include "mics6814.h"

static const char *TAG = "MICS6814";

static int read_adc_avg(int ch, int samples)
{
    uint32_t sum = 0;
    for (int i = 0; i < samples; i++) {
        int raw;
        if (adc2_get_raw((adc2_channel_t)ch, ADC_WIDTH_BIT_12, &raw) == ESP_OK) {
            sum += raw;
        }
        esp_rom_delay_us(1000);
    }
    return (int)(sum / samples);
}

static float adc_to_voltage(int raw, float vref, int resolution)
{
    return (float)raw * vref / (float)resolution;
}

static float voltage_to_co_ppm(float voltage)
{
    return 10.0f * powf(10.0f, (voltage - 1.5f) / 1.0f);
}

static float voltage_to_no2_ppm(float voltage)
{
    return 0.1f * powf(10.0f, (voltage - 1.5f) / 0.8f);
}

static float voltage_to_nh3_ppm(float voltage)
{
    return 5.0f * powf(10.0f, (voltage - 1.5f) / 0.9f);
}

bool mics6814_init(int adc_ch_co, int adc_ch_no2, int adc_ch_nh3,
                    mics6814_handle_t **handle)
{
    if (handle == NULL) return false;

    mics6814_handle_t *dev = calloc(1, sizeof(mics6814_handle_t));
    if (dev == NULL) return false;

    dev->adc_ch_co  = adc_ch_co;
    dev->adc_ch_no2 = adc_ch_no2;
    dev->adc_ch_nh3 = adc_ch_nh3;
    dev->voltage_ref = 3.3f;
    dev->adc_resolution = 4095;
    dev->warmed_up = false;

    adc2_config_channel_atten((adc2_channel_t)adc_ch_co, ADC_ATTEN_DB_12);
    adc2_config_channel_atten((adc2_channel_t)adc_ch_no2, ADC_ATTEN_DB_12);
    adc2_config_channel_atten((adc2_channel_t)adc_ch_nh3, ADC_ATTEN_DB_12);

    *handle = dev;
    ESP_LOGI(TAG, "Initialized (CO CH%d, NO2 CH%d, NH3 CH%d)",
             adc_ch_co, adc_ch_no2, adc_ch_nh3);
    return true;
}

bool mics6814_read(mics6814_handle_t *handle, mics6814_data_t *data)
{
    if (handle == NULL || data == NULL) return false;

    if (!handle->warmed_up) {
        ESP_LOGW(TAG, "Sensor may not be warmed up yet (need %d ms)",
                 MICS6814_WARMUP_MS);
        handle->warmed_up = true;
    }

    int raw_co  = read_adc_avg(handle->adc_ch_co, MICS6814_SAMPLE_COUNT);
    int raw_no2 = read_adc_avg(handle->adc_ch_no2, MICS6814_SAMPLE_COUNT);
    int raw_nh3 = read_adc_avg(handle->adc_ch_nh3, MICS6814_SAMPLE_COUNT);

    float v_co  = adc_to_voltage(raw_co, handle->voltage_ref, handle->adc_resolution);
    float v_no2 = adc_to_voltage(raw_no2, handle->voltage_ref, handle->adc_resolution);
    float v_nh3 = adc_to_voltage(raw_nh3, handle->voltage_ref, handle->adc_resolution);

    data->co_ppm  = voltage_to_co_ppm(v_co);
    data->no2_ppm = voltage_to_no2_ppm(v_no2);
    data->nh3_ppm = voltage_to_nh3_ppm(v_nh3);

    return true;
}
