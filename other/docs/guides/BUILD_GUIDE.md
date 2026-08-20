# Build Guide — ESP-IDF Firmware

## Prerequisites

### ESP-IDF v5.x Installation

```bash
# macOS
brew install cmake ninja dfu-util

# Linux (Ubuntu/Debian)
sudo apt-get install git wget flex bison gperf python3 python3-pip python3-venv \
    cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0

# Clone ESP-IDF
git clone -b v5.4 --recursive https://github.com/espressif/esp-idf.git ~/esp/esp-idf
cd ~/esp/esp-idf
./install.sh esp32s3
. ./export.sh
```

### Verify Installation

```bash
idf.py --version
# Should show: ESP-IDF v5.4.x
```

---

## Project Build

### 1. Configure Target

```bash
cd /path/to/Dp/firmware
idf.py set-target esp32s3
```

### 2. Menuconfig (Optional)

```bash
idf.py menuconfig
```

Key settings to verify:
- **Serial flasher config** → Default baud rate: 921600
- **Partition Table** → Custom partition table CSV
- **Compiler options** → Optimization Level: `-Os` (size)

### 3. Build

```bash
idf.py build
```

Expected output:
```
Project build complete. To flash, run this command:
/path/to/esp-idf/components/esptool_py/esptool/esptool.py -p (PORT) -b 921600 write_flash ...
```

### 4. Build Artifacts

```
build/
├── weather_station.bin          # Main app binary
├── weather_station.elf          # ELF for debugging
├── bootloader/bootloader.bin    # Bootloader
├── partition_table/partition-table.bin
└── weather_station.map          # Memory map
```

---

## Flash & Monitor

### Single Command (Flash + Monitor)

```bash
idf.py -p /dev/ttyUSB0 flash monitor
```

- **Flash**: Writes bootloader, partition table, app
- **Monitor**: Opens serial console (Ctrl+] to exit)

### Separate Commands

```bash
# Flash only
idf.py -p /dev/ttyUSB0 flash

# Monitor only
idf.py -p /dev/ttyUSB0 monitor

# Erase flash (factory reset)
idf.py -p /dev/ttyUSB0 erase_flash
```

### Common Ports

| OS | Port Pattern |
|----|--------------|
| Linux | `/dev/ttyUSB0`, `/dev/ttyACM0` |
| macOS | `/dev/tty.usbserial-*`, `/dev/tty.usbmodem-*` |
| Windows | `COM3`, `COM4`, etc. |

---

## Memory Map (partitions.csv)

| Partition | Offset | Size | Purpose |
|-----------|--------|------|---------|
| nvs | 0x9000 | 16 KB | Non-volatile storage |
| factory | 0x10000 | 3 MB | App (factory) |
| ota_0 | (future) | 3 MB | OTA slot 0 |
| ota_1 | (future) | 3 MB | OTA slot 1 |

Total flash: 8 MB (ESP32-S3-WROOM-1)

---

## Debugging

### GDB via OpenOCD

```bash
# Terminal 1: OpenOCD
openocd -f board/esp32s3-devkitc-1.cfg

# Terminal 2: GDB
riscv32-esp-elf-gdb build/weather_station.elf
(gdb) target remote :3333
(gdb) load
(gdb) continue
```

### Logging Levels

In `menuconfig` → **Component config** → **Log output**:
- Default log level: `INFO`
- Max verbosity: `DEBUG` (for development)

Component-specific levels in code:
```c
esp_log_level_set("SENSOR", ESP_LOG_DEBUG);
esp_log_level_set("MESH", ESP_LOG_INFO);
```

### JTAG Pins (ESP32-S3)

| Signal | GPIO |
|--------|------|
| TDO | 39 |
| TDI | 40 |
| TCK | 41 |
| TMS | 42 |

---

## CI/CD (GitHub Actions Example)

```yaml
# .github/workflows/build.yml
name: Build Firmware

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    container: espressif/idf:v5.4
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: |
          cd firmware
          idf.py build
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: firmware-bin
          path: firmware/build/*.bin
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `idf.py: command not found` | Run `. ./export.sh` in ESP-IDF dir |
| `Failed to connect to ESP32` | Hold BOOT, press EN, release BOOT → flash mode |
| `Partition table doesn't match` | `idf.py erase_flash` then rebuild |
| `Guru Meditation Error` | Check `CONFIG_ESP_SYSTEM_PANIC_GDBSTUB` in menuconfig |
| Slow flash | Use `-b 921600` or `-b 460800` |

---

## Size Optimization Tips

1. **Link-time optimization**: `CONFIG_COMPILER_OPTIMIZATION_SIZE=y`
2. **Strip symbols**: `CONFIG_APP_REDUCE_BIN_SIZE=y`
3. **Compress binary**: `CONFIG_ESPTOOLPY_FLASHFREQ_80M=y`
4. **Remove unused components**: Disable WiFi/BT in `sdkconfig.defaults`

---

## References

- [ESP-IDF Programming Guide](https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32s3/index.html)
- [ESP32-S3 Technical Reference Manual](https://www.espressif.com/sites/default/files/documentation/esp32-s3_technical_reference_manual_en.pdf)