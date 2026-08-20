/**
 * sx1276.h - SX1276 LoRa Transceiver Driver
 * 
 * Real hardware driver for Semtech SX1276/RFM95W
 * Operating frequency: 865 MHz (India ISM band)
 */

#ifndef SX1276_H
#define SX1276_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/spi_master.h"
#include "driver/gpio.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================
 * SX1276 REGISTERS (Real Hardware)
 * ============================================ */

// Common registers
#define SX1276_REG_FIFO              0x00
#define SX1276_REG_OP_MODE           0x01
#define SX1276_REG_FRF_MSB           0x06
#define SX1276_REG_FRF_MID           0x07
#define SX1276_REG_FRF_LSB           0x08
#define SX1276_REG_PA_CONFIG         0x09
#define SX1276_REG_PA_RAMP           0x0A
#define SX1276_REG_OCP               0x0B
#define SX1276_REG_LNA               0x0C

// LoRa registers
#define SX1276_REG_FIFO_ADDR_PTR     0x0D
#define SX1276_REG_FIFO_TX_BASE_ADDR 0x0E
#define SX1276_REG_FIFO_RX_BASE_ADDR 0x0F
#define SX1276_REG_FIFO_RX_CUR_ADDR  0x10
#define SX1276_REG_IRQ_FLAGS_MASK    0x11
#define SX1276_REG_IRQ_FLAGS         0x12
#define SX1276_REG_RX_NB_BYTES       0x13
#define SX1276_REG_RX_HEADER_MSB     0x14
#define SX1276_REG_RX_HEADER_LSB     0x15
#define SX1276_REG_RX_PACKET_CNT     0x16
#define SX1276_REG_MODEM_STATUS      0x17
#define SX1276_REG_PKT_SNR_VALUE     0x19
#define SX1276_REG_PKT_RSSI_VALUE    0x1A
#define SX1276_REG_RSSI_VALUE        0x1B
#define SX1276_REG_HOP_CHANNEL       0x1C
#define SX1276_REG_MODEM_CONFIG1     0x1D
#define SX1276_REG_MODEM_CONFIG2     0x1E
#define SX1276_REG_SYMB_TIMEOUT_LSB  0x1F
#define SX1276_REG_PREAMBLE_MSB      0x20
#define SX1276_REG_PREAMBLE_LSB      0x21
#define SX1276_REG_PAYLOAD_LENGTH    0x22
#define SX1276_REG_MAX_PAYLOAD_LENGTH 0x23
#define SX1276_REG_HOP_PERIOD        0x24
#define SX1276_REG_FIFO_RX_BYTE_ADDR 0x25
#define SX1276_REG_MODEM_CONFIG3     0x26
#define SX1276_REG_SYNC_CONFIG       0x27
#define SX1276_REG_SYNC_VALUE1       0x28
#define SX1276_REG_SYNC_VALUE2       0x29
#define SX1276_REG_SYNC_VALUE3       0x2A
#define SX1276_REG_SYNC_VALUE4       0x2B
#define SX1276_REG_SYNC_VALUE5       0x2C
#define SX1276_REG_SYNC_VALUE6       0x2D
#define SX1276_REG_SYNC_VALUE7       0x2E
#define SX1276_REG_SYNC_VALUE8       0x2F
#define SX1276_REG_INVERTIQ          0x33
#define SX1276_REG_INVERTIQ2         0x3B
#define SX1276_REG_DIO_MAPPING1      0x40
#define SX1276_REG_DIO_MAPPING2      0x41
#define SX1276_REG_VERSION           0x42
#define SX1276_REG_PA_DAC            0x4D

// Operating modes
#define SX1276_MODE_SLEEP            0x00
#define SX1276_MODE_STANDBY          0x01
#define SX1276_MODE_FSTX             0x02
#define SX1276_MODE_TX               0x03
#define SX1276_MODE_FSRX             0x04
#define SX1276_MODE_RX_CONTINUOUS    0x05
#define SX1276_MODE_RX_SINGLE        0x06
#define SX1276_MODE_CAD              0x07

// LoRa mode bit
#define SX1276_LONG_RANGE_MODE       0x80

// IRQ flags
#define SX1276_IRQ_RX_DONE           0x40
#define SX1276_IRQ_RX_TIMEOUT        0x80
#define SX1276_IRQ_TX_DONE           0x08
#define SX1276_IRQ_CAD_DONE          0x04
#define SX1276_IRQ_FHSS_CHANGE       0x02
#define SX1276_IRQ_CAD_DETECTED      0x01

// PA Config
#define SX1276_PA_BOOST              0x80
#define SX1276_PA_OUTPUT_RFO         0x00

// DIO mapping for LoRa
#define SX1276_DIO0_RX_DONE          0x00
#define SX1276_DIO0_TX_DONE          0x40
#define SX1276_DIO1_RX_TIMEOUT       0x00

/* ============================================
 * CONFIGURATION STRUCTURES
 * ============================================ */

typedef struct {
    spi_host_device_t spi_host;     // SPI2_HOST or SPI3_HOST
    gpio_num_t pin_mosi;
    gpio_num_t pin_miso;
    gpio_num_t pin_sclk;
    gpio_num_t pin_cs;              // NSS chip select
    gpio_num_t pin_rst;             // Reset
    gpio_num_t pin_dio0;            // DIO0 (IRQ)
    gpio_num_t pin_dio1;            // DIO1
    uint32_t frequency;             // Hz (e.g., 865000000 for India)
    int8_t tx_power;                // dBm (2-20)
    uint8_t spreading_factor;       // 6-12
    uint8_t bandwidth;              // 0=7.8kHz, 1=10.4kHz, ..., 9=500kHz
    uint8_t coding_rate;            // 1-4 (4/5, 4/6, 4/7, 4/8)
    uint8_t sync_word;              // Network sync word
    uint16_t preamble_length;       // Symbol count
} sx1276_config_t;

typedef struct {
    spi_device_handle_t spi;
    gpio_num_t pin_cs;
    gpio_num_t pin_rst;
    gpio_num_t pin_dio0;
    gpio_num_t pin_dio1;
    uint32_t frequency;
    int8_t tx_power;
    uint8_t spreading_factor;
    bool is_transmitting;
    bool is_receiving;
} sx1276_handle_t;

/* ============================================
 * API FUNCTIONS
 * ============================================ */

/**
 * @brief Initialize SX1276 LoRa transceiver
 * @param config Configuration structure
 * @param handle Output handle
 * @return true on success
 */
bool sx1276_init(const sx1276_config_t *config, sx1276_handle_t **handle);

/**
 * @brief Configure LoRa parameters
 * @param handle Device handle
 * @param freq Frequency in Hz
 * @param sf Spreading factor (6-12)
 * @param bw Bandwidth setting
 * @param cr Coding rate (1-4)
 * @return true on success
 */
bool sx1276_configure(sx1276_handle_t *handle, uint32_t freq, uint8_t sf, 
                      uint8_t bw, uint8_t cr);

/**
 * @brief Set TX power
 * @param handle Device handle
 * @param power dBm (2-20)
 */
void sx1276_set_tx_power(sx1276_handle_t *handle, int8_t power);

/**
 * @brief Transmit data packet
 * @param handle Device handle
 * @param data Data buffer
 * @param len Data length (max 255)
 * @param timeout_ms Timeout in milliseconds
 * @return true on success, false on timeout
 */
bool sx1276_transmit(sx1276_handle_t *handle, const uint8_t *data, 
                     uint8_t len, uint32_t timeout_ms);

/**
 * @brief Start receiving packets
 * @param handle Device handle
 */
void sx1276_start_receive(sx1276_handle_t *handle);

/**
 * @brief Check if packet received
 * @param handle Device handle
 * @return true if packet available
 */
bool sx1276_received(sx1276_handle_t *handle);

/**
 * @brief Read received packet
 * @param handle Device handle
 * @param buffer Output buffer
 * @param max_len Maximum buffer size
 * @param rssi Output RSSI value
 * @param snr Output SNR value
 * @return Number of bytes received, 0 if no packet
 */
uint8_t sx1276_read(sx1276_handle_t *handle, uint8_t *buffer, 
                    uint8_t max_len, int8_t *rssi, float *snr);

/**
 * @brief Put SX1276 to sleep
 * @param handle Device handle
 */
void sx1276_sleep(sx1276_handle_t *handle);

/**
 * @brief Put SX1276 to standby
 * @param handle Device handle
 */
void sx1276_standby(sx1276_handle_t *handle);

/**
 * @brief Perform channel activity detection
 * @param handle Device handle
 * @return true if channel is free
 */
bool sx1276_channel_activity_detect(sx1276_handle_t *handle);

/**
 * @brief Perform CSMA/CA with exponential backoff before transmission
 * @param handle Device handle
 * @param max_retries Maximum number of backoff retries (0 = no retry)
 * @param base_backoff_ms Base backoff time in milliseconds
 * @return true if channel became free and ready to transmit, false if max retries exceeded
 */
bool sx1276_csma_ca(sx1276_handle_t *handle, uint8_t max_retries, uint16_t base_backoff_ms);

/**
 * @brief Get current RSSI
 * @param handle Device handle
 * @return RSSI in dBm
 */
int16_t sx1276_get_rssi(sx1276_handle_t *handle);

/**
 * @brief Set implicit/explicit header mode
 * @param handle Device handle
 * @param implicit true for implicit header, false for explicit
 */
void sx1276_set_implicit_header(sx1276_handle_t *handle, bool implicit);

/**
 * @brief Set CRC enable/disable
 * @param handle Device handle
 * @param enable true to enable CRC, false to disable
 */
void sx1276_set_crc(sx1276_handle_t *handle, bool enable);

/**
 * @brief Set IQ inversion (for relay/hop)
 * @param handle Device handle
 * @param invert true to invert IQ
 */
void sx1276_set_iq_inversion(sx1276_handle_t *handle, bool invert);

/**
 * @brief Set LoRa sync word
 * @param handle Device handle
 * @param sync_word Sync word value
 */
void sx1276_set_sync_word(sx1276_handle_t *handle, uint8_t sync_word);

/**
 * @brief Set preamble length
 * @param handle Device handle
 * @param length Preamble length in symbols
 */
void sx1276_set_preamble_length(sx1276_handle_t *handle, uint16_t length);

/**
 * @brief Set coding rate
 * @param handle Device handle
 * @param cr Coding rate (1-4 for 4/5, 4/6, 4/7, 4/8)
 */
void sx1276_set_coding_rate(sx1276_handle_t *handle, uint8_t cr);

/**
 * @brief Mode switch helper: TX -> RX continuous
 * @param handle Device handle
 * @return true on success
 */
bool sx1276_switch_tx_to_rx(sx1276_handle_t *handle);

/**
 * @brief Mode switch helper: RX -> TX
 * @param handle Device handle
 * @return true on success
 */
bool sx1276_switch_rx_to_tx(sx1276_handle_t *handle);

/**
 * @brief Mode switch helper: Sleep -> Standby
 * @param handle Device handle
 * @return true on success
 */
bool sx1276_wake_from_sleep(sx1276_handle_t *handle);

/**
 * @brief Set LoRa bandwidth
 * @param handle Device handle
 * @param bw Bandwidth setting (0-9)
 */
void sx1276_set_bandwidth(sx1276_handle_t *handle, uint8_t bw);

/**
 * @brief Set spreading factor
 * @param handle Device handle
 * @param sf Spreading factor (6-12)
 */
void sx1276_set_spreading_factor(sx1276_handle_t *handle, uint8_t sf);

/**
 * @brief Get current SNR
 * @param handle Device handle
 * @return SNR in dB
 */
float sx1276_get_snr(sx1276_handle_t *handle);

/**
 * @brief Configure all LoRa parameters at once
 * @param handle Device handle
 * @param freq Frequency in Hz
 * @param sf Spreading factor (6-12)
 * @param bw Bandwidth (0-9)
 * @param cr Coding rate (1-4)
 * @param sync_word Network sync word
 * @param preamble Preamble length
 * @param tx_power TX power in dBm
 * @return true on success
 */
bool sx1276_set_all_params(sx1276_handle_t *handle, uint32_t freq, uint8_t sf, 
                           uint8_t bw, uint8_t cr, uint8_t sync_word,
                           uint16_t preamble, int8_t tx_power);

/**
 * @brief Get current operating mode
 * @param handle Device handle
 * @return Current mode register value
 */
uint8_t sx1276_get_mode(sx1276_handle_t *handle);

#ifdef __cplusplus
}
#endif

#endif // SX1276_H
