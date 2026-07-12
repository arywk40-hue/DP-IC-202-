/**
 * bme280.c - BME280 Temperature/Humidity/Pressure Sensor Driver
 * 
 * Real hardware driver for Bosch BME280
 * Uses ESP-IDF I2C driver
 */

#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "bme280.h"

static const char *TAG = "BME280";

/* ============================================
 * I2C HELPERS
 * ============================================ */

static esp_err_t bme280_write_reg(bme280_handle_t *handle, uint8_t reg, uint8_t value) {
    return i2c_master_write_to_device(handle->i2c_port, handle->addr,
                                      &reg, 1, &value, 1, pdMS_TO_TICKS(100));
}

static esp_err_t bme280_read_reg(bme280_handle_t *handle, uint8_t reg, 
                                  uint8_t *value, size_t len) {
    return i2c_master_write_read_device(handle->i2c_port, handle->addr,
                                        &reg, 1, value, len, pdMS_TO_TICKS(100));
}

/* ============================================
 * CALIBRATION DATA
 * ============================================ */

static bool bme280_read_calibration(bme280_handle_t *handle) {
    uint8_t calib[26];
    
    // Read temperature and pressure calibration data (0x88-0xA1)
    if (bme280_read_reg(handle, BME280_REG_CALIB_00, calib, 26) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to read calibration data");
        return false;
    }
    
    handle->dig_T1 = (uint16_t)(calib[1] << 8 | calib[0]);
    handle->dig_T2 = (int16_t)(calib[3] << 8 | calib[2]);
    handle->dig_T3 = (int16_t)(calib[5] << 8 | calib[4]);
    
    handle->dig_P1 = (uint16_t)(calib[7] << 8 | calib[6]);
    handle->dig_P2 = (int16_t)(calib[9] << 8 | calib[8]);
    handle->dig_P3 = (int16_t)(calib[11] << 8 | calib[10]);
    handle->dig_P4 = (int16_t)(calib[13] << 8 | calib[12]);
    handle->dig_P5 = (int16_t)(calib[15] << 8 | calib[14]);
    handle->dig_P6 = (int16_t)(calib[17] << 8 | calib[16]);
    handle->dig_P7 = (int16_t)(calib[19] << 8 | calib[18]);
    handle->dig_P8 = (int16_t)(calib[21] << 8 | calib[20]);
    handle->dig_P9 = (int16_t)(calib[23] << 8 | calib[22]);
    
    handle->dig_H1 = calib[25];
    
    // Read humidity calibration data (0xA1, 0xE1-0xE7)
    uint8_t hum_calib[7];
    if (bme280_read_reg(handle, 0xE1, hum_calib, 7) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to read humidity calibration data");
        return false;
    }
    
    handle->dig_H2 = (int16_t)(hum_calib[1] << 8 | hum_calib[0]);
    handle->dig_H3 = hum_calib[2];
    handle->dig_H4 = (int16_t)((hum_calib[3] << 4) | (hum_calib[4] & 0x0F));
    handle->dig_H5 = (int16_t)((hum_calib[4] >> 4) | (hum_calib[5] << 4));
    handle->dig_H6 = (int8_t)hum_calib[6];
    
    ESP_LOGI(TAG, "Calibration data loaded");
    ESP_LOGI(TAG, "  T1=%u, T2=%d, T3=%d", handle->dig_T1, handle->dig_T2, handle->dig_T3);
    ESP_LOGI(TAG, "  P1=%u, P2=%d, P3=%d", handle->dig_P1, handle->dig_P2, handle->dig_P3);
    ESP_LOGI(TAG, "  H1=%u, H2=%d, H3=%d", handle->dig_H1, handle->dig_H2, handle->dig_H3);
    
    return true;
}

/* ============================================
 * COMPENSATION FORMULAS (from Bosch datasheet)
 * ============================================ */

static int32_t bme280_compensate_T(bme280_handle_t *handle, int32_t adc_T) {
    int32_t var1, var2, T;
    
    var1 = ((((adc_T >> 3) - ((int32_t)handle->dig_T1 << 1))) * ((int32_t)handle->dig_T2)) >> 11;
    var2 = (((((adc_T >> 4) - ((int32_t)handle->dig_T1)) * 
             ((adc_T >> 4) - ((int32_t)handle->dig_T1))) >> 12) * 
            ((int32_t)handle->dig_T3)) >> 14;
    
    handle->t_fine = var1 + var2;
    T = (handle->t_fine * 5 + 128) >> 8;
    
    return T;  // Temperature in 0.01°C
}

static uint32_t bme280_compensate_H(bme280_handle_t *handle, int32_t adc_H) {
    int32_t v_x1_u32r;
    
    v_x1_u32r = (handle->t_fine - ((int32_t)76800));
    
    if (v_x1_u32r == 0) {
        return 0;
    }
    
    v_x1_u32r = (((((adc_H << 14) - (((int32_t)handle->dig_H4) << 20) - 
                    (((int32_t)handle->dig_H5) * v_x1_u32r)) + 
                   ((int32_t)16384)) >> 15) * (((((((v_x1_u32r * 
                   ((int32_t)handle->dig_H6)) >> 10) * ((v_x1_u32r * 
                   ((int32_t)handle->dig_H3)) >> 11)) + ((int32_t)32768)) >> 10) + 
                   ((int32_t)2097152)) * ((int32_t)handle->dig_H2 + 32768)) >> 15);
    
    v_x1_u32r = (v_x1_u32r - (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) * 
                                 ((int32_t)handle->dig_H1)) >> 4));
    
    if (v_x1_u32r < 0) v_x1_u32r = 0;
    if (v_x1_u32r > 419430400) v_x1_u32r = 419430400;
    
    return (uint32_t)(v_x1_u32r >> 12);  // Humidity in 0.01%RH
}

static uint32_t bme280_compensate_P(bme280_handle_t *handle, int32_t adc_P) {
    int64_t var1, var2, p;
    
    var1 = ((int64_t)handle->t_fine) - 128000;
    var2 = var1 * var1 * (int64_t)handle->dig_P6;
    var2 = var2 + ((var1 * (int64_t)handle->dig_P5) << 17);
    var2 = var2 + (((int64_t)handle->dig_P4) << 35);
    var1 = ((var1 * var1 * (int64_t)handle->dig_P3) >> 8) + 
           ((var1 * (int64_t)handle->dig_P2) << 12);
    var1 = (((((int64_t)1) << 47) + var1)) * ((int64_t)handle->dig_P1) >> 33;
    
    if (var1 == 0) {
        return 0;
    }
    
    p = 1048576 - adc_P;
    p = (((p << 31) - var2) * 3125) / var1;
    var1 = (((int64_t)handle->dig_P9) * (p >> 13) * (p >> 13)) >> 25;
    var2 = (((int64_t)handle->dig_P8) * p) >> 19;
    p = ((p + var1 + var2) >> 8) + (((int64_t)handle->dig_P7) << 4);
    
    return (uint32_t)(p >> 4);  // Pressure in Pa
}

/* ============================================
 * PUBLIC API
 * ============================================ */

bool bme280_init(i2c_port_t port, uint8_t addr, bme280_handle_t **handle) {
    ESP_LOGI(TAG, "Initializing BME280 at address 0x%02X...", addr);
    
    // Allocate handle
    bme280_handle_t *dev = calloc(1, sizeof(bme280_handle_t));
    if (!dev) {
        ESP_LOGE(TAG, "Failed to allocate handle");
        return false;
    }
    
    dev->i2c_port = port;
    dev->addr = addr;
    
    // Check chip ID
    uint8_t chip_id;
    if (bme280_read_reg(dev, BME280_REG_ID, &chip_id, 1) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to read chip ID");
        free(dev);
        return false;
    }
    
    if (chip_id != BME280_CHIP_ID) {
        ESP_LOGE(TAG, "Invalid chip ID: 0x%02X (expected 0x%02X)", 
                 chip_id, BME280_CHIP_ID);
        free(dev);
        return false;
    }
    ESP_LOGI(TAG, "BME280 detected, chip ID: 0x%02X", chip_id);
    
    // Reset device
    bme280_write_reg(dev, BME280_REG_RESET, BME280_RESET_VALUE);
    vTaskDelay(pdMS_TO_TICKS(100));
    
    // Read calibration data
    if (!bme280_read_calibration(dev)) {
        free(dev);
        return false;
    }
    
    // Default configuration: normal mode, oversampling 1x, filter off
    bme280_configure(dev, BME280_OVERSAMPLING_1X, BME280_OVERSAMPLING_1X,
                     BME280_OVERSAMPLING_1X, BME280_MODE_NORMAL,
                     BME280_STANDBY_500MS, BME280_FILTER_OFF);
    
    *handle = dev;
    ESP_LOGI(TAG, "BME280 initialized successfully");
    return true;
}

void bme280_configure(bme280_handle_t *handle, uint8_t osrs_h, uint8_t osrs_t,
                      uint8_t osrs_p, uint8_t mode, uint8_t standby, uint8_t filter) {
    // Configure humidity oversampling
    bme280_write_reg(handle, BME280_REG_CTRL_HUM, osrs_h & 0x07);
    
    // Configure temperature/pressure oversampling and mode
    uint8_t ctrl_meas = (osrs_t << 5) | (osrs_p << 2) | mode;
    bme280_write_reg(handle, BME280_REG_CTRL_MEAS, ctrl_meas);
    
    // Configure standby time and IIR filter
    uint8_t config = (standby << 5) | (filter << 2);
    bme280_write_reg(handle, BME280_REG_CONFIG, config);
    
    ESP_LOGI(TAG, "Configured: osrs_h=%d, osrs_t=%d, osrs_p=%d, mode=%d",
             osrs_h, osrs_t, osrs_p, mode);
}

bool bme280_read(bme280_handle_t *handle, bme280_data_t *data) {
    uint8_t raw[8];
    
    // Read raw data (0xF7-0xFE: press, temp, humidity)
    if (bme280_read_reg(handle, BME270_REG_DATA_START, raw, 8) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to read sensor data");
        return false;
    }
    
    // Parse raw data
    int32_t adc_P = ((int32_t)raw[0] << 12) | ((int32_t)raw[1] << 4) | (raw[2] >> 4);
    int32_t adc_T = ((int32_t)raw[3] << 12) | ((int32_t)raw[4] << 4) | (raw[5] >> 4);
    int32_t adc_H = ((int32_t)raw[6] << 8) | raw[7];
    
    // Compensate values
    int32_t temp_raw = bme280_compensate_T(handle, adc_T);
    uint32_t hum_raw = bme280_compensate_H(handle, adc_H);
    uint32_t pres_raw = bme280_compensate_P(handle, adc_P);
    
    // Convert to real units
    data->temperature = temp_raw / 100.0f;      // °C
    data->humidity = hum_raw / 1024.0f;          // %RH
    data->pressure = pres_raw / 25600.0f;        // hPa
    data->altitude = bme280_calculate_altitude(data->pressure, 1013.25f);
    
    ESP_LOGI(TAG, "Read: T=%.2f°C, H=%.2f%%, P=%.2f hPa, Alt=%.1fm",
             data->temperature, data->humidity, data->pressure, data->altitude);
    
    return true;
}

float bme280_read_temperature(bme280_handle_t *handle) {
    uint8_t raw[3];
    if (bme280_read_reg(handle, BME280_REG_DATA_START + 3, raw, 3) != ESP_OK) {
        return -999.0f;
    }
    
    int32_t adc_T = ((int32_t)raw[0] << 12) | ((int32_t)raw[1] << 4) | (raw[2] >> 4);
    int32_t temp = bme280_compensate_T(handle, adc_T);
    
    return temp / 100.0f;
}

float bme280_read_humidity(bme280_handle_t *handle) {
    uint8_t raw[2];
    if (bme280_read_reg(handle, BME280_REG_DATA_START + 6, raw, 2) != ESP_OK) {
        return -999.0f;
    }
    
    int32_t adc_H = ((int32_t)raw[0] << 8) | raw[1];
    uint32_t hum = bme280_compensate_H(handle, adc_H);
    
    return hum / 1024.0f;
}

float bme280_read_pressure(bme280_handle_t *handle) {
    uint8_t raw[3];
    if (bme280_read_reg(handle, BME280_REG_DATA_START, raw, 3) != ESP_OK) {
        return -999.0f;
    }
    
    int32_t adc_P = ((int32_t)raw[0] << 12) | ((int32_t)raw[1] << 4) | (raw[2] >> 4);
    uint32_t pres = bme280_compensate_P(handle, adc_P);
    
    return pres / 25600.0f;
}

float bme280_calculate_altitude(float pressure_hPa, float sea_level_hPa) {
    // Barometric formula
    return 44330.0f * (1.0f - powf(pressure_hPa / sea_level_hPa, 0.190284f));
}

void bme280_sleep(bme280_handle_t *handle) {
    bme280_configure(handle, BME280_OVERSAMPLING_SKIP, BME280_OVERSAMPLING_SKIP,
                     BME280_OVERSAMPLING_SKIP, BME280_MODE_SLEEP,
                     BME280_STANDBY_0_5MS, BME280_FILTER_OFF);
    ESP_LOGI(TAG, "Entered sleep mode");
}
