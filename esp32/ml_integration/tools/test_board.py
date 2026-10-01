"""Replay synthetic hourly readings over USB and verify actual ESP32 predictions."""
import argparse
import json
import math
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--environment', choices=['esp32-s3-ml', 'esp32-s3-ml-usb'], default='esp32-s3-ml')
    parser.add_argument('--output', type=Path, default=Path('results/esp32_board_test.json'))
    args = parser.parse_args()
    import serial
    from build_identity import identity
    expected_identity = identity(Path(__file__).resolve().parents[1], args.environment)
    fixture = json.loads((Path(__file__).resolve().parents[1] / 'self_test_fixture.json').read_text())
    responses = []
    def receive(connection, key):
        end = time.monotonic() + 10
        while time.monotonic() < end:
            line = connection.readline().decode('utf-8', errors='replace').strip()
            try:
                value = json.loads(line)
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict) and key in value:
                responses.append(value)
                return value
        raise RuntimeError('Timed out waiting for board response: ' + key)
    def command(connection, text, key):
        connection.write((text + '\n').encode())
        connection.flush()
        return receive(connection, key)
    def check(condition, message):
        if not condition:
            raise RuntimeError(message)
    def compare(actual, expected):
        check(len(actual) == len(expected), 'Output shape mismatch')
        for a, b in zip(actual, expected):
            if b is None:
                check(a is None, 'Unavailable event must be null')
            else:
                check(isinstance(a, (int, float)) and math.isfinite(a) and abs(a-b) <= 5e-4,
                      f'Python/board mismatch: {a} vs {b}')
    report = {'status': 'FAIL', 'fixture': 'synthetic', 'port': args.port, 'responses': responses}
    try:
        with serial.Serial(args.port, 115200, timeout=.25) as connection:
            time.sleep(2)
            connection.reset_input_buffer()
            check(command(connection, 'SELFTEST', 'self_test')['self_test'] == 'PASS', 'On-board self-test failed')
            info = command(connection, 'INFO', 'info')
            check(info.get('self_test_passed') is True, 'Firmware self-test state missing')
            check(info.get('build_sha256') == expected_identity['build'], 'Wrong firmware build')
            report['firmware_info'] = info
            check(command(connection, 'RESET', 'reset')['reset'] is True, 'Reset failed')
            for i, (timestamp, values) in enumerate(zip(fixture['timestamps'], fixture['readings'])):
                line = ','.join([str(timestamp)] + [str(x) for x in values])
                result = command(connection, line, 'status')
                check(result['timestamp_utc'] == timestamp, 'Timestamp mismatch')
                check(result.get('measurements') == values, 'Raw measurement mismatch')
                check(result.get('forecast_timestamp_utc') == timestamp + 21600, 'Forecast time mismatch')
                check(result.get('build_sha256') == expected_identity['build'], 'Prediction build mismatch')
                check(result['history_rows'] == i+1, 'History length mismatch')
                check(result['status'] == ('READY' if i == 6 else 'WARMING_UP'), 'History state mismatch')
                if i < 6:
                    check(result['event_valid_mask'] == 0 and all(v is None for v in result['event_scores']), 'Fabricated warmup event')
            compare(result['forecast_6h'], fixture['forecast_last'])
            compare(result['event_scores'], fixture['events_last'])
            check(result['event_valid_mask'] == fixture['event_valid_mask'], 'Event mask mismatch')
            check(command(connection, line, 'status')['status'] == 'OUT_OF_ORDER', 'Duplicate timestamp accepted')
            check(command(connection, 'invalid', 'error')['error'] == 'INVALID_CSV', 'Malformed CSV accepted')
            check(command(connection, 'x' * 250, 'error')['error'] == 'LINE_TOO_LONG', 'Oversized line accepted')
            timestamp = fixture['timestamps'][-1] + 3600
            result = command(connection, f'{timestamp},20,101,1013,35,60,2', 'status')
            check(result['status'] == 'INVALID_INPUT', 'Out-of-range sensor accepted')
            result = command(connection, f'{timestamp+3600},20,50,1013,35,60,2', 'status')
            check(result['status'] == 'WARMING_UP' and result['history_rows'] == 1, 'Gap failed to reset history')
        report['status'] = 'PASS'
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        print(f"{report['status']}: {args.output}")


if __name__ == '__main__':
    main()
