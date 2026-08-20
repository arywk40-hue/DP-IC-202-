/**
 * calibration_log.c - Calibration Log Implementation
 */

#include <string.h>
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_err.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "calibration_log.h"

static const char *TAG = "CAL_LOG";

static nvs_handle_t g_nvs_handle = 0;
static uint16_t g_next_record_id = 1;
static bool g_initialized = false;

static const char *CAL_TYPE_STR[] = {
    "OFFSET", "GAIN", "LINEAR", "POLY2", "LOOKUP", "CUSTOM"
};

static const char *CAL_STATUS_STR[] = {
    "PENDING", "VERIFIED", "REJECTED", "EXPIRED"
};

esp_err_t cal_log_init(void)
{
    if (g_initialized) {
        return ESP_OK;
    }

    esp_err_t err = nvs_open(CAL_NVS_NAMESPACE, NVS_READWRITE, &g_nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(err));
        return err;
    }

    // Load next record ID
    uint32_t stored_id = 0;
    err = nvs_get_u32(g_nvs_handle, CAL_NVS_INDEX_KEY, &stored_id);
    if (err == ESP_OK) {
        g_next_record_id = (uint16_t)(stored_id + 1);
    } else if (err == ESP_ERR_NVS_NOT_FOUND) {
        g_next_record_id = 1;
    } else {
        ESP_LOGW(TAG, "Could not read index: %s", esp_err_to_name(err));
        g_next_record_id = 1;
    }

    g_initialized = true;
    ESP_LOGI(TAG, "Calibration log initialized (next ID: %u)", g_next_record_id);
    return ESP_OK;
}

static char *cal_make_key(uint16_t record_id)
{
    static char key[32];
    snprintf(key, sizeof(key), "%s%04u", CAL_NVS_RECORD_PREFIX, record_id);
    return key;
}

esp_err_t cal_log_write(const calibration_record_t *rec)
{
    if (!g_initialized) return ESP_ERR_INVALID_STATE;
    if (rec == NULL) return ESP_ERR_INVALID_ARG;

    calibration_record_t to_write = *rec;
    to_write.magic = CAL_LOG_MAGIC;
    to_write.version = 1;
    to_write.timestamp_ms = (uint32_t)(esp_timer_get_time() / 1000);

    if (to_write.record_id == 0) {
        to_write.record_id = g_next_record_id++;
    } else if (to_write.record_id >= g_next_record_id) {
        g_next_record_id = to_write.record_id + 1;
    }

    // Update index
    esp_err_t err = nvs_set_u32(g_nvs_handle, CAL_NVS_INDEX_KEY, g_next_record_id - 1);
    if (err != ESP_OK) return err;

    // Write record
    char *key = cal_make_key(to_write.record_id);
    err = nvs_set_blob(g_nvs_handle, key, &to_write, sizeof(calibration_record_t));
    if (err != ESP_OK) return err;

    err = nvs_commit(g_nvs_handle);
    if (err != ESP_OK) return err;

    ESP_LOGI(TAG, "Cal record written: ID=%u, sensor=%s, type=%s",
             to_write.record_id, to_write.sensor_name, CAL_TYPE_STR[to_write.type]);
    return ESP_OK;
}

esp_err_t cal_log_read(uint16_t record_id, calibration_record_t *rec)
{
    if (!g_initialized) return ESP_ERR_INVALID_STATE;
    if (rec == NULL) return ESP_ERR_INVALID_ARG;

    if (record_id == 0) {
        // Read latest
        for (uint16_t id = g_next_record_id; id > 0; id--) {
            char *key = cal_make_key(id);
            size_t len = sizeof(calibration_record_t);
            esp_err_t err = nvs_get_blob(g_nvs_handle, key, rec, &len);
            if (err == ESP_OK && rec->magic == CAL_LOG_MAGIC) {
                return ESP_OK;
            }
        }
        return ESP_ERR_NOT_FOUND;
    }

    char *key = cal_make_key(record_id);
    size_t len = sizeof(calibration_record_t);
    esp_err_t err = nvs_get_blob(g_nvs_handle, key, rec, &len);
    if (err != ESP_OK) return err;

    if (rec->magic != CAL_LOG_MAGIC) return ESP_ERR_INVALID_CRC;
    return ESP_OK;
}

esp_err_t cal_log_read_all(calibration_record_t *out_recs, uint16_t *out_count)
{
    if (!g_initialized) return ESP_ERR_INVALID_STATE;
    if (out_recs == NULL || out_count == NULL) return ESP_ERR_INVALID_ARG;

    uint16_t count = 0;
    for (uint16_t id = 1; id < g_next_record_id && count < CAL_NVS_MAX_RECORDS; id++) {
        calibration_record_t rec;
        char *key = cal_make_key(id);
        size_t len = sizeof(calibration_record_t);
        esp_err_t err = nvs_get_blob(g_nvs_handle, key, &rec, &len);
        if (err == ESP_OK && rec.magic == CAL_LOG_MAGIC) {
            out_recs[count++] = rec;
        }
    }
    *out_count = count;
    return ESP_OK;
}

esp_err_t cal_log_delete(uint16_t record_id)
{
    if (!g_initialized) return ESP_ERR_INVALID_STATE;

    char *key = cal_make_key(record_id);
    esp_err_t err = nvs_erase_key(g_nvs_handle, key);
    if (err == ESP_OK) {
        nvs_commit(g_nvs_handle);
        ESP_LOGI(TAG, "Deleted cal record %u", record_id);
    }
    return err;
}

esp_err_t cal_log_export_csv(char *csv_buf, size_t buf_size, size_t *out_len)
{
    if (!g_initialized) return ESP_ERR_INVALID_STATE;
    if (csv_buf == NULL || out_len == NULL) return ESP_ERR_INVALID_ARG;

    calibration_record_t recs[CAL_NVS_MAX_RECORDS];
    uint16_t count = 0;
    cal_log_read_all(recs, &count);

    size_t written = 0;
    const char *header =
        "magic,version,timestamp_ms,node_id,record_id,sequence,sensor_name,type,status,"
        "param_a,param_b,param_c,ref_value,measured_value,temperature_c,humidity_pct,"
        "rms_error,max_error,num_samples,valid_from_ms,valid_until_ms,unit,notes,operator_id\n";

    if (buf_size < strlen(header) + 1) return ESP_ERR_INVALID_SIZE;
    strcpy(csv_buf, header);
    written = strlen(header);

    for (uint16_t i = 0; i < count; i++) {
        calibration_record_t *r = &recs[i];
        char line[512];
        int len = snprintf(line, sizeof(line),
            "%08lX,%lu,%lu,%08lX,%u,%u,%s,%s,%s,"
            "%.6f,%.6f,%.6f,%.6f,%.6f,%.2f,%.2f,"
            "%.6f,%.6f,%u,%lu,%lu,%s,%s,%08lX\n",
            (unsigned long)r->magic, (unsigned long)r->version,
            (unsigned long)r->timestamp_ms, (unsigned long)r->node_id,
            r->record_id, r->sequence, r->sensor_name,
            CAL_TYPE_STR[r->type], CAL_STATUS_STR[r->status],
            r->param_a, r->param_b, r->param_c,
            r->ref_value, r->measured_value, r->temperature_c, r->humidity_pct,
            r->rms_error, r->max_error, r->num_samples,
            (unsigned long)r->valid_from_ms, (unsigned long)r->valid_until_ms,
            r->unit, r->notes, (unsigned long)r->operator_id);

        if (len < 0 || written + len >= buf_size) {
            *out_len = written;
            return ESP_ERR_INVALID_SIZE;
        }
        strcpy(csv_buf + written, line);
        written += len;
    }

    *out_len = written;
    return ESP_OK;
}

esp_err_t cal_log_import_csv(const char *csv_data, size_t len, uint16_t *imported)
{
    if (!g_initialized) return ESP_ERR_INVALID_STATE;
    if (csv_data == NULL || imported == NULL) return ESP_ERR_INVALID_ARG;

    *imported = 0;
    const char *line = csv_data;
    const char *end = csv_data + len;

    // Skip header
    line = strchr(line, '\n');
    if (line == NULL) return ESP_OK;
    line++;

    while (line < end) {
        const char *line_end = strchr(line, '\n');
        if (line_end == NULL) line_end = end;
        size_t line_len = line_end - line;
        if (line_len == 0) break;

        // Simple CSV parse (18 fields expected)
        calibration_record_t rec = {0};
        rec.magic = CAL_LOG_MAGIC;
        rec.version = 1;
        rec.timestamp_ms = (uint32_t)(esp_timer_get_time() / 1000);

        int fields_parsed = sscanf(line,
            "%8lX,%lu,%lu,%8lX,%hu,%hu,%15[^,],%7[^,],%7[^,],"
            "%f,%f,%f,%f,%f,%f,%f,"
            "%f,%f,%hhu,%lu,%lu,%7[^,],%63[^,],%8lX",
            (unsigned long*)&rec.magic, (unsigned long*)&rec.version,
            (unsigned long*)&rec.timestamp_ms, (unsigned long*)&rec.node_id,
            &rec.record_id, &rec.sequence, rec.sensor_name,
            // type/status parsed as strings then mapped
            &rec.param_a, &rec.param_b, &rec.param_c,
            &rec.ref_value, &rec.measured_value, &rec.temperature_c, &rec.humidity_pct,
            &rec.rms_error, &rec.max_error, &rec.num_samples,
            (unsigned long*)&rec.valid_from_ms, (unsigned long*)&rec.valid_until_ms,
            rec.unit, rec.notes, (unsigned long*)&rec.operator_id);

        if (fields_parsed >= 18) {
            // Map type/status strings
            for (int t = 0; t < 6; t++) {
                if (strcmp(rec.notes, CAL_TYPE_STR[t]) == 0) { rec.type = t; break; }
            }
            for (int s = 0; s < 4; s++) {
                if (strcmp(rec.unit, CAL_STATUS_STR[s]) == 0) { rec.status = s; break; }
            }

            if (cal_log_write(&rec) == ESP_OK) {
                (*imported)++;
            }
        }

        line = line_end + 1;
    }

    ESP_LOGI(TAG, "Imported %u calibration records", *imported);
    return ESP_OK;
}