# Firmware API Reference

## Components Overview

```
firmware/components/
├── common/          # Shared types, error codes
├── sensors/         # 11 sensor drivers
├── lora/            # SX1276 driver
├── mesh/            # Mesh networking
└── ml/              # XGBoost inference
```

---

## Common (`components/common/include/common.h`)

### Error Codes

```c
#define ERR_SENSOR_BASE       0x0100
#define ERR_ML_BASE           0x0200
#define ERR_MESH_BASE         0x0300
#define ERR_RADIO_BASE        0x0400
#define ERR_PACKET_BASE       0x0500
```

### Sensor Reading (`sensor_reading_t`)

```c
typedef struct {
    float temperature;        // °C
    float humidity;           // %RH
    float pressure;           // hPa
    float altitude;           // m
    float wind_speed;         // m/s
    float wind_direction;     // degrees
    float precipitation;      // mm/h
    float uv_index;           // UV index
    float pm1_0;              // μg/m³
    float pm2_5;              // μg/m³
    float pm10;               // μg/m³
    float co2;                // ppm
    float voc_index;          // VOC index
    float nox_index;          // NOx index
    float co_ppm;             // ppm CO
    float no2_ppm;            // ppm NO2
    float nh3_ppm;            // ppm NH3
    float lightning_dist;     // km
    uint8_t lightning_count;  // strikes
    uint32_t timestamp;       // ms since boot
    uint8_t sensor_mask;      // valid field bitmask
} sensor_reading_t;
```

### Sensor Mask Bits

```c
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
```

### Feature Vector (`feature_vector_t`)

```c
#define MAX_FEATURES 16

typedef struct {
    float values[MAX_FEATURES];
    uint8_t count;
    uint32_t timestamp_ms;
} feature_vector_t;
```

---

## Sensors (`components/sensors/`)

### BME280 (`bme280.h` / `bme280.c`)

```c
// Init
bool bme280_init(i2c_port_t port, uint8_t addr, bme280_handle_t **handle);

// Configure
void bme280_configure(bme280_handle_t *h, uint8_t osrs_h, uint8_t osrs_t,
                      uint8_t osrs_p, uint8_t mode, uint8_t standby, uint8_t filter);

// Read all
bool bme280_read(bme280_handle_t *h, bme280_data_t *data);

// Individual reads
float bme280_read_temperature(bme280_handle_t *h);
float bme280_read_humidity(bme280_handle_t *h);
float bme280_read_pressure(bme280_handle_t *h);

// Utility
float bme280_calculate_altitude(float pressure_hPa, float sea_level_hPa);
void bme280_sleep(bme280_handle_t *h);
```

### PMS5003 (`pms5003.h` / `pms5003.c`)

```c
bool pms5003_init(uart_port_t uart, gpio_num_t pin_set, gpio_num_t pin_rst,
                  pms5003_handle_t **handle);
bool pms5003_read(pms5003_handle_t *h, pms5003_data_t *data);
bool pms5003_read_timeout(pms5003_handle_t *h, pms5003_data_t *data, uint32_t ms);
void pms5003_set_passive(pms5003_handle_t *h, bool passive);
void pms5003_request_data(pms5003_handle_t *h);
void pms5003_sleep(pms5003_handle_t *h);
void pms5003_wake_up(pms5003_handle_t *h);
void pms5003_reset(pms5003_handle_t *h);
const char* pms5003_get_aqi_category(uint16_t pm25);
```

### DS18B20 (`ds18b20.h` / `ds18b20.c`)

```c
esp_err_t ds18b20_init(int gpio_pin, ds18b20_handle_t **handle);
esp_err_t ds18b20_read_temperature(ds18b20_handle_t *h, float *temp);
esp_err_t ds18b20_read_scratchpad(ds18b20_handle_t *h, uint8_t *scratch);
esp_err_t ds18b20_set_resolution(ds18b20_handle_t *h, uint8_t res);
bool ds18b20_detect(int gpio_pin);
```

### Anemometer (`anemometer.h` / `anemometer.c`)

```c
bool anemometer_init(int adc_speed_ch, int adc_dir_ch, anemometer_handle_t **handle);
bool anemometer_read_speed(anemometer_handle_t *h, float *speed_ms);
bool anemometer_read_direction(anemometer_handle_t *h, float *direction_deg);
```

### SEN0575 Rain (`sen0575.h` / `sen0575.c`)

```c
typedef enum { RAIN_NONE=0, RAIN_LIGHT=1, RAIN_MODERATE=2, RAIN_HEAVY=3 } rain_intensity_t;

bool sen0575_init(int adc_ch, sen0575_handle_t **handle);
bool sen0575_read_voltage(sen0575_handle_t *h, float *voltage_mv);
bool sen0575_read_intensity(sen0575_handle_t *h, rain_intensity_t *intensity);
```

### LTR-390UV (`ltr390.h` / `ltr390.c`)

```c
bool ltr390_init(i2c_port_t port, uint8_t addr, ltr390_handle_t **handle);
bool ltr390_read_uvs(ltr390_handle_t *h, float *uv_index);
bool ltr390_read_als(ltr390_handle_t *h, float *lux);
void ltr390_set_gain(ltr390_handle_t *h, uint8_t gain);
void ltr390_set_resolution(ltr390_handle_t *h, uint8_t res);
```

### SCD41 CO2 (`scd41.h` / `scd41.c`)

```c
bool scd41_init(i2c_port_t port, uint8_t addr, scd41_handle_t **handle);
bool scd41_read(scd41_handle_t *h, float *co2_ppm, float *temp, float *hum);
bool scd41_start_periodic(scd41_handle_t *h);
bool scd41_stop_periodic(scd41_handle_t *h);
bool scd41_sleep(scd41_handle_t *h);
bool scd41_wake(scd41_handle_t *h);
bool scd41_set_temp_offset(scd41_handle_t *h, float offset_c);
bool scd41_self_test(scd41_handle_t *h);
```

### SGP41 VOC/NOx (`sgp41.h` / `sgp41.c`)

```c
bool sgp41_init(i2c_port_t port, uint8_t addr, sgp41_handle_t **handle);
bool sgp41_read_raw(sgp41_handle_t *h, uint16_t *voc_raw, uint16_t *nox_raw);
bool sgp41_conditioning(sgp41_handle_t *h);
bool sgp41_self_test(sgp41_handle_t *h);
void sgp41_heater_off(sgp41_handle_t *h);
```

### MICS-6814 (`mics6814.h` / `mics6814.c`)

```c
bool mics6814_init(int adc_ch_co, int adc_ch_no2, int adc_ch_nh3,
                   mics6814_handle_t **handle);
bool mics6814_read(mics6814_handle_t *h, mics6814_data_t *data);

typedef struct {
    float co_ppm;
    float no2_ppm;
    float nh3_ppm;
} mics6814_data_t;
```

### AS3935 Lightning (`as3935.h` / `as3935.c`)

```c
bool as3935_init(i2c_port_t port, uint8_t addr, bool outdoor,
                 as3935_handle_t **handle);
bool as3935_read_event(as3935_handle_t *h, as3935_data_t *data);
bool as3935_clear_stats(as3935_handle_t *h);
bool as3935_set_noise_floor(as3935_handle_t *h, uint8_t level);
bool as3935_set_watchdog_threshold(as3935_handle_t *h, uint8_t thresh);
bool as3935_power_down(as3935_handle_t *h);
bool as3935_power_up(as3935_handle_t *h);
bool as3935_calibrate_rco(as3935_handle_t *h);

typedef struct {
    uint8_t distance_km;
    uint8_t strike_count;
    uint32_t energy;
    uint8_t interrupt_source;  // 0x01=noise, 0x04=disturber, 0x08=lightning
} as3935_data_t;
```

### Battery (`battery.h` / `battery.c`)

```c
typedef enum { BATTERY_OK=0, BATTERY_LOW=1, BATTERY_CRITICAL=2, BATTERY_EMPTY=3 } battery_level_t;

bool battery_init(int adc_ch, float divider_ratio, battery_handle_t **handle);
bool battery_read(battery_handle_t *h, battery_status_t *status);

typedef struct {
    float voltage;
    float percent;
    battery_level_t level;
} battery_status_t;
```

---

## LoRa (`components/lora/`)

### SX1276 (`sx1276.h` / `sx1276.c`)

```c
// Config
typedef struct {
    spi_host_device_t spi_host;
    gpio_num_t pin_mosi, pin_miso, pin_sclk, pin_cs, pin_rst, pin_dio0, pin_dio1;
    uint32_t frequency;      // Hz (e.g., 865000000)
    int8_t tx_power;         // dBm (2-20)
    uint8_t spreading_factor; // 6-12
    uint8_t bandwidth;       // 0=7.8kHz...9=500kHz
    uint8_t coding_rate;     // 1-4 (4/5, 4/6, 4/7, 4/8)
    uint8_t sync_word;       // network ID
    uint16_t preamble_length;
} sx1276_config_t;

// API
bool sx1276_init(const sx1276_config_t *config, sx1276_handle_t **handle);
bool sx1276_configure(sx1276_handle_t *h, uint32_t freq, uint8_t sf, uint8_t bw, uint8_t cr);
void sx1276_set_tx_power(sx1276_handle_t *h, int8_t power);
bool sx1276_transmit(sx1276_handle_t *h, const uint8_t *data, uint8_t len, uint32_t timeout_ms);
void sx1276_start_receive(sx1276_handle_t *h);
bool sx1276_received(sx1276_handle_t *h);
uint8_t sx1276_read(sx1276_handle_t *h, uint8_t *buf, uint8_t max_len, int8_t *rssi, float *snr);
void sx1276_sleep(sx1276_handle_t *h);
void sx1276_standby(sx1276_handle_t *h);
bool sx1276_channel_activity_detect(sx1276_handle_t *h);
int16_t sx1276_get_rssi(sx1276_handle_t *h);
void sx1276_reset(sx1276_handle_t *h);
uint8_t sx1276_read_register(sx1276_handle_t *h, uint8_t reg);
void sx1276_write_register(sx1276_handle_t *h, uint8_t reg, uint8_t val);
```

---

## Mesh (`components/mesh/`)

### Mesh (`mesh.h` / `mesh.c`)

```c
// Packet flags
#define MESH_FLAG_ACK_REQ  (1 << 0)
#define MESH_FLAG_ACK      (1 << 1)
#define MESH_FLAG_ALERT    (1 << 2)

// Init & config
esp_err_t mesh_init(uint32_t node_id);
void mesh_set_lora_handle(sx1276_handle_t *handle);
void mesh_set_rx_callback(mesh_rx_callback_t cb);

// Send / receive
esp_err_t mesh_send(uint32_t dest_id, const uint8_t *payload, uint8_t len, uint8_t flags);
esp_err_t mesh_receive(const uint8_t *data, uint8_t len, int16_t rssi, float snr);

// Periodic (call from comms task loop)
void mesh_periodic(uint32_t now_ms);
void mesh_send_heartbeat(void);

// Query
uint32_t mesh_get_node_id(void);
uint8_t mesh_neighbor_count(void);
esp_err_t mesh_get_neighbor(uint8_t index, mesh_neighbor_t *entry);
void mesh_get_stats(mesh_stats_t *stats);
uint32_t mesh_get_time_ms(void);
```

### Neighbor Entry (`mesh_neighbor_t`)

```c
typedef struct {
    uint32_t node_id;
    int16_t rssi_last;
    float snr_last;
    uint32_t last_seen_ms;
    uint32_t packets_rx;
    uint8_t hop_count;
} mesh_neighbor_t;
```

### Statistics (`mesh_stats_t`)

```c
typedef struct {
    uint32_t packets_sent;
    uint32_t packets_received;
    uint32_t packets_forwarded;
    uint32_t packets_dropped;
    uint32_t duplicates_filtered;
    uint32_t seq_num;
    uint8_t neighbor_count;
} mesh_stats_t;
```

---

## ML (`components/ml/`)

See `docs/reference/ML_INFERENCE.md` for full details.

```c
esp_err_t ml_init(void);
esp_err_t ml_normalize(const float *raw, float *norm);
esp_err_t ml_predict(const float *features, uint8_t class_id, float *output);
float ml_confidence(float raw_output);
size_t ml_model_ram_usage(void);
size_t ml_model_flash_usage(void);
uint32_t ml_last_inference_us(void);
```

---

## Main Application (`main/main.c`)

### Key Definitions

```c
#define SENSOR_POLL_INTERVAL_MS   60000
#define ALERT_QUEUE_LENGTH        8

#define ALERT_THRESHOLD_WILDFIRE      0.70f
#define ALERT_THRESHOLD_FLOOD         0.70f
#define ALERT_THRESHOLD_STORM         0.75f
#define ALERT_THRESHOLD_AIR_QUALITY   0.65f
```

### FreeRTOS Tasks

| Task | Core | Priority | Stack | Function |
|------|------|----------|-------|----------|
| `sensor_ml` | 0 | 5 | 4096 | Sensor polling, ML inference, alert queueing |
| `mesh_comms` | 1 | 4 | 4096 | LoRa RX, mesh processing, alert TX, heartbeat |

### Alert Queue Item

```c
typedef struct {
    uint8_t  payload[MAX_PACKET_PAYLOAD];
    uint8_t  payload_len;
    uint32_t hazard_class;    // 0-3
    float    confidence;
    uint32_t timestamp_ms;
} alert_queue_item_t;
```

### Mesh RX Callback

```c
void mesh_rx_handler(const mesh_packet_t *packet, uint32_t from_id,
                     int16_t rssi, float snr);
```

---

## Build Configuration

### `sdkconfig.defaults`

```ini
CONFIG_IDF_TARGET_ESP32S3=y
CONFIG_ESP32S3_DEFAULT_CPU_FREQ_240=y
CONFIG_FLASH_SIZE_8MB=y
CONFIG_PARTITION_TABLE_CUSTOM=y
CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions.csv"
# WiFi/BT disabled for power
CONFIG_ESP_WIFI_ENABLED=n
CONFIG_BT_ENABLED=n
```

### `partitions.csv`

```csv
# Name,   Type, SubType, Offset,  Size, Flags
nvs,      data, nvs,     0x9000,  0x4000,
factory,  app,  factory, 0x10000, 0x300000,
```

---

## Constants Summary

| Constant | Value | Location |
|----------|-------|----------|
| `ML_FEATURE_COUNT` | 14 | `ml.h` |
| `NUM_HAZARD_CLASSES` | 4 | `main.c` |
| `MAX_PACKET_PAYLOAD` | 240 | `common.h` |
| `ALERT_QUEUE_LENGTH` | 8 | `main.c` |
| `SENSOR_POLL_INTERVAL_MS` | 60000 | `main.c` |
| `MESH_DEFAULT_TTL` | 5 | `mesh.h` |
| `MESH_HEARTBEAT_INTERVAL_MS` | 30000 | `mesh.h` |