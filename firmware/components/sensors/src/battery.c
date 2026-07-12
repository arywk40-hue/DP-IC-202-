#include <stdlib.h>
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "driver/adc.h"
#include "battery.h"

static const char *TAG = "BATTERY";

static int read_adc_avg(int ch, int samples)
{
    uint32_t sum = 0;
    for (int i = 0; i < samples; i++) {
        int raw = adc1_get_raw((adc1_channel_t)ch);
        sum += raw;
        esp_rom_delay_us(1000);
    }
    return (int)(sum / samples);
}

bool battery_init(int adc_ch, float divider_ratio, battery_handle_t **handle)
{
    if (handle == NULL) return false;

    battery_handle_t *dev = calloc(1, sizeof(battery_handle_t));
    if (dev == NULL) return false;

    dev->adc_ch = adc_ch;
    dev->divider_ratio = divider_ratio;
    dev->voltage_ref = 3.3f;
    dev->adc_resolution = 4095;

    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten((adc1_channel_t)adc_ch, ADC_ATTEN_DB_12);

    *handle = dev;
    ESP_LOGI(TAG, "Initialized (ADC%d, ratio=%.1f)", adc_ch, divider_ratio);
    return true;
}

bool battery_read(battery_handle_t *handle, battery_status_t *status)
{
    if (handle == NULL || status == NULL) return false;

    int raw = read_adc_avg(handle->adc_ch, BATTERY_SAMPLE_COUNT);
    float adc_voltage = (float)raw * handle->voltage_ref / (float)handle->adc_resolution;

    float vbat = adc_voltage * handle->divider_ratio;
    float percent = (vbat - BATTERY_EMPTY_V) / (BATTERY_FULLY_CHARGED_V - BATTERY_EMPTY_V) * 100.0f;
    if (percent < 0.0f)  percent = 0.0f;
    if (percent > 100.0f) percent = 100.0f;

    if (vbat <= BATTERY_EMPTY_V)      status->level = BATTERY_EMPTY;
    else if (vbat <= BATTERY_CRITICAL_V) status->level = BATTERY_CRITICAL;
    else if (vbat <= BATTERY_LOW_V)   status->level = BATTERY_LOW;
    else                               status->level = BATTERY_OK;

    status->voltage = vbat;
    status->percent = percent;

    return true;
}
