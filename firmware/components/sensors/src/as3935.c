#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "as3935.h"

static const char *TAG = "AS3935";

static esp_err_t as3935_write_reg(as3935_handle_t *handle, uint8_t reg, uint8_t value)
{
    return i2c_master_write_to_device(handle->i2c_port, handle->addr,
                                       &reg, 1, &value, 1, pdMS_TO_TICKS(100));
}

static esp_err_t as3935_read_reg(as3935_handle_t *handle, uint8_t reg, uint8_t *value)
{
    return i2c_master_write_read_device(handle->i2c_port, handle->addr,
                                         &reg, 1, value, 1, pdMS_TO_TICKS(100));
}

static esp_err_t as3935_read_burst(as3935_handle_t *handle, uint8_t start_reg,
                                    uint8_t *buf, size_t len)
{
    return i2c_master_write_read_device(handle->i2c_port, handle->addr,
                                         &start_reg, 1, buf, len,
                                         pdMS_TO_TICKS(100));
}

static bool as3935_clear_interrupt(as3935_handle_t *handle)
{
    uint8_t reg = AS3935_REG_INT_MASK;
    return i2c_master_write_to_device(handle->i2c_port, handle->addr,
                                       &reg, 1, NULL, 0,
                                       pdMS_TO_TICKS(100)) == ESP_OK;
}

bool as3935_init(i2c_port_t port, uint8_t addr, bool outdoor, as3935_handle_t **handle)
{
    if (handle == NULL) return false;

    as3935_handle_t *dev = calloc(1, sizeof(as3935_handle_t));
    if (dev == NULL) return false;

    dev->i2c_port = port;
    dev->addr = addr;
    dev->outdoor = outdoor;
    dev->noise_floor = AS3935_NOISE_FLOOR_DEFAULT;

    uint8_t chip_id;
    if (as3935_read_reg(dev, AS3935_REG_AFE_GAIN, &chip_id) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to read AFE gain register");
        free(dev);
        return false;
    }

    if (outdoor) {
        as3935_write_reg(dev, AS3935_REG_AFE_GAIN, AS3935_SETTING_OUTDOOR);
        as3935_write_reg(dev, AS3935_REG_THRESHOLD, 0x0E);
    } else {
        as3935_write_reg(dev, AS3935_REG_AFE_GAIN, AS3935_SETTING_INDOOR);
        as3935_write_reg(dev, AS3935_REG_THRESHOLD, 0x0A);
    }

    as3935_write_reg(dev, AS3935_REG_NOISE_FLOOR, dev->noise_floor);
    as3935_write_reg(dev, AS3935_REG_INT_MASK, 0x0F);

    as3935_calibrate_rco(dev);

    vTaskDelay(pdMS_TO_TICKS(10));

    *handle = dev;
    ESP_LOGI(TAG, "Initialized (%s mode)", outdoor ? "outdoor" : "indoor");
    return true;
}

bool as3935_read_event(as3935_handle_t *handle, as3935_data_t *data)
{
    if (handle == NULL || data == NULL) return false;

    memset(data, 0, sizeof(as3935_data_t));

    uint8_t int_source;
    if (as3935_read_reg(handle, AS3935_REG_INT_MASK, &int_source) != ESP_OK) {
        return false;
    }
    int_source &= 0x0F;
    data->interrupt_source = int_source;

    if (int_source == AS3935_INT_LIGHTNING) {
        uint8_t buf[3];
        if (as3935_read_burst(handle, AS3935_REG_S_LIG_L, buf, 3) != ESP_OK) {
            as3935_clear_interrupt(handle);
            return false;
        }
        data->distance_km = buf[2] & 0x3F;
        data->strike_count = (buf[1] >> 4) & 0x0F;
        data->energy = ((uint32_t)(buf[0] & 0x1F) << 16)
                     | ((uint32_t)buf[1] << 8)
                     | buf[0];
    }

    as3935_clear_interrupt(handle);
    return true;
}

bool as3935_clear_stats(as3935_handle_t *handle)
{
    if (handle == NULL) return false;
    uint8_t val;
    if (as3935_read_reg(handle, AS3935_REG_S_LIG_MM, &val) != ESP_OK) {
        return false;
    }
    val |= 0x20;
    return as3935_write_reg(handle, AS3935_REG_S_LIG_MM, val) == ESP_OK;
}

bool as3935_set_noise_floor(as3935_handle_t *handle, uint8_t level)
{
    if (handle == NULL) return false;
    if (level > 7) level = 7;
    handle->noise_floor = level;
    esp_err_t ret = as3935_write_reg(handle, AS3935_REG_NOISE_FLOOR, level);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Noise floor set to %d", level);
    }
    return ret == ESP_OK;
}

bool as3935_set_watchdog_threshold(as3935_handle_t *handle, uint8_t threshold)
{
    if (handle == NULL) return false;
    if (threshold > 0x0F) threshold = 0x0F;
    return as3935_write_reg(handle, AS3935_REG_THRESHOLD, threshold) == ESP_OK;
}

bool as3935_power_down(as3935_handle_t *handle)
{
    if (handle == NULL) return false;
    uint8_t val;
    if (as3935_read_reg(handle, AS3935_REG_AFE_GAIN, &val) != ESP_OK) {
        return false;
    }
    val |= 0x20;
    return as3935_write_reg(handle, AS3935_REG_AFE_GAIN, val) == ESP_OK;
}

bool as3935_power_up(as3935_handle_t *handle)
{
    if (handle == NULL) return false;
    uint8_t val;
    if (as3935_read_reg(handle, AS3935_REG_AFE_GAIN, &val) != ESP_OK) {
        return false;
    }
    val &= ~0x20;
    return as3935_write_reg(handle, AS3935_REG_AFE_GAIN, val) == ESP_OK;
}

bool as3935_calibrate_rco(as3935_handle_t *handle)
{
    if (handle == NULL) return false;
    uint8_t calib;
    if (as3935_read_reg(handle, AS3935_REG_CALIB, &calib) != ESP_OK) {
        return false;
    }
    calib |= 0x40;
    if (as3935_write_reg(handle, AS3935_REG_CALIB, calib) != ESP_OK) {
        return false;
    }
    vTaskDelay(pdMS_TO_TICKS(5));
    calib &= ~0x40;
    as3935_write_reg(handle, AS3935_REG_CALIB, calib);
    return true;
}
