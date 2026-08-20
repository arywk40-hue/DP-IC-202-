/**
 * pms5003.c - PMS5003 Particulate Matter Sensor Implementation
 *
 * Real hardware driver for Plantower PMS5003 laser-scattering
 * particulate matter sensor. Interface: UART (9600 baud, 8N1).
 *
 * The PMS5003 operates in either active mode (continuous data push)
 * or passive mode (query-response). This driver uses passive mode
 * to conserve power, waking the sensor only for periodic readings.
 *
 * Data frame format (32 bytes):
 *   [0-1]     Start characters (0x42, 0x4D)
 *   [2-3]     Frame length (28 bytes, big-endian)
 *   [4-5]     PM1.0 (CF=1, μg/m³)
 *   [6-7]     PM2.5 (CF=1, μg/m³)
 *   [8-9]     PM10  (CF=1, μg/m³)
 *   [10-11]   PM1.0 (atmospheric, μg/m³)
 *   [12-13]   PM2.5 (atmospheric, μg/m³)
 *   [14-15]   PM10  (atmospheric, μg/m³)
 *   [16-17]   Particles >0.3 μm / 0.1L
 *   [18-19]   Particles >0.5 μm / 0.1L
 *   [20-21]   Particles >1.0 μm / 0.1L
 *   [22-23]   Particles >2.5 μm / 0.1L
 *   [24-25]   Particles >5.0 μm / 0.1L
 *   [26-27]   Particles >10 μm / 0.1L
 *   [28-29]   Reserved (or density/temp/humidity in newer models)
 *   [30-31]   Checksum (sum of bytes 0..29)
 *
 * Reference: Plantower PMS5003 datasheet v1.3
 */

#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "pms5003.h"

static const char *TAG = "PMS5003";

/*
 * Timeout for waiting for UART data (milliseconds).
 * The sensor streams data every ~200ms in active mode.
 * In passive mode, data arrives within ~500ms of request.
 */
#define PMS5003_READ_TIMEOUT_MS     2000
#define PMS5003_RESPONSE_TIMEOUT_MS 1000

/**
 * @brief Send a command to the PMS5003.
 * Commands are 7-byte frames: 0x42 0x4D <cmd> 0x00 0x00 <checksum_high> <checksum_low>
 */
static void pms5003_send_command(pms5003_handle_t *handle, uint8_t cmd)
{
    uint8_t buf[7];
    buf[0] = 0x42;
    buf[1] = 0x4D;
    buf[2] = cmd;
    buf[3] = 0x00;
    buf[4] = 0x00;
    /* Checksum = sum of bytes 0..4 */
    uint16_t sum = 0x42 + 0x4D + cmd;
    buf[5] = (sum >> 8) & 0xFF;
    buf[6] = sum & 0xFF;

    uart_write_bytes(handle->uart_num, buf, 7);
}

/**
 * @brief Read and validate a 32-byte PMS5003 data frame.
 * @return true if frame is valid (start chars + checksum match).
 */
static bool pms5003_read_frame(pms5003_handle_t *handle, uint8_t *buf, uint32_t timeout_ms)
{
    int len = uart_read_bytes(handle->uart_num, buf, PMS5003_DATA_LENGTH,
                              pdMS_TO_TICKS(timeout_ms));
    if (len < PMS5003_DATA_LENGTH) {
        ESP_LOGW(TAG, "Short read: %d bytes (expected %d)", len, PMS5003_DATA_LENGTH);
        return false;
    }

    /* Validate start characters */
    if (buf[0] != PMS5003_START_CHAR_1 || buf[1] != PMS5003_START_CHAR_2) {
        ESP_LOGW(TAG, "Invalid start chars: 0x%02X 0x%02X", buf[0], buf[1]);
        return false;
    }

    /* Validate checksum */
    uint16_t calc = 0;
    for (int i = 0; i < 30; i++) {
        calc += buf[i];
    }
    uint16_t reported = ((uint16_t)buf[30] << 8) | buf[31];
    if (calc != reported) {
        ESP_LOGW(TAG, "Checksum mismatch: calc=0x%04X, reported=0x%04X", calc, reported);
        return false;
    }

    return true;
}

/* ======================== Public API ======================== */

bool pms5003_init(uart_port_t uart_num, gpio_num_t pin_set,
                  gpio_num_t pin_rst, pms5003_handle_t **handle)
{
    ESP_LOGI(TAG, "Initializing PMS5003 on UART%d...", uart_num);

    pms5003_handle_t *dev = (pms5003_handle_t *)calloc(1, sizeof(pms5003_handle_t));
    if (!dev) {
        ESP_LOGE(TAG, "Failed to allocate handle");
        return false;
    }

    dev->uart_num = uart_num;
    dev->pin_set = pin_set;
    dev->pin_rst = pin_rst;
    dev->is_sleeping = false;
    dev->passive_mode = true;

    /* Configure SET pin if connected */
    if (pin_set >= 0) {
        gpio_config_t io_conf = {
            .pin_bit_mask = (1ULL << pin_set),
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&io_conf);
        gpio_set_level(pin_set, 1);  /* Enable sensor */
    }

    /* Configure RST pin if connected */
    if (pin_rst >= 0) {
        gpio_config_t io_conf = {
            .pin_bit_mask = (1ULL << pin_rst),
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&io_conf);
        gpio_set_level(pin_rst, 1);  /* Release reset */
    }

    /* Reset sensor */
    if (pin_rst >= 0) {
        gpio_set_level(pin_rst, 0);
        vTaskDelay(pdMS_TO_TICKS(10));
        gpio_set_level(pin_rst, 1);
        vTaskDelay(pdMS_TO_TICKS(1000));  /* Sensor startup time */
    }

    /* Flush any stale UART data */
    uart_flush_input(uart_num);

    /* Switch to passive mode */
    pms5003_set_passive(dev, true);

    *handle = dev;
    ESP_LOGI(TAG, "PMS5003 initialized");
    return true;
}

bool pms5003_read(pms5003_handle_t *handle, pms5003_data_t *data)
{
    return pms5003_read_timeout(handle, data, PMS5003_READ_TIMEOUT_MS);
}

bool pms5003_read_timeout(pms5003_handle_t *handle, pms5003_data_t *data,
                          uint32_t timeout_ms)
{
    if (handle == NULL || data == NULL) {
        return false;
    }

    uint8_t buf[PMS5003_DATA_LENGTH];

    /* In passive mode, request data */
    if (handle->passive_mode) {
        if (handle->is_sleeping) {
            pms5003_wake_up(handle);
        }
        pms5003_request_data(handle);
    }

    /* Read frame */
    if (!pms5003_read_frame(handle, buf, timeout_ms)) {
        return false;
    }

    /* Parse all fields (big-endian) */
    data->pm1_0_cf   = ((uint16_t)buf[4]  << 8) | buf[5];
    data->pm2_5_cf   = ((uint16_t)buf[6]  << 8) | buf[7];
    data->pm10_cf    = ((uint16_t)buf[8]  << 8) | buf[9];
    data->pm1_0_atm  = ((uint16_t)buf[10] << 8) | buf[11];
    data->pm2_5_atm  = ((uint16_t)buf[12] << 8) | buf[13];
    data->pm10_atm   = ((uint16_t)buf[14] << 8) | buf[15];
    data->count_0_3  = ((uint16_t)buf[16] << 8) | buf[17];
    data->count_0_5  = ((uint16_t)buf[18] << 8) | buf[19];
    data->count_1_0  = ((uint16_t)buf[20] << 8) | buf[21];
    data->count_2_5  = ((uint16_t)buf[22] << 8) | buf[23];
    data->count_5_0  = ((uint16_t)buf[24] << 8) | buf[25];
    data->count_10   = ((uint16_t)buf[26] << 8) | buf[27];

    /* Flush any remaining bytes in the RX buffer */
    uart_flush_input(handle->uart_num);

    ESP_LOGD(TAG, "PM2.5: %d μg/m³ (CF=1), %d μg/m³ (atm)",
             data->pm2_5_cf, data->pm2_5_atm);
    return true;
}

void pms5003_set_passive(pms5003_handle_t *handle, bool passive)
{
    if (passive) {
        pms5003_send_command(handle, PMS5003_CMD_PASSIVE_MODE);
    } else {
        pms5003_send_command(handle, PMS5003_CMD_ACTIVE_MODE);
    }
    handle->passive_mode = passive;
    vTaskDelay(pdMS_TO_TICKS(100));
}

void pms5003_request_data(pms5003_handle_t *handle)
{
    pms5003_send_command(handle, PMS5003_CMD_READ_DATA);
}

void pms5003_sleep(pms5003_handle_t *handle)
{
    pms5003_send_command(handle, PMS5003_CMD_SLEEP);
    handle->is_sleeping = true;
    ESP_LOGI(TAG, "Entered sleep mode");
}

void pms5003_wake_up(pms5003_handle_t *handle)
{
    /* Wake requires pulling SET high for 100ms */
    if (handle->pin_set >= 0) {
        gpio_set_level(handle->pin_set, 1);
    }
    vTaskDelay(pdMS_TO_TICKS(100));

    /* Wake command */
    pms5003_send_command(handle, PMS5003_CMD_WAKE_UP);
    handle->is_sleeping = false;

    /* Sensor needs ~30s to stabilize after wake */
    vTaskDelay(pdMS_TO_TICKS(100));

    /* Flush startup data */
    uart_flush_input(handle->uart_num);
    ESP_LOGI(TAG, "Woken up");
}

void pms5003_reset(pms5003_handle_t *handle)
{
    if (handle->pin_rst >= 0) {
        gpio_set_level(handle->pin_rst, 0);
        vTaskDelay(pdMS_TO_TICKS(10));
        gpio_set_level(handle->pin_rst, 1);
        vTaskDelay(pdMS_TO_TICKS(1000));
        uart_flush_input(handle->uart_num);
        ESP_LOGI(TAG, "Reset complete");
    }
}

const char* pms5003_get_aqi_category(uint16_t pm25)
{
    /* Based on US EPA AQI breakpoints */
    if (pm25 <= 12)    return "Good";
    if (pm25 <= 35)    return "Moderate";
    if (pm25 <= 55)    return "Unhealthy for Sensitive";
    if (pm25 <= 150)   return "Unhealthy";
    if (pm25 <= 250)   return "Very Unhealthy";
    return "Hazardous";
}
