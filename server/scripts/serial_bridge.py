#!/usr/bin/env python3
"""Forward ESP32 readings from USB serial to the INDRA server's /api/ingest.

Works with today's firmware with no WiFi: plug the board(s) into this computer,
start the server, then run for example

    .venv/bin/python server/scripts/serial_bridge.py                      # auto-detect boards
    .venv/bin/python server/scripts/serial_bridge.py --port /dev/cu.usbmodem1101 \
        --node-id ridge-01 --lat 31.725 --lon 76.942 --elevation 1280

Each serial port is read in its own thread, so several boards on one laptop
work at once (repeat --port, or let auto-detect find them all).

Master/slave: plug in only the MASTER. It prints its own readings and every slave
reading it receives over ESP-NOW; each keeps its own node id on the server.

Lines understood from the board:
  * JSON from weather_payload.h ({"schema_version":"indra_weather_records_v1",...})
  * Any flat JSON object with channel fields ({"temperature_c":..., ...})
  * CSV "ts,temp,rh,pressure,pm25,pm10,wind" or "temp,rh,pressure,pm25,pm10,wind"
Everything else (boot banners, diagnostics) is printed as a device log line.

LoRa mesh gateway (unknown or third-party format): add --lora. Every node in the mesh
becomes its own node on the map (ids prefixed "lora-"), using the lat/lon in each packet:

    .venv/bin/python server/scripts/serial_bridge.py --lora --capture lora_raw.log -v

Readings that cannot be delivered (server down, WiFi drop) are buffered in
memory and retried, so a short server restart does not lose data.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

try:                                    # run as a script: server/scripts is on sys.path
    from lora_adapter import LoraParser
except ImportError:                     # imported as a package (tests)
    from server.scripts.lora_adapter import LoraParser

CHANNELS = ["temperature_c", "relative_humidity_pct", "pressure_hpa",
            "pm25_ug_m3", "pm10_ug_m3", "wind_speed_mps"]
PORT_PATTERNS = ["/dev/cu.usbmodem*", "/dev/cu.usbserial*", "/dev/cu.wchusbserial*", "/dev/cu.SLAB_USBtoUART*",
                 "/dev/ttyUSB*", "/dev/ttyACM*"]
MAX_BUFFER = 20_000


def detect_ports() -> list[str]:
    ports = sorted({p for pattern in PORT_PATTERNS for p in glob.glob(pattern)})
    if not ports:
        try:
            from serial.tools import list_ports
            ports = [p.device for p in list_ports.comports() if p.vid is not None]
        except ImportError:
            pass
    return ports


def parse_line(line: str, args, port_node: str | None):
    """Return an ingest payload (dict) or None for non-data lines."""
    text = line.strip()
    if not text:
        return None
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        if isinstance(payload.get("observations"), list):
            for obs in payload["observations"]:
                if obs.get("relay"):
                    continue          # a slave reading relayed by a master: keep its own id/location
                obs.setdefault("transport", "usb_serial")
                if port_node:
                    obs["node_id"] = port_node
                if obs.get("latitude") is None and args.lat is not None:
                    obs["latitude"], obs["longitude"] = args.lat, args.lon
                if obs.get("elevation_m") is None and args.elevation is not None:
                    obs["elevation_m"] = args.elevation
            return payload
        if not any(k in payload for k in CHANNELS + ["temperature", "temp"]):
            return None
        if port_node:
            payload["node_id"] = port_node
        payload.setdefault("node_id", port_node)
        return _with_location(payload, args)
    parts = [p.strip() for p in text.split(",")]
    if len(parts) in (6, 7):
        try:
            numbers = [float(p) for p in parts]
        except ValueError:
            return None
        if not port_node:
            return None
        reading = {"node_id": port_node}
        if len(numbers) == 7:
            reading["timestamp_utc"] = numbers.pop(0)
        reading.update(zip(CHANNELS, numbers))
        return _with_location(reading, args)
    return None


def _with_location(reading: dict, args) -> dict:
    if args.lat is not None:
        reading.setdefault("lat", args.lat)
        reading.setdefault("lon", args.lon)
    if args.elevation is not None:
        reading.setdefault("elevation_m", args.elevation)
    if args.name:
        reading.setdefault("name", args.name)
    reading.setdefault("transport", "usb_serial")
    return reading


class Uploader:
    def __init__(self, server: str, token: str | None, dry_run: bool):
        self.url = server.rstrip("/") + "/api/ingest"
        self.token = token
        self.dry_run = dry_run
        self.queue: collections.deque = collections.deque(maxlen=MAX_BUFFER)
        self.lock = threading.Lock()
        self.sent = self.failed = 0
        self.last_error = None

    def submit(self, payload):
        with self.lock:
            self.queue.append(payload)

    def _post(self, body):
        data = json.dumps(body).encode()
        request = urllib.request.Request(self.url, data=data, method="POST",
                                         headers={"Content-Type": "application/json"})
        if self.token:
            request.add_header("X-Indra-Token", self.token)
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read() or b"{}")

    def flush(self):
        with self.lock:
            batch = list(self.queue)
            self.queue.clear()
        if not batch:
            return
        if self.dry_run:
            for item in batch:
                print("DRY-RUN", json.dumps(item)[:200])
            self.sent += len(batch)
            return
        try:
            self._post(batch if len(batch) > 1 else batch[0])
            self.sent += len(batch)
            self.last_error = None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            self.last_error = f"HTTP {exc.code}: {detail}"
            if 400 <= exc.code < 500 and exc.code not in (401, 408, 429):
                if len(batch) > 1:               # isolate the bad reading(s); keep the good ones
                    for item in batch:
                        try:
                            self._post(item)
                            self.sent += 1
                        except urllib.error.HTTPError as one:
                            self.failed += 1
                            print(f"[bridge] rejected: {one.read().decode(errors='replace')[:200]}", file=sys.stderr)
                        except (urllib.error.URLError, TimeoutError, OSError):
                            self._requeue([item])
                    return
                self.failed += 1                 # payload problem: retrying will not help
                print(f"[bridge] server rejected reading: {self.last_error}", file=sys.stderr)
                return
            self._requeue(batch)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            self.last_error = str(exc)
            self._requeue(batch)

    def _requeue(self, batch):
        with self.lock:
            self.queue.extendleft(reversed(batch))
        print(f"[bridge] server unreachable ({self.last_error}); buffering {len(self.queue)} reading(s)",
              file=sys.stderr)


def node_of(payload) -> str:
    if isinstance(payload.get("observations"), list) and payload["observations"]:
        return str(payload["observations"][0].get("node_id"))
    return str(payload.get("node_id"))


_capture_lock = threading.Lock()


def capture(path: str, port: str, line: str):
    """Append every raw gateway line so an unknown mesh format can be inspected later."""
    with _capture_lock, open(path, "a", encoding="utf-8") as handle:
        handle.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {port} {line.rstrip()}\n")


def read_port(port: str, node_id: str | None, args, uploader: Uploader, stop: threading.Event):
    import serial

    last_sent: dict[str, float] = {}   # per node: a master relays several nodes over one port
    lora = LoraParser(args) if args.lora else None
    while not stop.is_set():
        try:
            with serial.Serial(port, args.baud, timeout=1) as ser:
                print(f"[{port}] connected at {args.baud} baud" + (f" as {node_id}" if node_id else ""))
                while not stop.is_set():
                    raw = ser.readline()
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="replace")
                    if args.capture and line.strip():
                        capture(args.capture, port, line)
                    payloads = lora.parse(line, node_id) if lora else []
                    if not payloads:
                        single = parse_line(line, args, node_id)
                        payloads = [single] if single is not None else []
                    if not payloads:
                        if (args.verbose or lora) and line.strip():
                            print(f"[{port}] unparsed: {line.rstrip()[:200]}")
                        continue
                    for payload in payloads:
                        now = time.monotonic()
                        key = node_of(payload)
                        if now - last_sent.get(key, 0.0) < args.interval:
                            continue
                        last_sent[key] = now
                        uploader.submit(payload)
        except serial.SerialException as exc:
            print(f"[{port}] {exc}; retrying in 3 s", file=sys.stderr)
            stop.wait(3)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--server", default="http://127.0.0.1:8080", help="INDRA server base URL")
    parser.add_argument("--port", action="append", help="Serial port (repeat for several boards); auto-detect if omitted")
    parser.add_argument("--node-id", action="append",
                        help="Node id per --port, in the same order. Overrides the id the firmware prints "
                             "(never applied to slave readings relayed by a master).")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Forward at most one reading per board every N seconds (firmware prints every 1 s)")
    parser.add_argument("--lat", type=float, help="Fixed latitude for a node without GPS")
    parser.add_argument("--lon", type=float, help="Fixed longitude for a node without GPS")
    parser.add_argument("--elevation", type=float, help="Surveyed elevation in metres (enables lapse-rate maths)")
    parser.add_argument("--name", help="Display name for the node")
    parser.add_argument("--token", help="Shared secret matching the server's --ingest-token")
    parser.add_argument("--lora", action="store_true",
                        help="Gateway of a LoRa mesh: parse JSON / key=value / CSV lines from any node, using each "
                             "packet's own node id and lat/lon (see lora_adapter.py)")
    parser.add_argument("--node-prefix", default="lora-",
                        help="Prefix for mesh node ids so they never collide with your own nodes (default lora-)")
    parser.add_argument("--nodes-file", type=Path,
                        help='JSON {"<mesh id or prefixed id>": {"lat":..,"lon":..,"elevation_m":..,"name":..}} '
                             "used only for fields a packet does not carry")
    parser.add_argument("--capture", help="Append every raw serial line to this file (to learn an unknown format)")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads instead of sending")
    parser.add_argument("-v", "--verbose", action="store_true", help="Also print non-data device lines")
    args = parser.parse_args(argv)
    if (args.lat is None) != (args.lon is None):
        parser.error("--lat and --lon go together")
    args.nodes = json.loads(args.nodes_file.read_text()) if args.nodes_file else {}
    try:
        import serial  # noqa: F401
    except ImportError:
        parser.error("pyserial is missing: .venv/bin/pip install pyserial")

    ports = args.port or detect_ports()
    if not ports:
        parser.error("No USB serial boards found. Plug one in or pass --port.")
    ids = args.node_id or []
    if ids and len(ids) != len(ports):
        parser.error("Give one --node-id per --port")
    uploader = Uploader(args.server, args.token, args.dry_run)
    stop = threading.Event()
    threads = []
    for i, port in enumerate(ports):
        t = threading.Thread(target=read_port, args=(port, ids[i] if ids else None, args, uploader, stop), daemon=True)
        t.start()
        threads.append(t)
    print(f"[bridge] forwarding {len(ports)} board(s) to {uploader.url} (Ctrl+C to stop)")
    try:
        last_report = time.monotonic()
        while True:
            time.sleep(1)
            uploader.flush()
            if time.monotonic() - last_report >= 60:
                last_report = time.monotonic()
                print(f"[bridge] sent={uploader.sent} failed={uploader.failed} buffered={len(uploader.queue)}")
    except KeyboardInterrupt:
        stop.set()
        uploader.flush()
        print(f"\n[bridge] stopped. sent={uploader.sent} failed={uploader.failed} unsent={len(uploader.queue)}")


if __name__ == "__main__":
    main()
