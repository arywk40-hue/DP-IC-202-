"""Synthetic physical-role protocol actors; not observations or training data."""
from datetime import datetime, timezone
import hashlib

from ml.himachal.consensus import Coordinator
from ml.himachal.health import Health
from ml.himachal.nodes import Registry
from ml.himachal.radio import Frame, HEARTBEAT, REQUEST, VOTE, encode

EPOCH=1782864000  # 2026-07-01 UTC, synthetic protocol clock.
RAW=(20.,60.,900.,25.,50.,3.)


def iso(t):
    return datetime.fromtimestamp(t,timezone.utc).isoformat()


def registration(i,**changes):
    return dict(node_id=f"fixture-{i}",physical_site_id=f"fixture-site-{i}",registration_id=f"fixture-registration-{i}",
        latitude=31.71+(i%10)*.002,longitude=76.93+(i//10)*.002,elevation_m=1000.+i%10*10,
        elevation_datum="surveyed_orthometric",source_class="physical_indra",upstream_sensor_id=f"synthetic-sensor-{i}",
        native_profile="native_minute",capability_mask=63,quality_weight=1.,failure_domain=f"fixture-domain-{i%3}",
        profile_id=1,sensor_height_m=2.,wind_height_m=10.,site_reviewed=True,**changes)


def rig(count=3):
    registry=Registry()
    for i in range(count):
        registry.register(registration(i),hashlib.sha256(f"SYNTHETIC_KEY_ONLY_{i}".encode()).digest())
    health=Health(registry)
    counter=iter(range(100,100000))
    coordinator=Coordinator(registry,health,query_id_factory=lambda:next(counter))
    sequence={n:0 for n in registry.entries}
    for t in (EPOCH-120,EPOCH-60,EPOCH):
        for n in registry.entries:
            wire=message(registry,n,sequence[n],kind=HEARTBEAT,observed=t)
            coordinator.ingest(wire,iso(t))
            sequence[n]+=1
    return registry,health,coordinator,sequence


def message(registry,node,sequence,*,kind=REQUEST,observed=EPOCH,event_mask=1,query=None,boot=10,**changes):
    p=registry.public(node)
    fields=dict(kind=kind,peer_id=p["radio_id"],origin_id=p["radio_id"] if query is None else query["membership"][0]["radio_id"],
        boot_id=boot,query_id=1 if query is None else query["query_id"],sequence=sequence,
        observed_epoch=observed,deadline_epoch=EPOCH+30 if query is None else query["deadline_epoch"],
        profile_id=1,event_mask=event_mask if kind!=HEARTBEAT else 0,valid_channel_mask=63,
        clock_uncertainty_seconds=2.,measurements=RAW,scores=(1.,1.,1.))
    fields.update(changes)
    return encode(Frame(**fields),registry.entries[node].key)


def open_default(registry,coordinator,sequences,event_mask=1):
    origin="fixture-0"
    wire=message(registry,origin,sequences[origin],event_mask=event_mask)
    sequences[origin]+=1
    return coordinator.open_query(origin,event_mask,iso(EPOCH+1),wire)


def vote_all(registry,coordinator,sequences,q,event_mask=1):
    for i,p in enumerate(q["membership"][1:]):
        n=p["node_id"]
        wire=message(registry,n,sequences[n],kind=VOTE,query=q,event_mask=event_mask)
        sequences[n]+=1
        coordinator.accept_vote(wire,iso(EPOCH+2+i))
