"""Discrete reservations, collisions, half duplex and conservative rolling duty.

No ALOHA probability substitutes for the actual scheduled transmissions here.
Link-loss draws remain explicit synthetic assumptions, not measured RF behavior.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
import math

from ml.himachal.radio import airtime, load_profile, validate_profile


@dataclass
class Transmission:
    identifier: int
    sender: str
    receiver: str
    kind: str
    start: float
    end: float
    payload_bytes: int
    domain: int
    channel: int
    role: str
    attempt: int
    wire: bytes | None=None
    cancelled: bool=False


class Scheduler:
    def __init__(self,profile=None):
        self.profile=profile or load_profile()
        validate_profile(self.profile)
        self.transmissions=[]
        self.by_device={}
        self.by_channel={}
        self.maximum_airtime=0.
        self.rejections={"duty_deadline":0,"busy_deadline":0}
        self.defer_seconds=[]

    def _used(self,reservations,end):
        beginning=end-self.profile["duty_observation_seconds"]
        # Count the entire frame if any of it can lie in the window. This is
        # conservative at both edges; actual transmitted duration cannot exceed
        # this accounting. No per-channel duty reset is permitted.
        return sum(t.end-t.start for t in reservations if not t.cancelled and t.end>beginning and t.start<end)

    def reserve(self,sender,receiver,kind,earliest,deadline,payload_bytes,*,domain=0,channel=0,role="device",attempt=0):
        if (not math.isfinite(earliest) or not math.isfinite(deadline) or earliest>=deadline
                or role not in {"device","access_point"} or not 0<=channel<len(self.profile["channels_mhz"])
                or type(payload_bytes) is not int or not 1<=payload_bytes<=255):
            raise ValueError("Bounded valid radio reservation required")
        duration=airtime(payload_bytes,profile=self.profile)
        existing=self.by_device.setdefault(sender,[])
        duty=self.profile["access_point_duty_fraction" if role=="access_point" else "device_duty_fraction"]
        budget=duty*self.profile["duty_observation_seconds"]
        start=earliest
        reason="busy_deadline"
        # Each iteration advances beyond an actual finite reservation boundary;
        # at most existing reservations + two passes are required.
        for _ in range(2*len(existing)+3):
            overlap=next((t for t in existing if not t.cancelled and t.start<start+duration and t.end>start),None)
            if overlap is not None:
                start=overlap.end+self.profile["slot_guard_seconds"]
                reason="busy_deadline"
                if start+duration>deadline:
                    break
                continue
            # Also protect pre-reserved future transmissions whose rolling
            # window would include this newly inserted earlier packet.
            checks=[start+duration]+[t.end for t in existing if not t.cancelled and start<t.end<start+duration+self.profile["duty_observation_seconds"]]
            violating=[t for t in checks if self._used(existing,t)+duration>budget+1e-9]
            if violating:
                active=[t for t in existing if not t.cancelled and t.end>min(violating)-self.profile["duty_observation_seconds"] and t.start<max(violating)]
                if not active:
                    raise ValueError("One packet exceeds the configured duty budget")
                next_release=[t.end+self.profile["duty_observation_seconds"] for t in active if t.end+self.profile["duty_observation_seconds"]>start]
                start=min(next_release) if next_release else deadline+duration
                reason="duty_deadline"
                if start+duration>deadline:
                    break
                continue
            if start+duration>deadline:
                break
            tx=Transmission(len(self.transmissions),sender,receiver,kind,start,start+duration,payload_bytes,domain,channel,role,attempt)
            self.transmissions.append(tx)
            bisect.insort(existing,tx,key=lambda t:t.start)
            group=self.by_channel.setdefault((domain,channel),[])
            bisect.insort(group,tx,key=lambda t:t.start)
            self.maximum_airtime=max(self.maximum_airtime,duration)
            self.defer_seconds.append(start-earliest)
            return tx
        self.rejections[reason]+=1
        return None

    def delivery(self,tx,rng,*,packet_loss=0.,receiver_online=True):
        if tx.cancelled:
            return False,"sender_offline"
        if not receiver_online:
            return False,"receiver_offline"
        group=self.by_channel[(tx.domain,tx.channel)]
        first=bisect.bisect_left(group,tx.start-self.maximum_airtime,key=lambda t:t.start)
        last=bisect.bisect_left(group,tx.end,key=lambda t:t.start)
        if any(not other.cancelled and other.identifier!=tx.identifier and other.start<tx.end and other.end>tx.start for other in group[first:last]):
            return False,"collision"
        if any(not other.cancelled and other.start<tx.end and other.end>tx.start for other in self.by_device.get(tx.receiver,[])):
            return False,"receiver_half_duplex"
        if rng.random()<packet_loss:
            return False,"assumed_link_loss"
        return True,"delivered"

    def receipt(self,start,end):
        if end<=start:
            raise ValueError("Positive observation interval required")
        frames=[t for t in self.transmissions if not t.cancelled and start<=t.start<end]
        counts={}
        for tx in frames:
            counts[tx.kind]=counts.get(tx.kind,0)+1
        channels={}
        for identity,rows in self.by_channel.items():
            chosen=sorted((max(start,t.start),min(end,t.end)) for t in rows if not t.cancelled and t.start<end and t.end>start)
            occupied=0.
            cursor=start
            for a,b in chosen:
                occupied+=max(0.,b-max(cursor,a))
                cursor=max(cursor,b)
            offered=sum(b-a for a,b in chosen)
            channels[f"{identity[0]}:{identity[1]}"]=dict(offered_airtime_fraction=offered/(end-start),occupied_airtime_fraction=occupied/(end-start))
        devices={}
        for device,rows in self.by_device.items():
            included=[t for t in rows if not t.cancelled and start<=t.start<end]
            if not included:
                continue
            peak=max(self._used(rows,t.end) for t in included)
            role=included[0].role
            budget=self.profile["access_point_duty_fraction" if role=="access_point" else "device_duty_fraction"]*self.profile["duty_observation_seconds"]
            if peak>budget+1e-6:
                raise AssertionError("Scheduler violated conservative device airtime budget")
            devices[device]=dict(frames=len(included),tx_seconds=sum(t.end-t.start for t in included),
                maximum_accounted_rolling_window_tx_seconds=peak,budget_seconds=budget,role=role)
        return dict(frames=len(frames),frame_bytes=sum(t.payload_bytes for t in frames),
            frames_by_kind=counts,channels=channels,devices=devices,rejections=dict(self.rejections),
            actual_phy_airtime_seconds=sum(t.end-t.start for t in frames),
            accounting="All scheduled heartbeats/queries/votes/results/ACKs/retries/relays use the same per-device rolling duty ledger")
