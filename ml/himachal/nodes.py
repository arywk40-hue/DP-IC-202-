"""Operator-provisioned dynamic registry; auth keys never enter public records."""
from __future__ import annotations

from dataclasses import dataclass, field
import copy
import json
import math
import hashlib
from pathlib import Path
import re

import numpy as np
from scipy.spatial import cKDTree

CONFIG = Path(__file__).resolve().parents[2]/"ml/configs/himachal_network_v1.json"
EARTH_RADIUS_M = 6371008.8


def load_config(path=CONFIG):
    config=json.loads(Path(path).read_text())
    if (config.get("schema_version")!="indra_himachal_network_v1" or config["maximum_peers"]>6
            or not 6<=config["maximum_candidate_scan"]<=256 or config["public_notifications_enabled"] is not False):
        raise ValueError("Bounded research network profile required")
    return config


def sphere(latitude, longitude):
    lat,lon=math.radians(latitude),math.radians(longitude)
    return EARTH_RADIUS_M*np.array([math.cos(lat)*math.cos(lon),math.cos(lat)*math.sin(lon),math.sin(lat)])


def separation_m(a,b):
    chord=float(np.linalg.norm(sphere(a["latitude"],a["longitude"])-sphere(b["latitude"],b["longitude"])))
    return 2*EARTH_RADIUS_M*math.asin(min(1.,chord/(2*EARTH_RADIUS_M)))


@dataclass
class Registration:
    public: dict
    key: bytes=field(repr=False)


class Registry:
    def __init__(self,config=None):
        self.config=config or load_config()
        self.entries={}
        self.radio_ids={}
        self.generation=0
        self._tree=None
        self._indexed_generation=-1
        self._ids=[]
        self._used_keys={}

    def register(self,record,key):
        required={"node_id","physical_site_id","registration_id","latitude","longitude","elevation_m","elevation_datum",
                  "source_class","upstream_sensor_id","native_profile","capability_mask","quality_weight","failure_domain",
                  "profile_id","sensor_height_m","wind_height_m","site_reviewed"}
        if not isinstance(record,dict) or set(record)-required-{"radio_id"} or not required<=set(record):
            raise ValueError("Exact reviewed registration metadata required")
        r=dict(record)
        for name in ("node_id","physical_site_id","registration_id","upstream_sensor_id"):
            if not isinstance(r[name],str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,96}",r[name]):
                raise ValueError("Invalid bounded registration identity")
        if not isinstance(key,bytes) or len(key)<32 or len(key)>64:
            raise ValueError("Provision an independent per-node 32-64 byte key offline")
        if any(other.key==key for name,other in self.entries.items() if name!=r["node_id"]):
            raise ValueError("Per-node keys must be distinct")
        for name,lo,hi in (("latitude",-90,90),("longitude",-180,180),("elevation_m",-500,9000),("quality_weight",0,1)):
            if type(r[name]) not in {int,float} or not math.isfinite(r[name]) or not lo<=r[name]<=hi:
                raise ValueError("Finite surveyed coordinates/height/quality required")
        if r["elevation_datum"] not in {"EGM96","EGM2008","surveyed_orthometric"}:
            raise ValueError("Known orthometric elevation datum required")
        if r["source_class"] not in {"physical_indra","observed_external_station","modeled_grid","synthetic_demo"}:
            raise ValueError("Unknown source class")
        for name in ("sensor_height_m","wind_height_m"):
            if r[name] is not None and (type(r[name]) not in {int,float} or not math.isfinite(r[name]) or not 0<=r[name]<=100):
                raise ValueError("Instrument height must be explicit finite or null")
        if r["failure_domain"] is not None and (not isinstance(r["failure_domain"],str) or not r["failure_domain"].strip()):
            raise ValueError("Failure domain must be reviewed string or null")
        if (r["native_profile"] not in self.config["cadence_profiles"] or type(r["capability_mask"]) is not int
                or not 0<=r["capability_mask"]<=63 or type(r["profile_id"]) is not int or r["profile_id"]!=self.config["profile_id"] or type(r["site_reviewed"]) is not bool):
            raise ValueError("Unknown cadence/capability/version profile")
        for node,other in self.entries.items():
            if node!=r["node_id"] and (other.public["physical_site_id"]==r["physical_site_id"] or other.public["upstream_sensor_id"]==r["upstream_sensor_id"]):
                raise ValueError("Active aliases cannot manufacture independent physical nodes")
        previous=self.entries.get(r["node_id"])
        key_hash=hashlib.sha256(key).hexdigest()
        retired=self._used_keys.get(r["node_id"],{})
        if r["registration_id"] in retired and (previous is None or previous.public["registration_id"]!=r["registration_id"]):
            raise ValueError("Retired registration cannot be reused")
        if previous and previous.public["registration_id"]!=r["registration_id"] and previous.key==key:
            raise ValueError("Relocation/registration change requires rotated authentication key")
        if (previous is None or previous.public["registration_id"]!=r["registration_id"]) and key_hash in retired.values():
            raise ValueError("Do not reuse retired registration keys")
        radio=r.get("radio_id",previous.public["radio_id"] if previous else max(self.radio_ids,default=0)+1)
        if type(radio) is not int or not 1<=radio<=0xffffffff or radio in self.radio_ids and self.radio_ids[radio]!=r["node_id"]:
            raise ValueError("Radio ID reserved or already assigned")
        r["radio_id"]=radio
        if previous and previous.public["registration_id"]==r["registration_id"]:
            if previous.public!=r or previous.key!=key:
                raise ValueError("Changed site/key requires a new reviewed registration ID")
            return dict(r)
        if previous and radio!=previous.public["radio_id"]:
            raise ValueError("Retain radio identity across registration versions")
        self.entries[r["node_id"]]=Registration(r,key)
        self._used_keys.setdefault(r["node_id"],{})[r["registration_id"]]=key_hash
        self.radio_ids[radio]=r["node_id"]
        self.generation+=1
        return dict(r)

    def remove(self,node_id):
        if node_id not in self.entries:
            raise ValueError("Unknown node")
        del self.entries[node_id]
        # Radio IDs stay reserved, preventing accidental identity reuse.
        self.generation+=1

    def public(self,node_id):
        return dict(self.entries[node_id].public)

    def load_provisioning(self,registrations_path,keys_path):
        """Load operator-managed offline provisioning; never return key material.

        Keep the keys file in ignored/private storage with owner-only permissions.
        The same verified registry can run on an isolated local gateway.
        """
        from ml.operational.ingestion import strict_json
        paths=[Path(registrations_path),Path(keys_path)]
        if any(p.stat().st_size>64_000_000 for p in paths):
            raise ValueError("Partition large provisioning batches")
        records=strict_json(paths[0].read_bytes())
        keys=strict_json(paths[1].read_bytes())
        if not isinstance(records,list) or not isinstance(keys,dict) or {r["node_id"] for r in records}!=set(keys):
            raise ValueError("Provisioning identity/key sets must agree exactly")
        # Validate in a temporary registry before changing the active one.
        probe=Registry(self.config)
        # Retired identities and radio reservations are part of validation too.
        # Rebuilding only active entries could accept a retired record in the
        # probe, then fail midway through applying the batch to this registry.
        probe.entries=copy.deepcopy(self.entries)
        probe.radio_ids=dict(self.radio_ids)
        probe._used_keys=copy.deepcopy(self._used_keys)
        probe.generation=self.generation
        for record in records:
            probe.register(record,bytes.fromhex(keys[record["node_id"]]))
        self.entries=probe.entries
        self.radio_ids=probe.radio_ids
        self._used_keys=probe._used_keys
        self.generation=probe.generation
        return [self.public(r["node_id"]) for r in records]

    def nearest_candidates(self,node_id):
        if self.generation!=self._indexed_generation:
            self._ids=sorted(self.entries)
            self._tree=cKDTree([sphere(self.entries[n].public["latitude"],self.entries[n].public["longitude"]) for n in self._ids]) if self._ids else None
            self._indexed_generation=self.generation
        if self._tree is None:
            return [],False
        origin=self.public(node_id)
        k=min(len(self._ids),self.config["maximum_candidate_scan"]+1)
        _,indexes=self._tree.query(sphere(origin["latitude"],origin["longitude"]),k=k)
        candidates=[self._ids[int(i)] for i in np.atleast_1d(indexes) if self._ids[int(i)]!=node_id]
        candidates=candidates[:self.config["maximum_candidate_scan"]]
        return candidates,len(self._ids)-1>len(candidates)
