"""Event-driven synthetic transport that calls the real registry/health/quorum.

Local flags are injected engineering fixtures, not a weather model or labels.
Phase N supplies history-driven rule/model actors through these same interfaces.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import heapq
import math
import time
import tracemalloc

import numpy as np

from ml.himachal.consensus import Coordinator
from ml.himachal.health import Health
from ml.himachal.nodes import Registry, separation_m
from ml.himachal.radio import ACK, FRAME_BYTES, HEARTBEAT, QUERY, REQUEST, RESULT, VOTE, Frame, decode, encode, load_profile
from simulator.radio import Scheduler

SCENARIOS=("nominal","dropouts","clock_drift","common_faults","packet_loss","combined")
EPOCH=1782864000
RAW=(20.,60.,900.,25.,50.,3.)


def iso(t):
    return datetime.fromtimestamp(t,timezone.utc).isoformat()


class NetworkSimulation:
    def __init__(self,count,scenario,seed,config,*,rounds=None,topology=None):
        if scenario not in SCENARIOS or not 2<=count<=2000:
            raise ValueError("Bounded engineering node count/scenario required")
        self.n,self.scenario,self.seed=count,scenario,seed
        self.config=config
        self.rounds=rounds or config["simulation"]["rounds"]
        self.topology=topology or config["simulation"]["topology"]
        if self.topology not in {"dense","multi_valley"} or not 1<=self.rounds<=600:
            raise ValueError("Known topology and bounded round count required")
        self.rng=np.random.default_rng(config["simulation"]["seed_base"]+seed+count*1009)
        self.radio=load_profile(config["radio_profile"])
        if config["simulation"]["channels"]!=len(self.radio["channels_mhz"]):
            raise ValueError("Requested channel count differs from actual receiver profile")
        self.scheduler=Scheduler(self.radio)
        self.registry=Registry(config)
        self.health=Health(self.registry)
        self.coordinator=Coordinator(self.registry,self.health,self.radio,query_id_factory=lambda:int(self.rng.integers(1,2**63-1)))
        self.nodes=[]
        self.node_indexes={}
        self.domains={}
        self.sequences={}
        self.raw_flags={}
        self.events=[]
        self.event_number=0
        self.tx_callbacks={}
        self.tx_builders={}
        self.cases=[]
        self.case_by_query={}
        self.delivery_counts=Counter()
        self.protocol_counts=Counter()
        self.peer_ack=set()
        self.completed_queries=set()
        self.current_time=EPOCH-180
        for i in range(count):
            node=f"synthetic-actor-{i}"
            domain=i%3 if self.topology=="multi_valley" else 0
            x,y=map(float,self.rng.uniform(-2000,2000,2))
            if count==3:
                x,y=((-500,0),(500,0),(0,866))[i]
            record=dict(node_id=node,physical_site_id=f"synthetic-site-{i}",registration_id="synthetic-registration-1",
                latitude=31.71+y/111195,longitude=76.93+x/(111195*math.cos(math.radians(31.71)))+domain*.35,
                elevation_m=1000.+.05*x+.05*y,elevation_datum="surveyed_orthometric",source_class="physical_indra",
                upstream_sensor_id=f"synthetic-device-{i}",native_profile="native_minute",capability_mask=63,
                quality_weight=1.,failure_domain=f"synthetic-reviewed-domain-{i%3}",profile_id=config["profile_id"],
                sensor_height_m=2.,wind_height_m=10.,site_reviewed=True)
            self.registry.register(record,hashlib.sha256(f"SYNTHETIC_PROTOCOL_KEY_NOT_PRODUCTION:{seed}:{i}".encode()).digest())
            self.nodes.append(node)
            self.node_indexes[node]=i
            self.domains[node]=domain
            self.sequences[node]=0
        size=(self.rounds+6,count)
        stress=scenario in {"dropouts","combined"}
        self.online=self.rng.random(size)>= (.15 if stress else 0.)
        self.drift=self.rng.normal(0,80 if scenario in {"clock_drift","combined"} else 0,size)
        self.common_members=self.rng.random(count)<.35
        self.self_test_fault=self.rng.random(size)<.75
        self.common_round=self.rng.random(self.rounds+6)<.3 if scenario in {"common_faults","combined"} else np.zeros(self.rounds+6,dtype=bool)
        self.loss=.10 if scenario in {"packet_loss","combined"} else 0.

    def _round(self,t):
        return max(0,min(self.rounds+5,int((t-EPOCH)//60)+3))

    def _online(self,node,t):
        return True if node.startswith("gateway-") else bool(self.online[self._round(t),self.node_indexes[node]])

    def _gateway(self,node):
        return f"gateway-{self.domains[node]}"

    def _channel(self,node):
        return self.node_indexes[node]%len(self.radio["channels_mhz"])

    def _event(self,t,kind,*args):
        if t<self.current_time-1e-6:
            raise AssertionError("Simulation cannot create events in its past")
        self.event_number+=1
        heapq.heappush(self.events,(t,self.event_number,kind,args))

    def _send(self,sender,receiver,kind,earliest,deadline,builder,callback,*,node,attempt=0):
        earliest=max(earliest,self.current_time)
        if earliest>=deadline:
            self.protocol_counts["expired_before_queue"]+=1
            return None
        if not self._online(sender,earliest):
            self.protocol_counts["sender_offline_before_queue"]+=1
            return None
        tx=self.scheduler.reserve(sender,receiver,kind,max(earliest,self.current_time),deadline,FRAME_BYTES,
            domain=self.domains[node],channel=self._channel(node),role="access_point" if sender.startswith("gateway-") else "device",attempt=attempt)
        if tx is not None:
            self.tx_builders[tx.identifier]=builder
            self.tx_callbacks[tx.identifier]=callback
            self._event(tx.start,"tx_start",tx)
            self._event(tx.end,"tx_end",tx)
        return tx

    def _quality(self,node,t):
        i,round_id=self.node_indexes[node],self._round(t)
        drift=float(self.drift[round_id,i])
        fault=bool(self.common_round[round_id] and self.common_members[i] and self.self_test_fault[round_id,i])
        uncertainty=min(65.535,abs(drift))
        observed=int(math.floor(t/60)*60)+int(round(drift/60))*60
        return dict(observed=observed,uncertainty=uncertainty,fault=fault,flags=(7 if fault else 0)|(16 if uncertainty>30 else 0),valid=0 if fault else 63)

    def _uplink(self,node,kind,*,case=None,query=None,event_mask=0):
        p=self.registry.public(node)
        quality=self._quality(node,self.current_time)
        self.sequences[node]+=1
        if query is None:
            observed=quality["observed"]
            origin=p["radio_id"]
            query_id=0 if kind==HEARTBEAT else self.sequences[node]
            deadline=int(case["deadline"]) if kind==REQUEST and case is not None else int(self.current_time+30)
        else:
            # A node may respond only for its available matching epoch. It does
            # not relabel a stale sample with the requested timestamp.
            observed=quality["observed"]
            origin=query["membership"][0]["radio_id"]
            query_id=query["query_id"]
            deadline=query["deadline_epoch"]
        mask=event_mask
        if quality["fault"] or quality["flags"]&16:
            mask=0
        scores=tuple(None if quality["fault"] else 1. if mask&(1<<i) else 0. for i in range(3))
        frame=Frame(kind,p["radio_id"],origin,10+self.node_indexes[node],query_id,self.sequences[node],observed,deadline,
            p["profile_id"],mask,quality["valid"],quality["uncertainty"],RAW,63 if quality["fault"] else 0,scores,quality["flags"])
        return encode(frame,self.registry.entries[node].key)

    def _heartbeat_received(self,tx):
        try:
            self.coordinator.ingest(tx.wire,iso(self.current_time))
            self.protocol_counts["heartbeat_accepted"]+=1
        except ValueError:
            self.protocol_counts["heartbeat_rejected_by_runtime"]+=1

    def _trigger(self,case):
        node=case["origin"]
        if not self._online(node,self.current_time):
            case["reason"]="ORIGIN_OFFLINE"
            return
        self._send(node,self._gateway(node),"request",self.current_time,case["deadline"],
            lambda:self._uplink(node,REQUEST,case=case,event_mask=case["target_mask"]),
            lambda tx:self._request_received(case,tx),node=node)

    def _request_received(self,case,tx):
        try:
            q=self.coordinator.open_query(case["origin"],case["target_mask"],iso(self.current_time),tx.wire)
        except ValueError as exc:
            case["reason"]="ORIGIN_RUNTIME_GATE:"+str(exc)
            self.protocol_counts["origin_runtime_rejected"]+=1
            return
        case["query"]=q
        self.case_by_query[q["query_id"]]=case
        duration=self.scheduler.maximum_airtime+self.radio["slot_guard_seconds"]
        query_frames=self.coordinator.peer_requests(q["query_id"])
        response_start=self.current_time+(len(query_frames)+1)*duration
        case["response_start"]=response_start
        for i,(node,wire) in enumerate(query_frames):
            self._send(self._gateway(node),node,"query",self.current_time+i*duration,q["deadline_epoch"],
                lambda w=wire:w,lambda tx,n=node,slot=i:self._query_received(case,n,slot,tx),node=node)
        self._event(q["deadline_epoch"],"timeout",case)
        if not query_frames:
            self._finish_decision(case)

    def _query_received(self,case,node,slot,tx):
        q=case["query"]
        try:
            frame=decode(tx.wire,self.registry.entries[node].key)
            if frame.kind!=QUERY or frame.boot_id!=10+self.node_indexes[node] or frame.profile_id!=self.config["profile_id"] or frame.deadline_epoch<self.current_time:
                raise ValueError("Client query identity/window")
        except ValueError:
            self.protocol_counts["client_query_rejected"]+=1
            return
        duration=self.scheduler.maximum_airtime+self.radio["slot_guard_seconds"]
        ready=max(self.current_time+self.radio["slot_guard_seconds"],case["response_start"]+slot*2*duration)
        self._send_vote(case,node,ready,0)

    def _send_vote(self,case,node,earliest,attempt):
        q=case["query"]
        if q["query_id"] in self.completed_queries or (q["query_id"],node) in self.peer_ack or earliest>=q["deadline_epoch"]:
            return
        mask=case["target_mask"] if case["local_flags"][node] else 0
        tx=self._send(node,self._gateway(node),"vote_retry" if attempt else "vote",earliest,q["deadline_epoch"],
            lambda:self._uplink(node,VOTE,case=case,query=q,event_mask=mask),
            lambda tx:self._vote_received(case,node,tx),node=node,attempt=attempt)
        if tx is not None and attempt<self.config["maximum_retries"]:
            retry=tx.end+3*(self.scheduler.maximum_airtime+self.radio["slot_guard_seconds"])
            if retry<q["deadline_epoch"]:
                self._event(retry,"retry_vote",case,node,attempt+1)

    def _downlink(self,case,node,kind,event_mask=0):
        q=case["query"]
        p=self.registry.public(node)
        frame=Frame(kind,p["radio_id"],q["membership"][0]["radio_id"],10+self.node_indexes[node],q["query_id"],
            0,q["observed_epoch"],q["deadline_epoch"],q["profile_id"],event_mask,0,0.,(None,)*6,
            scores=tuple(1. if event_mask&(1<<i) else None for i in range(3)))
        return encode(frame,self.registry.entries[node].key)

    def _vote_received(self,case,node,tx):
        q=case["query"]
        try:
            response=self.coordinator.accept_vote(tx.wire,iso(self.current_time))
        except ValueError:
            self.protocol_counts["vote_rejected_by_runtime"]+=1
            return
        self.protocol_counts[response["status"]]+=1
        if not case.get("replay_injected") and (self.scenario=="combined" or self.rng.random()<.1):
            case["replay_injected"]=True
            self._send(node,self._gateway(node),"replayed_vote",self.current_time+2*(self.scheduler.maximum_airtime+self.radio["slot_guard_seconds"]),q["deadline_epoch"],
                lambda w=tx.wire:w,lambda replay:self._vote_received(case,node,replay),node=node,attempt=1)
        self._send(self._gateway(node),node,"vote_ack",self.current_time+self.radio["slot_guard_seconds"],q["deadline_epoch"],
            lambda:self._downlink(case,node,ACK),lambda tx:self.peer_ack.add((q["query_id"],node)),node=node)
        self._finish_decision(case)

    def _finish_decision(self,case):
        q=case.get("query")
        if q is None or q["query_id"] in self.completed_queries:
            return
        result=self.coordinator.finalize(q["query_id"],iso(self.current_time),force_timeout=self.current_time>=q["deadline_epoch"])
        if result["status"]=="PENDING":
            return
        self.completed_queries.add(q["query_id"])
        case["decision"]=result
        case["decision_latency"]=self.current_time-case["trigger_time"]
        target=next(iter(result["event_results"].values()))
        if target["corroborated"]:
            self._send_result(case,0)

    def _send_result(self,case,attempt):
        q=case["query"]
        if case.get("result_received") or self.current_time>=q["deadline_epoch"]:
            return
        node=case["origin"]
        tx=self._send(self._gateway(node),node,"result_retry" if attempt else "result",self.current_time+self.radio["slot_guard_seconds"],q["deadline_epoch"],
            lambda:self._downlink(case,node,RESULT,case["target_mask"]),lambda tx:self._result_received(case,tx),node=node,attempt=attempt)
        if tx and attempt<self.config["maximum_retries"]:
            retry=tx.end+2*(self.scheduler.maximum_airtime+self.radio["slot_guard_seconds"])
            if retry<q["deadline_epoch"]:
                self._event(retry,"retry_result",case,attempt+1)

    def _result_received(self,case,tx):
        node=case["origin"]
        frame=decode(tx.wire,self.registry.entries[node].key)
        if frame.kind==RESULT and frame.query_id==case["query"]["query_id"] and frame.deadline_epoch>=self.current_time:
            case["result_received"]=True
            case["delivery_latency"]=self.current_time-case["trigger_time"]
            self._send(node,self._gateway(node),"result_ack",self.current_time+self.radio["slot_guard_seconds"],frame.deadline_epoch,
                lambda:self._downlink(case,node,ACK),lambda tx:None,node=node)

    def _plan(self):
        # Three radio warm-up minutes precede the measured interval. They use
        # the same real ledger and can fail through collisions/clock/dropout.
        phases=self.rng.uniform(0,55,self.n)
        for round_number in range(-3,self.rounds):
            base=EPOCH+round_number*60
            for i,node in enumerate(self.nodes):
                when=base+float(phases[i])+float(self.rng.uniform(0,1))
                self._send(node,self._gateway(node),"heartbeat",when,base+60,
                    lambda n=node:self._uplink(n,HEARTBEAT),self._heartbeat_received,node=node)
        for i in range(self.rounds):
            node=self.nodes[int(self.rng.integers(self.n))]
            positive=bool(self.rng.random()<self.config["simulation"]["positive_query_fraction"])
            local={}
            for peer in self.nodes:
                nearby=separation_m(self.registry.public(node),self.registry.public(peer))<=2000
                flag=bool(self.rng.random()<(.9 if positive and nearby else .025))
                index=self.node_indexes[peer]
                if self.common_round[i+3] and self.common_members[index]:
                    flag=True
                local[peer]=flag
            local[node]=True # Conditional on a local indication, including false indications.
            case=dict(origin=node,positive=positive,target_mask=1<<(i%3),local_flags=local,
                trigger_time=EPOCH+i*60+5.,deadline=EPOCH+i*60+35.,result_received=False)
            self.cases.append(case)
            self._event(case["trigger_time"],"trigger",case)
            self._event(case["deadline"],"local_timeout",case)

    def run(self):
        started=time.process_time()
        tracemalloc.start()
        self._plan()
        while self.events:
            now,_,kind,args=heapq.heappop(self.events)
            self.current_time=now
            if kind=="tx_start":
                tx=args[0]
                builder=self.tx_builders.pop(tx.identifier)
                if not self._online(tx.sender,now):
                    tx.cancelled=True
                else:
                    tx.wire=builder()
                    if len(tx.wire)!=tx.payload_bytes:
                        raise AssertionError("Actual wire length differs from reserved airtime")
            elif kind=="tx_end":
                tx=args[0]
                delivered,reason=self.scheduler.delivery(tx,self.rng,packet_loss=self.loss,receiver_online=self._online(tx.receiver,now))
                self.delivery_counts[reason]+=1
                callback=self.tx_callbacks.pop(tx.identifier)
                if delivered:
                    callback(tx)
            elif kind=="trigger":
                self._trigger(*args)
            elif kind=="timeout":
                self._finish_decision(*args)
            elif kind=="retry_vote":
                self._send_vote(args[0],args[1],now,args[2])
            elif kind=="retry_result":
                self._send_result(*args)
            elif kind=="local_timeout":
                args[0]["local_timer_expired"]=not args[0]["result_received"]
        _,peak=tracemalloc.get_traced_memory()
        tracemalloc.stop()
        metrics=self.scheduler.receipt(EPOCH,EPOCH+self.rounds*60)
        positives=[c for c in self.cases if c["positive"]]
        negatives=[c for c in self.cases if not c["positive"]]
        warned=[c for c in self.cases if c["result_received"]]
        false=sum(not c["positive"] for c in warned)
        misses=sum(not c["result_received"] for c in positives)
        latencies=[c.get("delivery_latency",c["deadline"]-c["trigger_time"]) for c in self.cases]
        successful=[c["delivery_latency"] for c in warned]
        return dict(nodes=self.n,scenario=self.scenario,seed=self.seed,topology=self.topology,
            query_rounds=len(self.cases),positive_synthetic_queries=len(positives),negative_synthetic_queries=len(negatives),
            corroborated_delivered=len(warned),false_corrob_episodes=false,missed_positive_queries=misses,
            false_corrob_fraction=false/len(negatives) if negatives else None,
            missed_positive_fraction=misses/len(positives) if positives else None,
            timeout_or_unresolved_count=len(self.cases)-len(warned),
            all_query_latency_p50_s=float(np.quantile(latencies,.5)),all_query_latency_p95_s=float(np.quantile(latencies,.95)),
            successful_delivery_latency_p95_s=float(np.quantile(successful,.95)) if successful else None,
            latency_denominator="All local query indications; unresolved/no-quorum/undelivered rounds include the full declared 30s wait",
            scheduler=metrics,radio_delivery=dict(self.delivery_counts),runtime_protocol=dict(self.protocol_counts),
            cpu_seconds=time.process_time()-started,python_tracemalloc_peak_bytes=peak,
            public_dispatch=False,evidence_kind="SYNTHETIC_NETWORK_ENGINEERING_ONLY")
