#ifndef SGP41_H
#define SGP41_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/i2c.h"

#ifdef __cplusplus
extern "C" {
#endif

#define SGP41_ADDR                     0x59

#define SGP41_CMD_MEASURE_RAW          0x2602
#define SGP41_CMD_EXECUTE_SELF_TEST    0x280E
#define SGP41_CMD_TURN_HEATER_OFF      0x3615
#define SGP41_CMD_GET_SERIAL_NUM       0x3682
#define SGP41_CMD_AUTO_CLEAN           0x260E
#define SGP41_CMD_CONDITIONING         0x2612

#define SGP41_MEAS_WAIT_MS             50
#define SGP41_CONDITIONING_WAIT_MS     1000

typedef struct {
    i2c_port_t i2c_port;
    uint8_t    addr;
    uint16_t   serial_number[3];
    bool       heater_on;
} sgp41_handle_t;

bool sgp41_init(i2c_port_t port, uint8_t addr, sgp41_handle_t **handle);
bool sgp41_read_raw(sgp41_handle_t *handle, uint16_t *voc_raw, uint16_t *nox_raw);
bool sgp41_conditioning(sgp41_handle_t *handle);
bool sgp41_self_test(sgp41_handle_t *handle);
void sgp41_heater_off(sgp41_handle_t *handle);

#ifdef __cplusplus
}
#endif

#endif
