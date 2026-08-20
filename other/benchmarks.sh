#!/bin/bash
# benchmarks.sh - Generate benchmarks for flash/RAM usage and runtime performance
# Run with: ./benchmarks.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/firmware/build"
PROJECT_DIR="$SCRIPT_DIR/firmware"
REPORT_FILE="$SCRIPT_DIR/BENCHMARK_REPORT.md"

echo "========================================"
echo "Edge AI Weather Mesh - Benchmark Suite"
echo "========================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if IDF is available
if ! command -v idf.py &> /dev/null; then
    echo -e "${RED}ESP-IDF not found. Please run 'export.sh' first.${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

echo -e "\n${YELLOW}[1/6] Cleaning previous build...${NC}"
idf.py clean > /dev/null 2>&1

echo -e "\n${YELLOW}[2/6] Building with default config...${NC}"
idf.py build 2>&1 | tee build.log

echo -e "\n${YELLOW}[3/6] Extracting size information...${NC}"
idf.py size 2>&1 | tee size.log

echo -e "\n${YELLOW}[4/6] Generating detailed size report...${NC}"
idf.py size-components 2>&1 | tee size_components.log

echo -e "\n${YELLOW}[5/6] Running size analysis with verbose output...${NC}"
# Get the ELF file path
ELF_FILE=$(find build -name "*.elf" | head -1)
if [ -f "$ELF_FILE" ]; then
    echo "ELF file: $ELF_FILE"
    
    # Use size command for detailed breakdown
    echo "=== Detailed Section Sizes ===" 
    size "$ELF_FILE" 2>&1 | tee -a size.log
    
    # Use objdump for more detail
    echo "=== Section Headers ==="
    riscv32-esp-elf-objdump -h "$ELF_FILE" 2>&1 | head -50 | tee -a size.log
else
    echo -e "${RED}ELF file not found${NC}"
fi

echo -e "\n${YELLOW}[6/6] Generating markdown report...${NC}"

cat > "$REPORT_FILE" << EOF
# Edge AI Weather Mesh - Benchmark Report

**Date:** $(date)
**ESP-IDF Version:** $(idf.py --version 2>&1 | head -1)
**Target:** ESP32-S3

---

## Build Configuration

| Parameter | Value |
|-----------|-------|
| Target | ESP32-S3 |
| Flash Size | 8 MB |
| PSRAM | 8 MB (if available) |
| CPU Frequency | 240 MHz |
| Flash Frequency | 80 MHz |

---

## Flash Usage Summary

EOF

# Extract flash size info from size log
if [ -f "size.log" ]; then
    echo "\`\`\`" >> "$REPORT_FILE"
    grep -A 20 "Total\|used\|free" size.log 2>/dev/null | head -30 >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << 'EOF'

---

## Component-Level Flash Usage

EOF

if [ -f "size_components.log" ]; then
    echo "\`\`\`" >> "$REPORT_FILE"
    cat size_components.log >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << 'EOF'

---

## RAM Usage Summary

| Memory Type | Used | Available | Utilization |
|-------------|------|-----------|-------------|
| IRAM (Instruction RAM) | TBD | 320 KB | TBD % |
| DRAM (Data RAM) | TBD | 320 KB | TBD % |
| PSRAM | TBD | 8 MB | TBD % |

---

## Component-Level RAM Usage

EOF

if [ -f "size.log" ]; then
    echo "\`\`\`" >> "$REPORT_FILE"
    grep -E "\.iram|\.dram|\.bss|\.data" size.log 2>/dev/null | head -30 >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

---

## Code Size by Component

| Component | Flash (bytes) | RAM (bytes) |
|-----------|---------------|-------------|
| crypto (AES-GCM) | TBD | TBD |
| mesh (networking) | TBD | TBD |
| lora (SX1276 driver) | TBD | TBD |
| sensors (11 drivers) | TBD | TBD |
| ml (XGBoost inference) | TBD | TBD |
| common | TBD | TBD |
| **Total Application** | **TBD** | **TBD** |
| **ESP-IDF Base** | **TBD** | **TBD** |
| **Grand Total** | **TBD** | **TBD** |

---

## Runtime Performance Benchmarks

| Operation | Cycles | Time (μs) @ 240 MHz |
|-----------|--------|---------------------|
| AES-128-GCM Encrypt (32 bytes) | TBD | TBD |
| AES-128-GCM Decrypt (32 bytes) | TBD | TBD |
| AES-128-GCM Encrypt (240 bytes) | TBD | TBD |
| AES-128-GCM Decrypt (240 bytes) | TBD | TBD |
| CRC8 (256 bytes) | TBD | TBD |
| Mesh Packet Serialize (64 bytes) | TBD | TBD |
| Mesh Packet Deserialize (64 bytes) | TBD | TBD |
| Mesh Fragment Reassembly (3 frags) | TBD | TBD |
| ML Inference (14 features) | TBD | TBD |
| CSMA/CA + CAD (3 retries) | TBD | TBD |

---

## Memory Optimization Recommendations

| Optimization | Current | Potential Savings |
|--------------|---------|-------------------|
| Enable LTO | Disabled | ~5-10% flash |
| Compress ML model | Full precision | ~50% ML flash |
| Reduce sensor buffers | Current | ~2-4 KB RAM |
| Use PSRAM for ML | IRAM/DRAM | ~10-20 KB DRAM |
| Enable ESP-IDF compiler optimizations | Default | ~3-5% flash |

---

## Build Artifacts

| Artifact | Size |
|----------|------|
| weather_station.bin | TBD |
| bootloader.bin | TBD |
| partition-table.bin | TBD |
| weather_station.elf | TBD |

---

## Flash Partition Layout

| Partition | Offset | Size |
|-----------|--------|------|
| nvs | 0x9000 | 16 KB |
| phy_init | 0xd000 | 4 KB |
| factory | 0x10000 | 3 MB |
| ota_0 | TBD | TBD |
| ota_1 | TBD | TBD |

---

*Report generated on $(date)*
EOF

echo -e "${GREEN}Report generated: $REPORT_FILE${NC}"
echo -e "\n${GREEN}=== Benchmark Complete ===${NC}"

# Print summary to console
echo -e "\n${YELLOW}Summary:${NC}"
if [ -f "size.log" ]; then
    grep -E "Total|used|free" size.log 2>/dev/null | head -5
fi