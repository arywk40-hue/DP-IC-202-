/**
 * pms5003.h - PMS5003 Particulate Matter Sensor Driver
 * 
 * Real hardware driver for Plantower PMS5003
 * Interface: UART (9600 baud)
 */

#ifndef PMS5003_H
#define PMS5003_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/uart.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================
 * PMS5003 CONSTANTS
 * ============================================ */

#define PMS5003_BAUD_RATE           9600
#define PMS5003_DATA_LENGTH         32
#define PMS5003_START_CHAR_1        0x42
#define PMS5003_START_CHAR_2        0x4D

// Passive mode commands
#define PMS5003_CMD_PASSIVE_MODE    0xE1
#define PMS5003_CMD_ACTIVE_MODE     0xE0
#define PMS5003_CMD_READ_DATA       0xE2
#define PMS5003_CMD_SLEEP           0xE4
#define PMS5003_CMD_WAKE_UP         0xE3

/* ============================================
 * DATA STRUCTURES
 * ============================================ */

typedef struct {
    uart_port_t uart_num;
    gpio_num_t pin_set;           // SET pin (active high to enable)
    gpio_num_t pin_rst;           // RST pin (active low to reset)
    bool is_sleeping;
    bool passive_mode;
} pms5003_handle_t;

typedef struct {
    // Standard PM concentrations (μg/m³)
    uint16_t pm1_0_cf;            // PM1.0 (CF=1, atmospheric)
    uint16_t pm2_5_cf;            // PM2.5 (CF=1, atmospheric)
    uint16_t pm10_cf;             // PM10 (CF=1, atmospheric)
    uint16_t pm1_0_atm;           // PM1.0 (atmospheric environment)
    uint16_t pm2_5_atm;           // PM2.5 (atmospheric environment)
    uint16_t pm10_atm;            // PM10 (atmospheric environment)
    
    // Particle counts (particles per 0.1L air)
    uint16_t count_0_3;           // >0.3 μm
    uint16_t count_0_5;           // >0.5 μm
    uint16_t count_1_0;           // >1.0 μm
    uint16_t count_2_5;           // >2.5 μm
    uint16_t count_5_0;           // >5.0 μm
    uint16_t count_10;            // >10 μm
    
    // Environmental
    uint16_t particle_density;    // Raw particle density
    uint16_t temperature;         // Reserved (not available in standard PMS5003)
    uint16_t humidity;            // Reserved (not available in standard PMS5003)
    uint16_t version;             // Firmware version
    uint16_t error_code;          // Error code
} pms5003_data_t;

/* ============================================
 * API FUNCTIONS
 * ============================================ */

/**
 * @brief Initialize PMS5003 sensor
 * @param uart_num UART port number
 * @param pin_set SET pin (or -1 if not connected)
 * @param pin_rst RST pin (or -1 if not connected)
 * @param handle Output handle
 * @return true on success
 */
bool pms5003_init(uart_port_t uart_num, gpio_num_t pin_set, 
                  gpio_num_t pin_rst, pms5003_handle_t **handle);

/**
 * @brief Read sensor data (blocking)
 * @param handle Device handle
 * @param data Output data structure
 * @return true on success
 */
bool pms5003_read(pms5003_handle_t *handle, pms5003_data_t *data);

/**
 * @brief Read data with timeout
 * @param handle Device handle
 * @param data Output data structure
 * @param timeout_ms Timeout in milliseconds
 * @return true on success, false on timeout
 */
bool pms5003_read_timeout(pms5003_handle_t *handle, pms5003_data_t *data, 
                          uint32_t timeout_ms);

/**
 * @brief Set passive mode (query-based)
 * @param handle Device handle
 * @param passive true for passive, false for active
 */
void pms5003_set_passive(pms5003_handle_t *handle, bool passive);

/**
 * @brief Request data in passive mode
 * @param handle Device handle
 */
void pms5003_request_data(pms5003_handle_t *handle);

/**
 * @brief Put sensor to sleep
 * @param handle Device handle
 */
void pms5003_sleep(pms5003_handle_t *handle);

/**
 * @brief Wake up sensor from sleep
 * @param handle Device handle
 */
void pms5003_wake_up(pms5003_handle_t *handle);

/**
 * @brief Reset sensor via RST pin
 * @param handle Device handle
 */
void pms5003_reset(pms5003_handle_t *handle);

/**
 * @brief Get PM2.5 AQI category
 * @param pm25 PM2.5 value in μg/m³
 * @return AQI category string
 */
const char* pms5003_get_aqi_category(uint16_t pm25);

#ifdef __cplusplus
}
#endif

#endif // PMS5003_H
