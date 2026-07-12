#include <stdlib.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "driver/adc.h"
#include "anemometer.h"

static const char *TAG = "ANEMOMETER";

const float ANEMOMETER_DIR_DEG[ANEMOMETER_NUM_DIRECTIONS] = {
    0.0f, 22.5f, 45.0f, 67.5f,
    90.0f, 112.5f, 135.0f, 157.5f,
    180.0f, 202.5f, 225.0f, 247.5f,
    270.0f, 292.5f, 315.0f, 337.5f
};

static int read_adc_avg(int ch, int samples, int resolution)
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

bool anemometer_init(int adc_speed_ch, int adc_dir_ch, anemometer_handle_t **handle)
{
    if (handle == NULL) return false;

    anemometer_handle_t *dev = calloc(1, sizeof(anemometer_handle_t));
    if (dev == NULL) return false;

    dev->adc_speed_ch = adc_speed_ch;
    dev->adc_dir_ch = adc_dir_ch;
    dev->voltage_ref = ANEMOMETER_VOLTAGE_REF;
    dev->adc_resolution = ANEMOMETER_ADC_RESOLUTION;

    adc2_config_channel_atten((adc2_channel_t)adc_speed_ch, ADC_ATTEN_DB_12);
    adc2_config_channel_atten((adc2_channel_t)adc_dir_ch, ADC_ATTEN_DB_12);

    *handle = dev;
    ESP_LOGI(TAG, "Initialized (speed CH%d, dir CH%d)", adc_speed_ch, adc_dir_ch);
    return true;
}

bool anemometer_read_speed(anemometer_handle_t *handle, float *speed_ms)
{
    if (handle == NULL || speed_ms == NULL) return false;

    int raw = read_adc_avg(handle->adc_speed_ch, ANEMOMETER_SAMPLE_COUNT,
                            handle->adc_resolution);
    float voltage = adc_to_voltage(raw, handle->voltage_ref, handle->adc_resolution);

    if (voltage < 0.05f) {
        *speed_ms = 0.0f;
        return true;
    }

    *speed_ms = voltage * 20.0f;
    return true;
}

bool anemometer_read_direction(anemometer_handle_t *handle, float *direction_deg)
{
    if (handle == NULL || direction_deg == NULL) return false;

    int raw = read_adc_avg(handle->adc_dir_ch, ANEMOMETER_SAMPLE_COUNT,
                            handle->adc_resolution);
    float voltage = adc_to_voltage(raw, handle->voltage_ref, handle->adc_resolution);

    int idx = (int)(voltage / handle->voltage_ref * ANEMOMETER_NUM_DIRECTIONS);
    if (idx >= ANEMOMETER_NUM_DIRECTIONS) idx = ANEMOMETER_NUM_DIRECTIONS - 1;
    if (idx < 0) idx = 0;

    *direction_deg = ANEMOMETER_DIR_DEG[idx];
    return true;
}
