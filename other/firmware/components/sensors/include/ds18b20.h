/**
 * ds18b20.h - DS18B20 1-Wire Temperature Sensor Driver
 *
 * Real hardware driver for Maxim Integrated DS18B20.
 * Interface: 1-Wire on a single GPIO pin.
 *
 * The DS18B20 measures enclosure temperature and serves as
 * a water-ingress detector (temperature spike from evaporative cooling).
 */

#ifndef DS18B20_H
#define DS18B20_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/*
 * DS18B20 commands (from Maxim Integrated datasheet)
 */
#define DS18B20_CMD_CONVERT_T      0x44
#define DS18B20_CMD_READ_SCRATCH   0xBE
#define DS18B20_CMD_WRITE_SCRATCH  0x4E
#define DS18B20_CMD_COPY_SCRATCH   0x48
#define DS18B20_CMD_RECALL_E2      0xB8
#define DS18B20_CMD_READ_POWER     0xB4

/*
 * Scratchpad byte offsets (9 bytes total)
 */
#define DS18B20_SCRATCH_TEMP_LSB   0
#define DS18B20_SCRATCH_TEMP_MSB   1
#define DS18B20_SCRATCH_TH         2
#define DS18B20_SCRATCH_TL         3
#define DS18B20_SCRATCH_CONFIG     4
#define DS18B20_SCRATCH_CRC        8

/*
 * Resolution bits in config register
 */
#define DS18B20_RES_9BIT           0x00
#define DS18B20_RES_10BIT          0x20
#define DS18B20_RES_11BIT          0x40
#define DS18B20_RES_12BIT          0x60

/* Default resolution (12-bit, 750ms conversion time) */
#define DS18B20_DEFAULT_RESOLUTION DS18B20_RES_12BIT

typedef struct {
    int gpio_pin;
    bool parasitic_power;
} ds18b20_handle_t;

/**
 * @brief Initialize DS18B20 sensor on a GPIO pin.
 * @param gpio_pin  1-Wire data pin (must be GPIO-compatible).
 * @param handle    Output handle.
 * @return ESP_OK on success.
 */
esp_err_t ds18b20_init(int gpio_pin, ds18b20_handle_t **handle);

/**
 * @brief Read temperature in Celsius.
 * Initiates conversion, waits for completion (max 750ms at 12-bit),
 * then reads and returns the temperature.
 * @param handle  Device handle.
 * @param temp    Output temperature in °C.
 * @return ESP_OK on success.
 */
esp_err_t ds18b20_read_temperature(ds18b20_handle_t *handle, float *temp);

/**
 * @brief Read the 9-byte scratchpad.
 * @param handle    Device handle.
 * @param scratch   Output buffer (must be 9 bytes).
 * @return ESP_OK on success.
 */
esp_err_t ds18b20_read_scratchpad(ds18b20_handle_t *handle, uint8_t *scratch);

/**
 * @brief Set sensor resolution.
 * @param handle      Device handle.
 * @param resolution  One of DS18B20_RES_* constants.
 * @return ESP_OK on success.
 */
esp_err_t ds18b20_set_resolution(ds18b20_handle_t *handle, uint8_t resolution);

/**
 * @brief Check if the sensor is present on the bus (presence pulse).
 * @param gpio_pin  1-Wire data pin.
 * @return true if sensor responded.
 */
bool ds18b20_detect(int gpio_pin);

#ifdef __cplusplus
}
#endif

#endif /* DS18B20_H */
