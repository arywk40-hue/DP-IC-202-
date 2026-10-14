"""Bounded per-channel robust diagnostics; valid weather changes are not faults."""
from __future__ import annotations

import json
import math
from pathlib import Path
import statistics
import struct

from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS

CONFIG = Path(__file__).resolve().parents[2]/"configs/himachal_anomaly_v1.json"
STATES = ("UNAVAILABLE", "WARMUP", "WITHIN_BASELINE", "ENVIRONMENTAL_ANOMALY", "SENSOR_FAULT")
PACKET_STATES = ("ACCEPTED", "CRC_REJECTED", "TIME_REJECTED", "CLOCK_UNVERIFIED")


def f32(value):
    try:
        return struct.unpack("f", struct.pack("f", value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def validate(config):
    if (config["schema_version"] != "indra_himachal_anomaly_v1" or config["ring_capacity"] != 16
            or not 2 <= config["warmup_valid_samples"] <= 16 or not 0 < config["ewma_alpha"] <= 1
            or len(config["noise_floors"]) != 6 or any(not math.isfinite(v) or v<=0 for v in config["noise_floors"])
            or not math.isfinite(config["threshold_scale"]) or config["threshold_scale"] <= 0):
        raise ValueError("Unsupported bounded anomaly configuration")
    return config


def load(path=CONFIG):
    return validate(json.loads(Path(path).read_text()))


class Detector:
    def __init__(self, config=None, cadence_seconds=None):
        self.config = load() if config is None else validate(config)
        self.cadence = self.config["serial_demo_native_cadence_seconds"] if cadence_seconds is None else cadence_seconds
        if type(self.cadence) is not int or self.cadence <= 0 or 3600 % self.cadence:
            raise ValueError("Explicit native cadence must divide an hour")
        self.reset()

    def reset(self):
        self.last = None
        self.rings = [[] for _ in range(6)]
        self.ewma = [None]*6

    def push(self, timestamp, values, *, crc_ok=True, clock_uncertainty_seconds=0, self_test_fault_mask=0):
        if len(values) != 6 or type(self_test_fault_mask) is not int or not 0 <= self_test_fault_mask <= 63:
            raise ValueError("Six channels and six-bit self-test mask required")
        cfg = self.config
        packet = "ACCEPTED"
        if crc_ok is not True:
            packet = "CRC_REJECTED"
        elif (type(timestamp) is not int or not cfg["unix_time_bounds"][0] <= timestamp <= cfg["unix_time_bounds"][1]
              or timestamp % self.cadence or self.last is not None and timestamp <= self.last):
            packet = "TIME_REJECTED"
        elif (type(clock_uncertainty_seconds) not in {int, float} or not math.isfinite(clock_uncertainty_seconds)
              or not 0 <= clock_uncertainty_seconds <= cfg["maximum_clock_uncertainty_seconds"]):
            packet = "CLOCK_UNVERIFIED"
        states, residuals, scales = ["UNAVAILABLE"]*6, [None]*6, [None]*6
        if packet != "ACCEPTED":
            if packet == "CRC_REJECTED":
                states = ["SENSOR_FAULT"]*6
            return dict(packet_state=packet, channel_states=states, residuals=residuals, scales=scales,
                        valid_mask=0, environmental_mask=0, fault_mask=63 if packet=="CRC_REJECTED" else 0,
                        baseline_counts=[len(r) for r in self.rings], ewma=self.ewma.copy())
        if self.last is not None and timestamp-self.last > cfg["maximum_gap_intervals"]*self.cadence:
            self.reset()
        self.last = timestamp
        valid_mask = environment = faults = 0
        for i, (raw, channel) in enumerate(zip(values, RAW_SENSOR_COLUMNS)):
            value = math.nan if raw is None else f32(raw)
            if self_test_fault_mask & (1 << i) or math.isinf(value) or math.isfinite(value) and not PHYSICAL_RANGES[channel][0] <= value <= PHYSICAL_RANGES[channel][1]:
                states[i], faults = "SENSOR_FAULT", faults | (1 << i)
                self.rings[i], self.ewma[i] = [], None
                continue
            if math.isnan(value):
                # A missing sample cannot bridge a formerly contiguous baseline.
                self.rings[i], self.ewma[i] = [], None
                continue
            valid_mask |= 1 << i
            ring = self.rings[i]
            if len(ring) < cfg["warmup_valid_samples"]:
                states[i] = "WARMUP"
            else:
                median = statistics.median(ring)
                mad = statistics.median(abs(v-median) for v in ring)
                scale = max(cfg["noise_floors"][i], cfg["mad_consistency_factor"]*mad)
                residuals[i], scales[i] = f32(value-median), f32(scale)
                changed = abs(value-median) > cfg["threshold_scale"]*scale
                states[i] = "ENVIRONMENTAL_ANOMALY" if changed else "WITHIN_BASELINE"
                if changed:
                    environment |= 1 << i
            # Preserve valid meteorological changes; an anomaly is not rejection.
            ring.append(value)
            del ring[:-cfg["ring_capacity"]]
            self.ewma[i] = value if self.ewma[i] is None else f32(self.ewma[i]+cfg["ewma_alpha"]*(value-self.ewma[i]))
        return dict(packet_state=packet, channel_states=states, residuals=residuals, scales=scales,
                    valid_mask=valid_mask, environmental_mask=environment, fault_mask=faults,
                    baseline_counts=[len(r) for r in self.rings], ewma=self.ewma.copy())
