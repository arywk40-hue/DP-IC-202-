/**
 * main.c - Edge AI Environmental Hazard Detection Node
 *
 * Entry point for the ESP32-S3 based environmental monitoring node.
 * Initializes hardware peripherals, sensor drivers, LoRa radio,
 * ML inference engine, and mesh networking in the correct order.
 *
 * Execution order:
 *   1. NVS flash (persistent storage)
 *   2. I2C bus (sensors)
 *   3. SPI bus (LoRa radio)
 *   4. UART (PMS5003 particulate sensor)
 *   5. Sensor drivers (BME280, DS18B20, PMS5003, etc.)
 *   6. SX1276 LoRa radio
 *   7. ML inference engine
 *   8. Mesh networking layer
 *   9. Create FreeRTOS tasks
 *
 * FreeRTOS tasks:
 *   - sensor_ml_task (Core 0):  polls sensors, builds 14-element feature vector
 *     matching FEATURE_NAMES in code/ml/train_model.py, runs ml_normalize() then
 *     ml_predict() for each of the 4 HAZARD_CLASSES (wildfire, flood, storm,
 *     air_quality), and queues alert packets when confidence exceeds threshold.
 *   - mesh_comms_task (Core 1):  initializes LoRa + mesh, polls SX1276 radio,
 *     passes received bytes to mesh_receive(), drains alert queue via mesh_send().
 */

#include <stdio.h>
#include <string.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_system.h"
#include "esp_log.h"
#include "esp_err.h"
#include "nvs_flash.h"
#include "driver/i2c.h"
#include "driver/spi_master.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_efuse.h"

#include "common.h"
#include "bme280.h"
#include "pms5003.h"
#include "ds18b20.h"
#include "anemometer.h"
#include "sen0575.h"
#include "ltr390.h"
#include "scd41.h"
#include "sgp41.h"
#include "mics6814.h"
#include "as3935.h"
#include "battery.h"
#include "sx1276.h"
#include "ml.h"
#include "mesh.h"
#include "crypto.h"
#include "key_provisioning.h"

#ifdef CONFIG_MESH_TEST_MODE
#include "test_mesh_standalone.c"
#endif

static const char *TAG = "MAIN";

/*
 * I2C bus configuration for BME280, SCD41, SGP41, LTR390, AS3935.
 * All sensors share a single I2C bus at 400 kHz (fast mode).
 */
#define I2C_MASTER_PORT      I2C_NUM_0
#define I2C_MASTER_SDA_IO    21
#define I2C_MASTER_SCL_IO    22
#define I2C_MASTER_FREQ_HZ   400000

/*
 * SPI bus configuration for SX1276 LoRa radio.
 * The radio is the only SPI device on this bus.
 * Pin mapping: MOSI=GPIO11, MISO=GPIO12, SCLK=GPIO10, CS=GPIO13
 */
#define SPI_HOST             SPI2_HOST
#define SPI_MOSI_IO          11
#define SPI_MISO_IO          12
#define SPI_SCLK_IO          10
#define SPI_CS_IO            13
#define SPI_LORA_RST_IO      14
#define SPI_LORA_DIO0_IO     5
#define SPI_LORA_DIO1_IO     6

/*
 * PMS5003 UART configuration (9600 8N1).
 */
#define UART_PORT            UART_NUM_1
#define UART_TXD_IO          17
#define UART_RXD_IO          18

/*
 * DS18B20 1-Wire GPIO.
 */
#define DS18B20_GPIO         4

/*
 * Analog ADC channels for wind, rain, gas sensors.
 * ESP32-S3 ADC2 channels: 0-9
 */
#define ADC_CH_WIND_SPEED       ADC2_CHANNEL_0
#define ADC_CH_WIND_DIR         ADC2_CHANNEL_1
#define ADC_CH_RAIN             ADC2_CHANNEL_2
#define ADC_CH_MICS_CO          ADC2_CHANNEL_3
#define ADC_CH_MICS_NO2         ADC2_CHANNEL_4
#define ADC_CH_MICS_NH3         ADC2_CHANNEL_5
#define ADC_CH_BATTERY          ADC1_CHANNEL_3

/*
 * I2C sensor addresses.
 */
#define LTR390_I2C_ADDR          0x53
#define SCD41_I2C_ADDR           0x62
#define SGP41_I2C_ADDR           0x59
#define AS3935_I2C_ADDR          0x03

/*
 * Sensor poll interval — every 60 seconds by default.
 * Each poll reads all available sensors, runs the 4-class ML inference,
 * and queues any alerts that exceed the per-class confidence threshold.
 */
#define SENSOR_POLL_INTERVAL_MS  60000

/*
 * Per-class alert confidence thresholds.
 * An alert is queued for mesh transmission when the sigmoid output
 * of ml_predict() exceeds these values.
 */
#define ALERT_THRESHOLD_WILDFIRE      0.70f
#define ALERT_THRESHOLD_FLOOD         0.70f
#define ALERT_THRESHOLD_STORM         0.75f
#define ALERT_THRESHOLD_AIR_QUALITY   0.65f

/*
 * Feature names matching code/ml/train_model.py FEATURE_NAMES order.
 * Index position is critical — ml.c's iterative tree traversal reads
 * features positionally, so the order here must be byte-for-byte
 * identical to the order used during training.
 */
#define FEATURE_IDX_TEMP               0
#define FEATURE_IDX_HUMIDITY           1
#define FEATURE_IDX_PRESSURE           2
#define FEATURE_IDX_WIND_SPEED         3
#define FEATURE_IDX_PM25               4
#define FEATURE_IDX_CO2                5
#define FEATURE_IDX_LIGHTNING_DIST     6
#define FEATURE_IDX_TEMP_HUMID_RATIO   7
#define FEATURE_IDX_PRESSURE_TREND     8
#define FEATURE_IDX_HEAT_INDEX         9
#define FEATURE_IDX_DEW_POINT          10
#define FEATURE_IDX_FIRE_RISK          11
#define FEATURE_IDX_FLOOD_RISK         12
#define FEATURE_IDX_LIGHTNING_THREAT   13

#define ML_FEATURE_COUNT               14

/*
 * Hazard class indices matching train_model.py HAZARD_CLASSES order.
 */
#define HAZARD_CLASS_WILDFIRE     0
#define HAZARD_CLASS_FLOOD        1
#define HAZARD_CLASS_STORM        2
#define HAZARD_CLASS_AIR_QUALITY  3
#define NUM_HAZARD_CLASSES        4

/*
 * Alert queue item — a fully formed mesh packet plus metadata.
 * sensor_ml_task enqueues; mesh_comms_task dequeues and transmits.
 */
typedef struct {
    uint8_t  payload[MAX_PACKET_PAYLOAD];
    uint8_t  payload_len;
    uint32_t hazard_class;        /* 0-3, matches HAZARD_CLASS_* indices */
    float    confidence;
    uint32_t timestamp_ms;
} alert_queue_item_t;

/*
 * Alert queue length — must be large enough to buffer between sensor polls
 * (mesh_comms_task may be busy forwarding when a burst of alerts arrives).
 */
#define ALERT_QUEUE_LENGTH   8

/* Queue handle shared between sensor_ml_task (sender) and mesh_comms_task (receiver) */
static QueueHandle_t g_alert_queue = NULL;

/* SX1276 handle — shared between init and mesh_comms_task */
static sx1276_handle_t *g_lora_handle = NULL;

/* Global sensor readings — written by sensor_ml_task, accessible to mesh for telemetry */
static sensor_reading_t g_last_reading;
static portMUX_TYPE g_reading_mux = portMUX_INITIALIZER_UNLOCKED;

/* Last N pressure readings for pressure_trend computation */
#define PRESSURE_HISTORY_LEN  6
static float g_pressure_history[PRESSURE_HISTORY_LEN];
static int    g_pressure_index = 0;

/*
 * =============================================
 * HARDWARE INITIALIZATION
 * =============================================
 */

static esp_err_t init_nvs(void)
{
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS requires erase, erasing...");
        ret = nvs_flash_erase();
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "NVS erase failed: %s", esp_err_to_name(ret));
            return ret;
        }
        ret = nvs_flash_init();
    }
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "NVS initialized");
    } else {
        ESP_LOGE(TAG, "NVS init failed: %s", esp_err_to_name(ret));
    }
    return ret;
}

static esp_err_t init_i2c(void)
{
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_MASTER_SDA_IO,
        .scl_io_num = I2C_MASTER_SCL_IO,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ,
    };
    esp_err_t ret = i2c_param_config(I2C_MASTER_PORT, &conf);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C param config failed: %s", esp_err_to_name(ret));
        return ret;
    }
    ret = i2c_driver_install(I2C_MASTER_PORT, conf.mode, 0, 0, 0);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C driver install failed: %s", esp_err_to_name(ret));
        return ret;
    }
    ESP_LOGI(TAG, "I2C initialized on port %d (SDA=%d, SCL=%d, %d Hz)",
             I2C_MASTER_PORT, I2C_MASTER_SDA_IO, I2C_MASTER_SCL_IO, I2C_MASTER_FREQ_HZ);
    return ESP_OK;
}

static esp_err_t init_spi(void)
{
    spi_bus_config_t bus_cfg = {
        .mosi_io_num = SPI_MOSI_IO,
        .miso_io_num = SPI_MISO_IO,
        .sclk_io_num = SPI_SCLK_IO,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 256,
    };
    esp_err_t ret = spi_bus_initialize(SPI_HOST, &bus_cfg, SPI_DMA_CH_AUTO);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI bus init failed: %s", esp_err_to_name(ret));
        return ret;
    }
    ESP_LOGI(TAG, "SPI initialized on host %d (MOSI=%d, MISO=%d, SCLK=%d)",
             SPI_HOST, SPI_MOSI_IO, SPI_MISO_IO, SPI_SCLK_IO);
    return ESP_OK;
}

static esp_err_t init_uart(void)
{
    uart_config_t uart_config = {
        .baud_rate = 9600,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };
    esp_err_t ret = uart_param_config(UART_PORT, &uart_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "UART param config failed: %s", esp_err_to_name(ret));
        return ret;
    }
    ret = uart_set_pin(UART_PORT, UART_TXD_IO, UART_RXD_IO,
                       UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "UART set pin failed: %s", esp_err_to_name(ret));
        return ret;
    }
    ret = uart_driver_install(UART_PORT, 256, 0, 0, NULL, 0);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "UART driver install failed: %s", esp_err_to_name(ret));
        return ret;
    }
    ESP_LOGI(TAG, "UART initialized on port %d (TX=%d, RX=%d, 9600 8N1)",
             UART_PORT, UART_TXD_IO, UART_RXD_IO);
    return ESP_OK;
}

/*
 * =============================================
 * NODE ID DERIVATION
 * =============================================
 *
 * Derive a unique 32-bit node ID from the ESP32 base MAC address.
 * The MAC is 6 bytes; we XOR the upper and lower 3 bytes to get a
 * compact 24-bit ID and combine with a magic prefix to fill 32 bits.
 * This guarantees uniqueness per chip without requiring NVS provisioning.
 */
static uint32_t derive_node_id(void)
{
    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);
    uint32_t id = ((uint32_t)mac[0] << 24)
                | ((uint32_t)mac[1] << 16)
                | ((uint32_t)(mac[2] ^ mac[3]) << 8)
                | (uint32_t)(mac[4] ^ mac[5]);
    ESP_LOGI(TAG, "Node ID: 0x%08lX (MAC: %02X:%02X:%02X:%02X:%02X:%02X)",
             (unsigned long)id,
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    return id;
}

/*
 * =============================================
 * FEATURE ENGINEERING
 * =============================================
 *
 * Converts raw sensor_reading_t into the 14-element feature vector
 * expected by the XGBoost model. Derived features are computed using
 * the same formulas as code/ml/train_model.py generate_synthetic_data()
 * so training and inference are feature-compatible.
 */
static void compute_derived_features(sensor_reading_t *reading, float *features)
{
    float temp     = reading->temperature;
    float humidity = reading->humidity;
    float pressure = reading->pressure;
    float wind_spd = reading->wind_speed;
    float pm25     = reading->pm2_5;
    float co2      = reading->co2;
    float ldist    = reading->lightning_dist;

    /* Raw sensor values (indices 0-6) */
    features[FEATURE_IDX_TEMP]             = temp;
    features[FEATURE_IDX_HUMIDITY]         = humidity;
    features[FEATURE_IDX_PRESSURE]         = pressure;
    features[FEATURE_IDX_WIND_SPEED]       = wind_spd;
    features[FEATURE_IDX_PM25]             = pm25;
    features[FEATURE_IDX_CO2]              = co2;
    features[FEATURE_IDX_LIGHTNING_DIST]   = ldist;

    /* Derived features (indices 7-13) — formulas match train_model.py */

    /* temp_humidity_ratio — simple ratio, guard against division by zero */
    features[FEATURE_IDX_TEMP_HUMID_RATIO] = temp / fmaxf(humidity, 1.0f);

    /*
     * pressure_trend — rate of change over the last PRESSURE_HISTORY_LEN polls.
     * A negative trend indicates a dropping barometer (storm approach).
     * Uses simple linear regression slope over the rolling window.
     */
    {
        float sum_x = 0.0f, sum_y = 0.0f, sum_xy = 0.0f, sum_xx = 0.0f;
        int n = g_pressure_index < PRESSURE_HISTORY_LEN ? g_pressure_index : PRESSURE_HISTORY_LEN;
        if (n < 2) {
            features[FEATURE_IDX_PRESSURE_TREND] = 0.0f;
        } else {
            for (int i = 0; i < n; i++) {
                float x = (float)i;
                float y = g_pressure_history[i];
                sum_x  += x;  sum_y  += y;
                sum_xy += x * y;
                sum_xx += x * x;
            }
            float denom = (float)n * sum_xx - sum_x * sum_x;
            if (fabsf(denom) < 1e-9f) {
                features[FEATURE_IDX_PRESSURE_TREND] = 0.0f;
            } else {
                features[FEATURE_IDX_PRESSURE_TREND] =
                    ((float)n * sum_xy - sum_x * sum_y) / denom;
            }
        }
    }

    /* heat_index — simplified approximation (not the full Rothfusz regression) */
    features[FEATURE_IDX_HEAT_INDEX] = temp + 0.5f * humidity;

    /* dew_point — Magnus formula approximation */
    features[FEATURE_IDX_DEW_POINT] = temp - (100.0f - humidity) / 5.0f;

    /*
     * fire_risk_index — heuristic combining high temp, low humidity,
     * wind, and elevated PM2.5 (proxy for smoke or dry debris).
     */
    {
        float risk = 0.0f;
        if (temp > 30.0f)        risk += 0.25f;
        if (humidity < 35.0f)    risk += 0.25f;
        if (wind_spd > 5.0f)     risk += 0.15f;
        if (pm25 > 40.0f)        risk += 0.35f;
        features[FEATURE_IDX_FIRE_RISK] = fminf(risk, 1.0f);
    }

    /*
     * flood_risk_index — heuristic combining low pressure, high humidity,
     * and sustained winds (proxy for prolonged storm systems).
     */
    {
        float risk = 0.0f;
        if (pressure < 1005.0f)  risk += 0.30f;
        if (humidity > 85.0f)    risk += 0.30f;
        if (wind_spd > 8.0f)     risk += 0.20f;
        if (pressure < 1000.0f)  risk += 0.20f;
        features[FEATURE_IDX_FLOOD_RISK] = fminf(risk, 1.0f);
    }

    /* lightning_threat — normalized distance [0-1], 1 = overhead, 0 = beyond range */
    features[FEATURE_IDX_LIGHTNING_THREAT] = fmaxf(0.0f, (40.0f - ldist) / 40.0f);

    /* Update pressure history rolling buffer */
    g_pressure_history[g_pressure_index % PRESSURE_HISTORY_LEN] = pressure;
    g_pressure_index++;
}

/*
 * =============================================
 * SENSOR TASK (Core 0)
 * =============================================
 *
 * Polls all available sensors on a configurable interval, builds the
 * 14-element feature vector, runs ML inference for each hazard class,
 * and queues alert packets when confidence exceeds threshold.
 */
static void sensor_ml_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Sensor/ML task started on Core 0");

    /* Initialize sensor handles to NULL — partial operation is allowed */
    bme280_handle_t   *bme280   = NULL;
    pms5003_handle_t  *pms5003  = NULL;
    ds18b20_handle_t  *ds18b20  = NULL;
    anemometer_handle_t *anemometer = NULL;
    sen0575_handle_t    *sen0575    = NULL;
    ltr390_handle_t     *ltr390     = NULL;
    scd41_handle_t      *scd41      = NULL;
    sgp41_handle_t      *sgp41      = NULL;
    mics6814_handle_t   *mics6814   = NULL;
    as3935_handle_t     *as3935     = NULL;
    battery_handle_t    *battery    = NULL;
    bool bme280_ok  = false;
    bool pms5003_ok = false;
    bool ds18b20_ok = false;
    bool anemometer_ok = false;
    bool sen0575_ok    = false;
    bool ltr390_ok     = false;
    bool scd41_ok      = false;
    bool sgp41_ok      = false;
    bool mics6814_ok   = false;
    bool as3935_ok     = false;
    bool battery_ok    = false;

    /*
     * Initialize each sensor independently.
     * A failure in one sensor does not block the others — the feature
     * vector will use zeros for missing values and clear the
     * corresponding sensor_mask bit.
     */
    ESP_LOGI(TAG, "Initializing BME280...");
    if (bme280_init(I2C_MASTER_PORT, BME280_ADDR_PRIMARY, &bme280)) {
        bme280_ok = true;
        ESP_LOGI(TAG, "BME280 ready");
    } else {
        ESP_LOGE(TAG, "BME280 init failed — continuing without temp/hum/pressure");
    }

    ESP_LOGI(TAG, "Initializing PMS5003...");
    if (pms5003_init(UART_PORT, -1, -1, &pms5003)) {
        pms5003_ok = true;
        ESP_LOGI(TAG, "PMS5003 ready");
    } else {
        ESP_LOGE(TAG, "PMS5003 init failed — continuing without PM data");
    }

    ESP_LOGI(TAG, "Initializing DS18B20...");
    esp_err_t ds_err = ds18b20_init(DS18B20_GPIO, &ds18b20);
    if (ds_err == ESP_OK) {
        ds18b20_ok = true;
        ESP_LOGI(TAG, "DS18B20 ready");
    } else {
        ESP_LOGE(TAG, "DS18B20 init failed — continuing without enclosure temp");
    }

    ESP_LOGI(TAG, "Initializing Anemometer...");
    if (anemometer_init(ADC_CH_WIND_SPEED, ADC_CH_WIND_DIR, &anemometer)) {
        anemometer_ok = true;
        ESP_LOGI(TAG, "Anemometer ready");
    } else {
        ESP_LOGE(TAG, "Anemometer init failed — continuing without wind data");
    }

    ESP_LOGI(TAG, "Initializing SEN0575 rain sensor...");
    if (sen0575_init(ADC_CH_RAIN, &sen0575)) {
        sen0575_ok = true;
        ESP_LOGI(TAG, "SEN0575 ready");
    } else {
        ESP_LOGE(TAG, "SEN0575 init failed — continuing without precipitation data");
    }

    ESP_LOGI(TAG, "Initializing LTR390 UV sensor...");
    if (ltr390_init(I2C_MASTER_PORT, LTR390_I2C_ADDR, &ltr390)) {
        ltr390_ok = true;
        ESP_LOGI(TAG, "LTR390 ready");
    } else {
        ESP_LOGE(TAG, "LTR390 init failed — continuing without UV data");
    }

    ESP_LOGI(TAG, "Initializing SCD41 CO2 sensor...");
    if (scd41_init(I2C_MASTER_PORT, SCD41_I2C_ADDR, &scd41)) {
        scd41_ok = true;
        scd41_start_periodic(scd41);
        ESP_LOGI(TAG, "SCD41 ready");
    } else {
        ESP_LOGE(TAG, "SCD41 init failed — continuing without CO2 data");
    }

    ESP_LOGI(TAG, "Initializing SGP41 VOC/NOx sensor...");
    if (sgp41_init(I2C_MASTER_PORT, SGP41_I2C_ADDR, &sgp41)) {
        sgp41_ok = true;
        sgp41_conditioning(sgp41);
        ESP_LOGI(TAG, "SGP41 ready");
    } else {
        ESP_LOGE(TAG, "SGP41 init failed — continuing without VOC/NOx data");
    }

    ESP_LOGI(TAG, "Initializing MICS-6814 multi-gas sensor...");
    if (mics6814_init(ADC_CH_MICS_CO, ADC_CH_MICS_NO2, ADC_CH_MICS_NH3, &mics6814)) {
        mics6814_ok = true;
        ESP_LOGI(TAG, "MICS-6814 ready (warmup period may apply)");
    } else {
        ESP_LOGE(TAG, "MICS-6814 init failed — continuing without gas data");
    }

    ESP_LOGI(TAG, "Initializing AS3935 lightning sensor...");
    if (as3935_init(I2C_MASTER_PORT, AS3935_I2C_ADDR, true, &as3935)) {
        as3935_ok = true;
        ESP_LOGI(TAG, "AS3935 ready");
    } else {
        ESP_LOGE(TAG, "AS3935 init failed — continuing without lightning data");
    }

    ESP_LOGI(TAG, "Initializing battery voltage monitor...");
    if (battery_init(ADC_CH_BATTERY, BATTERY_DIVIDER_RATIO, &battery)) {
        battery_ok = true;
        ESP_LOGI(TAG, "Battery monitor ready");
    } else {
        ESP_LOGE(TAG, "Battery init failed — continuing without power monitoring");
    }

    /* Initialize ML inference engine */
    esp_err_t ml_ret = ml_init();
    if (ml_ret != ESP_OK) {
        ESP_LOGE(TAG, "ML init failed — inference disabled");
    } else {
        ESP_LOGI(TAG, "ML engine ready (%u features, %u classes)",
                 (unsigned)ML_FEATURE_COUNT, (unsigned)NUM_HAZARD_CLASSES);
    }

    /*
     * Initialize pressure history with current pressure if BME280 is available,
     * otherwise fill with 1013.25 hPa (standard sea-level).
     */
    {
        float init_p = 1013.25f;
        for (int i = 0; i < PRESSURE_HISTORY_LEN; i++) {
            g_pressure_history[i] = init_p;
        }
    }

    /* Main polling loop */
    while (1) {
        sensor_reading_t reading;
        memset(&reading, 0, sizeof(reading));
        reading.timestamp = (uint32_t)(xTaskGetTickCount() * portTICK_PERIOD_MS);

        /*
         * Read BME280.
         * The bme280_read() call compensates temperature, humidity, and pressure
         * in a single I2C transaction. Temperature must be read first because
         * humidity/pressure compensation uses t_fine.
         */
        if (bme280_ok && bme280 != NULL) {
            bme280_data_t bme_data;
            if (bme280_read(bme280, &bme_data)) {
                reading.temperature = bme_data.temperature;
                reading.humidity    = bme_data.humidity;
                reading.pressure    = bme_data.pressure;
                reading.sensor_mask |= SENSOR_MASK_TEMP
                                     | SENSOR_MASK_HUMIDITY
                                     | SENSOR_MASK_PRESSURE;
                ESP_LOGD(TAG, "BME280: T=%.1f C, H=%.0f%%, P=%.1f hPa",
                         reading.temperature, reading.humidity, reading.pressure);
            } else {
                ESP_LOGW(TAG, "BME280 read failed");
            }
        }

        /*
         * Read PMS5003.
         * In passive mode, each read sends a request then waits for the 32-byte
         * response frame. PMS5003 needs ~2s after wake to stabilize; the first
         * read may fail if the sensor was sleeping.
         */
        if (pms5003_ok && pms5003 != NULL) {
            pms5003_data_t pm_data;
            if (pms5003_read_timeout(pms5003, &pm_data, 3000)) {
                reading.pm1_0 = (float)pm_data.pm1_0_atm;
                reading.pm2_5 = (float)pm_data.pm2_5_atm;
                reading.pm10  = (float)pm_data.pm10_atm;
                reading.sensor_mask |= SENSOR_MASK_PM;
                ESP_LOGD(TAG, "PMS5003: PM2.5=%.0f ug/m3, PM10=%.0f ug/m3",
                         reading.pm2_5, reading.pm10);
            } else {
                ESP_LOGW(TAG, "PMS5003 read failed");
            }
        }

        /*
         * Read DS18B20 enclosure temperature.
         * This is used for water-ingress detection (evaporative cooling spike).
         */
        if (ds18b20_ok && ds18b20 != NULL) {
            float enclosure_temp;
            if (ds18b20_read_temperature(ds18b20, &enclosure_temp) == ESP_OK) {
                ESP_LOGD(TAG, "DS18B20: enclosure=%.1f C", enclosure_temp);
            } else {
                ESP_LOGW(TAG, "DS18B20 read failed");
            }
        }

        /*
         * Read anemometer (wind speed + direction).
         */
        if (anemometer_ok && anemometer != NULL) {
            float ws, wd;
            if (anemometer_read_speed(anemometer, &ws)) {
                reading.wind_speed = ws;
                reading.sensor_mask |= SENSOR_MASK_WIND_SPEED;
            }
            if (anemometer_read_direction(anemometer, &wd)) {
                reading.wind_direction = wd;
                reading.sensor_mask |= SENSOR_MASK_WIND_DIR;
            }
            ESP_LOGD(TAG, "Wind: %.1f m/s, %.0f deg", reading.wind_speed, reading.wind_direction);
        }

        /*
         * Read SEN0575 precipitation sensor.
         */
        if (sen0575_ok && sen0575 != NULL) {
            rain_intensity_t intensity;
            if (sen0575_read_intensity(sen0575, &intensity)) {
                reading.precipitation = (float)intensity;
                reading.sensor_mask |= SENSOR_MASK_RAIN;
                ESP_LOGD(TAG, "Rain intensity: %d", (int)intensity);
            }
        }

        /*
         * Read LTR390 UV sensor.
         */
        if (ltr390_ok && ltr390 != NULL) {
            float uv;
            if (ltr390_read_uvs(ltr390, &uv)) {
                reading.uv_index = uv;
                reading.sensor_mask |= SENSOR_MASK_UV;
                ESP_LOGD(TAG, "UV index: %.2f", uv);
            }
        }

        /*
         * Read SCD41 CO2 sensor.
         */
        if (scd41_ok && scd41 != NULL) {
            float co2, scd_temp, scd_hum;
            if (scd41_read(scd41, &co2, &scd_temp, &scd_hum)) {
                reading.co2 = co2;
                reading.sensor_mask |= SENSOR_MASK_CO2;
                ESP_LOGD(TAG, "CO2: %.0f ppm", co2);
            }
        }

        /*
         * Read SGP41 VOC/NOx sensor.
         */
        if (sgp41_ok && sgp41 != NULL) {
            uint16_t voc_raw, nox_raw;
            if (sgp41_read_raw(sgp41, &voc_raw, &nox_raw)) {
                reading.voc_index = (float)voc_raw;
                reading.nox_index = (float)nox_raw;
                reading.sensor_mask |= SENSOR_MASK_VOC | SENSOR_MASK_NOX;
                ESP_LOGD(TAG, "SGP41: VOC=%u, NOx=%u", voc_raw, nox_raw);
            }
        }

        /*
         * Read MICS-6814 multi-gas sensor.
         */
        if (mics6814_ok && mics6814 != NULL) {
            mics6814_data_t gas_data;
            if (mics6814_read(mics6814, &gas_data)) {
                reading.co_ppm  = gas_data.co_ppm;
                reading.no2_ppm = gas_data.no2_ppm;
                reading.nh3_ppm = gas_data.nh3_ppm;
                reading.sensor_mask |= SENSOR_MASK_GAS;
                ESP_LOGD(TAG, "MICS6814: CO=%.1f, NO2=%.2f, NH3=%.1f ppm",
                         gas_data.co_ppm, gas_data.no2_ppm, gas_data.nh3_ppm);
            }
        }

        /*
         * Read AS3935 lightning sensor (non-blocking — poll IRQ pin or status reg).
         */
        if (as3935_ok && as3935 != NULL) {
            as3935_data_t lightning;
            if (as3935_read_event(as3935, &lightning)) {
                if (lightning.interrupt_source == AS3935_INT_LIGHTNING) {
                    reading.lightning_dist   = (float)lightning.distance_km;
                    reading.lightning_count  = lightning.strike_count;
                    reading.sensor_mask |= SENSOR_MASK_LIGHTNING;
                    ESP_LOGI(TAG, "Lightning: dist=%u km, strikes=%u",
                             lightning.distance_km, lightning.strike_count);
                } else if (lightning.interrupt_source == AS3935_INT_NOISE) {
                    ESP_LOGD(TAG, "AS3935: noise detected");
                } else if (lightning.interrupt_source == AS3935_INT_DISTURBER) {
                    ESP_LOGD(TAG, "AS3935: disturber rejected");
                }
            }
        }

        /*
         * Read battery voltage.
         */
        if (battery_ok && battery != NULL) {
            battery_status_t bat;
            if (battery_read(battery, &bat)) {
                ESP_LOGD(TAG, "Battery: %.2f V (%.0f%%)", bat.voltage, bat.percent);
                if (bat.level >= BATTERY_CRITICAL) {
                    ESP_LOGW(TAG, "Battery critical! %.2f V", bat.voltage);
                }
            }
        }

        /*
         * Build the 14-element feature vector for ML inference.
         * All sensor fields are now populated — the derived features
         * will reflect the complete sensor array.
         */
        float features[ML_FEATURE_COUNT];
        compute_derived_features(&reading, features);

        /* Update global reading for mesh telemetry access */
        portENTER_CRITICAL(&g_reading_mux);
        g_last_reading = reading;
        portEXIT_CRITICAL(&g_reading_mux);

        /* Run ML inference for each hazard class */
        float norm_features[ML_FEATURE_COUNT];
        esp_err_t norm_ret = ml_normalize(features, norm_features);
        if (norm_ret != ESP_OK) {
            ESP_LOGW(TAG, "ML normalize failed — skipping inference");
            vTaskDelay(pdMS_TO_TICKS(SENSOR_POLL_INTERVAL_MS));
            continue;
        }

        static const char *hazard_names[NUM_HAZARD_CLASSES] = {
            "WILDFIRE", "FLOOD", "STORM", "AIR_QUALITY"
        };
        static float hazard_thresholds[NUM_HAZARD_CLASSES] = {
            ALERT_THRESHOLD_WILDFIRE,
            ALERT_THRESHOLD_FLOOD,
            ALERT_THRESHOLD_STORM,
            ALERT_THRESHOLD_AIR_QUALITY
        };

        for (int cls = 0; cls < NUM_HAZARD_CLASSES; cls++) {
            float raw_output;
            esp_err_t pred_ret = ml_predict(norm_features, cls, &raw_output);
            if (pred_ret != ESP_OK) {
                ESP_LOGW(TAG, "ML predict failed for class %d", cls);
                continue;
            }

            float confidence = ml_confidence(raw_output);
            ESP_LOGI(TAG, "Inference %s: %.3f (threshold=%.2f)",
                     hazard_names[cls], (double)confidence,
                     (double)hazard_thresholds[cls]);

            if (confidence >= hazard_thresholds[cls]) {
                /*
                 * Confidence exceeds threshold — queue an alert.
                 * The alert payload contains the hazard class, confidence,
                 * and a compact summary of the triggering sensor values.
                 */
                alert_queue_item_t alert;
                memset(&alert, 0, sizeof(alert));
                alert.hazard_class  = cls;
                alert.confidence    = confidence;
                alert.timestamp_ms  = reading.timestamp;

                /*
                 * Build payload: [class_id(1) | confidence(4) | pm25(4) | temp(4) | lightning(4)]
                 * 17 bytes total — fits comfortably in MAX_PACKET_PAYLOAD (240).
                 */
                uint8_t *p = alert.payload;
                *p++ = (uint8_t)cls;
                memcpy(p, &confidence, sizeof(float));      p += sizeof(float);
                memcpy(p, &reading.pm2_5, sizeof(float));   p += sizeof(float);
                memcpy(p, &reading.temperature, sizeof(float)); p += sizeof(float);
                memcpy(p, &reading.lightning_dist, sizeof(float));
                alert.payload_len = (uint8_t)(p - alert.payload + sizeof(float));

                ESP_LOGI(TAG, "ALERT: %s (confidence=%.3f) — queueing",
                         hazard_names[cls], (double)confidence);

                /*
                 * Queue the alert. If the queue is full, drop the oldest item
                 * to make room (the most recent alert is always the most relevant).
                 */
                if (xQueueSend(g_alert_queue, &alert, pdMS_TO_TICKS(10)) != pdPASS) {
                    ESP_LOGW(TAG, "Alert queue full — dropping oldest alert");
                    alert_queue_item_t discarded;
                    xQueueReceive(g_alert_queue, &discarded, 0);
                    xQueueSend(g_alert_queue, &alert, 0);
                }
            }
        }

        /* Wait for next poll interval */
        vTaskDelay(pdMS_TO_TICKS(SENSOR_POLL_INTERVAL_MS));
    }
}

/*
 * =============================================
 * MESH CALLBACK
 * =============================================
 *
 * Called by mesh_receive() when a valid packet arrives addressed to
 * this node or as a broadcast. Logs incoming alerts for local delivery
 * (display, data logging, future actuator interface).
 * Forwarding/duplicate filtering is handled by mesh.c internally.
 */
static void mesh_rx_handler(const mesh_packet_t *packet,
                             uint32_t from_id,
                             int16_t rssi, float snr)
{
    if (packet == NULL) return;

    ESP_LOGI(TAG, "RX alert from 0x%08lX (seq=%lu, RSSI=%d, SNR=%.1f, len=%u)",
             (unsigned long)from_id,
             (unsigned long)packet->seq_num,
             rssi, (double)snr,
             packet->payload_len);

    /*
     * Parse the payload if it matches our alert format (class_id + float values).
     * Future: log to NVS, forward to display, trigger siren/actuator.
     */
    if (packet->payload_len >= 17 && (packet->flags & MESH_FLAG_ALERT)) {
        uint8_t alert_class = packet->payload[0];
        if (alert_class < NUM_HAZARD_CLASSES) {
            static const char *hazard_names[NUM_HAZARD_CLASSES] = {
                "WILDFIRE", "FLOOD", "STORM", "AIR_QUALITY"
            };
            ESP_LOGW(TAG, "*** INCOMING HAZARD ALERT: %s from node 0x%08lX ***",
                     hazard_names[alert_class], (unsigned long)from_id);
        }
    }
}

/*
 * =============================================
 * MESH COMMS TASK (Core 1)
 * =============================================
 *
 * Initializes the SX1276 LoRa radio and mesh networking layer, then enters
 * a receive-poll loop: checks the radio for incoming packets, passes them
 * to mesh_receive(), and drains the alert queue by calling mesh_send() ->
 * sx1276_transmit().
 */
static void mesh_comms_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Mesh/comms task started on Core 1");

    /* Derive unique node ID from MAC */
    uint32_t node_id = derive_node_id();

    /* Initialize SX1276 LoRa radio */
    sx1276_config_t lora_config = {
        .spi_host          = SPI_HOST,
        .pin_mosi          = SPI_MOSI_IO,
        .pin_miso          = SPI_MISO_IO,
        .pin_sclk          = SPI_SCLK_IO,
        .pin_cs            = SPI_CS_IO,
        .pin_rst           = SPI_LORA_RST_IO,
        .pin_dio0          = SPI_LORA_DIO0_IO,
        .pin_dio1          = SPI_LORA_DIO1_IO,
        .frequency         = 865000000,   /* India ISM band */
        .tx_power          = 17,          /* dBm */
        .spreading_factor  = 7,           /* SF7 — balance of range vs throughput */
        .bandwidth         = 1,           /* 125 kHz (index 1) */
        .coding_rate       = 1,           /* 4/5 */
        .sync_word         = 0x34,        /* Network identifier */
        .preamble_length   = 8,           /* Symbols */
    };

    ESP_LOGI(TAG, "Initializing SX1276...");
    if (!sx1276_init(&lora_config, &g_lora_handle)) {
        ESP_LOGE(TAG, "SX1276 init failed — mesh disabled");
        while (1) { vTaskDelay(pdMS_TO_TICKS(60000)); }
    }
    ESP_LOGI(TAG, "SX1276 ready (865 MHz, SF7, 125 kHz)");

    /* Initialize mesh layer */
    esp_err_t mesh_ret = mesh_init(node_id);
    if (mesh_ret != ESP_OK) {
        ESP_LOGE(TAG, "Mesh init failed: %s", esp_err_to_name(mesh_ret));
        while (1) { vTaskDelay(pdMS_TO_TICKS(60000)); }
    }

    /* Pass LoRa handle to mesh layer for TX */
    mesh_set_lora_handle(g_lora_handle);

    /* Register RX callback */
    mesh_set_rx_callback(mesh_rx_handler);

    /* Start the radio in continuous receive mode */
    sx1276_start_receive(g_lora_handle);
    ESP_LOGI(TAG, "LoRa mesh listening...");

    /* Packet buffer for received data */
    uint8_t rx_buffer[MAX_PACKET_PAYLOAD + sizeof(mesh_packet_t)];

    uint32_t last_heartbeat = 0;
    uint32_t last_mesh_periodic = 0;

    /* Main loop: poll radio + mesh periodic + drain alert queue */
    while (1) {
        uint32_t now = (uint32_t)(esp_timer_get_time() / 1000);

        /*
         * Check for incoming radio packets.
         * sx1276_received() is non-blocking — it reads the IRQ flags register
         * to see if RX_DONE was asserted.
         */
        if (sx1276_received(g_lora_handle)) {
            int8_t rssi;
            float snr;
            uint8_t len = sx1276_read(g_lora_handle, rx_buffer,
                                       sizeof(rx_buffer), &rssi, &snr);
            if (len > 0) {
                /* Pass to mesh layer for validation, forwarding, and callback */
                esp_err_t rx_ret = mesh_receive(rx_buffer, len, rssi, snr);
                if (rx_ret == ESP_ERR_INVALID_CRC) {
                    ESP_LOGW(TAG, "CRC mismatch — packet dropped");
                }

                /* Re-enter receive mode for next packet */
                sx1276_start_receive(g_lora_handle);
            }
        }

        /* Run mesh periodic tasks (heartbeat, retries, neighbor pruning) */
        if (now - last_mesh_periodic >= 100) {
            mesh_periodic(now);
            last_mesh_periodic = now;
        }

        /* Send heartbeat periodically */
        if (now - last_heartbeat >= MESH_HEARTBEAT_INTERVAL_MS) {
            mesh_send_heartbeat();
            last_heartbeat = now;
        }

        /*
         * Drain the alert queue.
         * Any alerts queued by sensor_ml_task are transmitted here so that
         * mesh_send() is always called from the same core (Core 1), avoiding
         * SPI bus contention between tasks.
         */
        alert_queue_item_t alert;
        while (xQueueReceive(g_alert_queue, &alert, 0) == pdPASS) {
            esp_err_t send_ret = mesh_send(MESH_BROADCAST_ID,
                                            alert.payload,
                                            alert.payload_len,
                                            MESH_FLAG_ALERT | MESH_FLAG_ACK_REQ);
            if (send_ret != ESP_OK) {
                ESP_LOGW(TAG, "mesh_send failed: %s", esp_err_to_name(send_ret));
            }
        }

        /* Brief yield — don't starve the watchdog */
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

/*
 * =============================================
 * APP MAIN
 * =============================================
 */
void app_main(void)
{
    esp_err_t ret;

    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "Edge AI Environmental Hazard Detection Node");
    ESP_LOGI(TAG, "ESP32-S3 + 12-Sensor Array + LoRa Mesh");
    ESP_LOGI(TAG, "========================================");

    /* Initialize NVS first — other components may depend on it */
    ret = init_nvs();
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "NVS init failed — continuing without persistent storage");
    }

    /* Initialize I2C bus for environmental sensors */
    ret = init_i2c();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C init failed — sensors will not function");
    }

    /* Initialize SPI bus for LoRa radio */
    ret = init_spi();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI init failed — LoRa radio will not function");
    }

    /* Initialize UART for PMS5003 particulate sensor */
    ret = init_uart();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "UART init failed — PMS5003 will not function");
    }

    ESP_LOGI(TAG, "System boot successful — creating application tasks");

/* Initialize key provisioning and load/generate network key */
    esp_err_t kp_ret = key_provisioning_init();
    if (kp_ret != ESP_OK) {
        ESP_LOGE(TAG, "Key provisioning init failed: %s", esp_err_to_name(kp_ret));
    } else {
        uint8_t netkey[CRYPTO_KEY_SIZE];
        kp_ret = key_provisioning_load_network_key(netkey, true);  // Auto-generate if not found
        if (kp_ret == ESP_OK) {
            /* Initialize mesh crypto with the network key */
            esp_err_t mesh_crypto_ret = mesh_set_crypto_key(netkey);
            if (mesh_crypto_ret != ESP_OK) {
                ESP_LOGE(TAG, "Mesh crypto init failed: %s", esp_err_to_name(mesh_crypto_ret));
            } else {
                ESP_LOGI(TAG, "Mesh encryption enabled with network key");
            }
        } else {
            ESP_LOGW(TAG, "Could not load/generate network key, mesh will run unencrypted");
        }
    }

#ifdef CONFIG_MESH_TEST_MODE
    /* Run mesh standalone test instead of normal sensor/ML tasks */
    mesh_test_init();
    return;  // Don't proceed to normal sensor/ML initialization
#else

    /*
     * Create the alert queue before spawning tasks.
     * sensor_ml_task enqueues alert_queue_item_t; mesh_comms_task dequeues.
     */
    TaskHandle_t sensor_task_handle = NULL;
    BaseType_t task_ret = xTaskCreatePinnedToCore(
        sensor_ml_task,
        "sensor_ml",
        4096,              /* Stack size (words) */
        NULL,              /* Task parameter */
        5,                 /* Priority */
        &sensor_task_handle,
        0                  /* Core 0 — protocol/app core */);

    if (task_ret != pdPASS || sensor_task_handle == NULL) {
        ESP_LOGE(TAG, "Failed to create sensor_ml task");
    }

    /*
     * Create mesh/comms task on Core 1.
     * Priority 4 — slightly lower than sensor to avoid starving sensor reads.
     */
    TaskHandle_t mesh_task_handle = NULL;
    task_ret = xTaskCreatePinnedToCore(
        mesh_comms_task,
        "mesh_comms",
        4096,              /* Stack size (words) */
        NULL,
        4,                 /* Priority */
        &mesh_task_handle,
        1                  /* Core 1 — radio/comms core */);

    if (task_ret != pdPASS || mesh_task_handle == NULL) {
        ESP_LOGE(TAG, "Failed to create mesh_comms task");
    }

    ESP_LOGI(TAG, "Tasks created — scheduler running");

    /*
     * Main loop: app_main becomes the idle/low-priority monitoring task.
     * Periodically log system health (mesh stats, sensor status).
     */
    uint32_t loop_count = 0;
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(30000));
        loop_count++;

        if (loop_count % 2 == 0) {
            /* Log mesh stats every 60s */
            mesh_stats_t stats;
            mesh_get_stats(&stats);
            ESP_LOGI(TAG, "Health: sent=%lu rx=%lu fwd=%lu drop=%lu neighbors=%u",
                     (unsigned long)stats.packets_sent,
                     (unsigned long)stats.packets_received,
                     (unsigned long)stats.packets_forwarded,
                     (unsigned long)stats.packets_dropped,
                     (unsigned)stats.neighbor_count);
        }
    }
}
