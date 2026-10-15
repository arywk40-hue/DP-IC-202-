"""Spatially indexed, bounded candidate scan; unknown coverage stays explicit."""
import math

from ml.himachal.nodes import separation_m


def select(registry,health,origin_id,now,required_channels=63):
    origin=registry.public(origin_id)
    candidates,truncated=registry.nearest_candidates(origin_id)
    eligible=[]
    for node_id in candidates:
        node=registry.public(node_id)
        if node["source_class"]!="physical_indra" or node["site_reviewed"] is not True:
            continue
        if node["profile_id"]!=origin["profile_id"] or node["native_profile"]!=origin["native_profile"] or node["elevation_datum"]!=origin["elevation_datum"]:
            continue
        d=separation_m(origin,node)
        dz=abs(origin["elevation_m"]-node["elevation_m"])
        cfg=registry.config
        if d>cfg["maximum_radius_m"] or dz>cfg["maximum_elevation_difference_m"]:
            continue
        status=health.assess(node_id,now,required_channels)
        if not status["eligible"]:
            continue
        weight=node["quality_weight"]*math.exp(-d/cfg["distance_scale_m"]-dz/cfg["elevation_scale_m"])
        if weight<=0:
            continue
        eligible.append(dict(node_id=node_id,radio_id=node["radio_id"],physical_site_id=node["physical_site_id"],
            registration_id=node["registration_id"],upstream_sensor_id=node["upstream_sensor_id"],failure_domain=node["failure_domain"],
            distance_m=d,elevation_difference_m=dz,weight=weight,health=status))
    eligible.sort(key=lambda r:(-r["weight"],r["node_id"]))
    peers=eligible[:registry.config["maximum_peers"]]
    return dict(origin_id=origin_id,peers=peers,eligible_in_scanned_candidates=len(eligible),queried_count=len(peers),
        candidates_scanned=len(candidates),search_truncated=truncated,eligible_total=None if truncated else len(eligible),
        coverage_scope="BOUNDED_NEAREST_CANDIDATE_LOWER_BOUND" if truncated else "EXHAUSTIVE_REGISTERED_CANDIDATES",
        required_channel_mask=required_channels)
