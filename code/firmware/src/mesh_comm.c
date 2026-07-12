/**
 * mesh_comm.c - LoRa mesh communication implementation
 * 
 * Multi-hop mesh for ESP32-S3 + SX1276 (RFM95W)
 * Uses 865 MHz ISM band (India)
 */

#include "mesh_comm.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "MESH_COMM";

/* ============================================
 * SX1276 REGISTERS
 * ============================================ */

#define REG_FIFO          0x00
#define REG_OP_MODE       0x01
#define REG_FRF_MSB       0x06
#define REG_FRF_MID       0x07
#define REG_FRF_LSB       0x08
#define REG_PA_CONFIG     0x09
#define REG_LNA           0x0C
#define REG_FIFO_ADDR_PTR      0x0D
#define REG_FIFO_TX_BASE_ADDR  0x0E
#define REG_FIFO_RX_BASE_ADDR  0x0F
#define REG_FIFO_RX_CUR_ADDR   0x10
#define REG_IRQ_FLAGS          0x12
#define REG_RX_NB_BYTES        0x13
#define REG_PKT_SNR            0x19
#define REG_PKT_RSSI           0x1A
#define REG_MODEM_CONFIG1      0x1D
#define REG_MODEM_CONFIG2      0x1E
#define REG_SYMB_TIMEOUT_LSB   0x1F
#define REG_PREAMBLE_MSB       0x20
#define REG_PREAMBLE_LSB       0x21
#define REG_PAYLOAD_LENGTH     0x22
#define REG_MAX_PAYLOAD_LENGTH 0x23
#define REG_MODEM_CONFIG3      0x26
#define REG_INVERTIQ           0x33
#define REG_SYNC_WORD          0x39
#define REG_INVERTIQ2          0x3B
#define REG_DIO_MAP1           0x40
#define REG_DIO_MAP2           0x41
#define REG_VERSION            0x42

// Op modes
#define MODE_LONG_RANGE_MODE   0x80
#define MODE_SLEEP             0x00
#define MODE_STANDBY           0x01
#define MODE_TX                0x03
#define MODE_RX_CONTINUOUS     0x05
#define MODE_RX_SINGLE         0x06

// IRQ flags
#define IRQ_RX_DONE            0x40
#define IRQ_TX_DONE            0x08
#define IRQ_PAYLOAD_CRC_ERROR  0x20

/* ============================================
 * SPI INTERFACE
 * ============================================ */

static spi_device_handle_t spi_handle;
static uint8_t node_id;
static uint32_t tx_count = 0;
static uint32_t rx_count = 0;
static uint8_t neighbor_count = 0;
static int8_t last_rssi = 0;

static void lora_write_reg(uint8_t reg, uint8_t val) {
    gpio_set_level(LORA_CS, 0);
    spi_transaction_t t = {
        .length = 16,
        .tx_buffer = (uint8_t[]){reg | 0x80, val},
    };
    spi_device_polling_transmit(spi_handle, &t);
    gpio_set_level(LORA_CS, 1);
}

static uint8_t lora_read_reg(uint8_t reg) {
    gpio_set_level(LORA_CS, 0);
    uint8_t data[2] = {reg & 0x7F, 0};
    spi_transaction_t t = {
        .length = 16,
        .tx_buffer = data,
        .rx_buffer = data,
    };
    spi_device_polling_transmit(spi_handle, &t);
    gpio_set_level(LORA_CS, 1);
    return data[1];
}

static void lora_write_fifo(uint8_t *data, uint8_t len) {
    lora_write_reg(REG_FIFO_ADDR_PTR, 0x00);
    lora_write_reg(REG_FIFO_TX_BASE_ADDR, 0x00);
    lora_write_reg(REG_PAYLOAD_LENGTH, len);
    
    gpio_set_level(LORA_CS, 0);
    uint8_t cmd = 0x80 | REG_FIFO;
    spi_transaction_t t = {
        .length = (len + 1) * 8,
        .tx_buffer = NULL,
    };
    uint8_t *buf = malloc(len + 1);
    buf[0] = cmd;
    memcpy(buf + 1, data, len);
    t.tx_buffer = buf;
    spi_device_polling_transmit(spi_handle, &t);
    free(buf);
    gpio_set_level(LORA_CS, 1);
}

static uint8_t lora_read_fifo(uint8_t *data, uint8_t max_len) {
    uint8_t len = lora_read_reg(REG_RX_NB_BYTES);
    if (len > max_len) len = max_len;
    
    lora_write_reg(REG_FIFO_RX_CUR_ADDR, lora_read_reg(REG_FIFO_RX_BASE_ADDR));
    
    gpio_set_level(LORA_CS, 0);
    uint8_t cmd = 0x00 | REG_FIFO;
    spi_transaction_t t = {
        .length = (len + 1) * 8,
        .tx_buffer = &cmd,
        .rx_buffer = data,
    };
    spi_device_polling_transmit(spi_handle, &t);
    gpio_set_level(LORA_CS, 1);
    
    return len;
}

/* ============================================
 * CHECKSUM
 * ============================================ */

static uint8_t xor_checksum(const void *data, uint16_t len) {
    const uint8_t *p = (const uint8_t *)data;
    uint8_t cksum = 0;
    for (uint16_t i = 0; i < len; i++) {
        cksum ^= p[i];
    }
    return cksum;
}

/* ============================================
 * MESH API
 * ============================================ */

bool mesh_init(uint8_t id) {
    node_id = id;
    ESP_LOGI(TAG, "Initializing LoRa mesh (node_id=%d)", node_id);
    
    // Configure SPI
    spi_bus_config_t bus_cfg = {
        .mosi_io_num = 23,
        .miso_io_num = 19,
        .sclk_io_num = 18,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 64,
    };
    spi_bus_initialize(SPI_HOST, &bus_cfg, SPI_DMA_DISABLED);
    
    spi_device_interface_config_t dev_cfg = {
        .clock_speed_hz = 1000000,
        .mode = 0,
        .spics_io_num = LORA_CS,
        .queue_size = 1,
    };
    spi_bus_add_device(SPI_HOST, &dev_cfg, &spi_handle);
    
    // Configure DIO0 as input (interrupt)
    gpio_set_direction(LORA_DIO0, GPIO_MODE_INPUT);
    gpio_set_direction(LORA_RST, GPIO_MODE_OUTPUT);
    
    // Reset SX1276
    gpio_set_level(LORA_RST, 0);
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(LORA_RST, 1);
    vTaskDelay(pdMS_TO_TICKS(10));
    
    // Check version
    uint8_t version = lora_read_reg(REG_VERSION);
    if (version != 0x12) {
        ESP_LOGE(TAG, "Invalid SX1276 version: 0x%02X", version);
        return false;
    }
    
    // Enter sleep mode (set LoRa mode)
    lora_write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_SLEEP);
    vTaskDelay(pdMS_TO_TICKS(10));
    
    // Set frequency: 865 MHz
    // FRF = (freq * 2^19) / 32MHz
    // 865 MHz = 865000000
    uint64_t frf = ((uint64_t)865000000 << 19) / 32000000;
    lora_write_reg(REG_FRF_MSB, (frf >> 16) & 0xFF);
    lora_write_reg(REG_FRF_MID, (frf >> 8) & 0xFF);
    lora_write_reg(REG_FRF_LSB, frf & 0xFF);
    
    // Set bandwidth 125 kHz, CR 4/5, explicit header
    lora_write_reg(REG_MODEM_CONFIG1, 0x70);  // BW=125kHz, CR=4/5
    lora_write_reg(REG_MODEM_CONFIG2, 0x74);  // SF=7, CRC=on
    lora_write_reg(REG_MODEM_CONFIG3, 0x00);  // LNA boost
    
    // Set preamble length: 8 symbols
    lora_write_reg(REG_PREAMBLE_MSB, 0x00);
    lora_write_reg(REG_PREAMBLE_LSB, 0x08);
    
    // Set sync word (private network)
    lora_write_reg(REG_SYNC_WORD, 0x34);
    
    // Set TX power: 14 dBm
    lora_write_reg(REG_PA_CONFIG, 0x8E);  // PA_BOOST, 14 dBm
    
    // Set LNA gain: max
    lora_write_reg(REG_LNA, 0x23);  // Max gain, LNA boost
    
    // Enter standby
    lora_write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_STANDBY);
    
    ESP_LOGI(TAG, "LoRa mesh initialized (865 MHz, SF7, BW125kHz)");
    return true;
}

bool mesh_send_alert(const mesh_alert_t *alert) {
    mesh_alert_t pkt = *alert;
    pkt.header.source_id = node_id;
    pkt.header.packet_type = PKT_ALERT;
    pkt.checksum = xor_checksum(&pkt, sizeof(pkt) - 1);
    
    lora_write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_STANDBY);
    lora_write_fifo((uint8_t *)&pkt, sizeof(pkt));
    lora_write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_TX);
    
    // Wait for TX done
    uint32_t start = xTaskGetTickCount();
    while (!(lora_read_reg(REG_IRQ_FLAGS) & IRQ_TX_DONE)) {
        if ((xTaskGetTickCount() - start) > pdMS_TO_TICKS(2000)) {
            ESP_LOGE(TAG, "TX timeout");
            return false;
        }
    }
    lora_write_reg(REG_IRQ_FLAGS, IRQ_TX_DONE);
    tx_count++;
    
    ESP_LOGI(TAG, "Alert sent (threat=%d%%, battery=%d%%)", 
             pkt.overall_threat, pkt.battery_pct);
    return true;
}

bool mesh_send_heartbeat(const mesh_heartbeat_t *heartbeat) {
    mesh_heartbeat_t pkt = *heartbeat;
    pkt.header.source_id = node_id;
    pkt.header.packet_type = PKT_HEARTBEAT;
    pkt.checksum = xor_checksum(&pkt, sizeof(pkt) - 1);
    
    lora_write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_STANDBY);
    lora_write_fifo((uint8_t *)&pkt, sizeof(pkt));
    lora_write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_TX);
    
    uint32_t start = xTaskGetTickCount();
    while (!(lora_read_reg(REG_IRQ_FLAGS) & IRQ_TX_DONE)) {
        if ((xTaskGetTickCount() - start) > pdMS_TO_TICKS(2000)) return false;
    }
    lora_write_reg(REG_IRQ_FLAGS, IRQ_TX_DONE);
    tx_count++;
    
    return true;
}

bool mesh_send_sensor_data(const mesh_sensor_t *sensor) {
    mesh_sensor_t pkt = *sensor;
    pkt.header.source_id = node_id;
    pkt.header.packet_type = PKT_SENSOR_DATA;
    pkt.checksum = xor_checksum(&pkt, sizeof(pkt) - 1);
    
    lora_write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_STANDBY);
    lora_write_fifo((uint8_t *)&pkt, sizeof(pkt));
    lora_write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_TX);
    
    uint32_t start = xTaskGetTickCount();
    while (!(lora_read_reg(REG_IRQ_FLAGS) & IRQ_TX_DONE)) {
        if ((xTaskGetTickCount() - start) > pdMS_TO_TICKS(2000)) return false;
    }
    lora_write_reg(REG_IRQ_FLAGS, IRQ_TX_DONE);
    tx_count++;
    
    return true;
}

bool mesh_broadcast_model(const uint8_t *model_data, uint16_t size) {
    // Model broadcast uses multiple packets
    uint8_t chunk_size = 40;  // Max payload per packet
    uint8_t chunks = (size + chunk_size - 1) / chunk_size;
    
    for (uint8_t i = 0; i < chunks; i++) {
        uint16_t offset = i * chunk_size;
        uint16_t len = (size - offset > chunk_size) ? chunk_size : (size - offset);
        
        // Build packet with header + chunk
        uint8_t pkt[50];
        pkt[0] = PKT_MODEL_UPDATE;  // type
        pkt[1] = node_id;           // source
        pkt[2] = 0xFF;              // broadcast
        pkt[3] = 0;                 // hop count
        pkt[4] = 5;                 // max hops
        pkt[5] = i;                 // chunk index
        pkt[6] = chunks;            // total chunks
        memcpy(pkt + 7, model_data + offset, len);
        pkt[7 + len] = xor_checksum(pkt, 7 + len);
        
        lora_write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_STANDBY);
        lora_write_fifo(pkt, 7 + len + 1);
        lora_write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_TX);
        
        uint32_t start = xTaskGetTickCount();
        while (!(lora_read_reg(REG_IRQ_FLAGS) & IRQ_TX_DONE)) {
            if ((xTaskGetTickCount() - start) > pdMS_TO_TICKS(2000)) return false;
        }
        lora_write_reg(REG_IRQ_FLAGS, IRQ_TX_DONE);
        
        vTaskDelay(pdMS_TO_TICKS(100));  // Inter-packet delay
    }
    
    tx_count++;
    ESP_LOGI(TAG, "Model broadcast sent (%d chunks)", chunks);
    return true;
}

uint8_t mesh_receive(void *buffer, uint16_t max_size, uint32_t timeout_ms) {
    // Enter RX continuous mode
    lora_write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_RX_CONTINUOUS);
    
    uint32_t start = xTaskGetTickCount();
    while (1) {
        uint8_t irq = lora_read_reg(REG_IRQ_FLAGS);
        
        if (irq & IRQ_RX_DONE) {
            lora_write_reg(REG_IRQ_FLAGS, IRQ_RX_DONE);
            
            // Check for CRC error
            if (irq & IRQ_PAYLOAD_CRC_ERROR) {
                ESP_LOGW(TAG, "CRC error");
                lora_write_reg(REG_IRQ_FLAGS, IRQ_PAYLOAD_CRC_ERROR);
                continue;
            }
            
            // Read packet
            uint8_t len = lora_read_fifo((uint8_t *)buffer, max_size);
            last_rssi = (int8_t)lora_read_reg(REG_PKT_RSSI) - 157;
            rx_count++;
            
            // Go back to standby
            lora_write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_STANDBY);
            
            return len;
        }
        
        if ((xTaskGetTickCount() - start) > pdMS_TO_TICKS(timeout_ms)) {
            lora_write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_STANDBY);
            return 0;  // Timeout
        }
        
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void mesh_get_stats(uint32_t *packets_sent, uint32_t *packets_received,
                    uint8_t *neighbors, int8_t *signal_strength) {
    if (packets_sent) *packets_sent = tx_count;
    if (packets_received) *packets_received = rx_count;
    if (neighbors) *neighbors = neighbor_count;
    if (signal_strength) *signal_strength = last_rssi;
}

void mesh_set_power(uint8_t power) {
    if (power < 2) power = 2;
    if (power > 20) power = 20;
    
    uint8_t pa_config;
    if (power > 17) {
        pa_config = 0x80 | (power - 5);  // PA_BOOST with high power
    } else {
        pa_config = 0x80 | (power - 2);  // PA_BOOST
    }
    lora_write_reg(REG_PA_CONFIG, pa_config);
}

void mesh_set_frequency(uint32_t freq_hz) {
    uint64_t frf = ((uint64_t)freq_hz << 19) / 32000000;
    lora_write_reg(REG_FRF_MSB, (frf >> 16) & 0xFF);
    lora_write_reg(REG_FRF_MID, (frf >> 8) & 0xFF);
    lora_write_reg(REG_FRF_LSB, frf & 0xFF);
}
