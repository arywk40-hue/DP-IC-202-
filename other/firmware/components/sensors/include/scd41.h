#ifndef SCD41_H
#define SCD41_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/i2c.h"

#ifdef __cplusplus
extern "C" {
#endif

#define SCD41_ADDR                     0x62
#define SCD41_CMD_START_PERIODIC       0x21B1
#define SCD41_CMD_READ_MEASUREMENT     0xEC05
#define SCD41_CMD_STOP_PERIODIC        0x3F86
#define SCD41_CMD_SET_TEMP_OFFSET      0x241D
#define SCD41_CMD_GET_SERIAL_NUM       0x3682
#define SCD41_CMD_FORCE_RECALIBRATE    0x362F
#define SCD41_CMD_SELF_TEST            0x3639
#define SCD41_CMD_WAKE_UP              0x36F6
#define SCD41_CMD_POWER_DOWN           0x36E0

#define SCD41_MEAS_WAIT_MS             5000
#define SCD41_WAKE_WAIT_MS             30
#define SCD41_SELF_TEST_WAIT_MS        10000

typedef struct {
    i2c_port_t i2c_port;
    uint8_t    addr;
    uint32_t   serial_number;
    bool       periodic_mode;
} scd41_handle_t;

bool scd41_init(i2c_port_t port, uint8_t addr, scd41_handle_t **handle);
bool scd41_read(scd41_handle_t *handle, float *co2_ppm, float *temperature, float *humidity);
bool scd41_start_periodic(scd41_handle_t *handle);
bool scd41_stop_periodic(scd41_handle_t *handle);
bool scd41_sleep(scd41_handle_t *handle);
bool scd41_wake(scd41_handle_t *handle);
bool scd41_set_temp_offset(scd41_handle_t *handle, float offset_c);
bool scd41_self_test(scd41_handle_t *handle);

#ifdef __cplusplus
}
#endif

#endif
