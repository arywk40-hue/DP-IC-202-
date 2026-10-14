#!/usr/bin/env python3
"""INDRA planning reference only; no weather, board, external weather service or RF validation claim.

Deterministic Monte Carlo protocol stress tests and elevation-aware kriging
on synthetic data. Radio delivery uses a homogeneous pure-ALOHA approximation,
not a full packet/capture/terrain simulator. All radio nodes are one collision
domain. The 62-byte frame is a proposed design, not an existing repo protocol.
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import least_squares
from scipy.spatial import Delaunay, QhullError, distance_matrix

SCALES = (3, 10, 50, 200)
SCENARIOS = ("nominal", "dropout_loss_clock", "correlated_faults", "combined")
PAYLOAD_BYTES = 62


def airtime(payload=PAYLOAD_BYTES, sf=9, bw=125000, cr=1, preamble=8):
    """SX127x explicit-header, CRC-on LoRa airtime, CR=1 denotes 4/5."""
    symbol = 2**sf / bw
    de = int(symbol >= 0.016)
    payload_symbols = 8 + max(
        math.ceil((8 * payload - 4 * sf + 28 + 16) / (4 * (sf - 2 * de)))
        * (cr + 4), 0)
    return (preamble + 4.25 + payload_symbols) * symbol


def layout(n, rng):
    # Dense 4 x 4 km valley footprint, independent of global registration count.
    xy = rng.uniform(0, 4000, (n, 2))
    if n == 3:
        xy = np.array([[500., 500.], [1500., 500.], [1000., 1366.]])
    z = 900 + 0.09 * xy[:, 0] + 0.06 * xy[:, 1]
    return xy, z


def stress(n, scenario, seeds, rounds, channels):
    start = time.perf_counter()
    counters = dict(rounds=0, negative_rounds=0, positive_rounds=0,
                    warning_rounds=0, false_warning_rounds=0,
                    positive_warning_rounds=0, degraded_rounds=0,
                    radio_frames=0, vote_frames=0, attempted_peers=0,
                    delivered_votes=0, eligible_peers=0)
    durations, completion, offered, per_device_tx = [], [], [], []
    air = airtime()
    for seed in range(seeds):
        rng = np.random.default_rng(20261014 + 1009 * n + seed)
        xy, z = layout(n, rng)
        distances = distance_matrix(xy, xy)
        health_bad = scenario in ("dropout_loss_clock", "combined")
        common_fault = scenario in ("correlated_faults", "combined")
        dropout = .15 if health_bad else 0.
        base_loss = .10 if health_bad else 0.
        # Known manufacturing groups do not capture a hidden firmware fault.
        failure_groups = np.arange(n) % 3
        for _ in range(rounds):
            online = rng.random(n) >= dropout
            drift = rng.normal(0, 80 if health_bad else 2, n)
            hidden_fault = (rng.random(n) < .35) if common_fault else np.zeros(n, bool)
            drift_alarm = hidden_fault & (rng.random(n) < .75)
            healthy = online & (np.abs(drift) <= 30) & ~drift_alarm
            # A query is deliberately triggered every minute to stress transport.
            # Origin is not selected by weather labels or neighbour agreement.
            origins = np.flatnonzero(healthy)
            counters["rounds"] += 1
            heartbeat_frames = int(online.sum())
            if not len(origins):
                counters["degraded_rounds"] += 1
                counters["radio_frames"] += heartbeat_frames
                durations.append(30.)
                continue
            origin = int(rng.choice(origins))
            event = bool(rng.random() < .15)
            counters["positive_rounds" if event else "negative_rounds"] += 1
            eligible = np.flatnonzero(
                healthy & (np.arange(n) != origin) & (distances[origin] <= 5000)
                & (np.abs(z - z[origin]) <= 750))
            eligible = eligible[np.argsort(distances[origin, eligible])][:6]
            counters["eligible_peers"] += len(eligible)
            flags = rng.random(n) < .025
            if event:
                # A localized footprint; a dry neighbour is not proof of safety.
                in_footprint = distances[origin] <= 2000
                flags[in_footprint] = rng.random(int(in_footprint.sum())) < .9
            if common_fault and rng.random() < .30:
                flags[hidden_fault] = True
            flags[origin] = True  # conditional on a query-triggering local anomaly
            anticipated = heartbeat_frames + 2 + len(eligible)
            g = anticipated * air / (60 * channels)
            offered.append(g)
            p_delivery = (1 - base_loss) * math.exp(-2 * g)
            # Shared query broadcast: downlink decode is independently sampled.
            got_query = rng.random(len(eligible)) < p_delivery
            replies = eligible[got_query]
            counters["attempted_peers"] += len(eligible)
            counters["vote_frames"] += len(replies)
            tx_frames = heartbeat_frames + 1 + len(replies)
            delivered = replies[rng.random(len(replies)) < p_delivery]
            counters["delivered_votes"] += len(delivered)
            voted = np.r_[origin, delivered]
            weights = np.exp(-distances[origin, voted] / 3000
                             - np.abs(z[voted] - z[origin]) / 500)
            agreeing = voted[flags[voted]]
            ratio = float(weights[flags[voted]].sum() / weights.sum())
            quorum = (len(agreeing) >= 3 and ratio >= 2 / 3
                      and len(set(failure_groups[agreeing].tolist())) >= 2)
            enough_responses = len(voted) >= 3
            if quorum:
                counters["warning_rounds"] += 1
                counters["positive_warning_rounds" if event else "false_warning_rounds"] += 1
                tx_frames += 1  # broadcast one idempotent consensus result
                elapsed = air + len(eligible) * (air + .1) + air
                completion.append(elapsed)
                durations.append(elapsed)
            else:
                counters["degraded_rounds"] += int(not enough_responses)
                durations.append(30.)  # full deadline for unresolved rounds
            counters["radio_frames"] += tx_frames
            # One minute of airtime accounting across this collision domain.
            per_device_tx.append(tx_frames * air / n / 60)
    negative = counters["negative_rounds"]
    positive = counters["positive_rounds"]
    simulated_hours = counters["rounds"] / 60
    result = dict(n=n, scenario=scenario, channels=channels,
                  **counters,
                  mean_round_latency_s=float(np.mean(durations)),
                  p95_round_latency_s=float(np.quantile(durations, .95)),
                  p95_successful_warning_latency_s=(float(np.quantile(completion, .95))
                                                   if completion else None),
                  radio_frames_per_simulated_hour=counters["radio_frames"] / simulated_hours,
                  average_offered_load_per_channel=(float(np.mean(offered)) if offered else 0.),
                  delivered_vote_fraction=(counters["delivered_votes"] / counters["vote_frames"]
                                           if counters["vote_frames"] else None),
                  false_warning_fraction_of_negative_query_rounds=(counters["false_warning_rounds"] / negative
                                                                    if negative else None),
                  synthetic_positive_query_warning_fraction=(counters["positive_warning_rounds"] / positive
                                                              if positive else None),
                  mean_transmit_fraction_per_node=(float(np.mean(per_device_tx)) if per_device_tx else 0.),
                  simulation_wall_time_s=time.perf_counter() - start)
    assert counters["false_warning_rounds"] <= negative
    assert counters["positive_warning_rounds"] <= positive
    return result


def spatial(n, scenario, seeds):
    """Synthetic withheld-node interpolation; fitted exponential variogram.

    At <8 valid training stations returns sparse-point mode and no variance.
    Solver uses all nodes here to expose cost; production prompts require
    bounded local tiles. Whole validation labels are excluded from fitting.
    """
    start = time.perf_counter()
    errors, covered, variances, timings = [], [], [], []
    methods = {}
    for seed in range(seeds):
        rng = np.random.default_rng(90907 + n * 31 + seed)
        xy, z = layout(n, rng)
        d = distance_matrix(xy, xy)
        covariance = 1.2 * np.exp(-d / 1200) + .09 * np.eye(n)
        temperature = 24 - .006 * z + rng.multivariate_normal(np.zeros(n), covariance)
        health_bad = scenario in ("dropout_loss_clock", "combined")
        common_fault = scenario in ("correlated_faults", "combined")
        healthy = rng.random(n) >= (.15 if health_bad else 0.)
        if health_bad:
            healthy &= np.abs(rng.normal(0, 80, n)) <= 30
        fault = rng.random(n) < (.35 if common_fault else 0.)
        detected = fault & (rng.random(n) < .75)
        healthy &= ~detected
        measured = temperature + np.where(fault & ~detected, 2., 0.)
        eligible = np.flatnonzero(healthy)
        held = max(1, len(eligible) // 5)
        rng.shuffle(eligible)
        test, train = eligible[:held], eligible[held:]
        if len(train) < 8 or len(test) == 0:
            methods["sparse_points_no_variance"] = methods.get("sparse_points_no_variance", 0) + 1
            continue
        points, query = xy[train], xy[test]
        pair_d = distance_matrix(points, points)
        X = np.column_stack([np.ones(len(train)), (z[train] - 1200) / 1000])
        beta = np.linalg.lstsq(X, measured[train], rcond=None)[0]
        residual = measured[train] - X @ beta
        upper = np.triu_indices(len(train), 1)
        lag = pair_d[upper]
        gamma = .5 * (residual[:, None] - residual[None, :]) ** 2
        gamma = gamma[upper]
        bins = np.linspace(0, max(lag.max(), 1.), 7)
        occupied = len(set(np.digitize(lag, bins).tolist()))
        if occupied < 5 or np.ptp(z[train]) < 150:
            methods["insufficient_spread_no_variance"] = methods.get("insufficient_spread_no_variance", 0) + 1
            continue
        t0 = time.perf_counter()
        def semiv(params):
            nugget, sill, radius = params
            return nugget + sill * (1 - np.exp(-lag / radius))
        fit = least_squares(lambda p: semiv(p) - gamma,
                            [.09, max(float(np.var(residual)), .1), 1200.],
                            bounds=([.005, .005, 100.], [4., 10., 10000.]),
                            max_nfev=80)
        nugget, sill, radius = fit.x
        C = sill * np.exp(-pair_d / radius) + (nugget + 1e-8) * np.eye(len(train))
        factor = cho_factor(C)
        inv_X = cho_solve(factor, X)
        normal = X.T @ inv_X
        beta = np.linalg.solve(normal, X.T @ cho_solve(factor, measured[train]))
        q_X = np.column_stack([np.ones(len(test)), (z[test] - 1200) / 1000])
        cross = sill * np.exp(-distance_matrix(points, query) / radius)
        inv_cross = cho_solve(factor, cross)
        pred = q_X @ beta + cross.T @ cho_solve(factor, measured[train] - X @ beta)
        drift = q_X.T - X.T @ inv_cross
        variance = sill + nugget - np.sum(cross * inv_cross, axis=0)
        variance += np.sum(drift * np.linalg.solve(normal, drift), axis=0)
        variance = np.maximum(variance, 0.)
        try:
            supported = Delaunay(points).find_simplex(query) >= 0
        except QhullError:
            supported = np.zeros(len(test), bool)
        err = pred[supported] - temperature[test][supported]
        errors.extend(err.tolist())
        variances.extend(variance[supported].tolist())
        covered.extend((np.abs(err) <= 1.96 * np.sqrt(variance[supported])).tolist())
        timings.append((time.perf_counter() - t0) * 1000)
        methods["regression_kriging"] = methods.get("regression_kriging", 0) + 1
        assert np.isfinite(pred).all() and np.isfinite(variance).all()
    return dict(n=n, scenario=scenario, replicas=seeds, modes=methods,
                supported_heldout_predictions=len(errors),
                synthetic_temperature_rmse_c=(float(np.sqrt(np.mean(np.square(errors)))) if errors else None),
                synthetic_95pct_observation_interval_coverage=(float(np.mean(covered)) if covered else None),
                mean_kriging_variance_c2=(float(np.mean(variances)) if variances else None),
                p95_fit_and_predict_cpu_ms=(float(np.quantile(timings, .95)) if timings else None),
                simulation_wall_time_s=time.perf_counter() - start)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--rounds", type=int, default=200)
    args = parser.parse_args()
    if not 1 <= args.seeds <= 100 or not 1 <= args.rounds <= 10000:
        parser.error("Bounded positive seed/round counts required")
    receipt = dict(evidence_kind="SYNTHETIC_ENGINEERING_PLANNING_ONLY",
                   scope="Reference proposal; current INDRA repo has no consensus protocol to validate",
                   assumptions=dict(payload_bytes=PAYLOAD_BYTES, sf=9, bandwidth_hz=125000,
                                    coding_rate="4/5", preamble_symbols=8, explicit_header=True,
                                    radio_crc=True, heartbeat_seconds=60, query_seconds=60,
                                    response_deadline_seconds=30, minimum_agreeing_nodes=3,
                                    maximum_queried_peers=6, radius_m=5000, elevation_gate_m=750,
                                    fault_domain_minimum=2, agreement_ratio=2/3,
                                    clock_uncertainty_gate_seconds=30,
                                    model="p_delivery=(1-p_loss)*exp(-2*offered_load); two transmissions per vote",
                                    synthetic_field="Elevation drift plus exponential Gaussian residual and .3 C observation noise",
                                    variogram="Fitted exponential, minimum 8 training stations and 5 occupied distance bins",
                                    airtime_regulatory_assumption="Table II device 2.5% only if the actual equipment/category/APC are compliant",
                                    omitted=["Terrain RF propagation", "capture", "inter-SF interference", "hidden terminals",
                                             "per-node duty-cycle scheduling", "cryptographic verification", "LoRaWAN RX windows",
                                             "multihop routing", "real weather", "learned event-model decisions"]),
                   runtime=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
                   seeds=args.seeds, rounds_per_seed=args.rounds,
                   airtime_s={str(sf): airtime(sf=sf) for sf in (7, 9, 10, 11, 12)},
                   consensus=[], spatial=[])
    for channels in (1, 3):
        for n in SCALES:
            for scenario in SCENARIOS:
                receipt["consensus"].append(stress(n, scenario, args.seeds, args.rounds, channels))
    for n in SCALES:
        for scenario in SCENARIOS:
            receipt["spatial"].append(spatial(n, scenario, args.seeds))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(output=str(args.output), consensus_cases=len(receipt["consensus"]),
                          spatial_cases=len(receipt["spatial"]), airtime_s=receipt["airtime_s"])))


if __name__ == "__main__":
    main()
