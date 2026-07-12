/**
 * calibration_log.h - Calibration Data Logging for NVS
 *
 * Stores sensor calibration records in ESP32 NVS with CSV export/import.
 * Each record captures the calibration parameters, reference conditions,
 * and metadata for traceability and re-verification.
 */

#ifndef CALIBRATION_LOG_H
#define CALIBRATION_LOG_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================
 * CONFIGURATION
 * ============================================ */

#define CAL_NVS_NAMESPACE        "calib"
#define CAL_NVS_RECORD_PREFIX    "rec_"
#define CAL_NVS_INDEX_KEY        "next_id"
#define CAL_NVS_MAX_RECORDS      64
#define CAL_LOG_MAGIC            0x43414C01  // "CAL" + version

/* ============================================
 * CALIBRATION TYPES
 * ============================================ */

typedef enum {
    CAL_TYPE_OFFSET     = 0,  // y = x + a
    CAL_TYPE_GAIN       = 1,  // y = a * x
    CAL_TYPE_LINEAR     = 2,  // y = a * x + b
    CAL_TYPE_POLY2      = 3,  // y = a*x^2 + b*x + c
    CAL_TYPE_LOOKUP     = 4,  // Piecewise linear table
    CAL_TYPE_CUSTOM     = 5,  // Sensor-specific
} cal_type_t;

typedef enum {
    CAL_STATUS_PENDING  = 0,  // Written, not yet verified
    CAL_STATUS_VERIFIED = 1,  // Verified against reference
    CAL_STATUS_REJECTED = 2,  // Failed verification
    CAL_STATUS_EXPIRED  = 3,  // Past valid_until_ms
} cal_status_t;

/* ============================================
 * CALIBRATION RECORD
 * ============================================ */

typedef struct __attribute__((packed)) {
    uint32_t magic;               // CAL_LOG_MAGIC
    uint32_t version;             // Format version (1)
    uint32_t timestamp_ms;        // When recorded (boot ms)
    uint32_t node_id;             // Originating node ID
    uint16_t record_id;           // Unique within node
    uint16_t sequence;            // Sequence for this sensor
    char     sensor_name[16];     // "bme280_temp", "mics6814_co", etc.
    uint8_t  type;                // cal_type_t
    uint8_t  status;              // cal_status_t

    // Model parameters (meaning depends on type)
    float    param_a;             // Offset / slope / poly_a
    float    param_b;             // Gain / intercept / poly_b
    float    param_c;             // Poly_c / unused

    // Reference conditions
    float    ref_value;           // Reference standard value
    float    measured_value;      // Sensor reading at ref
    float    temperature_c;       // Ambient temp during cal
    float    humidity_pct;        // Ambient humidity during cal

    // Quality metrics
    float    rms_error;           // RMS error over samples
    float    max_error;           // Max absolute error
    uint8_t  num_samples;         // Samples used

    // Validity window
    uint32_t valid_from_ms;       // Valid after this boot time
    uint32_t valid_until_ms;      // Expires at this boot time (0 = never)

    // Metadata
    char     unit[8];             // "C", "hPa", "ppm", "m/s"
    char     notes[64];           // Free text: "NIST traceable", "factory", etc.
    uint32_t operator_id;         // Personnel/badge ID (hashed)

    // Padding for alignment
    uint8_t  _reserved[8];
} calibration_record_t;

/* ============================================
 * API
 * ============================================ */

/**
 * @brief Initialize calibration log subsystem.
 * @return ESP_OK on success.
 */
esp_err_t cal_log_init(void);

/**
 * @brief Write a calibration record (auto-assigns ID if 0).
 * @param rec  Record to write (record_id = 0 for auto).
 * @return ESP_OK on success.
 */
esp_err_t cal_log_write(const calibration_record_t *rec);

/**
 * @brief Read a calibration record by ID.
 * @param record_id  ID to read (0 = latest).
 * @param rec        Output record.
 * @return ESP_OK, or ESP_ERR_NOT_FOUND.
 */
esp_err_t cal_log_read(uint16_t record_id, calibration_record_t *rec);

/**
 * @brief Read all valid calibration records.
 * @param out_recs    Buffer (max CAL_NVS_MAX_RECORDS).
 * @param out_count   Number of records returned.
 * @return ESP_OK.
 */
esp_err_t cal_log_read_all(calibration_record_t *out_recs, uint16_t *out_count);

/**
 * @brief Delete a calibration record.
 * @param record_id  ID to delete.
 * @return ESP_OK on success.
 */
esp_err_t cal_log_delete(uint16_t record_id);

/**
 * @brief Export all records as CSV to buffer.
 * @param csv_buf   Output buffer.
 * @param buf_size  Buffer size in bytes.
 * @param out_len   Bytes written.
 * @return ESP_OK, or ESP_ERR_INVALID_SIZE if buffer too small.
 */
esp_err_t cal_log_export_csv(char *csv_buf, size_t buf_size, size_t *out_len);

/**
 * @brief Import records from CSV string.
 * @param csv_data  CSV string (with header).
 * @param len       Length of csv_data.
 * @param imported  Number of records successfully imported.
 * @return ESP_OK.
 */
esp_err_t cal_log_import_csv(const char *csv_data, size_t len, uint16_t *imported);

/* ============================================
 * HELPER MACROS
 * ============================================ */

#define CAL_RECORD_INIT(sensor, cal_type) { \
    .magic = CAL_LOG_MAGIC, \
    .version = 1, \
    .sensor_name = {0}, \
    .type = cal_type, \
    .status = CAL_STATUS_PENDING, \
    .param_a = 0.0f, \
    .param_b = 1.0f, \
    .param_c = 0.0f, \
    .unit = {0}, \
    .notes = {0}, \
    .operator_id = 0, \
}

#ifdef __cplusplus
}
#endif

#endif // CALIBRATION_LOG_H