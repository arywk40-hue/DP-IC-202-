#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "scd41.h"

static const char *TAG = "SCD41";

static esp_err_t scd41_write_cmd(scd41_handle_t *handle, uint16_t cmd)
{
    uint8_t buf[2];
    buf[0] = (cmd >> 8) & 0xFF;
    buf[1] = cmd & 0xFF;
    return i2c_master_write_to_device(handle->i2c_port, handle->addr,
                                       buf, 2, pdMS_TO_TICKS(100));
}

static esp_err_t scd41_write_cmd_with_arg(scd41_handle_t *handle, uint16_t cmd,
                                            uint16_t arg)
{
    uint8_t buf[5];
    buf[0] = (cmd >> 8) & 0xFF;
    buf[1] = cmd & 0xFF;
    buf[2] = (arg >> 8) & 0xFF;
    buf[3] = arg & 0xFF;
    uint8_t crc = 0xFF;
    for (int i = 0; i < 2; i++) {
        crc ^= (arg >> (8 * (1 - i))) & 0xFF;
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80) crc = (crc << 1) ^ 0x31;
            else            crc <<= 1;
        }
    }
    buf[4] = crc;
    return i2c_master_write_to_device(handle->i2c_port, handle->addr,
                                       buf, 5, pdMS_TO_TICKS(100));
}

static bool scd41_read_measurement(scd41_handle_t *handle, uint16_t *co2,
                                    int16_t *temp, uint16_t *hum)
{
    uint8_t buf[9];
    esp_err_t ret = i2c_master_write_read_device(handle->i2c_port, handle->addr,
                                                   NULL, 0, buf, 9,
                                                   pdMS_TO_TICKS(1000));
    if (ret != ESP_OK) return false;

    uint8_t crc;
    crc = 0xFF;
    for (int i = 0; i < 2; i++) {
        crc ^= (buf[0] >> (8 * (1 - i))) & 0xFF;
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80) crc = (crc << 1) ^ 0x31;
            else            crc <<= 1;
        }
    }
    if (crc != buf[2]) return false;

    *co2 = ((uint16_t)buf[0] << 8) | buf[1];
    *temp = ((int16_t)buf[3] << 8) | buf[4];
    *hum  = ((uint16_t)buf[6] << 8) | buf[7];
    return true;
}

bool scd41_init(i2c_port_t port, uint8_t addr, scd41_handle_t **handle)
{
    if (handle == NULL) return false;

    scd41_handle_t *dev = calloc(1, sizeof(scd41_handle_t));
    if (dev == NULL) return false;

    dev->i2c_port = port;
    dev->addr = addr;
    dev->periodic_mode = false;

    if (scd41_wake(dev) != ESP_OK) {
        ESP_LOGI(TAG, "Sensor already awake or not responding to wake");
    }
    vTaskDelay(pdMS_TO_TICKS(30));

    uint8_t serial_buf[9];
    uint8_t cmd[2] = { (SCD41_CMD_GET_SERIAL_NUM >> 8) & 0xFF,
                        SCD41_CMD_GET_SERIAL_NUM & 0xFF };
    esp_err_t ret = i2c_master_write_read_device(port, addr, cmd, 2,
                                                   serial_buf, 9,
                                                   pdMS_TO_TICKS(1000));
    if (ret == ESP_OK) {
        dev->serial_number = ((uint32_t)serial_buf[0] << 24)
                           | ((uint32_t)serial_buf[1] << 16)
                           | ((uint32_t)serial_buf[3] << 8)
                           | serial_buf[4];
        ESP_LOGI(TAG, "SCD41 detected, S/N: %08lX", (unsigned long)dev->serial_number);
    } else {
        ESP_LOGW(TAG, "Could not read SCD41 serial number — continuing");
    }

    *handle = dev;
    ESP_LOGI(TAG, "Initialized");
    return true;
}

bool scd41_read(scd41_handle_t *handle, float *co2_ppm, float *temperature, float *humidity)
{
    if (handle == NULL || co2_ppm == NULL || temperature == NULL || humidity == NULL) {
        return false;
    }

    if (scd41_write_cmd(handle, SCD41_CMD_READ_MEASUREMENT) != ESP_OK) {
        ESP_LOGW(TAG, "Failed to request measurement");
        return false;
    }
    vTaskDelay(pdMS_TO_TICKS(10));

    uint16_t raw_co2;
    int16_t raw_temp;
    uint16_t raw_hum;
    if (!scd41_read_measurement(handle, &raw_co2, &raw_temp, &raw_hum)) {
        return false;
    }

    *co2_ppm     = (float)raw_co2;
    *temperature = -45.0f + 175.0f * (float)raw_temp / 65535.0f;
    *humidity    = 100.0f * (float)raw_hum / 65535.0f;

    return true;
}

bool scd41_start_periodic(scd41_handle_t *handle)
{
    if (handle == NULL) return false;
    if (scd41_write_cmd(handle, SCD41_CMD_START_PERIODIC) != ESP_OK) {
        return false;
    }
    handle->periodic_mode = true;
    ESP_LOGI(TAG, "Periodic measurement started (5s interval)");
    return true;
}

bool scd41_stop_periodic(scd41_handle_t *handle)
{
    if (handle == NULL) return false;
    if (scd41_write_cmd(handle, SCD41_CMD_STOP_PERIODIC) != ESP_OK) {
        return false;
    }
    handle->periodic_mode = false;
    vTaskDelay(pdMS_TO_TICKS(500));
    return true;
}

bool scd41_sleep(scd41_handle_t *handle)
{
    if (handle == NULL) return false;
    if (handle->periodic_mode) {
        scd41_stop_periodic(handle);
    }
    return scd41_write_cmd(handle, SCD41_CMD_POWER_DOWN) == ESP_OK;
}

bool scd41_wake(scd41_handle_t *handle)
{
    if (handle == NULL) return false;
    esp_err_t ret = scd41_write_cmd(handle, SCD41_CMD_WAKE_UP);
    vTaskDelay(pdMS_TO_TICKS(30));
    return ret == ESP_OK;
}

bool scd41_set_temp_offset(scd41_handle_t *handle, float offset_c)
{
    if (handle == NULL) return false;
    uint16_t raw = (uint16_t)(offset_c * 65535.0f / 175.0f);
    return scd41_write_cmd_with_arg(handle, SCD41_CMD_SET_TEMP_OFFSET, raw) == ESP_OK;
}

bool scd41_self_test(scd41_handle_t *handle)
{
    if (handle == NULL) return false;
    if (handle->periodic_mode) {
        scd41_stop_periodic(handle);
    }
    if (scd41_write_cmd(handle, SCD41_CMD_SELF_TEST) != ESP_OK) {
        return false;
    }
    vTaskDelay(pdMS_TO_TICKS(10000));

    uint8_t buf[3];
    esp_err_t ret = i2c_master_write_read_device(handle->i2c_port, handle->addr,
                                                   NULL, 0, buf, 3,
                                                   pdMS_TO_TICKS(1000));
    if (ret != ESP_OK) return false;
    return (buf[0] == 0 && buf[1] == 0);
}
