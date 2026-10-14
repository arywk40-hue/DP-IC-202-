"""Versioned meteorological estimates; legacy learned feature meanings frozen.

NPL Magnus water/ice formulae and NWS complete heat-index branches. RH is over
liquid water; frost point is obtained via actual vapour pressure, not by silently
reinterpreting RH as saturation over ice. No pressure enhancement correction.
"""
from __future__ import annotations

import math


def estimate(value, unit, status="AVAILABLE", **extra):
    return {"value": value, "unit": unit, "status": status, **extra}


def _valid(t, rh):
    return (t is not None and rh is not None and math.isfinite(t) and math.isfinite(rh)
            and 0 <= rh <= 100)


def humidity(t, rh):
    names = {"dewpoint_liquid_c": "degC", "frostpoint_ice_c": "degC", "vpd_liquid_kpa": "kPa"}
    result = {n: estimate(None, u, "MISSING_OR_OUTSIDE_MAGNUS_DOMAIN") for n, u in names.items()}
    if not _valid(t, rh) or not -45 <= t <= 60:
        return result
    saturation = .6112 * math.exp(17.62 * t / (243.12 + t))
    result["vpd_liquid_kpa"] = estimate(saturation * (1 - rh / 100), "kPa")
    if rh == 0:
        for n in ("dewpoint_liquid_c", "frostpoint_ice_c"):
            result[n] = estimate(None, "degC", "ZERO_RH_UNAVAILABLE")
        return result
    gamma = math.log(rh / 100) + 17.62 * t / (243.12 + t)
    dew = 243.12 * gamma / (17.62 - gamma)
    frost = 272.62 * gamma / (22.46 - gamma)
    if -45 <= dew <= 60:
        result["dewpoint_liquid_c"] = estimate(dew, "degC", "AVAILABLE_SUPERCOOLED_WATER" if dew < 0 else "AVAILABLE")
    if -65 <= frost <= 0:
        result["frostpoint_ice_c"] = estimate(frost, "degC", "AVAILABLE_ICE_FROM_WATER_RH")
    else:
        result["frostpoint_ice_c"] = estimate(None, "degC", "OUTSIDE_ICE_DOMAIN")
    return result


def heat_index(t, rh):
    if not _valid(t, rh):
        return estimate(None, "degC", "MISSING_OR_INVALID_HUMIDITY", branch=None)
    tf = t * 1.8 + 32
    # Explicit research screen, not an extension of Steadman's fitted domain.
    if not 40 <= tf <= 112:
        return estimate(None, "degC", "OUTSIDE_IMPLEMENTED_NWS_SCREEN", branch=None)
    simple = .5 * (tf + 61 + (tf - 68) * 1.2 + rh * .094)
    averaged = (simple + tf) / 2
    if averaged < 80:
        return estimate((averaged - 32) / 1.8, "degC", "NWS_SIMPLE_ESTIMATE", branch="simple_averaged")
    hi = (-42.379 + 2.04901523*tf + 10.14333127*rh - .22475541*tf*rh
          - .00683783*tf*tf - .05481717*rh*rh + .00122874*tf*tf*rh
          + .00085282*tf*rh*rh - .00000199*tf*tf*rh*rh)
    branch = "rothfusz"
    if rh < 13 and 80 <= tf <= 112:
        hi -= (13-rh)/4 * math.sqrt(max(0., (17-abs(tf-95))/17))
        branch += "_low_rh"
    elif rh > 85 and 80 <= tf <= 87:
        hi += (rh-85)/10 * (87-tf)/5
        branch += "_high_rh"
    return estimate((hi-32)/1.8, "degC", "NWS_REGRESSION_ESTIMATE_NOT_FIELD_VALIDATED", branch=branch)
