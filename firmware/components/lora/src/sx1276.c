/**
 * sx1276.c - SX1276 LoRa Transceiver Driver Implementation
 * 
 * Real hardware driver for Semtech SX1276/RFM95W
 * Uses ESP-IDF SPI master driver
 */

#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "sx1276.h"

static const char *TAG = "SX1276";

/* ============================================
 * LOW-LEVEL SPI FUNCTIONS
 * ============================================ */

static void sx1276_write_bytes(sx1276_handle_t *handle, uint8_t reg, 
                               const uint8_t *data, uint8_t len) {
    uint8_t buf[256];
    buf[0] = reg | 0x80;  // Write bit set
    memcpy(&buf[1], data, len);
    
    spi_transaction_t t = {
        .length = (len + 1) * 8,
        .tx_buffer = buf,
        .rx_buffer = NULL,
    };
    
    gpio_set_level(handle->pin_cs, 0);
    spi_device_transmit(handle->spi, &t);
    gpio_set_level(handle->pin_cs, 1);
}

static void sx1276_read_bytes(sx1276_handle_t *handle, uint8_t reg, 
                              uint8_t *data, uint8_t len) {
    uint8_t tx_buf = reg & 0x7F;  // Read bit cleared
    
    spi_transaction_t t = {
        .length = len * 8,
        .tx_buffer = &tx_buf,
        .rx_buffer = data,
        .rxlength = len * 8,
    };
    
    gpio_set_level(handle->pin_cs, 0);
    spi_device_transmit(handle->spi, &t);
    gpio_set_level(handle->pin_cs, 1);
}

uint8_t sx1276_read_register(sx1276_handle_t *handle, uint8_t reg) {
    uint8_t value;
    sx1276_read_bytes(handle, reg, &value, 1);
    return value;
}

void sx1276_write_register(sx1276_handle_t *handle, uint8_t reg, uint8_t value) {
    sx1276_write_bytes(handle, reg, &value, 1);
}

static void sx1276_write_fifo(sx1276_handle_t *handle, const uint8_t *data, uint8_t len) {
    sx1276_write_register(handle, SX1276_REG_FIFO_ADDR_PTR, 0x00);
    sx1276_write_register(handle, SX1276_REG_FIFO_TX_BASE_ADDR, 0x00);
    sx1276_write_register(handle, SX1276_REG_PAYLOAD_LENGTH, len);
    sx1276_write_bytes(handle, SX1276_REG_FIFO, data, len);
}

static void sx1276_read_fifo(sx1276_handle_t *handle, uint8_t *data, uint8_t len) {
    sx1276_write_register(handle, SX1276_REG_FIFO_ADDR_PTR, 
                          sx1276_read_register(handle, SX1276_REG_FIFO_RX_CUR_ADDR));
    sx1276_read_bytes(handle, SX1276_REG_FIFO, data, len);
}

/* ============================================
 * FREQUENCY CONFIGURATION
 * ============================================ */

static void sx1276_set_frequency(sx1276_handle_t *handle, uint32_t freq) {
    uint64_t frf = ((uint64_t)freq << 19) / 32000000ULL;
    
    sx1276_write_register(handle, SX1276_REG_FRF_MSB, (frf >> 16) & 0xFF);
    sx1276_write_register(handle, SX1276_REG_FRF_MID, (frf >> 8) & 0xFF);
    sx1276_write_register(handle, SX1276_REG_FRF_LSB, frf & 0xFF);
    
    handle->frequency = freq;
    ESP_LOGI(TAG, "Frequency set to %lu Hz", freq);
}

/* ============================================
 * MODE CONTROL
 * ============================================ */

static void sx1276_set_mode(sx1276_handle_t *handle, uint8_t mode) {
    sx1276_write_register(handle, SX1276_REG_OP_MODE, SX1276_LONG_RANGE_MODE | mode);
    vTaskDelay(pdMS_TO_TICKS(10));  // Mode switch delay
}

static void sx1276_clear_irq_flags(sx1276_handle_t *handle, uint8_t flags) {
    sx1276_write_register(handle, SX1276_REG_IRQ_FLAGS, flags);
}

/* ============================================
 * PUBLIC API
 * ============================================ */

bool sx1276_init(const sx1276_config_t *config, sx1276_handle_t **handle) {
    ESP_LOGI(TAG, "Initializing SX1276 LoRa transceiver...");
    
    // Allocate handle
    sx1276_handle_t *dev = calloc(1, sizeof(sx1276_handle_t));
    if (!dev) {
        ESP_LOGE(TAG, "Failed to allocate handle");
        return false;
    }
    
    dev->pin_cs = config->pin_cs;
    dev->pin_rst = config->pin_rst;
    dev->pin_dio0 = config->pin_dio0;
    dev->pin_dio1 = config->pin_dio1;
    
    // Configure GPIO pins
    gpio_config_t io_conf = {
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    
    // CS pin
    io_conf.pin_bit_mask = (1ULL << config->pin_cs);
    gpio_config(&io_conf);
    gpio_set_level(config->pin_cs, 1);
    
    // RST pin
    io_conf.pin_bit_mask = (1ULL << config->pin_rst);
    gpio_config(&io_conf);
    
    // DIO0 input
    io_conf.mode = GPIO_MODE_INPUT;
    io_conf.pull_up_en = GPIO_PULLUP_ENABLE;
    io_conf.pin_bit_mask = (1ULL << config->pin_dio0);
    gpio_config(&io_conf);
    
    // Initialize SPI
    spi_bus_config_t bus_cfg = {
        .mosi_io_num = config->pin_mosi,
        .miso_io_num = config->pin_miso,
        .sclk_io_num = config->pin_sclk,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 256,
    };
    
    esp_err_t ret = spi_bus_initialize(config->spi_host, &bus_cfg, SPI_DMA_CH_AUTO);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI bus init failed: %s", esp_err_to_name(ret));
        free(dev);
        return false;
    }
    
    spi_device_interface_config_t dev_cfg = {
        .mode = 0,
        .clock_speed_hz = 10 * 1000 * 1000,  // 10 MHz
        .spics_io_num = -1,  // We control CS manually
        .queue_size = 1,
    };
    
    ret = spi_bus_add_device(config->spi_host, &dev_cfg, &dev->spi);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI add device failed: %s", esp_err_to_name(ret));
        spi_bus_free(config->spi_host);
        free(dev);
        return false;
    }
    
    // Reset SX1276
    sx1276_reset(dev);
    
    // Check version register
    uint8_t version = sx1276_read_register(dev, SX1276_REG_VERSION);
    if (version != 0x12) {
        ESP_LOGE(TAG, "Invalid SX1276 version: 0x%02X (expected 0x12)", version);
        spi_bus_remove_device(dev->spi);
        spi_bus_free(config->spi_host);
        free(dev);
        return false;
    }
    ESP_LOGI(TAG, "SX1276 detected, version: 0x%02X", version);
    
    // Set LoRa mode
    sx1276_set_mode(dev, SX1276_MODE_SLEEP);
    vTaskDelay(pdMS_TO_TICKS(50));
    
    // Configure LoRa parameters
    sx1276_configure(dev, config->frequency, config->spreading_factor,
                     config->bandwidth, config->coding_rate);
    
    // Set sync word
    sx1276_write_register(dev, SX1276_REG_SYNC_CONFIG, 0x40);  // LoRa mode
    sx1276_write_register(dev, SX1276_REG_SYNC_VALUE1, config->sync_word);
    
    // Set preamble length
    sx1276_write_register(dev, SX1276_REG_PREAMBLE_MSB, 
                          (config->preamble_length >> 8) & 0xFF);
    sx1276_write_register(dev, SX1276_REG_PREAMBLE_LSB, 
                          config->preamble_length & 0xFF);
    
    // Set TX power
    sx1276_set_tx_power(dev, config->tx_power);
    
    // Enable LNA max gain
    sx1276_write_register(dev, SX1276_REG_LNA, 0x23);  // Max gain, LNA boost
    
    // Enable +20dBm PA_BOOST (if needed for high power)
    if (config->tx_power > 17) {
        sx1276_write_register(dev, SX1276_REG_PA_DAC, 0x87);  // Enable +20dBm
        sx1276_write_register(dev, SX1276_REG_PA_CONFIG, 
                              SX1276_PA_BOOST | 0x0F);
    }
    
    // Standby mode
    sx1276_set_mode(dev, SX1276_MODE_STANDBY);
    
    *handle = dev;
    ESP_LOGI(TAG, "SX1276 initialized successfully");
    return true;
}

bool sx1276_configure(sx1276_handle_t *handle, uint32_t freq, uint8_t sf, 
                      uint8_t bw, uint8_t cr) {
    ESP_LOGI(TAG, "Configuring: freq=%lu, SF=%d, BW=%d, CR=4/%d", 
             freq, sf, bw, cr + 5);
    
    // Set frequency
    sx1276_set_frequency(handle, freq);
    
    // Modem config 1: BW, CR, explicit header
    uint8_t reg1 = (bw << 4) | ((cr - 5) << 1) | 0x00;  // Explicit header
    sx1276_write_register(handle, SX1276_REG_MODEM_CONFIG1, reg1);
    
    // Modem config 2: SF, RX timeout MSB
    uint8_t reg2 = (sf << 4) | 0x00;  // SF, no CRC yet
    sx1276_write_register(handle, SX1276_REG_MODEM_CONFIG2, reg2);
    
    // Modem config 3: Low data rate optimize, AGC auto on
    uint8_t reg3 = 0x08;  // AGC auto on
    if (sf >= 11) {
        reg3 |= 0x01;  // Low data rate optimize for SF11, SF12
    }
    sx1276_write_register(handle, SX1276_REG_MODEM_CONFIG3, reg3);
    
    handle->spreading_factor = sf;
    
    return true;
}

void sx1276_set_tx_power(sx1276_handle_t *handle, int8_t power) {
    if (power < 2) power = 2;
    if (power > 20) power = 20;
    
    if (power > 17) {
        // PA_BOOST with PA_DAC for +20dBm
        sx1276_write_register(handle, SX1276_REG_PA_DAC, 0x87);
        sx1276_write_register(handle, SX1276_REG_PA_CONFIG, 
                              SX1276_PA_BOOST | 0x0F);
    } else if (power > 2) {
        // PA_BOOST
        sx1276_write_register(handle, SX1276_REG_PA_DAC, 0x84);  // Default
        sx1276_write_register(handle, SX1276_REG_PA_CONFIG, 
                              SX1276_PA_BOOST | (power - 2));
    } else {
        // RFO for low power
        sx1276_write_register(handle, SX1276_REG_PA_DAC, 0x84);
        sx1276_write_register(handle, SX1276_REG_PA_CONFIG, 
                              SX1276_PA_OUTPUT_RFO | power);
    }
    
    handle->tx_power = power;
    ESP_LOGI(TAG, "TX power set to %d dBm", power);
}

bool sx1276_transmit(sx1276_handle_t *handle, const uint8_t *data, 
                     uint8_t len, uint32_t timeout_ms) {
    ESP_LOGI(TAG, "Transmitting %d bytes...", len);
    
    // Standby first
    sx1276_set_mode(handle, SX1276_MODE_STANDBY);
    
    // Reset FIFO address
    sx1276_write_register(handle, SX1276_REG_FIFO_ADDR_PTR, 0x00);
    sx1276_write_register(handle, SX1276_REG_FIFO_TX_BASE_ADDR, 0x00);
    
    // Write data to FIFO
    sx1276_write_fifo(handle, data, len);
    
    // Set payload length
    sx1276_write_register(handle, SX1276_REG_PAYLOAD_LENGTH, len);
    
    // Clear IRQ flags
    sx1276_clear_irq_flags(handle, SX1276_IRQ_TX_DONE);
    
    // Enable DIO0 for TX done
    sx1276_write_register(handle, SX1276_REG_DIO_MAPPING1, SX1276_DIO0_TX_DONE);
    
    // Start TX
    sx1276_set_mode(handle, SX1276_MODE_TX);
    handle->is_transmitting = true;
    
    // Wait for TX done or timeout
    uint32_t start = xTaskGetTickCount();
    while ((xTaskGetTickCount() - start) < pdMS_TO_TICKS(timeout_ms)) {
        uint8_t irq = sx1276_read_register(handle, SX1276_REG_IRQ_FLAGS);
        if (irq & SX1276_IRQ_TX_DONE) {
            sx1276_clear_irq_flags(handle, SX1276_IRQ_TX_DONE);
            handle->is_transmitting = false;
            ESP_LOGI(TAG, "TX complete");
            return true;
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
    
    handle->is_transmitting = false;
    ESP_LOGE(TAG, "TX timeout");
    sx1276_set_mode(handle, SX1276_MODE_STANDBY);
    return false;
}

void sx1276_start_receive(sx1276_handle_t *handle) {
    sx1276_set_mode(handle, SX1276_MODE_STANDBY);
    
    // Reset FIFO RX pointer
    sx1276_write_register(handle, SX1276_REG_FIFO_ADDR_PTR, 0x00);
    sx1276_write_register(handle, SX1276_REG_FIFO_RX_BASE_ADDR, 0x00);
    
    // Enable DIO0 for RX done
    sx1276_write_register(handle, SX1276_REG_DIO_MAPPING1, SX1276_DIO0_RX_DONE);
    
    // Clear IRQ flags
    sx1276_clear_irq_flags(handle, SX1276_IRQ_RX_DONE | SX1276_IRQ_RX_TIMEOUT);
    
    // Start continuous RX
    sx1276_set_mode(handle, SX1276_MODE_RX_CONTINUOUS);
    handle->is_receiving = true;
    
    ESP_LOGI(TAG, "Receiving started");
}

bool sx1276_received(sx1276_handle_t *handle) {
    uint8_t irq = sx1276_read_register(handle, SX1276_REG_IRQ_FLAGS);
    return (irq & SX1276_IRQ_RX_DONE) != 0;
}

uint8_t sx1276_read(sx1276_handle_t *handle, uint8_t *buffer, 
                    uint8_t max_len, int8_t *rssi, float *snr) {
    uint8_t irq = sx1276_read_register(handle, SX1276_REG_IRQ_FLAGS);
    
    if (!(irq & SX1276_IRQ_RX_DONE)) {
        return 0;
    }
    
    // Get packet info
    uint8_t rx_bytes = sx1276_read_register(handle, SX1276_REG_RX_NB_BYTES);
    int8_t pkt_snr = (int8_t)sx1276_read_register(handle, SX1276_REG_PKT_SNR_VALUE);
    uint8_t pkt_rssi_raw = sx1276_read_register(handle, SX1276_REG_PKT_RSSI_VALUE);
    
    // Calculate RSSI (offset depends on frequency)
    int16_t pkt_rssi = -164 + pkt_rssi_raw;
    if (pkt_snr < 0) {
        pkt_rssi = pkt_rssi + pkt_snr;
    }
    
    // Read data from FIFO
    uint8_t len = (rx_bytes < max_len) ? rx_bytes : max_len;
    sx1276_read_fifo(handle, buffer, len);
    
    // Clear IRQ flags
    sx1276_clear_irq_flags(handle, SX1276_IRQ_RX_DONE);
    
    if (rssi) *rssi = (int8_t)pkt_rssi;
    if (snr) *snr = pkt_snr / 4.0f;
    
    ESP_LOGI(TAG, "Received %d bytes, RSSI=%d, SNR=%.1f", len, pkt_rssi, pkt_snr / 4.0f);
    
    return len;
}

void sx1276_sleep(sx1276_handle_t *handle) {
    sx1276_set_mode(handle, SX1276_MODE_SLEEP);
    handle->is_transmitting = false;
    handle->is_receiving = false;
    ESP_LOGI(TAG, "Entered sleep mode");
}

void sx1276_standby(sx1276_handle_t *handle) {
    sx1276_set_mode(handle, SX1276_MODE_STANDBY);
    ESP_LOGI(TAG, "Entered standby mode");
}

bool sx1276_channel_activity_detect(sx1276_handle_t *handle) {
    sx1276_set_mode(handle, SX1276_MODE_STANDBY);
    
    // Enable DIO0 for CAD done
    sx1276_write_register(handle, SX1276_REG_DIO_MAPPING1, 0x00);
    
    // Clear IRQ flags
    sx1276_clear_irq_flags(handle, SX1276_IRQ_CAD_DONE | SX1276_IRQ_CAD_DETECTED);
    
    // Start CAD
    sx1276_set_mode(handle, SX1276_MODE_CAD);
    
    // Wait for CAD done
    uint32_t start = xTaskGetTickCount();
    while ((xTaskGetTickCount() - start) < pdMS_TO_TICKS(1000)) {
        uint8_t irq = sx1276_read_register(handle, SX1276_REG_IRQ_FLAGS);
        if (irq & SX1276_IRQ_CAD_DONE) {
            bool detected = (irq & SX1276_IRQ_CAD_DETECTED) != 0;
            sx1276_clear_irq_flags(handle, SX1276_IRQ_CAD_DONE | SX1276_IRQ_CAD_DETECTED);
            return !detected;  // Return true if channel is free
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
    
    return false;  // Timeout, assume channel busy
}

int16_t sx1276_get_rssi(sx1276_handle_t *handle) {
    uint8_t rssi_raw = sx1276_read_register(handle, SX1276_REG_RSSI_VALUE);
    return -164 + rssi_raw;
}

void sx1276_reset(sx1276_handle_t *handle) {
    ESP_LOGI(TAG, "Resetting SX1276...");
    gpio_set_level(handle->pin_rst, 0);
    vTaskDelay(pdMS_TO_TICKS(1));
    gpio_set_level(handle->pin_rst, 1);
    vTaskDelay(pdMS_TO_TICKS(10));  // Wait for reset
}
