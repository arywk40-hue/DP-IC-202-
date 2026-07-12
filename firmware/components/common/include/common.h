/**
 * common.h - Shared types, error codes, and utilities
 *
 * All components in this project use these base types and error codes
 * to ensure consistent error propagation across sensor, ML, mesh, and
 * radio layers.
 */

#ifndef COMMON_H
#define COMMON_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Project-wide error codes.
 * Functions return esp_err_t with these custom error values
 * so callers can handle failures uniformly.
 */
#define ERR_SENSOR_BASE       0x0100
#define ERR_ML_BASE           0x0200
#define ERR_MESH_BASE         0x0300
#define ERR_RADIO_BASE        0x0400
#define ERR_PACKET_BASE       0x0500

/*
 * Maximum sizes for fixed buffers.
 * Chosen to fit within ESP32-S3 RAM while avoiding malloc.
 * All buffers are stack-allocated or statically allocated.
 */
#define MAX_SENSOR_NAME_LEN   24
#define MAX_SENSOR_VALUE_LEN  16
#define MAX_FEATURES          16
#define MAX_PACKET_PAYLOAD    240
#define MAX_NEIGHBORS         8
#define MAX_MESH_HOPS         8
#define NODE_ID_BYTES         4

/*
 * Sensor reading structure — the unified output of the sensor subsystem.
 * Every sensor driver fills this structure through the sensor_read() API.
 * Derived features (heat index, dew point, etc.) are computed in the
 * feature-engineering layer before being passed to ML inference.
 */
typedef struct {
    float temperature;       /* °C                    */
    float humidity;          /* %RH                   */
    float pressure;          /* hPa                   */
    float altitude;          /* m                     */
    float wind_speed;        /* m/s                   */
    float wind_direction;    /* degrees               */
    float precipitation;     /* mm/h                  */
    float uv_index;          /* UV index              */
    float pm1_0;             /* μg/m³                 */
    float pm2_5;             /* μg/m³                 */
    float pm10;              /* μg/m³                 */
    float co2;               /* ppm                   */
    float voc_index;         /* VOC index             */
    float nox_index;         /* NOx index             */
    float co_ppm;            /* ppm CO                */
    float no2_ppm;           /* ppm NO2               */
    float nh3_ppm;           /* ppm NH3               */
    float lightning_dist;    /* km                    */
    uint8_t lightning_count; /* strike count          */
    uint32_t timestamp;      /* Unix epoch (if NTP) or boot ms */
    uint8_t sensor_mask;     /* bitmask of valid sensors */
} sensor_reading_t;

/*
 * Bitmask values for sensor_reading_t.sensor_mask.
 * Each bit indicates whether the corresponding field is populated.
 */
#define SENSOR_MASK_TEMP         (1 << 0)
#define SENSOR_MASK_HUMIDITY     (1 << 1)
#define SENSOR_MASK_PRESSURE     (1 << 2)
#define SENSOR_MASK_WIND_SPEED   (1 << 3)
#define SENSOR_MASK_WIND_DIR     (1 << 4)
#define SENSOR_MASK_RAIN         (1 << 5)
#define SENSOR_MASK_UV           (1 << 6)
#define SENSOR_MASK_PM           (1 << 7)
#define SENSOR_MASK_CO2          (1 << 8)
#define SENSOR_MASK_VOC          (1 << 9)
#define SENSOR_MASK_NOX          (1 << 10)
#define SENSOR_MASK_GAS          (1 << 11)
#define SENSOR_MASK_LIGHTNING    (1 << 12)

/*
 * Feature vector — the fixed-size input to the ML inference engine.
 * Normalized before being passed to ml_predict().
 * Size is fixed at compile time to avoid dynamic allocation.
 */
typedef struct {
    float values[MAX_FEATURES];
    uint8_t count;
    uint32_t timestamp_ms;
} feature_vector_t;

#ifdef __cplusplus
}
#endif

#endif /* COMMON_H */
