"""Six geographic measurement surfaces, with explicit geometry and source support.

Local IDW estimates are not measured conditions, calibrated uncertainties, or
hazard probabilities. Two locations support only their connecting segment.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import Delaunay

from ml.operational.contracts import UNITS
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


def idw(xy, values, query):
    """Inverse-square weights, preserving exact measurements at known points."""
    xy = np.asarray(xy, float)
    values = np.asarray(values, float)
    query = np.asarray(query, float)
    if np.ptp(values) == 0:
        return np.full(len(query), float(values[0]))
    d = np.linalg.norm(query[:, None, :] - xy[None, :, :], axis=2)
    weights = 1 / np.maximum(d, 1e-8) ** 2
    estimates = weights @ values / weights.sum(axis=1)
    exact = d.min(axis=1) < 1e-8
    estimates[exact] = values[d[exact].argmin(axis=1)]
    return estimates


def parameter_maps(nodes, resolution=24):
    """One exact observation time/source/reference; no ffill or extrapolation."""
    if type(resolution) is not int or not 8 <= resolution <= 40:
        raise ValueError("Resolution must be an integer from 8 to 40")
    result = {
        "schema_version": "indra_parameter_maps_v1",
        "method": "LOCAL_PLANAR_IDW_POWER_2",
        "status": "UNAVAILABLE",
        "reason": "At least two synchronized distinct locations are needed.",
        "observation_timestamp": None,
        "source_class": None,
        "source_ids": [],
        "stale": False,
        "field_validated": False,
        "probability": None,
        "uncertainty": None,
        "interpretation": "INTERPOLATED_MEASUREMENTS_NOT_OBSERVATIONS_OR_HAZARD_PROBABILITIES",
        "layers": {},
        "excluded_nodes": [],
        "nodes": [],
        "bounds": None,
    }
    if not nodes:
        return result
    stamp = max(n["timestamp"] for n in nodes)
    result["observation_timestamp"] = stamp
    selected = []
    for n in nodes:
        if n["timestamp"] != stamp:
            result["excluded_nodes"].append(
                {"id": n["id"], "reason": "NOT_SYNCHRONIZED_WITH_LATEST_SNAPSHOT"}
            )
        else:
            selected.append(n)
    if len({(n["sourceClass"], n["pressureReference"]) for n in selected}) != 1:
        result["reason"] = (
            "Source classes or pressure references differ; maps do not mix them."
        )
        return result
    result.update(
        source_class=selected[0]["sourceClass"],
        source_ids=sorted({n["sourceId"] for n in selected}),
        stale=any(n["stale"] for n in selected),
    )
    identities = set()
    positions = set()
    kept = []
    for n in selected:
        position = (round(n["lat"], 7), round(n["lng"], 7))
        identity = (
            n.get("sourceCellId")
            if n["sourceClass"] == "modeled_grid"
            else n.get("physicalSiteId", n["id"])
        )
        if position in positions or identity in identities:
            result["excluded_nodes"].append(
                {"id": n["id"], "reason": "DUPLICATE_LOCATION_OR_SOURCE_CELL"}
            )
            continue
        kept.append(n)
        positions.add(position)
        identities.add(identity)
    selected = kept
    result["nodes"] = [
        {"id": n["id"], "lat": n["lat"], "lng": n["lng"], "measurements": n["sensors"]}
        for n in selected
    ]
    if len(selected) < 2:
        return result
    latlon = np.array([[n["lat"], n["lng"]] for n in selected], float)
    origin = latlon.mean(0)
    cos = np.cos(np.deg2rad(origin[0]))
    if abs(cos) < 0.1:
        result["reason"] = "Local projection is unsupported near the poles."
        return result
    scale = np.array([111195.0, 111195.0 * cos])
    # Coordinates are local east/north metres, never degrees in a distance formula.
    xy = ((latlon - origin) * scale)[:, ::-1]
    if np.ptp(xy, axis=0).max() > 100000:
        result["reason"] = "This local interpolation is limited to a 100 km extent."
        return result
    result["bounds"] = [
        latlon[:, 0].min(),
        latlon[:, 1].min(),
        latlon[:, 0].max(),
        latlon[:, 1].max(),
    ]
    rank = np.linalg.matrix_rank(xy - xy[0], tol=1e-3)
    line = rank < 2
    if line:
        _, _, v = np.linalg.svd(xy - xy[0])
        axis = v[0]
        position = xy @ axis
        endpoints = xy[[position.argmin(), position.argmax()]]
        query = np.linspace(endpoints[0], endpoints[1], resolution)
        shape = (1, resolution)
        corners = None
        step = None
    else:
        low = xy.min(0)
        high = xy.max(0)
        step = (high - low) / resolution
        xx, yy = np.meshgrid(
            low[0] + (np.arange(resolution) + 0.5) * step[0],
            low[1] + (np.arange(resolution) + 0.5) * step[1],
        )
        query = np.column_stack([xx.ravel(), yy.ravel()])
        shape = (resolution, resolution)
        corners = (
            query[:, None, :]
            + np.array([[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]]) * step
        )
    geographic = query[:, ::-1] / scale + origin
    result.update(
        shape=list(shape),
        coordinates=geographic.reshape(*shape, 2).tolist(),
        geometry="SEGMENT" if line else "CONSERVATIVE_CONVEX_HULL_CELLS",
        cell_size_degrees=None if line else (step[::-1] / scale).tolist(),
    )
    for channel in RAW_SENSOR_COLUMNS:
        valid = np.array([n["sensors"].get(channel) is not None for n in selected])
        values = np.array(
            [
                n["sensors"].get(channel, np.nan)
                if n["sensors"].get(channel) is not None
                else np.nan
                for n in selected
            ],
            float,
        )
        valid &= np.isfinite(values)
        supported = np.zeros(len(query), bool)
        if valid.sum() >= 2:
            pts = xy[valid]
            if line:
                axis = query[-1] - query[0]
                axis /= np.linalg.norm(axis)
                along = query @ axis
                limits = pts @ axis
                supported = (along >= limits.min() - 1e-7) & (
                    along <= limits.max() + 1e-7
                )
            elif (
                valid.sum() >= 3 and np.linalg.matrix_rank(pts - pts[0], tol=1e-3) == 2
            ):
                hull = Delaunay(pts)
                supported = (
                    hull.find_simplex(corners.reshape(-1, 2), tol=1e-8).reshape(-1, 4)
                    >= 0
                ).all(axis=1)
        estimates = np.full(len(query), np.nan)
        if supported.any():
            estimates[supported] = idw(xy[valid], values[valid], query[supported])
        finite = estimates[np.isfinite(estimates)]
        result["layers"][channel] = {
            "unit": UNITS[channel],
            "status": "ESTIMATED" if len(finite) else "INSUFFICIENT_SPATIAL_SUPPORT",
            "node_count": int(valid.sum()),
            "supported_cells": int(supported.sum()),
            "values": [
                [None if not np.isfinite(v) else float(v) for v in row]
                for row in estimates.reshape(shape)
            ],
            "minimum": float(finite.min()) if len(finite) else None,
            "maximum": float(finite.max()) if len(finite) else None,
        }
    any_surface = any(v["supported_cells"] for v in result["layers"].values())
    result["status"] = (
        ("LINE_ESTIMATE" if line else "AREA_ESTIMATE") if any_surface else "UNAVAILABLE"
    )
    result["reason"] = (
        (
            "Only the connecting segment is supported."
            if line
            else "Cells lie inside the contributing locations’ convex hull; no terrain correction."
        )
        if any_surface
        else "Insufficient noncollinear locations with complete channel measurements."
    )
    if result["stale"]:
        result["reason"] += " Historical/stale observations; not current conditions."
    return result


def geojson(bundle, channel):
    """Convert a selected numerical layer to colored cells or a line for Leaflet."""
    if channel not in RAW_SENSOR_COLUMNS:
        raise ValueError("Unknown parameter")
    features = []
    layer = bundle["layers"].get(channel, {})
    for i, row in enumerate(layer.get("values", [])):
        for j, value in enumerate(row):
            if value is None:
                continue
            lat, lon = bundle["coordinates"][i][j]
            if bundle["geometry"] == "SEGMENT":
                coords = bundle["coordinates"][0]
                left = coords[max(0, j - 1)]
                right = coords[min(len(coords) - 1, j + 1)]
                geometry = {
                    "type": "LineString",
                    "coordinates": [[left[1], left[0]], [right[1], right[0]]],
                }
            else:
                dy, dx = bundle["cell_size_degrees"]
                ring = [
                    [lon - dx / 2, lat - dy / 2],
                    [lon + dx / 2, lat - dy / 2],
                    [lon + dx / 2, lat + dy / 2],
                    [lon - dx / 2, lat + dy / 2],
                    [lon - dx / 2, lat - dy / 2],
                ]
                geometry = {"type": "Polygon", "coordinates": [ring]}
            intensity = (
                (value - layer["minimum"]) / (layer["maximum"] - layer["minimum"])
                if layer["maximum"] > layer["minimum"]
                else 0.5
            )
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "value": value,
                        "intensity": intensity,
                        "channel": channel,
                        "unit": layer["unit"],
                    },
                }
            )
    return {
        "type": "FeatureCollection",
        "features": features,
        "status": bundle["status"],
        "reason": bundle["reason"],
        "method": bundle["method"],
        "channel": channel,
        "unit": layer.get("unit", UNITS[channel]),
        "minimum": layer.get("minimum"),
        "maximum": layer.get("maximum"),
        "observation_timestamp": bundle["observation_timestamp"],
        "source_class": bundle["source_class"],
        "stale": bundle["stale"],
        "uncertainty": None,
        "probability": None,
        "field_validated": False,
    }
