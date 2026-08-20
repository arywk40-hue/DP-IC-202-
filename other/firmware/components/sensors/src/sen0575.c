#include <stdlib.h>
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "driver/adc.h"
#include "sen0575.h"

static const char *TAG = "SEN0575";

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

bool sen0575_init(int adc_ch, sen0575_handle_t **handle)
{
    if (handle == NULL) return false;

    sen0575_handle_t *dev = calloc(1, sizeof(sen0575_handle_t));
    if (dev == NULL) return false;

    dev->adc_ch = adc_ch;
    dev->voltage_ref = 3.3f;
    dev->adc_resolution = 4095;

    adc2_config_channel_atten((adc2_channel_t)adc_ch, ADC_ATTEN_DB_12);

    *handle = dev;
    ESP_LOGI(TAG, "Initialized on ADC CH%d", adc_ch);
    return true;
}

bool sen0575_read_voltage(sen0575_handle_t *handle, float *voltage_mv)
{
    if (handle == NULL || voltage_mv == NULL) return false;

    int raw = read_adc_avg(handle->adc_ch, SEN0575_SAMPLE_COUNT);
    *voltage_mv = adc_to_voltage(raw, handle->voltage_ref, handle->adc_resolution) * 1000.0f;
    return true;
}

bool sen0575_read_intensity(sen0575_handle_t *handle, rain_intensity_t *intensity)
{
    if (handle == NULL || intensity == NULL) return false;

    float voltage_v;
    if (!sen0575_read_voltage(handle, &voltage_v)) {
        return false;
    }

    if (voltage_v > SEN0575_DRY_VOLTAGE) {
        *intensity = RAIN_NONE;
    } else if (voltage_v > SEN0575_LIGHT_THRESH_V) {
        *intensity = RAIN_LIGHT;
    } else if (voltage_v > SEN0575_MODERATE_THRESH_V) {
        *intensity = RAIN_MODERATE;
    } else {
        *intensity = RAIN_HEAVY;
    }

    return true;
}
