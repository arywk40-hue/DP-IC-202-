"""Channel-specific exclusion; regional weather is not a proved sensor fault."""
from __future__ import annotations

import math

from ml.operational.contracts import utc


class Health:
    def __init__(self,registry):
        self.registry=registry
        self.config=registry.config
        self.records={}

    def restart(self,node_id):
        previous=self.records.get(node_id,{})
        self.records[node_id]=dict(registration_id=self.registry.public(node_id)["registration_id"],recovery=[0]*6,
            excluded_mask=63,drift_since=previous.get("drift_since",{}),
            maintenance_required_mask=previous.get("maintenance_required_mask",0),notes=previous.get("notes",[]))

    def update(self,node_id,observed_at,received_at,*,valid_mask=63,clock_uncertainty=0.,
               self_test_fault_mask=0,crc_ok=True,battery_critical=False):
        node=self.registry.public(node_id)
        t,received=utc(observed_at),utc(received_at)
        if type(valid_mask) is not int or not 0<=valid_mask<=63 or type(self_test_fault_mask) is not int or not 0<=self_test_fault_mask<=63:
            raise ValueError("Six-channel quality masks required")
        if type(clock_uncertainty) not in {int,float} or not math.isfinite(clock_uncertainty) or clock_uncertainty<0:
            raise ValueError("Explicit finite clock uncertainty required")
        previous=self.records.get(node_id)
        if previous and previous.get("observed_at") and previous["registration_id"]==node["registration_id"] and t<=utc(previous["observed_at"]):
            raise ValueError("Out-of-order or duplicate health update")
        if t>received:
            raise ValueError("Future observation cannot establish live freshness")
        if previous is None or previous["registration_id"]!=node["registration_id"]:
            previous=dict(recovery=[0]*6,excluded_mask=63,drift_since={},maintenance_required_mask=0,notes=[])
        profile=self.config["cadence_profiles"][node["native_profile"]]
        if previous.get("observed_at") and (t-utc(previous["observed_at"])).total_seconds()>3*profile["native_cadence_seconds"]:
            previous["excluded_mask"]=63
            previous["recovery"]=[0]*6
        bad=(63^valid_mask)|self_test_fault_mask|(0 if crc_ok else 63)
        for i in range(6):
            bit=1<<i
            if bad&bit:
                previous["excluded_mask"]|=bit
                previous["recovery"][i]=0
            elif previous["excluded_mask"]&bit:
                previous["recovery"][i]+=1
                if previous["recovery"][i]>=self.config["health_recovery_observations"] and not previous["maintenance_required_mask"]&bit:
                    previous["excluded_mask"]&=63^bit
        self.records[node_id]={**previous,"registration_id":node["registration_id"],"observed_at":t.isoformat(),
            "received_at":received.isoformat(),"valid_mask":valid_mask,"clock_uncertainty":clock_uncertainty,
            "battery_critical":battery_critical is True}

    def residual_diagnostic(self,node_id,channel_mask,at,*,persistent,independent_fault_evidence,evidence_id):
        state=self.records[node_id]
        if type(channel_mask) is not int or not 1<=channel_mask<=63 or not evidence_id:
            raise ValueError("Bounded channel mask and identified diagnostic evidence required")
        now=utc(at)
        key=str(channel_mask)
        if not persistent:
            state["drift_since"].pop(key,None)
            return
        state["drift_since"].setdefault(key,now.isoformat())
        age=(now-utc(state["drift_since"][key])).total_seconds()
        if independent_fault_evidence is True and age>=self.config["drift_persistence_seconds"]:
            state["excluded_mask"]|=channel_mask
            state["maintenance_required_mask"]|=channel_mask
            state["notes"]=(state["notes"]+["CONFIRMED_PERSISTENT_FAULT:"+str(evidence_id)])[-32:]
        elif independent_fault_evidence is not True:
            state["notes"]=(state["notes"]+["REGIONAL_OR_SENSOR_CHANGE_UNRESOLVED:"+str(evidence_id)])[-32:]

    def clear_after_maintenance(self,node_id,channel_mask,review_id):
        if type(channel_mask) is not int or not 1<=channel_mask<=63 or not isinstance(review_id,str) or not review_id.strip():
            raise ValueError("Identified maintenance review required")
        r=self.records[node_id]
        r["maintenance_required_mask"]&=63^channel_mask
        r["excluded_mask"]|=channel_mask
        for i in range(6):
            if channel_mask&(1<<i):
                r["recovery"][i]=0
        r["notes"]=(r["notes"]+["MAINTENANCE:"+review_id])[-32:]

    def assess(self,node_id,now,required_channels=63):
        node=self.registry.public(node_id)
        record=self.records.get(node_id)
        reasons=[]
        if record is None or not record.get("observed_at") or record["registration_id"]!=node["registration_id"]:
            return dict(eligible=False,status="UNAVAILABLE",reasons=["NO_CURRENT_REGISTRATION_OBSERVATION"],valid_channel_mask=0)
        profile=self.config["cadence_profiles"][node["native_profile"]]
        age=(utc(now)-utc(record["observed_at"])).total_seconds()
        heartbeat_age=(utc(now)-utc(record["received_at"])).total_seconds()
        if age<0 or heartbeat_age<0:
            reasons.append("CLOCK_ROLLBACK_OR_FUTURE")
        if age>profile["freshness_seconds"]:
            reasons.append("STALE_OBSERVATION")
        if heartbeat_age>3*profile["heartbeat_seconds"]:
            reasons.append("HEARTBEATS_MISSING")
        if record["clock_uncertainty"]>self.config["maximum_clock_uncertainty_seconds"]:
            reasons.append("CLOCK_UNCERTAIN")
        if record["battery_critical"]:
            reasons.append("BATTERY_CRITICAL")
        valid=record["valid_mask"]&(63^record["excluded_mask"])&node["capability_mask"]
        if valid&required_channels!=required_channels:
            reasons.append("REQUIRED_CHANNELS_EXCLUDED_OR_MISSING")
        return dict(eligible=not reasons,status="HEALTHY" if not reasons else "DEGRADED",reasons=reasons,
                    valid_channel_mask=valid,observation_age_seconds=age,heartbeat_age_seconds=heartbeat_age,
                    clock_uncertainty_seconds=record["clock_uncertainty"],notes=list(record["notes"]))
