#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "sgp41.h"

static const char *TAG = "SGP41";

static esp_err_t sgp41_write_cmd_raw(i2c_port_t port, uint8_t addr,
                                      const uint8_t *txbuf, size_t txlen)
{
    return i2c_master_write_to_device(port, addr, txbuf, txlen, pdMS_TO_TICKS(100));
}

static bool sgp41_execute_measurement(sgp41_handle_t *handle, uint16_t cmd,
                                       uint16_t *voc_raw, uint16_t *nox_raw,
                                       uint32_t wait_ms)
{
    uint8_t tx[2] = { (cmd >> 8) & 0xFF, cmd & 0xFF };
    esp_err_t ret = sgp41_write_cmd_raw(handle->i2c_port, handle->addr, tx, 2);
    if (ret != ESP_OK) return false;

    vTaskDelay(pdMS_TO_TICKS(wait_ms));

    uint8_t rx[6];
    ret = i2c_master_write_read_device(handle->i2c_port, handle->addr,
                                        NULL, 0, rx, 6, pdMS_TO_TICKS(500));
    if (ret != ESP_OK) return false;

    if (voc_raw)  *voc_raw  = ((uint16_t)rx[0] << 8) | rx[1];
    if (nox_raw)  *nox_raw  = ((uint16_t)rx[3] << 8) | rx[4];
    return true;
}

bool sgp41_init(i2c_port_t port, uint8_t addr, sgp41_handle_t **handle)
{
    if (handle == NULL) return false;

    sgp41_handle_t *dev = calloc(1, sizeof(sgp41_handle_t));
    if (dev == NULL) return false;

    dev->i2c_port = port;
    dev->addr = addr;
    dev->heater_on = false;

    uint8_t tx[2] = { (SGP41_CMD_GET_SERIAL_NUM >> 8) & 0xFF,
                       SGP41_CMD_GET_SERIAL_NUM & 0xFF };
    uint8_t rx[9];
    esp_err_t ret = i2c_master_write_read_device(port, addr, tx, 2,
                                                   rx, 9, pdMS_TO_TICKS(1000));
    if (ret == ESP_OK) {
        dev->serial_number[0] = ((uint16_t)rx[0] << 8) | rx[1];
        dev->serial_number[1] = ((uint16_t)rx[3] << 8) | rx[4];
        dev->serial_number[2] = ((uint16_t)rx[6] << 8) | rx[7];
        ESP_LOGI(TAG, "SGP41 detected, S/N: %04X-%04X-%04X",
                 dev->serial_number[0], dev->serial_number[1],
                 dev->serial_number[2]);
    } else {
        ESP_LOGW(TAG, "Could not read SGP41 serial number — continuing");
    }

    *handle = dev;
    ESP_LOGI(TAG, "Initialized");
    return true;
}

bool sgp41_read_raw(sgp41_handle_t *handle, uint16_t *voc_raw, uint16_t *nox_raw)
{
    if (handle == NULL) return false;
    bool ret = sgp41_execute_measurement(handle, SGP41_CMD_MEASURE_RAW,
                                          voc_raw, nox_raw, SGP41_MEAS_WAIT_MS);
    if (ret) {
        handle->heater_on = true;
    }
    return ret;
}

bool sgp41_conditioning(sgp41_handle_t *handle)
{
    if (handle == NULL) return false;
    uint16_t voc_dummy, nox_dummy;
    bool ret = sgp41_execute_measurement(handle, SGP41_CMD_CONDITIONING,
                                          &voc_dummy, &nox_dummy,
                                          SGP41_CONDITIONING_WAIT_MS);
    if (ret) {
        handle->heater_on = true;
    }
    return ret;
}

bool sgp41_self_test(sgp41_handle_t *handle)
{
    if (handle == NULL) return false;
    uint16_t voc_dummy, nox_dummy;
    return sgp41_execute_measurement(handle, SGP41_CMD_EXECUTE_SELF_TEST,
                                     &voc_dummy, &nox_dummy, 1000);
}

void sgp41_heater_off(sgp41_handle_t *handle)
{
    if (handle == NULL) return;
    uint8_t tx[2] = { (SGP41_CMD_TURN_HEATER_OFF >> 8) & 0xFF,
                       SGP41_CMD_TURN_HEATER_OFF & 0xFF };
    sgp41_write_cmd_raw(handle->i2c_port, handle->addr, tx, 2);
    handle->heater_on = false;
}
