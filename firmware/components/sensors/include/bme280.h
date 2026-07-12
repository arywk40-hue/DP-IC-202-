/**
 * bme280.h - BME280 Temperature/Humidity/Pressure Sensor Driver
 * 
 * Real hardware driver for Bosch BME280
 * Interface: I2C (0x76 or 0x77)
 */

#ifndef BME280_H
#define BME280_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/i2c.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================
 * BME280 REGISTERS (Real Hardware)
 * ============================================ */

#define BME280_ADDR_PRIMARY          0x76
#define BME280_ADDR_SECONDARY        0x77

// Calibration registers (0x88-0xA1, 0xE1-0xF0)
#define BME280_REG_CALIB_00          0x88
#define BME280_REG_CALIB_26          0xA1
#define BME280_REG_CALIB_33          0xE1

// Control registers
#define BME280_REG_ID                0xD0
#define BME280_REG_RESET             0xE0
#define BME280_REG_CTRL_HUM          0xF2
#define BME280_REG_CTRL_MEAS         0xF4
#define BME280_REG_CONFIG            0xF5
#define BME280_REG_DATA_START        0xF7

// Chip ID
#define BME280_CHIP_ID               0x60

// Reset value
#define BME280_RESET_VALUE           0xB6

// Oversampling settings
#define BME280_OVERSAMPLING_SKIP     0x00
#define BME280_OVERSAMPLING_1X       0x01
#define BME280_OVERSAMPLING_2X       0x02
#define BME280_OVERSAMPLING_4X       0x03
#define BME280_OVERSAMPLING_8X       0x04
#define BME280_OVERSAMPLING_16X      0x05

// Mode settings
#define BME280_MODE_SLEEP            0x00
#define BME280_MODE_FORCED           0x01
#define BME280_MODE_NORMAL           0x03

// Standby time settings
#define BME280_STANDBY_0_5MS         0x00
#define BME280_STANDBY_62_5MS        0x01
#define BME280_STANDBY_125MS         0x02
#define BME280_STANDBY_250MS         0x03
#define BME280_STANDBY_500MS         0x04
#define BME280_STANDBY_1000MS        0x05
#define BME280_STANDBY_10MS          0x06
#define BME280_STANDBY_20MS          0x07

// IIR filter settings
#define BME280_FILTER_OFF            0x00
#define BME280_FILTER_2              0x01
#define BME280_FILTER_4              0x02
#define BME280_FILTER_8              0x03
#define BME280_FILTER_16             0x04

/* ============================================
 * DATA STRUCTURES
 * ============================================ */

typedef struct {
    i2c_port_t i2c_port;
    uint8_t addr;
    int32_t t_fine;  // Temperature for compensation
    
    // Compensation parameters (from calibration)
    uint16_t dig_T1;
    int16_t  dig_T2;
    int16_t  dig_T3;
    uint8_t  dig_H1;
    int16_t  dig_H2;
    uint8_t  dig_H3;
    int16_t  dig_H4;
    int16_t  dig_H5;
    int8_t   dig_H6;
    uint8_t  dig_P1;
    int16_t  dig_P2;
    int16_t  dig_P3;
    int16_t  dig_P4;
    int16_t  dig_P5;
    int16_t  dig_P6;
    int16_t  dig_P7;
    int16_t  dig_P8;
    int16_t  dig_P9;
} bme280_handle_t;

typedef struct {
    float temperature;    // Celsius
    float humidity;       // %RH
    float pressure;       // hPa
    float altitude;       // meters (derived from pressure)
} bme280_data_t;

/* ============================================
 * API FUNCTIONS
 * ============================================ */

/**
 * @brief Initialize BME280 sensor
 * @param port I2C port number
 * @param addr I2C address (0x76 or 0x77)
 * @param handle Output handle
 * @return true on success
 */
bool bme280_init(i2c_port_t port, uint8_t addr, bme280_handle_t **handle);

/**
 * @brief Configure BME280
 * @param handle Device handle
 * @param osrs_h Humidity oversampling
 * @param osrs_t Temperature oversampling
 * @param osrs_p Pressure oversampling
 * @param mode Operating mode
 * @param standby Standby time
 * @param filter IIR filter coefficient
 */
void bme280_configure(bme280_handle_t *handle, uint8_t osrs_h, uint8_t osrs_t,
                      uint8_t osrs_p, uint8_t mode, uint8_t standby, uint8_t filter);

/**
 * @brief Read sensor data
 * @param handle Device handle
 * @param data Output data structure
 * @return true on success
 */
bool bme280_read(bme280_handle_t *handle, bme280_data_t *data);

/**
 * @brief Read temperature only (faster)
 * @param handle Device handle
 * @return Temperature in Celsius
 */
float bme280_read_temperature(bme280_handle_t *handle);

/**
 * @brief Read humidity only (faster)
 * @param handle Device handle
 * @return Humidity in %RH
 */
float bme280_read_humidity(bme280_handle_t *handle);

/**
 * @brief Read pressure only (faster)
 * @param handle Device handle
 * @return Pressure in hPa
 */
float bme280_read_pressure(bme280_handle_t *handle);

/**
 * @brief Calculate altitude from pressure
 * @param pressure_hPa Pressure in hPa
 * @param sea_level_hPa Sea level pressure in hPa
 * @return Altitude in meters
 */
float bme280_calculate_altitude(float pressure_hPa, float sea_level_hPa);

/**
 * @brief Put BME280 to sleep
 * @param handle Device handle
 */
void bme280_sleep(bme280_handle_t *handle);

#ifdef __cplusplus
}
#endif

#endif // BME280_H
