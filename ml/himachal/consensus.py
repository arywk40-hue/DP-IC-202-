"""Offline-capable authenticated coordinator; no Internet dependency or dispatch."""
from __future__ import annotations

from collections import OrderedDict
import copy
import hashlib
import secrets
import struct
import threading
from datetime import datetime, timezone

from ml.himachal.neighbours import select
from ml.himachal.radio import FRAME_BYTES, HEARTBEAT, QUERY, REQUEST, VOTE, Frame, airtime, decode, encode, load_profile
from ml.operational.contracts import canonical_bytes, utc


class Coordinator:
    def __init__(self,registry,health,radio_profile=None,query_id_factory=None):
        self.registry,self.health=registry,health
        self.config=registry.config
        self.radio=radio_profile or load_profile()
        self.boots={}
        self.messages=OrderedDict()
        self.queries=OrderedDict()
        self.coalescing={}
        self.last_now=None
        self.lock=threading.RLock()
        self.query_id_factory=query_id_factory or (lambda:secrets.randbits(64) or 1)

    def _now(self,value):
        t=utc(value)
        if self.last_now is not None and t<self.last_now:
            raise ValueError("Coordinator clock rollback; operator clock recovery required")
        self.last_now=t
        return t

    def _decode(self,wire):
        if not isinstance(wire,bytes) or len(wire)!=FRAME_BYTES:
            raise ValueError("Invalid frame size")
        radio_id=struct.unpack_from("!I",wire,6)[0]
        node_id=self.registry.radio_ids.get(radio_id)
        if node_id not in self.registry.entries:
            raise ValueError("Unknown registered peer")
        entry=self.registry.entries[node_id]
        return node_id,decode(wire,entry.key)

    def _authenticate_fresh(self,wire,now,allow_boot):
        node,frame=self._decode(wire)
        r=self.registry.public(node)
        profile=self.config["cadence_profiles"][r["native_profile"]]
        age=now.timestamp()-frame.observed_epoch
        if not 0<=age<=profile["freshness_seconds"] or frame.clock_uncertainty_seconds>self.config["maximum_clock_uncertainty_seconds"]:
            raise ValueError("Stale/future/clock-uncertain vote")
        if frame.observed_epoch%profile["native_cadence_seconds"]:
            raise ValueError("Observation does not lie on registered native grid")
        if frame.profile_id!=r["profile_id"] or frame.profile_id!=self.config["profile_id"]:
            raise ValueError("Feature/model/network profile mismatch")
        key=(node,r["registration_id"],frame.boot_id,frame.sequence)
        fingerprint=hashlib.sha256(wire).hexdigest()
        existing=self.boots.get(node)
        if existing and existing["registration_id"]==r["registration_id"] and frame.boot_id in existing["retired"]:
            raise ValueError("Retired boot replay")
        if not allow_boot and (existing is None or existing["registration_id"]!=r["registration_id"] or existing["active"]!=frame.boot_id):
            raise ValueError("Unestablished boot cannot vote")
        if key in self.messages:
            if self.messages[key]!=fingerprint:
                raise ValueError("Sequence reused with changed authenticated content")
            return node,frame,True
        current=self.boots.get(node)
        if current is None or current["registration_id"]!=r["registration_id"]:
            current=dict(registration_id=r["registration_id"],active=None,retired=set(),last_sequence=-1)
            self.boots[node]=current
        if current["active"]!=frame.boot_id:
            if frame.boot_id in current["retired"] or not allow_boot:
                raise ValueError("Retired/unestablished boot cannot vote")
            if len(current["retired"])>=self.config["maximum_boots_per_key"]:
                raise ValueError("Boot budget exhausted; rotate registration/key")
            if current["active"] is not None:
                current["retired"].add(current["active"])
                self.health.restart(node)
            current["active"],current["last_sequence"]=frame.boot_id,-1
        if frame.sequence<=current["last_sequence"]:
            raise ValueError("Replayed or out-of-order sequence")
        current["last_sequence"]=frame.sequence
        self.messages[key]=fingerprint
        while len(self.messages)>self.config["maximum_query_cache"]:
            self.messages.popitem(last=False)
        return node,frame,False

    def ingest(self,wire,now):
        """Only authenticated current telemetry establishes boot/health, not a vote."""
        with self.lock:
            reference=self._now(now)
            if self._decode(wire)[1].kind not in {HEARTBEAT,REQUEST}:
                raise ValueError("Telemetry/boot establishment requires heartbeat/request")
            node,frame,duplicate=self._authenticate_fresh(wire,reference,True)
            if duplicate:
                return {"status":"DUPLICATE_RETRY","node_id":node,"duplicate":True}
            raw_identity=hashlib.sha256(canonical_bytes(dict(epoch=frame.observed_epoch,measurements=frame.measurements,
                valid=frame.valid_channel_mask,fault=frame.fault_mask,clock=frame.clock_uncertainty_seconds,battery=bool(frame.flags&8)))).hexdigest()
            previous=self.health.records.get(node)
            t=utc(datetime.fromtimestamp(frame.observed_epoch,timezone.utc))
            registration=self.registry.public(node)["registration_id"]
            if previous and previous.get("observed_at") and previous["registration_id"]==registration and utc(previous["observed_at"])==t:
                if previous.get("snapshot_identity")!=raw_identity:
                    raise ValueError("Conflicting telemetry at same observation time")
            else:
                self.health.update(node,t.isoformat(),reference.isoformat(),valid_mask=frame.valid_channel_mask,
                    self_test_fault_mask=frame.fault_mask,clock_uncertainty=frame.clock_uncertainty_seconds,
                    battery_critical=bool(frame.flags&8))
                self.health.records[node]["snapshot_identity"]=raw_identity
            return dict(status="ACCEPTED",node_id=node,duplicate=False,health=self.health.assess(node,reference.isoformat()))

    def open_query(self,origin_id,event_mask,now,origin_frame):
        with self.lock:
            reference=self._now(now)
            origin,frame=self._decode(origin_frame)
            if origin!=origin_id or frame.kind!=REQUEST or type(event_mask) is not int or not 1<=event_mask<=7 or frame.event_mask&event_mask!=event_mask:
                raise ValueError("Authenticated origin request and local candidate mask required")
            self.ingest(origin_frame,reference.isoformat())
            node=self.registry.public(origin_id)
            required=31 if event_mask==1 else 63
            if (node["source_class"]!="physical_indra" or not node["site_reviewed"] or node["quality_weight"]<=0
                    or not self.health.assess(origin_id,reference.isoformat(),required)["eligible"]):
                raise ValueError("Origin is not an eligible reviewed physical node")
            identity=(origin_id,node["registration_id"],frame.boot_id,event_mask,frame.observed_epoch,frame.profile_id)
            previous=self.coalescing.get(identity)
            if previous in self.queries:
                return self.snapshot(previous)
            if frame.deadline_epoch<=reference.timestamp():
                raise ValueError("Expired origin query request")
            neighbours=select(self.registry,self.health,origin_id,reference.isoformat(),required)
            # Bound wire work (pairwise authenticated query + vote + result),
            # reserve retry/guard time; duty waiting can still cause timeout.
            scheduled=(2*len(neighbours["peers"])+2)*(1+self.config["maximum_retries"])*(airtime(profile=self.radio)+self.radio["slot_guard_seconds"])
            deadline=min(frame.deadline_epoch,int(reference.timestamp()+max(self.config["query_deadline_seconds"],scheduled)+.999999))
            query_id=self.query_id_factory()
            while query_id in self.queries:
                query_id=self.query_id_factory()
            origin_snapshot=dict(node_id=origin_id,radio_id=node["radio_id"],physical_site_id=node["physical_site_id"],
                registration_id=node["registration_id"],upstream_sensor_id=node["upstream_sensor_id"],failure_domain=node["failure_domain"],
                weight=node["quality_weight"],boot_id=frame.boot_id)
            peers=[]
            for p in neighbours["peers"]:
                boot=self.boots.get(p["node_id"])
                if boot and boot["registration_id"]==p["registration_id"]:
                    peers.append({**p,"boot_id":boot["active"]})
            q=dict(query_id=query_id,origin_id=origin_id,event_mask=event_mask,observed_epoch=frame.observed_epoch,
                created_epoch=int(reference.timestamp()),deadline_epoch=deadline,profile_id=frame.profile_id,
                membership=[origin_snapshot,*peers],neighbours=neighbours,votes={origin_id:frame.event_mask},
                final=None,identity=identity)
            self.queries[query_id]=q
            self.coalescing[identity]=query_id
            while len(self.queries)>self.config["maximum_query_cache"]:
                old_id,old=self.queries.popitem(last=False)
                self.coalescing.pop(old["identity"],None)
            return self.snapshot(query_id)

    def snapshot(self,query_id):
        q=self.queries[query_id]
        return copy.deepcopy({k:v for k,v in q.items() if k not in {"votes","identity","final"}})

    def peer_requests(self,query_id):
        q=self.queries[query_id]
        result=[]
        for i,peer in enumerate(q["membership"][1:]):
            frame=Frame(QUERY,peer["radio_id"],q["membership"][0]["radio_id"],peer["boot_id"],query_id,
                i,q["observed_epoch"],q["deadline_epoch"],q["profile_id"],q["event_mask"],0,0.,(None,)*6,ttl=0)
            result.append((peer["node_id"],encode(frame,self.registry.entries[peer["node_id"]].key)))
        return result

    def accept_vote(self,wire,now):
        with self.lock:
            reference=self._now(now)
            if self._decode(wire)[1].kind!=VOTE:
                raise ValueError("Only votes enter the vote handler")
            node,frame,_=self._authenticate_fresh(wire,reference,False)
            if frame.kind!=VOTE or frame.query_id not in self.queries:
                raise ValueError("Unsolicited vote; responses cannot create queries")
            q=self.queries[frame.query_id]
            if q["final"] is not None or reference.timestamp()>q["deadline_epoch"]:
                raise ValueError("Finalized/expired query")
            member=next((m for m in q["membership"][1:] if m["node_id"]==node),None)
            if (member is None or frame.boot_id!=member["boot_id"] or self.registry.public(node)["registration_id"]!=member["registration_id"]
                    or frame.origin_id!=q["membership"][0]["radio_id"] or frame.profile_id!=q["profile_id"]
                    or frame.deadline_epoch!=q["deadline_epoch"] or frame.observed_epoch!=q["observed_epoch"]):
                raise ValueError("Vote differs from locked origin/boot/membership/window/version")
            required=31 if q["event_mask"]==1 else 63
            if (frame.valid_channel_mask&required)!=required or frame.fault_mask&required or frame.flags&24:
                raise ValueError("Vote lacks required healthy synchronized channels")
            if node in q["votes"]:
                if q["votes"][node]!=frame.event_mask:
                    raise ValueError("Conflicting duplicate vote")
                return dict(status="DUPLICATE_RETRY",query_id=frame.query_id,node_id=node)
            q["votes"][node]=frame.event_mask
            return dict(status="VOTE_ACCEPTED",query_id=frame.query_id,node_id=node)

    def finalize(self,query_id,now,*,force_timeout=False):
        with self.lock:
            reference=self._now(now)
            q=self.queries[query_id]
            if q["final"] is not None:
                return copy.deepcopy(q["final"])
            if not force_timeout and len(q["votes"])<len(q["membership"]) and reference.timestamp()<q["deadline_epoch"]:
                return dict(status="PENDING",query_id=query_id)
            if force_timeout and reference.timestamp()<q["deadline_epoch"]:
                raise ValueError("Cannot manufacture an early timeout")
            required=31 if q["event_mask"]==1 else 63
            valid=[]
            for member in q["membership"]:
                node=member["node_id"]
                if node not in q["votes"] or node not in self.registry.entries:
                    continue
                current=self.registry.public(node)
                if (current["registration_id"]!=member["registration_id"] or current["source_class"]!="physical_indra"
                        or self.boots.get(node,{}).get("active")!=member["boot_id"]
                        or not self.health.assess(node,reference.isoformat(),required)["eligible"]):
                    continue
                valid.append(member)
            target_results={}
            for bit,target in enumerate(("rain","snowstorm","cloudburst_risk")):
                if not q["event_mask"]&(1<<bit):
                    continue
                agreeing=[m for m in valid if q["votes"][m["node_id"]]&(1<<bit)]
                weight=sum(m["weight"] for m in valid)
                ratio=sum(m["weight"] for m in agreeing)/weight if weight else None
                independent=len({m["physical_site_id"] for m in agreeing})==len(agreeing) and len({m["upstream_sensor_id"] for m in agreeing})==len(agreeing)
                domains={m["failure_domain"] for m in agreeing if m["failure_domain"] is not None}
                corroborated=(any(m["node_id"]==q["origin_id"] for m in agreeing) and independent
                    and len(agreeing)>=self.config["minimum_agreeing_physical_nodes"] and len(domains)>=self.config["minimum_failure_domains"]
                    and ratio is not None and ratio>=self.config["minimum_weighted_agreement"])
                target_results[target]=dict(status="CORROBORATED_WARNING_CANDIDATE" if corroborated else "LOCAL_ONLY_CONSENSUS_UNAVAILABLE",
                    agreeing_count=len(agreeing),known_failure_domains=len(domains),weighted_agreement=ratio,
                    corroborated=corroborated,probability=None,risk_only=True,public_dispatch=False)
            q["final"]=dict(status="FINAL",query_id=query_id,origin_id=q["origin_id"],event_results=target_results,
                queried_count=len(q["membership"])-1,responding_count=max(0,len(valid)-int(any(m["node_id"]==q["origin_id"] for m in valid))),
                response_coverage=len(valid)/len(q["membership"]),timed_out=reference.timestamp()>=q["deadline_epoch"] and len(q["votes"])<len(q["membership"]),
                eligible_in_scanned_candidates=q["neighbours"]["eligible_in_scanned_candidates"],eligible_total=q["neighbours"]["eligible_total"],
                coverage_scope=q["neighbours"]["coverage_scope"],latency_seconds=reference.timestamp()-q["created_epoch"],
                human_confirmation_required=True,public_dispatch=False)
            return copy.deepcopy(q["final"])
