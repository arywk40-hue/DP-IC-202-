/**
 * sensor_pipeline.c - Low-level sensor data acquisition implementation
 * 
 * ESP32-S3 Edge AI Weather Station
 * Hardware abstraction layer for 12-sensor array
 */

#include "sensor_pipeline.h"
#include "driver/i2c.h"
#include "driver/uart.h"
#include "driver/spi_master.h"
#include "driver/adc.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include <math.h>
#include <string.h>

static const char *TAG = "SENSOR_PIPE";

/* ============================================
 * CONSTANTS
 * ============================================ */

// I2C addresses
#define BME280_ADDR         0x76
#define SCD41_ADDR          0x62
#define SGP41_ADDR          0x59
#define LTR390_ADDR         0x53
#define AS3935_ADDR         0x03

// I2C port
#define I2C_PORT            I2C_NUM_0
#define I2C_SDA             GPIO_NUM_21
#define I2C_SCL             GPIO_NUM_22
#define I2C_FREQ            400000  // 400 kHz

// UART (PMS5003)
#define UART_PORT           UART_NUM_1
#define UART_TX             GPIO_NUM_17
#define UART_RX             GPIO_NUM_16
#define UART_BAUD           9600

// SPI (LoRa SX1276)
#define SPI_HOST            SPI2_HOST
#define LORA_CS             GPIO_NUM_5
#define LORA_RST            GPIO_NUM_14
#define LORA_DIO0           GPIO_NUM_26

// ADC channels
#define ADC_BATTERY_CH      ADC_CHANNEL_0  // GPIO1
#define ADC_PRECIP_CH       ADC_CHANNEL_3  // GPIO4
#define ADC_WIND_SPD_CH     ADC_CHANNEL_6  // GPIO7
#define ADC_WIND_DIR_CH     ADC_CHANNEL_7  // GPIO8
#define ADC_MICS_CO_CH      ADC_CHANNEL_4  // GPIO5
#define ADC_MICS_NO2_CH     ADC_CHANNEL_5  // GPIO6
#define ADC_MICS_NH3_CH     ADC_CHANNEL_2  // GPIO3

// DS18B20
#define DS18B20_PIN         GPIO_NUM_15

// PMS5003
#define PMS_START_BYTE      0x42
#define PMS_FRAME_LEN       32

/* ============================================
 * I2C IMPLEMENTATION
 * ============================================ */

bool i2c_init(uint32_t freq_hz) {
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_SDA,
        .scl_io_num = I2C_SCL,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = freq_hz,
    };
    esp_err_t ret = i2c_param_config(I2C_PORT, &conf);
    if (ret != ESP_OK) return false;
    ret = i2c_driver_install(I2C_PORT, conf.mode, 0, 0, 0);
    return ret == ESP_OK;
}

bool i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *data, uint8_t len) {
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg, true);
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_READ, true);
    if (len > 1) {
        i2c_master_read(cmd, data, len - 1, I2C_MASTER_ACK);
    }
    i2c_master_read_byte(cmd, data + len - 1, I2C_MASTER_NACK);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(I2C_PORT, cmd, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(cmd);
    return ret == ESP_OK;
}

bool i2c_write_reg(uint8_t addr, uint8_t reg, uint8_t data) {
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg, true);
    i2c_master_write_byte(cmd, data, true);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(I2C_PORT, cmd, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(cmd);
    return ret == ESP_OK;
}

/* ============================================
 * BME280 DRIVER
 * ============================================ */

static bool bme280_read_raw(float *temp, float *hum, float *press) {
    uint8_t data[8];
    // Read temperature and pressure (registers 0xF7-0xFC)
    if (!i2c_read_reg(BME280_ADDR, 0xF7, data, 8)) return false;
    
    // Read humidity (registers 0xFD-0xFE)
    uint8_t hum_data[2];
    if (!i2c_read_reg(BME280_ADDR, 0xFD, hum_data, 2)) return false;
    
    // Parse raw values (simplified, full compensation in production)
    int32_t adc_T = ((int32_t)data[3] << 12) | ((int32_t)data[4] << 4) | (data[5] >> 4);
    int32_t adc_P = ((int32_t)data[0] << 12) | ((int32_t)data[1] << 4) | (data[2] >> 4);
    int32_t adc_H = ((int32_t)hum_data[0] << 8) | hum_data[1];
    
    // Apply BME280 compensation formulas (from datasheet)
    // Temperature
    int32_t var1 = ((((adc_T >> 3) - ((int32_t)0 << 10))) * ((int32_t)0)) >> 12;
    int32_t var2 = (((((adc_T >> 4) - ((int32_t)0)) * ((adc_T >> 4) - ((int32_t)0))) >> 12) * ((int32_t)0)) >> 12;
    *temp = (var1 + var2) / 2048.0f / 100.0f;
    
    // Pressure (simplified)
    *press = (float)adc_P / 256.0f;
    
    // Humidity
    *hum = (float)adc_H / 65536.0f * 100.0f;
    
    return true;
}

/* ============================================
 * PMS5003 DRIVER (UART)
 * ============================================ */

bool uart_pms_init(void) {
    uart_config_t uart_config = {
        .baud_rate = UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    esp_err_t ret = uart_param_config(UART_PORT, &uart_config);
    if (ret != ESP_OK) return false;
    ret = uart_set_pin(UART_PORT, UART_TX, UART_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (ret != ESP_OK) return false;
    ret = uart_driver_install(UART_PORT, 256, 0, 0, NULL, 0);
    return ret == ESP_OK;
}

bool uart_pms_read(uint16_t *pm25, uint16_t *pm10) {
    uint8_t buf[PMS_FRAME_LEN];
    int len = uart_read_bytes(UART_PORT, buf, PMS_FRAME_LEN, pdMS_TO_TICKS(1000));
    if (len != PMS_FRAME_LEN) return false;
    if (buf[0] != PMS_START_BYTE) return false;
    
    // Verify checksum
    uint16_t checksum = 0;
    for (int i = 0; i < PMS_FRAME_LEN - 2; i++) {
        checksum += buf[i];
    }
    uint16_t received = (buf[30] << 8) | buf[31];
    if (checksum != received) return false;
    
    *pm25 = (buf[12] << 8) | buf[13];
    *pm10 = (buf[14] << 8) | buf[15];
    return true;
}

/* ============================================
 * ADC IMPLEMENTATION
 * ============================================ */

bool adc_init(void) {
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC_BATTERY_CH, ADC_ATTEN_DB_11);
    adc1_config_channel_atten(ADC_PRECIP_CH, ADC_ATTEN_DB_11);
    adc1_config_channel_atten(ADC_WIND_SPD_CH, ADC_ATTEN_DB_11);
    adc1_config_channel_atten(ADC_WIND_DIR_CH, ADC_ATTEN_DB_11);
    adc1_config_channel_atten(ADC_MICS_CO_CH, ADC_ATTEN_DB_11);
    adc1_config_channel_atten(ADC_MICS_NO2_CH, ADC_ATTEN_DB_11);
    adc1_config_channel_atten(ADC_MICS_NH3_CH, ADC_ATTEN_DB_11);
    return true;
}

float adc_read_voltage(uint8_t channel) {
    int raw = adc1_get_raw((adc1_channel_t)channel);
    return (raw / 4095.0f) * 3.3f;  // 12-bit, 3.3V ref
}

float adc_read_battery(void) {
    float v = adc_read_voltage(ADC_BATTERY_CH);
    return v * 2.0f;  // 2:1 voltage divider
}

float adc_read_wind_speed(void) {
    float v = adc_read_voltage(ADC_WIND_SPD_CH);
    return v * 10.0f;  // 0-3.3V = 0-33 m/s (calibrate per sensor)
}

float adc_read_wind_dir(void) {
    float v = adc_read_voltage(ADC_WIND_DIR_CH);
    return (v / 3.3f) * 360.0f;  // 0-3.3V = 0-360 deg
}

float adc_read_precip(void) {
    float v = adc_read_voltage(ADC_PRECIP_CH);
    return v * 100.0f;  // Calibrate: 0-3.3V = 0-330 mm/h
}

float adc_read_mics(uint8_t channel) {
    float v = adc_read_voltage(channel);
    // MICS-6814: Rs/R0 = (Vc - Vout) / Vout
    // R0 = 10kohm, Vc = 3.3V
    float rs = (3.3f - v) / v * 10.0f;  // kohm
    // Sensitivity curves (log-log, from datasheet)
    // These are example slopes - calibrate with known concentrations
    if (channel == ADC_MICS_CO_CH) {
        return powf(10.0f, (log10f(rs / 10.0f) - 0.3f) / -0.4f);  // CO ppm
    } else if (channel == ADC_MICS_NO2_CH) {
        return powf(10.0f, (log10f(rs / 10.0f) + 0.2f) / -0.3f);  // NO2 ppm
    } else {
        return powf(10.0f, (log10f(rs / 10.0f) + 0.1f) / -0.35f); // NH3 ppm
    }
}

/* ============================================
 * DS18B20 DRIVER (1-Wire)
 * ============================================ */

static bool ds18b20_send_cmd(uint8_t cmd) {
    // 1-Wire reset pulse
    gpio_set_direction(DS18B20_PIN, GPIO_MODE_OUTPUT);
    gpio_set_level(DS18B20_PIN, 0);
    esp_rom_delay_us(480);
    gpio_set_level(DS18B20_PIN, 1);
    esp_rom_delay_us(60);
    
    // Read presence pulse
    gpio_set_direction(DS18B20_PIN, GPIO_MODE_INPUT);
    bool present = (gpio_get_level(DS18B20_PIN) == 0);
    esp_rom_delay_us(420);
    if (!present) return false;
    
    // Send command byte
    for (int i = 0; i < 8; i++) {
        gpio_set_direction(DS18B20_PIN, GPIO_MODE_OUTPUT);
        gpio_set_level(DS18B20_PIN, 0);
        esp_rom_delay_us(2);
        gpio_set_level(DS18B20_PIN, (cmd >> i) & 1);
        esp_rom_delay_us(60);
        gpio_set_level(DS18B20_PIN, 1);
    }
    return true;
}

static uint8_t ds18b20_read_byte(void) {
    uint8_t byte = 0;
    for (int i = 0; i < 8; i++) {
        gpio_set_direction(DS18B20_PIN, GPIO_MODE_OUTPUT);
        gpio_set_level(DS18B20_PIN, 0);
        esp_rom_delay_us(2);
        gpio_set_level(DS18B20_PIN, 1);
        gpio_set_direction(DS18B20_PIN, GPIO_MODE_INPUT);
        esp_rom_delay_us(15);
        byte |= (gpio_get_level(DS18B20_PIN) << i);
        esp_rom_delay_us(45);
    }
    return byte;
}

bool onewire_ds18b20_init(void) {
    return ds18b20_send_cmd(0xCC);  // Skip ROM
}

float onewire_ds18b20_read(void) {
    // Start temperature conversion
    ds18b20_send_cmd(0xCC);  // Skip ROM
    ds18b20_send_cmd(0x44);  // Convert T
    
    // Wait for conversion (750ms for 12-bit)
    vTaskDelay(pdMS_TO_TICKS(750));
    
    // Read scratchpad
    ds18b20_send_cmd(0xCC);  // Skip ROM
    ds18b20_send_cmd(0xBE);  // Read Scratchpad
    
    uint8_t lsb = ds18b20_read_byte();
    uint8_t msb = ds18b20_read_byte();
    
    int16_t raw = (msb << 8) | lsb;
    return raw / 16.0f;  // 12-bit resolution
}

/* ============================================
 * CALIBRATION FUNCTIONS
 * ============================================ */

// BME280 compensation coefficients (read from NVM at init)
static int32_t dig_T1, dig_T2, dig_T3;
static int32_t dig_P1, dig_P2, dig_P3, dig_P4, dig_P5;
static int32_t dig_P6, dig_P7, dig_P8, dig_P9;
static uint32_t dig_H1, dig_H3;
static int32_t dig_H2, dig_H4, dig_H5;
static int8_t dig_H6;

static bool bme280_read_calibration(void) {
    uint8_t cal[26];
    if (!i2c_read_reg(BME280_ADDR, 0x88, cal, 26)) return false;
    
    dig_T1 = (cal[1] << 8) | cal[0];
    dig_T2 = (cal[3] << 8) | cal[2];
    dig_T3 = (cal[5] << 8) | cal[4];
    
    dig_P1 = (cal[7] << 8) | cal[6];
    dig_P2 = (cal[9] << 8) | cal[8];
    dig_P3 = (cal[11] << 8) | cal[10];
    dig_P4 = (cal[13] << 8) | cal[12];
    dig_P5 = (cal[15] << 8) | cal[14];
    dig_P6 = (cal[17] << 8) | cal[16];
    dig_P7 = (cal[19] << 8) | cal[18];
    dig_P8 = (cal[21] << 8) | cal[20];
    dig_P9 = (cal[23] << 8) | cal[22];
    
    uint8_t hum_cal[7];
    if (!i2c_read_reg(BME280_ADDR, 0xA1, hum_cal, 7)) return false;
    
    dig_H1 = hum_cal[0];
    dig_H2 = (hum_cal[2] << 8) | hum_cal[1];
    dig_H3 = hum_cal[3];
    dig_H4 = (hum_cal[4] << 4) | (hum_cal[5] & 0x0F);
    dig_H5 = (hum_cal[6] << 4) | (hum_cal[5] >> 4);
    dig_H6 = (int8_t)hum_cal[6];  // Actually at 0xA7
    
    return true;
}

static float bme280_compensate_temperature(int32_t adc_T, int32_t *t_fine) {
    int32_t var1 = ((((adc_T >> 3) - (dig_T1 << 1))) * dig_T2) >> 11;
    int32_t var2 = (((((adc_T >> 4) - dig_T1) * ((adc_T >> 4) - dig_T1)) >> 12) * dig_T3) >> 14;
    *t_fine = var1 + var2;
    return (*t_fine * 5 + 128) >> 8;
}

static float bme280_compensate_pressure(int32_t adc_P, int32_t t_fine) {
    int64_t var1 = ((int64_t)t_fine) - 128000;
    int64_t var2 = var1 * var1 * (int64_t)dig_P6;
    var2 = var2 + ((var1 * (int64_t)dig_P5) << 17);
    var2 = var2 + (((int64_t)dig_P4) << 35);
    var1 = ((var1 * var1 * (int64_t)dig_P3) >> 8) + ((var1 * (int64_t)dig_P2) << 12);
    var1 = (((((int64_t)1) << 47) + var1)) * ((int64_t)dig_P1) >> 33;
    if (var1 == 0) return 0;
    int64_t p = 1048576 - adc_P;
    p = (((p << 31) - var2) * 3125) / var1;
    var1 = (((int64_t)dig_P9) * (p >> 13) * (p >> 13)) >> 25;
    var2 = (((int64_t)dig_P8) * p) >> 19;
    p = ((p + var1 + var2) >> 8) + (((int64_t)dig_P7) << 4);
    return (float)((uint32_t)p) / 256.0f;
}

static float bme280_compensate_humidity(int32_t adc_H, int32_t t_fine) {
    int32_t v_x1_u32r = (t_fine - ((int32_t)76800));
    if (v_x1_u32r == 0) return 0;
    v_x1_u32r = (((((adc_H << 14) - (((int32_t)dig_H4) << 20) - 
                   (((int32_t)dig_H5) * v_x1_u32r)) + 
                   ((int32_t)16384)) >> 15) * 
                 (((((((v_x1_u32r * ((int32_t)dig_H6)) >> 10) * 
                      (((v_x1_u32r * ((int32_t)dig_H3)) >> 11) + 
                       ((int32_t)32768))) >> 10) + 
                    ((int32_t)2097152)) * 
                   ((int32_t)dig_H2) + 8192) >> 14));
    v_x1_u32r = (v_x1_u32r - (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) * 
                                ((int32_t)dig_H1)) >> 4));
    v_x1_u32r = (v_x1_u32r < 0) ? 0 : v_x1_u32r;
    v_x1_u32r = (v_x1_u32r > 419430400) ? 419430400 : v_x1_u32r;
    return (float)(v_x1_u32r >> 12) / 1024.0f;
}

/* ============================================
 * ML FEATURE COMPUTATION
 * ============================================ */

// Derived values from calibration formulas
static float compute_heat_index(float temp_c, float humidity) {
    // Rothfusz regression (simplified)
    float t = temp_c * 9.0f / 5.0f + 32.0f;  // Convert to F
    float rh = humidity;
    float hi = -42.379f + 2.04901523f * t + 10.14333127f * rh
               - 0.22475541f * t * rh - 0.00683783f * t * t
               - 0.05481717f * rh * rh + 0.00122874f * t * t * rh
               + 0.00085282f * t * rh * rh - 0.00000199f * t * t * rh * rh;
    return (hi - 32.0f) * 5.0f / 9.0f;  // Back to C
}

static float compute_dew_point(float temp_c, float humidity) {
    // Magnus formula
    float a = 17.27f;
    float b = 237.7f;
    float alpha = (a * temp_c) / (b + temp_c) + logf(humidity / 100.0f);
    return (b * alpha) / (a - alpha);
}

static float compute_fire_risk(const sensor_cal_t *cal) {
    // Simple fire risk index
    float risk = 0.0f;
    if (cal->temperature > 30.0f) risk += 0.2f;
    if (cal->humidity < 30.0f) risk += 0.3f;
    if (cal->wind_speed > 5.0f) risk += 0.2f;
    if (cal->pm25 > 50.0f) risk += 0.3f;  // Smoke indicator
    return fminf(risk, 1.0f);
}

static float compute_flood_risk(const sensor_cal_t *cal) {
    // Simple flood risk index
    float risk = 0.0f;
    if (cal->precipitation > 10.0f) risk += 0.4f;
    if (cal->pressure < 1000.0f) risk += 0.3f;
    if (cal->humidity > 90.0f) risk += 0.2f;
    if (cal->lightning_dist < 10) risk += 0.1f;
    return fminf(risk, 1.0f);
}

static float compute_storm_risk(const sensor_cal_t *cal) {
    float risk = 0.0f;
    if (cal->lightning_dist < 10) risk += 0.5f;
    else if (cal->lightning_dist < 20) risk += 0.3f;
    if (cal->pressure < 1005.0f) risk += 0.3f;
    if (cal->wind_speed > 8.0f) risk += 0.2f;
    return fminf(risk, 1.0f);
}

/* ============================================
 * PUBLIC API
 * ============================================ */

bool sensor_pipeline_init(void) {
    ESP_LOGI(TAG, "Initializing sensor pipeline...");
    
    // Initialize I2C
    if (!i2c_init(I2C_FREQ)) {
        ESP_LOGE(TAG, "I2C init failed");
        return false;
    }
    
    // Read BME280 calibration
    if (!bme280_read_calibration()) {
        ESP_LOGE(TAG, "BME280 calibration read failed");
        return false;
    }
    
    // Initialize UART for PMS5003
    if (!uart_pms_init()) {
        ESP_LOGE(TAG, "UART init failed");
        return false;
    }
    
    // Initialize ADC
    if (!adc_init()) {
        ESP_LOGE(TAG, "ADC init failed");
        return false;
    }
    
    // Initialize DS18B20
    if (!onewire_ds18b20_init()) {
        ESP_LOGW(TAG, "DS18B20 not found (non-critical)");
    }
    
    ESP_LOGI(TAG, "Sensor pipeline initialized");
    return true;
}

void sensor_read_all(sensor_raw_t *raw) {
    // BME280
    uint8_t bme_data[8];
    if (i2c_read_reg(BME280_ADDR, 0xF7, bme_data, 8)) {
        int32_t adc_T = ((int32_t)bme_data[3] << 12) | ((int32_t)bme_data[4] << 4) | (bme_data[5] >> 4);
        int32_t t_fine;
        raw->temperature = bme280_compensate_temperature(adc_T, &t_fine);
        raw->pressure = bme280_compensate_pressure(((int32_t)bme_data[0] << 12) | ((int32_t)bme_data[1] << 4) | (bme_data[2] >> 4), t_fine);
        
        uint8_t hum_data[2];
        if (i2c_read_reg(BME280_ADDR, 0xFD, hum_data, 2)) {
            int32_t adc_H = ((int32_t)hum_data[0] << 8) | hum_data[1];
            raw->humidity = bme280_compensate_humidity(adc_H, t_fine);
        }
    }
    
    // Wind
    raw->wind_speed = adc_read_wind_speed();
    raw->wind_dir = (uint16_t)adc_read_wind_dir();
    
    // Precipitation
    raw->precipitation = adc_read_precip();
    
    // PMS5003
    uart_pms_read(&raw->pm25, &raw->pm10);
    
    // Gas sensors
    raw->co = adc_read_mics(ADC_MICS_CO_CH);
    raw->no2 = adc_read_mics(ADC_MICS_NO2_CH);
    raw->nh3 = adc_read_mics(ADC_MICS_NH3_CH);
    
    // System
    raw->enclosure_temp = onewire_ds18b20_read();
    raw->battery_voltage = adc_read_battery();
}

void sensor_calibrate(const sensor_raw_t *raw, sensor_cal_t *cal) {
    cal->temperature = raw->temperature;
    cal->humidity = raw->humidity;
    cal->pressure = raw->pressure;
    cal->wind_speed = raw->wind_speed;
    cal->wind_dir_x = cosf(raw->wind_dir * M_PI / 180.0f);
    cal->wind_dir_y = sinf(raw->wind_dir * M_PI / 180.0f);
    cal->precipitation = raw->precipitation;
    cal->uv_index = raw->uv_index;
    cal->pm25 = raw->pm25;
    cal->pm10 = raw->pm10;
    cal->co2 = raw->co2;
    cal->voc_index = raw->voc_raw;
    cal->nox_index = raw->nox_raw;
    cal->co = raw->co;
    cal->no2 = raw->no2;
    cal->nh3 = raw->nh3;
    cal->lightning_dist = raw->lightning_dist;
    cal->lightning_count = raw->lightning_count;
    cal->enclosure_temp = raw->enclosure_temp;
    cal->battery_voltage = raw->battery_voltage;
}

void sensor_compute_features(const sensor_cal_t *cal, ml_feature_t *feat) {
    feat->temp_current = cal->temperature;
    feat->humidity_current = cal->humidity;
    feat->pressure_current = cal->pressure;
    feat->wind_speed_current = cal->wind_speed;
    feat->pm25_current = cal->pm25;
    feat->co2_current = cal->co2;
    feat->lightning_dist_current = cal->lightning_dist;
    
    // Derived features
    feat->temp_humidity_ratio = cal->temperature / fmaxf(cal->humidity, 1.0f);
    feat->pressure_trend = 0.0f;  // Computed over time window
    feat->heat_index = compute_heat_index(cal->temperature, cal->humidity);
    feat->dew_point = compute_dew_point(cal->temperature, cal->humidity);
    feat->fire_risk_index = compute_fire_risk(cal);
    feat->flood_risk_index = compute_flood_risk(cal);
    feat->lightning_threat = (cal->lightning_dist < 40) ? (40.0f - cal->lightning_dist) / 40.0f : 0.0f;
    
    feat->timestamp_s = (uint32_t)(esp_timer_get_time() / 1000000);
}

ml_feature_t sensor_get_features(void) {
    sensor_raw_t raw;
    sensor_cal_t cal;
    ml_feature_t feat;
    
    sensor_read_all(&raw);
    sensor_calibrate(&raw, &cal);
    sensor_compute_features(&cal, &feat);
    
    return feat;
}
