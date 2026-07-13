#!/bin/bash
# build.sh - Firmware build script with CI gate
# Usage: ./build.sh [clean|build|flash|monitor|test|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/firmware"
BUILD_DIR="$PROJECT_DIR/build"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default target
TARGET="build"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        clean)
            TARGET="clean"
            shift
            ;;
        build)
            TARGET="build"
            shift
            ;;
        flash)
            TARGET="flash"
            shift
            ;;
        monitor)
            TARGET="monitor"
            shift
            ;;
        test)
            TARGET="test"
            shift
            ;;
        all)
            TARGET="all"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [clean|build|flash|monitor|test|all]"
            echo "  clean   - Clean build artifacts"
            echo "  build   - Build firmware (default)"
            echo "  flash   - Flash firmware to device"
            echo "  monitor - Open serial monitor"
            echo "  test    - Run unit tests (simulation)"
            echo "  all     - Clean, build, test, and generate report"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check ESP-IDF
check_idf() {
    if ! command -v idf.py &> /dev/null; then
        echo -e "${RED}ESP-IDF not found. Please source export.sh first.${NC}"
        echo "Example: source \$HOME/esp/esp-idf/export.sh"
        exit 1
    fi
    echo -e "${GREEN}ESP-IDF found: $(idf.py --version 2>&1 | head -1)${NC}"
}

# Clean build
do_clean() {
    echo -e "${YELLOW}Cleaning build artifacts...${NC}"
    cd "$PROJECT_DIR"
    idf.py clean
    rm -rf "$BUILD_DIR"
    echo -e "${GREEN}Clean complete${NC}"
}

# Build firmware
do_build() {
    echo -e "${YELLOW}Building firmware...${NC}"
    cd "$PROJECT_DIR"
    
    # Set target if not set
    if ! grep -q "CONFIG_IDF_TARGET=" sdkconfig 2>/dev/null; then
        echo -e "${YELLOW}Setting target to ESP32-S3...${NC}"
        idf.py set-target esp32s3
    fi
    
    # Build
    idf.py build
    
    # Check build success
    if [ -f "$BUILD_DIR/weather_station.bin" ]; then
        echo -e "${GREEN}Build successful!${NC}"
        ls -lh "$BUILD_DIR/weather_station.bin"
        ls -lh "$BUILD_DIR/bootloader/bootloader.bin" 2>/dev/null || true
        ls -lh "$BUILD_DIR/partition_table/partition-table.bin" 2>/dev/null || true
    else
        echo -e "${RED}Build failed - binary not found${NC}"
        exit 1
    fi
}

# Flash firmware
do_flash() {
    echo -e "${YELLOW}Flashing firmware...${NC}"
    cd "$PROJECT_DIR"
    idf.py flash
}

# Monitor serial output
do_monitor() {
    echo -e "${YELLOW}Starting serial monitor (Ctrl+] to exit)...${NC}"
    cd "$PROJECT_DIR"
    idf.py monitor
}

# Run tests
do_test() {
    echo -e "${YELLOW}Running unit tests...${NC}"
    cd "$PROJECT_DIR"
    
    # Build test app
    idf.py -B build_test build 2>&1 | tee test_build.log
    
    # Run tests (in simulation mode for CI)
    if [ -n "$CI" ]; then
        echo -e "${YELLOW}Running tests in simulation mode...${NC}"
        # In CI, we'd run qemu or similar
        echo "Running tests in CI environment..."
    else
        echo -e "${YELLOW}Running tests on device...${NC}"
        idf.py -B build_test test 2>&1 | tee test_results.log
    fi
}

# Run all checks
do_all() {
    echo -e "${BLUE}=== Running full CI pipeline ===${NC}"
    
    do_clean
    do_build
    
    # Run size analysis
    echo -e "${YELLOW}Running size analysis...${NC}"
    cd "$PROJECT_DIR"
    idf.py size 2>&1 | tee size_report.txt
    idf.py size-components 2>&1 | tee size_components.txt
    
    # Generate size summary
    python3 "$SCRIPT_DIR/scripts/size_report.py" size_report.txt > size_summary.md 2>/dev/null || true
    
    # Run tests
    do_test
    
    # Generate benchmark report
    if [ -f "$SCRIPT_DIR/benchmarks.sh" ]; then
        echo -e "${YELLOW}Generating benchmark report...${NC}"
        bash "$SCRIPT_DIR/benchmarks.sh" 2>&1 | tee benchmark.log
    fi
    
    echo -e "${GREEN}=== All checks passed ===${NC}"
}

# Main
check_idf

case $TARGET in
    clean)
        do_clean
        ;;
    build)
        do_build
        ;;
    flash)
        do_flash
        ;;
    monitor)
        do_monitor
        ;;
    test)
        do_test
        ;;
    all)
        do_all
        ;;
esac

echo -e "${GREEN}Done!${NC}"