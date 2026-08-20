# Flashing & Debugging Guide

## Quick Flash Commands

```bash
cd ../../firmware/       # from other/docs/guides/ into other/firmware/

# Full flash + monitor (most common)
idf.py -p /dev/ttyUSB0 flash monitor

# Flash only
idf.py -p /dev/ttyUSB0 flash

# Monitor only (after flash)
idf.py -p /dev/ttyUSB0 monitor

# Erase entire flash (factory reset)
idf.py -p /dev/ttyUSB0 erase_flash
```

---

## Boot Modes

| Mode | GPIO0 | EN (Reset) | Use Case |
|------|-------|------------|----------|
| Normal boot | High (1) | Press/release | Normal operation |
| **Flash/download** | **Low (0)** | **Press/release** | **Flash firmware** |
| USB-JTAG | High | — | Debug via OpenOCD |

**To enter flash mode**: Hold BOOT button, press/release EN, release BOOT.

---

## Port Detection

### Linux
```bash
ls /dev/ttyUSB* /dev/ttyACM*
# Typically /dev/ttyUSB0
```

### macOS
```bash
ls /dev/tty.usbserial-* /dev/tty.usbmodem*
# Typically /dev/tty.usbserial-XXXX or /dev/tty.usbmodemXXXX
```

### Windows
```powershell
# Device Manager → Ports (COM & LPT)
# Typically COM3, COM4, etc.
```

---

## Flash Options

```bash
# Specify port explicitly
idf.py -p /dev/ttyUSB0 flash

# Custom baud rate (faster)
idf.py -p /dev/ttyUSB0 -b 921600 flash

# Flash specific partition
idf.py -p /dev/ttyUSB0 flash bootloader
idf.py -p /dev/ttyUSB0 flash partition-table
idf.py -p /dev/ttyUSB0 flash app

# Force flash mode (DIO/QIO)
idf.py -p /dev/ttyUSB0 --flash-mode dio flash
```

---

## Monitor Usage

```bash
# Start monitor (Ctrl+] to exit)
idf.py -p /dev/ttyUSB0 monitor

# Monitor with custom baud
idf.py -p /dev/ttyUSB0 -b 115200 monitor

# Monitor with timestamps
idf.py -p /dev/ttyUSB0 monitor --print-filter "tag1=I tag2=W"
```

### Monitor Keybindings

| Key | Action |
|-----|--------|
| `Ctrl+]` | Exit monitor |
| `Ctrl+T` | Menu (toggle timestamps, etc.) |
| `Ctrl+H` | Help |
| `Ctrl+R` | Reset target |

---

## Common Issues & Fixes

### "Failed to connect to ESP32-S3"

```bash
# 1. Check port
ls /dev/ttyUSB*

# 2. Ensure correct boot mode
# Hold BOOT, press EN, release BOOT

# 3. Try lower baud
idf.py -p /dev/ttyUSB0 -b 115200 flash

# 4. Erase flash first
idf.py -p /dev/ttyUSB0 erase_flash
idf.py -p /dev/ttyUSB0 flash
```

### "Invalid head of packet" / "Timed out waiting for packet header"

- USB cable issue → try different cable (data + power)
- Port conflict → close other serial monitors
- Wrong chip → ensure `idf.py set-target esp32s3`

### "Partition table doesn't match"

```bash
idf.py -p /dev/ttyUSB0 erase_flash
idf.py -p /dev/ttyUSB0 flash
```

### Slow Flash Speed

```bash
# Use higher baud (if stable)
idf.py -p /dev/ttyUSB0 -b 921600 flash

# Or use DIO mode
idf.py -p /dev/ttyUSB0 --flash-mode dio flash
```

---

## Advanced: OpenOCD + GDB Debugging

### Hardware Required

- ESP-Prog or FT2232H/FT232H breakout
- Connect JTAG pins:

| JTAG | ESP32-S3 GPIO |
|------|---------------|
| TCK | 41 |
| TMS | 42 |
| TDI | 40 |
| TDO | 39 |
| GND | GND |

### OpenOCD Config (`openocd.cfg`)

```cfg
source [find interface/ftdi/esp32_devkitj_v1.cfg]
source [find target/esp32s3.cfg]
adapter speed 5000
```

### Debug Session

```bash
# Terminal 1: OpenOCD
openocd -f openocd.cfg

# Terminal 2: GDB
riscv32-esp-elf-gdb build/weather_station.elf
(gdb) target remote :3333
(gdb) load
(gdb) monitor reset halt
(gdb) break sensor_ml_task
(gdb) continue
```

### Useful GDB Commands

```gdb
info threads          # List FreeRTOS tasks
thread apply all bt   # Backtrace all tasks
break mesh_receive    # Break on mesh RX
watch g_mesh.stats.packets_dropped  # Watch variable
```

---

## Logging & Diagnostics

### Enable Verbose Logging

In `menuconfig`:
```
Component config → Log output
  → Default log verbosity: DEBUG
  → Maximum verbosity: DEBUG
```

### Component-Specific Logging

```c
// In code
esp_log_level_set("SENSOR", ESP_LOG_DEBUG);
esp_log_level_set("MESH", ESP_LOG_VERBOSE);
esp_log_level_set("ML", ESP_LOG_INFO);
```

### Runtime Log Control

```bash
# In monitor
esp_log_level_set("*", ESP_LOG_DEBUG)  # All debug
esp_log_level_set("WIFI", ESP_LOG_NONE)  # Silence WiFi
```

---

## Memory Analysis

### Heap Info

```c
// In code
ESP_LOGI("HEAP", "Free: %lu, Min: %lu", 
         esp_get_free_heap_size(), 
         esp_get_minimum_free_heap_size());
```

### Task Stack Watermark

```c
UBaseType_t hwm = uxTaskGetStackHighWaterMark(NULL);
ESP_LOGI("TASK", "Stack high water mark: %u bytes", hwm * 4);
```

### Build Size Analysis

```bash
idf.py size
idf.py size-components
idf.py size-files
```

---

## OTA Updates (Future)

### Partition Table for OTA

```csv
# partitions_ota.csv
nvs,      data, nvs,     0x9000,  0x4000,
otadata,  data, ota,     0xd000,  0x2000,
factory,  app,  factory, 0x10000, 0x1E0000,
ota_0,    app,  ota_0,   0x1F0000, 0x1E0000,
ota_1,    app,  ota_1,   0x3D0000, 0x1E0000,
```

### OTA Process

1. Build: `idf.py build`
2. Host binary: `build/weather_station.bin`
3. ESP32 downloads → writes to `ota_0` or `ota_1`
4. Sets `otadata` → reboots into new app

---

## References

- [ESP-IDF Flash Encryption](https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32s3/security/flash-encryption.html)
- [ESP-IDF Secure Boot](https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32s3/security/secure-boot-v2.html)
- [OpenOCD for ESP32](https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32s3/api-guides/jtag-debugging/index.html)