#ifndef LTR390_H
#define LTR390_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/i2c.h"

#ifdef __cplusplus
extern "C" {
#endif

#define LTR390_ADDR                    0x53
#define LTR390_CHIP_ID                 0x06

#define LTR390_REG_MAIN_CTRL           0x00
#define LTR390_REG_ALS_UVS_MEAS        0x04
#define LTR390_REG_ALS_DATA_LSB        0x0D
#define LTR390_REG_ALS_DATA_MSB        0x0E
#define LTR390_REG_UVS_DATA_LSB        0x10
#define LTR390_REG_UVS_DATA_MSB        0x11
#define LTR390_REG_INT_CFG             0x19
#define LTR390_REG_PART_ID             0x06

#define LTR390_CTRL_ALS_EN             (1 << 1)
#define LTR390_CTRL_UVS_EN             (1 << 2)
#define LTR390_CTRL_SW_RESET           (1 << 4)

#define LTR390_MEAS_ALS                (0 << 2)
#define LTR390_MEAS_UVS                (1 << 2)
#define LTR390_MEAS_RES_20BIT          (0 << 4)
#define LTR390_MEAS_RES_19BIT          (1 << 4)
#define LTR390_MEAS_RES_18BIT          (2 << 4)
#define LTR390_MEAS_RES_17BIT          (3 << 4)
#define LTR390_MEAS_RES_16BIT          (4 << 4)
#define LTR390_MEAS_RES_13BIT          (5 << 4)

#define LTR390_MEAS_GAIN_1             (0 << 0)
#define LTR390_MEAS_GAIN_3             (1 << 0)
#define LTR390_MEAS_GAIN_6             (2 << 0)
#define LTR390_MEAS_GAIN_9             (3 << 0)
#define LTR390_MEAS_GAIN_18            (4 << 0)

typedef struct {
    i2c_port_t i2c_port;
    uint8_t    addr;
    uint8_t    gain;
    uint8_t    resolution;
} ltr390_handle_t;

bool ltr390_init(i2c_port_t port, uint8_t addr, ltr390_handle_t **handle);
bool ltr390_read_uvs(ltr390_handle_t *handle, float *uv_index);
bool ltr390_read_als(ltr390_handle_t *handle, float *lux);
void ltr390_set_gain(ltr390_handle_t *handle, uint8_t gain);
void ltr390_set_resolution(ltr390_handle_t *handle, uint8_t resolution);

#ifdef __cplusplus
}
#endif

#endif
