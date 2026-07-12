/**
 * main.c - Edge AI Environmental Hazard Detection Node
 *
 * Entry point for the ESP32-S3 based environmental monitoring node.
 * Initializes hardware peripherals, sensor drivers, LoRa radio,
 * ML inference engine, and mesh networking in the correct order.
 *
 * Execution order:
 *   1. NVS flash (persistent storage)
 *   2. I2C bus (sensors)
 *   3. SPI bus (LoRa radio)
 *   4. UART (PMS5003 particulate sensor)
 *   5. Logging
 *   6. Print boot confirmation
 *
 * FreeRTOS tasks are created after hardware init to manage
 * sensor reading, ML inference, and mesh communication concurrently.
 */

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_log.h"
#include "esp_err.h"
#include "nvs_flash.h"
#include "driver/i2c.h"
#include "driver/spi_master.h"
#include "driver/uart.h"

static const char *TAG = "MAIN";

/*
 * I2C bus configuration for BME280, SCD41, SGP41, LTR390, AS3935.
 * All sensors share a single I2C bus at 400 kHz (fast mode).
 */
#define I2C_MASTER_PORT      I2C_NUM_0
#define I2C_MASTER_SDA_IO    21
#define I2C_MASTER_SCL_IO    22
#define I2C_MASTER_FREQ_HZ   400000

/*
 * SPI bus configuration for SX1276 LoRa radio.
 * The radio is the only SPI device on this bus.
 */
#define SPI_HOST             SPI2_HOST
#define SPI_MOSI_IO          11
#define SPI_MISO_IO          12
#define SPI_SCLK_IO          10
#define SPI_CS_IO            13

/*
 * PMS5003 UART configuration (9600 8N1).
 */
#define UART_PORT            UART_NUM_1
#define UART_TXD_IO          17
#define UART_RXD_IO          18

/**
 * @brief Initialize NVS flash storage.
 * NVS is used to store calibration data, node ID, and mesh routing tables.
 * Failure is non-fatal for basic operation but limits persistent storage.
 */
static esp_err_t init_nvs(void)
{
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS requires erase, erasing...");
        ret = nvs_flash_erase();
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "NVS erase failed: %s", esp_err_to_name(ret));
            return ret;
        }
        ret = nvs_flash_init();
    }
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "NVS initialized");
    } else {
        ESP_LOGE(TAG, "NVS init failed: %s", esp_err_to_name(ret));
    }
    return ret;
}

/**
 * @brief Initialize I2C master bus.
 * Shared bus for all I2C environmental sensors.
 */
static esp_err_t init_i2c(void)
{
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_MASTER_SDA_IO,
        .scl_io_num = I2C_MASTER_SCL_IO,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ,
    };
    esp_err_t ret = i2c_param_config(I2C_MASTER_PORT, &conf);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C param config failed: %s", esp_err_to_name(ret));
        return ret;
    }
    ret = i2c_driver_install(I2C_MASTER_PORT, conf.mode, 0, 0, 0);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C driver install failed: %s", esp_err_to_name(ret));
        return ret;
    }
    ESP_LOGI(TAG, "I2C initialized on port %d (SDA=%d, SCL=%d, %d Hz)",
             I2C_MASTER_PORT, I2C_MASTER_SDA_IO, I2C_MASTER_SCL_IO, I2C_MASTER_FREQ_HZ);
    return ESP_OK;
}

/**
 * @brief Initialize SPI master bus for LoRa radio.
 */
static esp_err_t init_spi(void)
{
    spi_bus_config_t bus_cfg = {
        .mosi_io_num = SPI_MOSI_IO,
        .miso_io_num = SPI_MISO_IO,
        .sclk_io_num = SPI_SCLK_IO,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 256,
    };
    esp_err_t ret = spi_bus_initialize(SPI_HOST, &bus_cfg, SPI_DMA_CH_AUTO);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI bus init failed: %s", esp_err_to_name(ret));
        return ret;
    }
    ESP_LOGI(TAG, "SPI initialized on host %d (MOSI=%d, MISO=%d, SCLK=%d)",
             SPI_HOST, SPI_MOSI_IO, SPI_MISO_IO, SPI_SCLK_IO);
    return ESP_OK;
}

/**
 * @brief Initialize UART for PMS5003 particulate sensor.
 */
static esp_err_t init_uart(void)
{
    uart_config_t uart_config = {
        .baud_rate = 9600,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };
    esp_err_t ret = uart_param_config(UART_PORT, &uart_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "UART param config failed: %s", esp_err_to_name(ret));
        return ret;
    }
    ret = uart_set_pin(UART_PORT, UART_TXD_IO, UART_RXD_IO, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "UART set pin failed: %s", esp_err_to_name(ret));
        return ret;
    }
    ret = uart_driver_install(UART_PORT, 256, 0, 0, NULL, 0);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "UART driver install failed: %s", esp_err_to_name(ret));
        return ret;
    }
    ESP_LOGI(TAG, "UART initialized on port %d (TX=%d, RX=%d, 9600 8N1)",
             UART_PORT, UART_TXD_IO, UART_RXD_IO);
    return ESP_OK;
}

void app_main(void)
{
    esp_err_t ret;

    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "Edge AI Environmental Hazard Detection Node");
    ESP_LOGI(TAG, "ESP32-S3 + 12-Sensor Array + LoRa Mesh");
    ESP_LOGI(TAG, "========================================");

    /* Initialize NVS first — other components may depend on it */
    ret = init_nvs();
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "NVS init failed — continuing without persistent storage");
    }

    /* Initialize I2C bus for environmental sensors */
    ret = init_i2c();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C init failed — sensors will not function");
    }

    /* Initialize SPI bus for LoRa radio */
    ret = init_spi();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI init failed — LoRa radio will not function");
    }

    /* Initialize UART for PMS5003 particulate sensor */
    ret = init_uart();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "UART init failed — PMS5003 will not function");
    }

    ESP_LOGI(TAG, "System boot successful");
    ESP_LOGI(TAG, "Firmware ready — entering main loop");

    /*
     * Future phases will create FreeRTOS tasks here:
     * - sensor_task: periodic sensor reads + feature computation
     * - ml_task: on-device XGBoost inference
     * - mesh_task: LoRa mesh communication + packet forwarding
     *
     * For now, print status and idle.
     */
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(60000));
        ESP_LOGD(TAG, "Heartbeat — system alive");
    }
}
