#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "ltr390.h"

static const char *TAG = "LTR390";

static esp_err_t ltr390_write_reg(ltr390_handle_t *handle, uint8_t reg, uint8_t value)
{
    return i2c_master_write_to_device(handle->i2c_port, handle->addr,
                                       &reg, 1, &value, 1, pdMS_TO_TICKS(100));
}

static esp_err_t ltr390_read_reg(ltr390_handle_t *handle, uint8_t reg, uint8_t *value)
{
    return i2c_master_write_read_device(handle->i2c_port, handle->addr,
                                         &reg, 1, value, 1, pdMS_TO_TICKS(100));
}

static esp_err_t ltr390_read_u16(ltr390_handle_t *handle, uint8_t reg_lsb, uint16_t *value)
{
    uint8_t buf[2];
    esp_err_t ret = i2c_master_write_read_device(handle->i2c_port, handle->addr,
                                                   &reg_lsb, 1, buf, 2, pdMS_TO_TICKS(100));
    if (ret == ESP_OK) {
        *value = ((uint16_t)buf[1] << 8) | buf[0];
    }
    return ret;
}

bool ltr390_init(i2c_port_t port, uint8_t addr, ltr390_handle_t **handle)
{
    if (handle == NULL) return false;

    ltr390_handle_t *dev = calloc(1, sizeof(ltr390_handle_t));
    if (dev == NULL) return false;

    dev->i2c_port = port;
    dev->addr = addr;
    dev->gain = LTR390_MEAS_GAIN_3;
    dev->resolution = LTR390_MEAS_RES_18BIT;

    uint8_t chip_id;
    if (ltr390_read_reg(dev, LTR390_REG_PART_ID, &chip_id) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to read chip ID");
        free(dev);
        return false;
    }
    if ((chip_id >> 4) != LTR390_CHIP_ID) {
        ESP_LOGE(TAG, "Invalid chip ID: 0x%02X", chip_id);
        free(dev);
        return false;
    }
    ESP_LOGI(TAG, "LTR390 detected (chip ID: 0x%02X)", chip_id);

    ltr390_write_reg(dev, LTR390_REG_MAIN_CTRL, LTR390_CTRL_SW_RESET);
    vTaskDelay(pdMS_TO_TICKS(10));

    ltr390_write_reg(dev, LTR390_REG_MAIN_CTRL, LTR390_CTRL_UVS_EN);
    ltr390_write_reg(dev, LTR390_REG_ALS_UVS_MEAS, LTR390_MEAS_UVS |
                      dev->resolution | dev->gain);
    vTaskDelay(pdMS_TO_TICKS(100));

    *handle = dev;
    ESP_LOGI(TAG, "Initialized (gain=%d, res=%d)", dev->gain, dev->resolution);
    return true;
}

bool ltr390_read_uvs(ltr390_handle_t *handle, float *uv_index)
{
    if (handle == NULL || uv_index == NULL) return false;

    uint16_t raw;
    if (ltr390_read_u16(handle, LTR390_REG_UVS_DATA_LSB, &raw) != ESP_OK) {
        ESP_LOGW(TAG, "Failed to read UVS data");
        return false;
    }

    *uv_index = (float)raw / 2300.0f;
    return true;
}

bool ltr390_read_als(ltr390_handle_t *handle, float *lux)
{
    if (handle == NULL || lux == NULL) return false;

    uint16_t raw;
    if (ltr390_read_u16(handle, LTR390_REG_ALS_DATA_LSB, &raw) != ESP_OK) {
        ESP_LOGW(TAG, "Failed to read ALS data");
        return false;
    }

    *lux = (float)raw / 2300.0f * 100.0f;
    return true;
}

void ltr390_set_gain(ltr390_handle_t *handle, uint8_t gain)
{
    if (handle == NULL) return;
    handle->gain = gain;
    ltr390_write_reg(handle, LTR390_REG_ALS_UVS_MEAS,
                     LTR390_MEAS_UVS | handle->resolution | gain);
}

void ltr390_set_resolution(ltr390_handle_t *handle, uint8_t resolution)
{
    if (handle == NULL) return;
    handle->resolution = resolution;
    ltr390_write_reg(handle, LTR390_REG_ALS_UVS_MEAS,
                     LTR390_MEAS_UVS | resolution | handle->gain);
}
