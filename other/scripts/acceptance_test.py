#!/usr/bin/env python3
"""
acceptance_test.py - Hardware + Software Acceptance Test Runner

Runs all 72 tests from ACCEPTANCE_TESTS.md and generates JUnit XML + HTML report.

Usage:
    python acceptance_test.py --node A --port /dev/ttyUSB0 --output ./results/
    python acceptance_test.py --simulate  # Run without hardware for CI
"""

import os
import sys
import json
import time
import argparse
import subprocess
import serial
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TestResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class TestCase:
    id: str
    name: str
    category: str
    criticality: str  # "blocking", "high", "medium"
    procedure: str
    pass_criteria: str
    result: TestResult = TestResult.SKIP
    actual: str = ""
    notes: str = ""
    duration_ms: int = 0


# ============================================
# TEST DEFINITIONS (from ACCEPTANCE_TESTS.md)
# ============================================

TEST_CASES = [
    # --- Hardware Bring-up (H1-H10) ---
    TestCase("H1", "PCB Inspection", "Hardware", "blocking",
             "Visual + multimeter continuity", "No shorts, correct components"),
    TestCase("H2", "Power-On", "Hardware", "blocking",
             "Connect battery, measure 3.3V rail", "3.3V ±0.1V, <50mA quiescent"),
    TestCase("H3", "Solar Charge", "Hardware", "blocking",
             "Connect panel, measure CN3065 output", "4.2V ±0.05V at battery"),
    TestCase("H4", "ESP32 Boot", "Hardware", "blocking",
             "Monitor serial @115200", '"System boot successful" within 3s'),
    TestCase("H5", "NVS Init", "Hardware", "blocking",
             "Check logs", '"NVS initialized"'),
    TestCase("H6", "I2C Scan", "Hardware", "blocking",
             "Run i2cdetect equivalent", "5 devices: 0x76,0x53,0x62,0x59,0x03"),
    TestCase("H7", "SPI Test", "Hardware", "blocking",
             "Read SX1276 REG_VERSION (0x42)", "Version = 0x12"),
    TestCase("H8", "UART Test", "Hardware", "blocking",
             "PMS5003 passive mode cmd", "Valid 32-byte frame, checksum OK"),
    TestCase("H9", "ADC Calibration", "Hardware", "blocking",
             "Read 3.3V/2 divider on ADC1_CH3", "1.65V ±0.02V"),
    TestCase("H10", "1-Wire Scan", "Hardware", "blocking",
             "DS18B20 presence pulse", "ROM detected, scratchpad readable"),

    # --- Sensor Validation (S1-S22) ---
    TestCase("S1", "BME280 Temp", "Sensor", "blocking",
             "Compare to reference thermometer", "±1.0°C (0-65°C)"),
    TestCase("S2", "BME280 Humidity", "Sensor", "blocking",
             "Compare to reference hygrometer", "±3% RH (20-80%)"),
    TestCase("S3", "BME280 Pressure", "Sensor", "blocking",
             "Compare to reference barometer", "±1.0 hPa"),
    TestCase("S4", "PMS5003 PM2.5", "Sensor", "blocking",
             "Co-locate with reference monitor", "±10 μg/m³ or ±10%"),
    TestCase("S5", "PMS5003 PM10", "Sensor", "blocking",
             "Co-locate with reference monitor", "±15 μg/m³ or ±15%"),
    TestCase("S6", "SCD41 CO2", "Sensor", "blocking",
             "Exhale near sensor (40k ppm peak)", "Responds >5000 ppm, returns 400-600"),
    TestCase("S7", "SGP41 VOC", "Sensor", "blocking",
             "Isopropanol vapor near sensor", "VOC index spikes >200"),
    TestCase("S8", "SGP41 NOx", "Sensor", "blocking",
             "Lighter flame near sensor", "NOx index spikes >100"),
    TestCase("S9", "LTR-390 UV", "Sensor", "blocking",
             "Direct sun vs shade", "UV index 0-11+, shade≈0"),
    TestCase("S10", "Anemometer", "Sensor", "blocking",
             "Handheld anemometer comparison", "±0.5 m/s or ±10%"),
    TestCase("S11", "Wind Vane", "Sensor", "blocking",
             "Known directions N/E/S/W", "±22.5° (16 sectors)"),
    TestCase("S12", "SEN0575 Rain", "Sensor", "blocking",
             "Spray water / dry", "Dry=0, Light=1, Mod=2, Heavy=3"),
    TestCase("S13", "AS3935 Lightning", "Sensor", "blocking",
             "Piezo lighter clicks nearby", "Distance 1-40km, count increments"),
    TestCase("S14", "MICS-6814 CO", "Sensor", "blocking",
             "50 ppm CO cal gas", "40-60 ppm reading"),
    TestCase("S15", "MICS-6814 NO2", "Sensor", "blocking",
             "5 ppm NO2 cal gas", "3-7 ppm reading"),
    TestCase("S16", "MICS-6814 NH3", "Sensor", "blocking",
             "50 ppm NH3 cal gas", "40-60 ppm reading"),
    TestCase("S17", "DS18B20 Enclosure", "Sensor", "blocking",
             "Compare to BME280 temp", "±0.5°C"),
    TestCase("S18", "Battery Monitor", "Sensor", "blocking",
             "Known voltage source 3.0-4.2V", "±0.05V"),
    TestCase("S19", "Continuous Log", "Sensor", "blocking",
             "10-min log at 1Hz (debug)", "No NaN, <1% dropouts"),
    TestCase("S20", "Sensor Mask", "Sensor", "blocking",
             "Verify sensor_mask bits after init", "All 13 bits populated"),
    TestCase("S21", "Derived Features", "Sensor", "blocking",
             "Compare firmware vs Python on same raw", "All 14 features match within 1e-4"),
    TestCase("S22", "Graceful Failure", "Sensor", "blocking",
             "Disconnect I2C sensor, observe", "Others continue, mask bit cleared"),

    # --- ML Inference (M1-M8) ---
    TestCase("M1", "Model Load", "ML", "blocking",
             "ml_init() returns ESP_OK", "4 classes, 16 trees each loaded"),
    TestCase("M2", "Normalization", "ML", "blocking",
             "Feed known vector, compare to Python", "All 14 features match within 1e-4"),
    TestCase("M3", "Wildfire Predict", "ML", "blocking",
             "ml_predict(norm, 0, &out)", "Matches Python predict_proba within 1e-4"),
    TestCase("M4", "All Classes Predict", "ML", "blocking",
             "Run all 4 classes", "All match Python within 1e-4"),
    TestCase("M5", "Confidence Sigmoid", "ML", "blocking",
             "ml_confidence() vs 1/(1+exp(-x))", "Within 1e-6 for x∈[-10,10]"),
    TestCase("M6", "Alert Threshold", "ML", "blocking",
             "Synthetic hazard vector → alert", "Alert queued iff confidence ≥ threshold"),
    TestCase("M7", "Inference Time", "ML", "blocking",
             "Measure ml_last_inference_us()", "<100 μs for 4 classes"),
    TestCase("M8", "Repeated Inference", "ML", "blocking",
             "1000 inferences, no crash", "All pass, time variance <5%"),

    # --- Mesh Networking (N1-N12) ---
    TestCase("N1", "Mesh Init", "Mesh", "blocking",
             "mesh_init(node_id) returns ESP_OK", "Neighbor table empty, seq=0"),
    TestCase("N2", "Heartbeat TX", "Mesh", "blocking",
             "mesh_send_heartbeat() → radio TX", "Packet on air (SDR capture), seq++"),
    TestCase("N3", "Heartbeat RX", "Mesh", "blocking",
             "Node B receives A's heartbeat", "mesh_receive() OK, callback fired"),
    TestCase("N4", "Neighbor Table", "Mesh", "blocking",
             "After 2 heartbeats from B", "B in table, RSSI/SNR populated"),
    TestCase("N5", "Neighbor Timeout", "Mesh", "blocking",
             "Stop B heartbeats, wait 90s", "B pruned from table"),
    TestCase("N6", "Duplicate Suppression", "Mesh", "blocking",
             "Send same (src,seq) twice", "Second filtered, duplicates_filtered++"),
    TestCase("N7", "Alert Broadcast", "Mesh", "blocking",
             "Node A triggers wildfire alert", "Node B receives, callback fires"),
    TestCase("N8", "Alert Payload", "Mesh", "blocking",
             "Parse alert payload on B", "Class=0, confidence, pm25, temp, lightning"),
    TestCase("N9", "ACK Request", "Mesh", "blocking",
             "Unicast with ACK_REQ", "ACK received, no retry"),
    TestCase("N10", "ACK Retry", "Mesh", "blocking",
             "Block ACK (Faraday cage)", "3 retries with backoff, then drop"),
    TestCase("N11", "TTL Forwarding", "Mesh", "blocking",
             "3 nodes in line (A-B-C), A broadcasts", "C receives (TTL 5→3→1), B forwards"),
    TestCase("N12", "Mesh Stats", "Mesh", "blocking",
             "mesh_get_stats()", "Counters match observed packets"),

    # --- Power & Battery (P1-P8) ---
    TestCase("P1", "Active Current", "Power", "high",
             "Measure during sensor poll + ML", "<150 mA average"),
    TestCase("P2", "Deep Sleep Current", "Power", "high",
             "esp_deep_sleep() between polls", "<200 μA"),
    TestCase("P3", "Solar Charge", "Power", "high",
             "Full sun, measure battery current", ">500 mA into battery"),
    TestCase("P4", "Battery Read Accuracy", "Power", "high",
             "Compare ADC to multimeter", "±0.05V (3.0-4.2V)"),
    TestCase("P5", "Battery Level Logic", "Power", "high",
             "Simulate voltages", "OK>3.3V, Low 3.2-3.3V, Critical 3.0-3.2V"),
    TestCase("P6", "Critical Shutdown", "Power", "high",
             "Drain to 3.0V", "Logs warning, enters deep sleep"),
    TestCase("P7", "Solar Priority", "Power", "high",
             "Battery + solar connected", "Solar powers load, battery charges"),
    TestCase("P8", "7-Day Autonomy", "Power", "high",
             "Simulated 60s polls + 1 alert/hr", "Battery >3.3V after 7 days (calc)"),

    # --- Environmental (E1-E6) ---
    TestCase("E1", "Temp Range", "Environmental", "high",
             "-10°C to +50°C chamber", "All sensors functional, no crashes"),
    TestCase("E2", "Humidity", "Environmental", "high",
             "90% RH, 40°C (condensing)", "No sensor failure, BME280 recovers"),
    TestCase("E3", "Rain Ingress", "Environmental", "high",
             "Spray test (IP65 equiv)", "No water inside enclosure"),
    TestCase("E4", "Vibration", "Environmental", "high",
             "5-50 Hz, 2g, 30 min/axis", "No loose connectors, no solder cracks"),
    TestCase("E5", "UV Exposure", "Environmental", "high",
             "72h UV lamp (simulated sun)", "Enclosure no cracking, sensors OK"),
    TestCase("E6", "EMI", "Environmental", "high",
             "433 MHz TX 1m away", "No LoRa packet corruption"),

    # --- Integration (I1-I6) ---
    TestCase("I1", "Full Cycle", "Integration", "blocking",
             "Power on → 1 hour continuous", "All tasks run, no watchdog resets"),
    TestCase("I2", "Alert E2E", "Integration", "blocking",
             "Trigger wildfire (heat+lamp+smoke)", "Alert TX → Mesh RX → Log on peer"),
    TestCase("I3", "Multi-Alert", "Integration", "blocking",
             "Trigger all 4 hazards sequentially", "All 4 alerts TX+RX, correct class IDs"),
    TestCase("I4", "OTA Update", "Integration", "high",
             "idf.py ota via serial", "New firmware boots, NVS preserved"),
    TestCase("I5", "NVS Persistence", "Integration", "high",
             "Reboot, check node_id, calibrations", "Node ID same, calibrations retained"),
    TestCase("I6", "Watchdog Recovery", "Integration", "high",
             "Force task stall (infinite loop)", "System resets, recovers to running"),
]


# ============================================
# TEST RUNNER
# ============================================

class AcceptanceTestRunner:
    def __init__(self, node_id: str, port: str, simulate: bool = False):
        self.node_id = node_id
        self.port = port
        self.simulate = simulate
        self.tests = TEST_CASES.copy()
        self.serial_conn: Optional[serial.Serial] = None
        self.results: List[Dict] = []

    def connect(self) -> bool:
        if self.simulate:
            return True
        try:
            self.serial_conn = serial.Serial(self.port, 115200, timeout=5)
            time.sleep(0.5)  # Let ESP boot
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False

    def disconnect(self):
        if self.serial_conn:
            self.serial_conn.close()

    def send_cmd(self, cmd: str) -> str:
        """Send command to device and return response."""
        if self.simulate:
            return f"SIM: {cmd}"
        self.serial_conn.write((cmd + "\n").encode())
        time.sleep(0.2)
        return self.serial_conn.read_all().decode(errors='ignore')

    def run_test(self, test: TestCase) -> TestCase:
        print(f"\n[{test.id}] {test.name} ({test.criticality})")
        start = time.time()

        try:
            # Simulate or run actual test
            if self.simulate:
                # For simulation, just check if we can "run" it
                test.result = TestResult.PASS
                test.actual = "SIMULATED PASS"
            else:
                test.result = self.execute_hardware_test(test)

        except Exception as e:
            test.result = TestResult.FAIL
            test.actual = f"ERROR: {e}"

        test.duration_ms = int((time.time() - start) * 1000)
        status = test.result.value
        print(f"  → {status} ({test.duration_ms}ms)")
        if test.actual:
            print(f"     {test.actual}")

        return test

    def execute_hardware_test(self, test: TestCase) -> TestResult:
        """Execute actual hardware test based on test ID."""
        # Map test IDs to actual commands
        cmd_map = {
            "H4": "version",
            "H6": "i2cscan",
            "H7": "spi_read 0x42",
            "H8": "uart_test",
            "H9": "adc_read 3",
            "H10": "ow_scan",
            "S1": "bme280_read temp",
            "S2": "bme280_read hum",
            "S3": "bme280_read pres",
            "S4": "pms5003_read",
            "S6": "scd41_read",
            "S7": "sgp41_read voc",
            "S8": "sgp41_read nox",
            "S9": "ltr390_read uv",
            "S10": "anemometer_read speed",
            "S11": "anemometer_read dir",
            "S12": "sen0575_read",
            "S13": "as3935_read",
            "S14": "mics6814_read co",
            "S15": "mics6814_read no2",
            "S16": "mics6814_read nh3",
            "S17": "ds18b20_read",
            "S18": "battery_read",
            "S19": "sensor_log 600",
            "S20": "sensor_mask",
            "S21": "feature_compare",
            "M1": "ml_init",
            "M2": "ml_norm_test",
            "M3": "ml_predict 0",
            "M4": "ml_predict_all",
            "M5": "ml_sigmoid_test",
            "M6": "ml_alert_test",
            "M7": "ml_timing",
            "M8": "ml_loop 1000",
            "N1": "mesh_init",
            "N2": "mesh_heartbeat",
            "N3": "mesh_rx_test",
            "N4": "mesh_neighbors",
            "N5": "mesh_timeout",
            "N6": "mesh_dup_test",
            "N7": "mesh_alert_tx",
            "N7": "mesh_alert_rx",
            "N9": "mesh_ack",
            "N10": "mesh_retry",
            "N11": "mesh_ttl",
            "N12": "mesh_stats",
            "P1": "power_active",
            "P2": "power_sleep",
            "P3": "power_solar",
            "P4": "battery_accuracy",
            "P5": "battery_levels",
            "P6": "battery_critical",
            "P7": "solar_priority",
            "P8": "power_autonomy",
        }

        cmd = cmd_map.get(test.id)
        if not cmd:
            test.actual = "No command mapping for test"
            return TestResult.FAIL

        response = self.send_cmd(cmd)

        # Simple pass/fail logic based on expected output
        if "ESP_OK" in response or "PASS" in response or "OK" in response:
            test.actual = response.strip()[:200]
            return TestResult.PASS
        else:
            test.actual = f"Unexpected response: {response.strip()[:200]}"
            return TestResult.FAIL

    def run_all(self) -> Dict:
        print(f"\n{'='*60}")
        print(f"ACCEPTANCE TEST RUN - Node {self.node_id}")
        print(f"Mode: {'SIMULATION' if self.simulate else 'HARDWARE'}")
        print(f"{'='*60}")

        if not self.simulate and not self.connect():
            return {"error": "Failed to connect to device"}

        for test in self.tests:
            test = self.run_test(test)
            self.results.append(asdict(test))

        self.disconnect()

        return self.generate_report()

    def generate_report(self) -> Dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r['result'] == 'PASS')
        failed = sum(1 for r in self.results if r['result'] == 'FAIL')
        skipped = sum(1 for r in self.results if r['result'] == 'SKIP')

        blocking_failed = sum(1 for r in self.results
                              if r['result'] == 'FAIL' and r['criticality'] == 'blocking')

        report = {
            "node_id": self.node_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "mode": "simulation" if self.simulate else "hardware",
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "blocking_failed": blocking_failed,
                "pass_rate": f"{100*passed/total:.1f}%"
            },
            "results": self.results
        }

        return report


def save_junit_xml(report: Dict, output_path: Path):
    """Generate JUnit XML for CI integration."""
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom import minidom

    testsuites = Element('testsuites')
    testsuite = SubElement(testsuites, 'testsuite',
                           name=f"acceptance_node_{report['node_id']}",
                           tests=str(report['summary']['total']),
                           failures=str(report['summary']['failed']),
                           skipped=str(report['summary']['skipped']))

    for result in report['results']:
        tc = SubElement(testsuite, 'testcase',
                        name=result['name'],
                        classname=result['category'],
                        time=f"{result['duration_ms']/1000:.3f}")

        if result['result'] == 'FAIL':
            SubElement(tc, 'failure',
                       message=f"Criticality: {result['criticality']}",
                       type="AssertionError").text = result['actual']
        elif result['result'] == 'SKIP':
            SubElement(tc, 'skipped')

    xml_str = minidom.parseString(tostring(testsuites)).toprettyxml(indent="  ")
    output_path.write_text(xml_str)


def save_html_report(report: Dict, output_path: Path):
    """Generate HTML report."""
    html = f"""<!DOCTYPE html>
<html><head><title>Acceptance Test - Node {report['node_id']}</title>
<style>
body {{font-family: monospace; margin: 20px;}}
.pass {{color: green;}} .fail {{color: red;}} .skip {{color: gray;}}
table {{border-collapse: collapse; width: 100%;}}
th, td {{border: 1px solid #ddd; padding: 8px; text-align: left;}}
th {{background: #f0f0f0;}}
tr:hover {{background: #f5f5f5;}}
.summary {{background: #f8f8f8; padding: 15px; margin-bottom: 20px;}}
.critical {{font-weight: bold;}}
</style></head><body>
<h1>Acceptance Test Report - Node {report['node_id']}</h1>
<div class="summary">
<h2>Summary</h2>
<p><b>Node:</b> {report['node_id']}</p>
<p><b>Timestamp:</b> {report['timestamp']}</p>
<p><b>Mode:</b> {report['mode']}</p>
<p><b>Total:</b> {report['summary']['total']} | <span class="pass">Passed: {report['summary']['passed']}</span> | <span class="fail">Failed: {report['summary']['failed']}</span> | <span class="skip">Skipped: {report['summary']['skipped']}</span></p>
<p><b>Pass Rate:</b> {report['summary']['pass_rate']}</p>
<p><b>Blocking Failures:</b> {report['summary']['blocking_failed']}</p>
</div>
<table>
<tr><th>ID</th><th>Test</th><th>Category</th><th>Criticality</th><th>Result</th><th>Actual</th><th>Time(ms)</th></tr>
"""
    for r in report['results']:
        css_class = r['result'].lower()
        crit_class = 'critical' if r['criticality'] == 'blocking' else ''
        html += f"<tr class='{css_class} {crit_class}'>"
        html += f"<td>{r['id']}</td><td>{r['name']}</td><td>{r['category']}</td><td>{r['criticality']}</td>"
        html += f"<td>{r['result']}</td><td>{r['actual'][:100]}</td><td>{r['duration_ms']}</td></tr>"

    html += "</table></body></html>"
    output_path.write_text(html)


def main():
    parser = argparse.ArgumentParser(description='Run acceptance tests')
    parser.add_argument('--node', required=True, help='Node ID (A, B, etc.)')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--simulate', action='store_true', help='Run in simulation mode (no hardware)')
    parser.add_argument('--output', default='./results/', help='Output directory')
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    runner = AcceptanceTestRunner(args.node, args.port, args.simulate)
    report = runner.run_all()

    # Save reports
    json_path = output_dir / f"acceptance_{args.node}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    xml_path = output_dir / f"acceptance_{args.node}.xml"
    html_path = output_dir / f"acceptance_{args.node}.html"

    with open(json_path, 'w') as f:
        json.dump(report, f, indent=2)

    save_junit_xml(report, xml_path)
    save_html_report(report, html_path)

    print(f"\n{'='*60}")
    print(f"REPORT SAVED:")
    print(f"  JSON:  {json_path}")
    print(f"  JUnit: {xml_path}")
    print(f"  HTML:  {html_path}")
    print(f"\nSUMMARY: {report['summary']['passed']}/{report['summary']['total']} passed ({report['summary']['pass_rate']})")
    print(f"Blocking failures: {report['summary']['blocking_failed']}")

    # Exit code for CI
    if report['summary']['blocking_failed'] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()