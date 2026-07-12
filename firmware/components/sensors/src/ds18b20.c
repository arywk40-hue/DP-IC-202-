/**
 * ds18b20.c - DS18B20 1-Wire Temperature Sensor Implementation
 *
 * Implements the Maxim Integrated DS18B20 protocol over a single GPIO pin
 * using bit-banged 1-Wire timing. All timing constants come from the
 * DS18B20 datasheet (Maxim Integrated, rev 042208).
 *
 * Key timing parameters:
 *   - Reset pulse:  480 µs low, then 480 µs release
 *   - Presence pulse: 60–240 µs (slave pulls low)
 *   - Write 1 slot:   1–15 µs low, then >60 µs release
 *   - Write 0 slot:   60–120 µs low
 *   - Read slot:      1–15 µs low, sample within 15 µs, >45 µs release
 *   - Conversion:     750 ms max at 12-bit resolution
 */

#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "ds18b20.h"

static const char *TAG = "DS18B20";

/*
 * 1-Wire timing constants in microseconds.
 * Derived from the DS18B20 datasheet Figures 12–16.
 */
#define OW_RESET_LOW_US       480
#define OW_RESET_RELEASE_US   480
#define OW_PRESENCE_WAIT_US   60
#define OW_WRITE_1_LOW_US     5
#define OW_WRITE_1_RELEASE_US 65
#define OW_WRITE_0_LOW_US     65
#define OW_READ_LOW_US        5
#define OW_READ_SAMPLE_US     10
#define OW_READ_RELEASE_US    50

/**
 * @brief Microsecond delay using ESP32 ROM function.
 * More accurate than vTaskDelay() for sub-millisecond 1-Wire timing.
 */
static inline void delay_us(uint32_t us)
{
    esp_rom_delay_us(us);
}

/**
 * @brief Set GPIO direction and level for 1-Wire operations.
 */
static inline void ow_set_output(int gpio_pin, int level)
{
    gpio_set_direction(gpio_pin, GPIO_MODE_OUTPUT_OD);
    gpio_set_level(gpio_pin, level);
}

/**
 * @brief Set GPIO to input (high-impedance) to read from the bus.
 */
static inline void ow_set_input(int gpio_pin)
{
    gpio_set_direction(gpio_pin, GPIO_MODE_INPUT);
}

/**
 * @brief Read the current bus level.
 */
static inline int ow_read_level(int gpio_pin)
{
    return gpio_get_level(gpio_pin);
}

/**
 * @brief Perform 1-Wire reset and presence detection.
 * @return true if a device responded with a presence pulse.
 */
static bool ow_reset(int gpio_pin)
{
    /* Drive bus low for 480 µs (reset pulse) */
    ow_set_output(gpio_pin, 0);
    delay_us(OW_RESET_LOW_US);

    /* Release bus and wait for presence pulse */
    ow_set_input(gpio_pin);
    delay_us(OW_PRESENCE_WAIT_US);

    /* Sample bus — presence pulse pulls low */
    bool present = (ow_read_level(gpio_pin) == 0);

    /* Wait remainder of reset sequence */
    delay_us(OW_RESET_RELEASE_US - OW_PRESENCE_WAIT_US);

    return present;
}

/**
 * @brief Write a single bit to the 1-Wire bus.
 */
static void ow_write_bit(int gpio_pin, int bit)
{
    if (bit) {
        /* Write 1: drive low for <15 µs, then release */
        ow_set_output(gpio_pin, 0);
        delay_us(OW_WRITE_1_LOW_US);
        ow_set_output(gpio_pin, 1);
        delay_us(OW_WRITE_1_RELEASE_US);
    } else {
        /* Write 0: drive low for >60 µs */
        ow_set_output(gpio_pin, 0);
        delay_us(OW_WRITE_0_LOW_US);
        ow_set_output(gpio_pin, 1);
        delay_us(OW_WRITE_1_RELEASE_US);
    }
}

/**
 * @brief Read a single bit from the 1-Wire bus.
 */
static int ow_read_bit(int gpio_pin)
{
    int bit;
    ow_set_output(gpio_pin, 0);
    delay_us(OW_READ_LOW_US);
    ow_set_input(gpio_pin);
    delay_us(OW_READ_SAMPLE_US);
    bit = ow_read_level(gpio_pin);
    delay_us(OW_READ_RELEASE_US);
    return bit;
}

/**
 * @brief Write a byte LSB-first to the 1-Wire bus.
 */
static void ow_write_byte(int gpio_pin, uint8_t byte)
{
    for (int i = 0; i < 8; i++) {
        ow_write_bit(gpio_pin, byte & 0x01);
        byte >>= 1;
    }
}

/**
 * @brief Read a byte LSB-first from the 1-Wire bus.
 */
static uint8_t ow_read_byte(int gpio_pin)
{
    uint8_t byte = 0;
    for (int i = 0; i < 8; i++) {
        byte >>= 1;
        if (ow_read_bit(gpio_pin)) {
            byte |= 0x80;
        }
    }
    return byte;
}

/* ======================== Public API ======================== */

esp_err_t ds18b20_init(int gpio_pin, ds18b20_handle_t **handle)
{
    if (handle == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    ds18b20_handle_t *dev = (ds18b20_handle_t *)calloc(1, sizeof(ds18b20_handle_t));
    if (dev == NULL) {
        return ESP_ERR_NO_MEM;
    }

    /* Configure GPIO as open-drain with pull-up */
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << gpio_pin),
        .mode = GPIO_MODE_INPUT_OUTPUT_OD,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t ret = gpio_config(&io_conf);
    if (ret != ESP_OK) {
        free(dev);
        return ret;
    }

    /* Set bus high (inactive) */
    gpio_set_level(gpio_pin, 1);

    dev->gpio_pin = gpio_pin;
    dev->parasitic_power = false;

    /* Verify device presence */
    if (!ow_reset(gpio_pin)) {
        ESP_LOGW(TAG, "DS18B20 not detected on GPIO %d", gpio_pin);
        free(dev);
        return ESP_ERR_NOT_FOUND;
    }

    /* Set default 12-bit resolution */
    ret = ds18b20_set_resolution(dev, DS18B20_DEFAULT_RESOLUTION);
    if (ret != ESP_OK) {
        free(dev);
        return ret;
    }

    *handle = dev;
    ESP_LOGI(TAG, "DS18B20 initialized on GPIO %d", gpio_pin);
    return ESP_OK;
}

esp_err_t ds18b20_read_temperature(ds18b20_handle_t *handle, float *temp)
{
    if (handle == NULL || temp == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    uint8_t scratch[9];

    /* Start temperature conversion */
    if (!ow_reset(handle->gpio_pin)) {
        return ESP_ERR_NOT_FOUND;
    }
    ow_write_byte(handle->gpio_pin, 0xCC);          /* Skip ROM (single device) */
    ow_write_byte(handle->gpio_pin, DS18B20_CMD_CONVERT_T);

    /* Wait for conversion (12-bit = 750 ms max) */
    vTaskDelay(pdMS_TO_TICKS(750));

    /* Read scratchpad */
    if (!ow_reset(handle->gpio_pin)) {
        return ESP_ERR_NOT_FOUND;
    }
    ow_write_byte(handle->gpio_pin, 0xCC);          /* Skip ROM */
    ow_write_byte(handle->gpio_pin, DS18B20_CMD_READ_SCRATCH);

    for (int i = 0; i < 9; i++) {
        scratch[i] = ow_read_byte(handle->gpio_pin);
    }

    /* Combine raw temperature (12-bit signed) */
    int16_t raw = (int16_t)((scratch[DS18B20_SCRATCH_TEMP_MSB] << 8)
                            | scratch[DS18B20_SCRATCH_TEMP_LSB]);

    /* Convert to Celsius (resolution is 0.0625 °C per LSB) */
    *temp = raw * 0.0625f;

    ESP_LOGD(TAG, "Temperature: %.2f °C", (double)*temp);
    return ESP_OK;
}

esp_err_t ds18b20_read_scratchpad(ds18b20_handle_t *handle, uint8_t *scratch)
{
    if (handle == NULL || scratch == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    if (!ow_reset(handle->gpio_pin)) {
        return ESP_ERR_NOT_FOUND;
    }
    ow_write_byte(handle->gpio_pin, 0xCC);          /* Skip ROM */
    ow_write_byte(handle->gpio_pin, DS18B20_CMD_READ_SCRATCH);

    for (int i = 0; i < 9; i++) {
        scratch[i] = ow_read_byte(handle->gpio_pin);
    }

    return ESP_OK;
}

esp_err_t ds18b20_set_resolution(ds18b20_handle_t *handle, uint8_t resolution)
{
    if (handle == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    /* Write scratchpad (TH, TL, config) */
    if (!ow_reset(handle->gpio_pin)) {
        return ESP_ERR_NOT_FOUND;
    }
    ow_write_byte(handle->gpio_pin, 0xCC);          /* Skip ROM */
    ow_write_byte(handle->gpio_pin, DS18B20_CMD_WRITE_SCRATCH);
    ow_write_byte(handle->gpio_pin, 0x7F);          /* TH register (user register, unused) */
    ow_write_byte(handle->gpio_pin, 0x7F);          /* TL register (user register, unused) */
    ow_write_byte(handle->gpio_pin, resolution);    /* Config register */

    /* Copy scratchpad to EEPROM */
    if (!ow_reset(handle->gpio_pin)) {
        return ESP_ERR_NOT_FOUND;
    }
    ow_write_byte(handle->gpio_pin, 0xCC);          /* Skip ROM */
    ow_write_byte(handle->gpio_pin, DS18B20_CMD_COPY_SCRATCH);
    vTaskDelay(pdMS_TO_TICKS(10));                  /* EEPROM write time */

    return ESP_OK;
}

bool ds18b20_detect(int gpio_pin)
{
    /* Temporary GPIO config for detection */
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << gpio_pin),
        .mode = GPIO_MODE_INPUT_OUTPUT_OD,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);
    gpio_set_level(gpio_pin, 1);

    return ow_reset(gpio_pin);
}
