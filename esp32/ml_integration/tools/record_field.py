"""Read-only serial recorder for supervised trials; never issues hazard alerts."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class Validator:
    def __init__(self, expected_build):
        self.expected_build = expected_build
        self.info = None
        self.node_id = None
        self.last_sequence = 0

    def classify(self, value):
        if not isinstance(value, dict):
            return 'REJECTED', 'JSON object required'
        if value.get('info') is True:
            if (value.get('protocol_version') != 1 or value.get('research_only') is not True
                    or value.get('self_test_passed') is not True
                    or value.get('build_sha256') != self.expected_build
                    or type(value.get('boot_id')) is not int
                    or not isinstance(value.get('node_id'), str)):
                self.info = None
                return 'REJECTED', 'Unverified firmware identity/self-test'
            if self.node_id is not None and value['node_id'] != self.node_id:
                self.info = None
                return 'REJECTED', 'Device changed within session'
            if self.info is None or self.info['boot_id'] != value['boot_id']:
                self.last_sequence = 0
            self.node_id = value['node_id']
            self.info = value
            return 'INFO', None
        if 'self_test' in value:
            if value['self_test'] != 'PASS':
                self.info = None
            return 'SELF_TEST', None
        if 'reset' in value or 'error' in value:
            return 'DEVICE_NOTICE', None
        if self.info is None:
            return 'REJECTED', 'INFO handshake required'
        if (value.get('build_sha256') != self.expected_build
                or value.get('boot_id') != self.info['boot_id']
                or value.get('protocol_version') != 1 or value.get('research_only') is not True):
            return 'REJECTED', 'Firmware/session mismatch; request INFO after reboot'
        seq = value.get('sequence')
        if type(seq) is not int or seq <= self.last_sequence:
            return 'REJECTED', 'Invalid, duplicate or out-of-order sequence'
        ts = value.get('timestamp_utc')
        if type(ts) is not int or not 0 < ts <= 0xffffffff or value.get('forecast_timestamp_utc') != ts + 21600:
            return 'REJECTED', 'Invalid forecast time contract'
        for name, length in [('measurements', 6), ('forecast_6h', 6), ('event_scores', 12)]:
            array = value.get(name)
            if not isinstance(array, list) or len(array) != length or any(x is not None and not finite(x) for x in array):
                return 'REJECTED', 'Invalid array: ' + name
        status = value.get('status')
        if status not in ['READY', 'WARMING_UP', 'FEATURES_UNAVAILABLE', 'INVALID_INPUT', 'OUT_OF_ORDER']:
            return 'REJECTED', 'Unknown status'
        expected_mask = 0xff9 if status == 'READY' else 0
        if value.get('event_valid_mask') != expected_mask:
            return 'REJECTED', 'Invalid event availability mask'
        for i, score in enumerate(value['event_scores']):
            valid = expected_mask & (1 << i)
            if (valid and (not finite(score) or not 0 <= score <= 1)) or (not valid and score is not None):
                return 'REJECTED', 'Unavailable/invalid event score'
        self.last_sequence = seq
        if status in ['INVALID_INPUT', 'OUT_OF_ORDER']:
            return 'INVALID_OBSERVATION', None
        if not all(finite(x) for x in value['measurements'] + value['forecast_6h']):
            return 'REJECTED', 'Missing measurements or forecasts'
        return 'OBSERVATION', None


def append_record(handle, record):
    handle.write(json.dumps(record, allow_nan=False, separators=(',', ':')) + '\n')
    handle.flush()
    os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--station', required=True)
    parser.add_argument('--expected-build', required=True, help='Approved build SHA256 printed by INFO and stored in build_identity.h')
    parser.add_argument('--output', type=Path, required=True, help='New JSONL journal; existing files are never overwritten')
    parser.add_argument('--max-age-seconds', type=float, default=7200, help='Quarantine stale or future-dated readings using the host UTC clock')
    parser.add_argument('--idle-timeout', type=float, default=7500, help='Stop after this many seconds without an observation; default allows hourly sampling')
    args = parser.parse_args()
    if (len(args.expected_build) != 64 or any(c not in '0123456789abcdef' for c in args.expected_build)
            or not math.isfinite(args.idle_timeout) or args.idle_timeout <= 0
            or not math.isfinite(args.max_age_seconds) or args.max_age_seconds <= 0
            or not args.station.strip()):
        parser.error('Provide a lowercase SHA256, station and positive idle timeout')
    import serial
    validator = Validator(args.expected_build)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as journal:
        def log(kind, **details):
            append_record(journal, dict(received_at_utc=datetime.now(timezone.utc).isoformat(),
                                        station=args.station, kind=kind, **details))
        log('SESSION_START', expected_build=args.expected_build, source='serial',
            meaning='experimental predictions; sensor provenance must be documented separately')
        try:
            with serial.Serial(args.port, 115200, timeout=.5) as connection:
                time.sleep(2)
                connection.write(b'INFO\n')
                last_observation = time.monotonic()
                discard = False
                buffer = bytearray()
                while time.monotonic() - last_observation < args.idle_timeout:
                    chunk = connection.read(min(max(connection.in_waiting, 1), 1024))
                    for byte in chunk:
                        if byte != 10:
                            if not discard:
                                buffer.append(byte)
                                if len(buffer) > 4096:
                                    log('REJECTED', reason='Line exceeds 4096 bytes')
                                    discard = True
                                    buffer.clear()
                            continue
                        if discard:
                            discard = False
                            continue
                        text = buffer.decode('utf-8', errors='replace').strip()
                        buffer.clear()
                        if not text:
                            continue
                        try:
                            value = json.loads(text, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
                            kind, reason = validator.classify(value)
                        except ValueError:
                            log('DEVICE_TEXT', text=text)
                            continue
                        if kind == 'OBSERVATION':
                            age = time.time() - value['timestamp_utc']
                            if age < -60 or age > args.max_age_seconds:
                                kind, reason = 'STALE_OBSERVATION', 'Outside host-clock freshness window'
                        log(kind, reason=reason, payload=value)
                        if kind == 'OBSERVATION':
                            last_observation = time.monotonic()
                log('IDLE_TIMEOUT')
        except KeyboardInterrupt:
            log('STOPPED_BY_OPERATOR')
        except Exception as exc:
            log('COLLECTOR_ERROR', error=str(exc))
            raise
        finally:
            log('SESSION_END')


if __name__ == '__main__':
    main()
