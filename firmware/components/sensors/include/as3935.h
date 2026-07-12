#ifndef AS3935_H
#define AS3935_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/i2c.h"

#ifdef __cplusplus
extern "C" {
#endif

#define AS3935_ADDR                    0x03

/* Indoor/outdoor settings */
#define AS3935_SETTING_INDOOR          0x12
#define AS3935_SETTING_OUTDOOR         0x1E

/* Registers */
#define AS3935_REG_AFE_GAIN            0x00
#define AS3935_REG_THRESHOLD           0x01
#define AS3935_REG_INT_MASK            0x03
#define AS3935_REG_S_LIG_L            0x04
#define AS3935_REG_S_LIG_M            0x05
#define AS3935_REG_S_LIG_MM           0x06
#define AS3935_REG_DISTANCE            0x07
#define AS3935_REG_DISP_ENERGY_L       0x08
#define AS3935_REG_DISP_ENERGY_M       0x09
#define AS3935_REG_DISP_ENERGY_H       0x0A
#define AS3935_REG_NF_LEVEL            0x0B
#define AS3935_REG_NOISE_FLOOR         0x0C
#define AS3935_REG_CALIB               0x3D

/* Interrupt source values */
#define AS3935_INT_NOISE               0x01
#define AS3935_INT_DISTURBER           0x04
#define AS3935_INT_LIGHTNING           0x08

/* Default calibration */
#define AS3935_DEFAULT_CAPACITANCE     0x00
#define AS3935_NOISE_FLOOR_DEFAULT     0x02

typedef struct {
    i2c_port_t i2c_port;
    uint8_t    addr;
    bool       outdoor;
    uint8_t    noise_floor;
} as3935_handle_t;

typedef struct {
    uint8_t  distance_km;
    uint8_t  strike_count;
    uint32_t energy;            /* Relative energy of last strike */
    uint8_t  interrupt_source;
} as3935_data_t;

bool as3935_init(i2c_port_t port, uint8_t addr, bool outdoor, as3935_handle_t **handle);
bool as3935_read_event(as3935_handle_t *handle, as3935_data_t *data);
bool as3935_clear_stats(as3935_handle_t *handle);
bool as3935_set_noise_floor(as3935_handle_t *handle, uint8_t level);
bool as3935_set_watchdog_threshold(as3935_handle_t *handle, uint8_t threshold);
bool as3935_power_down(as3935_handle_t *handle);
bool as3935_power_up(as3935_handle_t *handle);
bool as3935_calibrate_rco(as3935_handle_t *handle);

#ifdef __cplusplus
}
#endif

#endif
