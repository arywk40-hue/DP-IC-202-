/**
 * sensor_pipeline.h - Low-level sensor data acquisition pipeline
 * 
 * ESP32-S3 Edge AI Weather Station
 * Reads 12 sensors via I2C, UART, SPI, Analog, 1-Wire
 * Outputs fused feature vector for ML inference
 */

#ifndef SENSOR_PIPELINE_H
#define SENSOR_PIPELINE_H

#include <stdint.h>
#include <stdbool.h>

/* ============================================
 * SENSOR DATA STRUCTURES
 * ============================================ */

// Raw sensor readings (before calibration)
typedef struct {
    float temperature;      // BME280 (C)
    float humidity;         // BME280 (%RH)
    float pressure;         // BME280 (hPa)
    float wind_speed;       // SparkFun (m/s)
    uint16_t wind_dir;      // SparkFun (degrees 0-359)
    float precipitation;    // SEN0575 (mm/h)
    float uv_index;         // LTR390 (UV index)
    uint16_t pm25;          // PMS5003 (ug/m3)
    uint16_t pm10;          // PMS5003 (ug/m3)
    float co2;              // SCD41 (ppm)
    uint16_t voc_raw;       // SGP41 (index)
    uint16_t nox_raw;       // SGP41 (index)
    float co;               // MICS-6814 (ppm)
    float no2;              // MICS-6814 (ppm)
    float nh3;              // MICS-6814 (ppm)
    uint8_t lightning_dist; // AS3935 (km, 0=no storm)
    uint8_t lightning_count;// AS3935 (events/15min)
    float enclosure_temp;   // DS18B20 (C)
    float battery_voltage;  // ADC divider (V)
} sensor_raw_t;

// Calibrated sensor readings
typedef struct {
    float temperature;
    float humidity;
    float pressure;
    float wind_speed;
    float wind_dir_x;       // cos(direction) for ML
    float wind_dir_y;       // sin(direction) for ML
    float precipitation;
    float uv_index;
    float pm25;
    float pm10;
    float co2;
    float voc_index;
    float nox_index;
    float co;
    float no2;
    float nh3;
    float lightning_dist;
    float lightning_count;
    float enclosure_temp;
    float battery_voltage;
} sensor_cal_t;

// ML feature vector (input to XGBoost)
typedef struct {
    // Temporal features (current)
    float temp_current;
    float humidity_current;
    float pressure_current;
    float wind_speed_current;
    float pm25_current;
    float co2_current;
    float lightning_dist_current;
    
    // Derived features
    float temp_humidity_ratio;  // temp / humidity
    float pressure_trend;       // delta P / delta t
    float heat_index;           // calculated
    float dew_point;            // calculated
    float fire_risk_index;      // composite
    float flood_risk_index;     // composite
    
    // Lightning proximity score
    float lightning_threat;     // 0-1 score
    
    // Timestamp
    uint32_t timestamp_s;       // epoch seconds
} ml_feature_t;

// Hazard alert output
typedef struct {
    uint8_t wildfire_risk;      // 0-100%
    uint8_t flood_risk;         // 0-100%
    uint8_t storm_risk;         // 0-100%
    uint8_t air_quality_risk;   // 0-100%
    uint8_t overall_threat;     // 0-100%
    uint16_t alert_code;        // bitfield
} hazard_alert_t;

// Alert code bitfield
#define ALERT_NONE          0x0000
#define ALERT_WILDFIRE      0x0001
#define ALERT_FLOOD         0x0002
#define ALERT_STORM         0x0004
#define ALERT_POOR_AIR      0x0008
#define ALERT_LOW_BATTERY   0x0010
#define ALERT_SENSOR_FAULT  0x0020
#define ALERT_HIGH_WIND     0x0040
#define ALERT_TEMP_EXTREME  0x0080

/* ============================================
 * SENSOR INTERFACE FUNCTIONS
 * ============================================ */

/**
 * Initialize all sensor buses and peripherals
 * @return true if all critical sensors initialized
 */
bool sensor_pipeline_init(void);

/**
 * Read all sensors and populate raw struct
 * Blocking call, ~200ms total
 */
void sensor_read_all(sensor_raw_t *raw);

/**
 * Apply calibration offsets to raw readings
 */
void sensor_calibrate(const sensor_raw_t *raw, sensor_cal_t *cal);

/**
 * Compute derived features for ML
 */
void sensor_compute_features(const sensor_cal_t *cal, ml_feature_t *feat);

/**
 * Get fused feature vector for ML inference
 * Reads sensors, calibrates, computes features
 * @return populated feature vector
 */
ml_feature_t sensor_get_features(void);

/* ============================================
 * LOW-LEVEL HARDWARE ABSTRACTION
 * ============================================ */

// I2C bus
bool i2c_init(uint32_t freq_hz);
bool i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *data, uint8_t len);
bool i2c_write_reg(uint8_t addr, uint8_t reg, uint8_t data);

// UART (PMS5003)
bool uart_pms_init(void);
bool uart_pms_read(uint16_t *pm25, uint16_t *pm10);

// SPI (LoRa SX1276)
bool spi_lora_init(void);
bool spi_lora_send(uint8_t *data, uint8_t len);
bool spi_lora_receive(uint8_t *data, uint8_t *len);

// ADC (battery, analog sensors)
float adc_read_voltage(uint8_t channel);
float adc_read_battery(void);

// 1-Wire (DS18B20)
bool onewire_ds18b20_init(void);
float onewire_ds18b20_read(void);

#endif // SENSOR_PIPELINE_H
