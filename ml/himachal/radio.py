"""Actual authenticated frame codec and conditional radio-profile constraints."""
from __future__ import annotations

import binascii
from dataclasses import dataclass
import hashlib
import hmac
import json
import math
from pathlib import Path
import struct

from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS

BODY=struct.Struct("!2sBBBBIIQQIIIHBBH6hB3B")
FRAME_BYTES=BODY.size+16+2
REQUEST,QUERY,VOTE,RESULT,HEARTBEAT,ACK=range(6)
SCALES=(100,100,10,1,1,100)
MISSING=-32768
PROFILE=Path(__file__).resolve().parents[2]/"configs/india_radio_profile_v1.json"


@dataclass(frozen=True)
class Frame:
    kind: int
    peer_id: int
    origin_id: int
    boot_id: int
    query_id: int
    sequence: int
    observed_epoch: int
    deadline_epoch: int
    profile_id: int
    event_mask: int
    valid_channel_mask: int
    clock_uncertainty_seconds: float
    measurements: tuple
    fault_mask: int=0
    scores: tuple=(None,None,None)
    flags: int=0
    ttl: int=0


def half_away(value):
    return math.floor(value+.5) if value>=0 else math.ceil(value-.5)


def _check(frame):
    for value,bits in ((frame.peer_id,32),(frame.origin_id,32),(frame.boot_id,64),(frame.query_id,64),
                       (frame.sequence,32),(frame.observed_epoch,32),(frame.deadline_epoch,32),(frame.profile_id,16)):
        if type(value) is not int or not 0<=value<2**bits:
            raise ValueError("Frame integer outside its exact wire representation")
    if any(type(v) is not int for v in (frame.kind,frame.flags,frame.ttl,frame.event_mask,frame.valid_channel_mask,frame.fault_mask)):
        raise ValueError("Integer masks/types required")
    if (frame.kind not in range(6) or frame.flags&~63 or not 0<=frame.ttl<=1
            or not 0<=frame.event_mask<=7 or not 0<=frame.valid_channel_mask<=63 or not 0<=frame.fault_mask<=63
            or len(frame.measurements)!=6 or len(frame.scores)!=3 or type(frame.clock_uncertainty_seconds) not in {int,float} or not 0<=frame.clock_uncertainty_seconds<=65.535
            or not math.isfinite(frame.clock_uncertainty_seconds)):
        raise ValueError("Invalid frame type/mask/cadence/score contract")
    if frame.kind in {REQUEST,VOTE,RESULT} and frame.event_mask&(frame.flags&7):
        raise ValueError("Unavailable target cannot be an affirmative event vote")


def encode(frame: Frame,key: bytes):
    if not isinstance(key,bytes) or len(key)<32:
        raise ValueError("Provision a per-node authentication key")
    _check(frame)
    measurements=[]
    for i,(v,scale,channel) in enumerate(zip(frame.measurements,SCALES,RAW_SENSOR_COLUMNS)):
        if not frame.valid_channel_mask&(1<<i):
            measurements.append(MISSING)
            continue
        if v is None or isinstance(v,bool) or not math.isfinite(v) or not PHYSICAL_RANGES[channel][0]<=v<=PHYSICAL_RANGES[channel][1]:
            raise ValueError("Valid-channel mask contradicts measurement/range")
        measurements.append(half_away(v*scale))
    scores=[]
    for v in frame.scores:
        if v is not None and (type(v) not in {int,float} or not math.isfinite(v) or not 0<=v<=1):
            raise ValueError("Raw rule scores must be finite in [0,1] or unavailable")
        scores.append(255 if v is None else half_away(v*254))
    body=BODY.pack(b"IH",1,frame.kind,frame.flags,frame.ttl,frame.peer_id,frame.origin_id,frame.boot_id,frame.query_id,
                   frame.sequence,frame.observed_epoch,frame.deadline_epoch,frame.profile_id,frame.event_mask,
                   frame.valid_channel_mask,math.ceil(frame.clock_uncertainty_seconds*1000),*measurements,frame.fault_mask,*scores)
    signed=body+hmac.new(key,body,hashlib.sha256).digest()[:16]
    return signed+struct.pack("!H",binascii.crc_hqx(signed,0xffff))


def decode(wire: bytes,key: bytes) -> Frame:
    if not isinstance(wire,bytes) or len(wire)!=FRAME_BYTES or not isinstance(key,bytes) or len(key)<32:
        raise ValueError("Exact binary frame and provisioned key required")
    if binascii.crc_hqx(wire[:-2],0xffff)!=struct.unpack("!H",wire[-2:])[0]:
        raise ValueError("Frame CRC failed")
    body,tag=wire[:BODY.size],wire[BODY.size:-2]
    if not hmac.compare_digest(tag,hmac.new(key,body,hashlib.sha256).digest()[:16]):
        raise ValueError("Frame authentication failed")
    values=BODY.unpack(body)
    if values[:2]!=(b"IH",1):
        raise ValueError("Unknown frame schema")
    _,_,kind,flags,ttl,peer,origin,boot,query,seq,observed,deadline,profile,event,valid,uncertainty,*tail=values
    measurements=tuple(None if v==MISSING else v/scale for v,scale in zip(tail[:6],SCALES))
    scores=tuple(None if v==255 else v/254 for v in tail[7:])
    frame=Frame(kind,peer,origin,boot,query,seq,observed,deadline,profile,event,valid,uncertainty/1000,measurements,tail[6],scores,flags,ttl)
    _check(frame)
    for i,(v,c) in enumerate(zip(frame.measurements,RAW_SENSOR_COLUMNS)):
        if frame.valid_channel_mask&(1<<i) and (v is None or not PHYSICAL_RANGES[c][0]<=v<=PHYSICAL_RANGES[c][1]):
            raise ValueError("Authenticated but inconsistent measurement/mask")
    return frame


def load_profile(path=PROFILE):
    p=json.loads(Path(path).read_text())
    validate_profile(p)
    return p


def validate_profile(p):
    if p.get("schema_version")!="indra_india_radio_profile_v1" or p["legal_category"]!="GSR_853E_2021_TABLE_II_METEOROLOGY_POLLUTION_CONDITIONAL":
        raise ValueError("Explicit Indian meteorology equipment category required")
    if (not 7<=p["spreading_factor"]<=12 or p["bandwidth_hz"] not in (125000,) or p["coding_rate_denominator"] not in (5,6,7,8)
            or p["explicit_header"] is not True or p["radio_crc"] is not True or p["preamble_symbols"]<6):
        raise ValueError("Unsupported declared LoRa PHY")
    if (p["maximum_erp_mw"]>500 or not 0<p["device_duty_fraction"]<=.025 or not 0<p["access_point_duty_fraction"]<=.1
            or p["duty_observation_seconds"]!=3600 or not p["channels_mhz"]
            or any(not 865<=f-p["bandwidth_hz"]/2e6 or not f+p["bandwidth_hz"]/2e6<=868 for f in p["channels_mhz"])):
        raise ValueError("Incompatible ERP/duty/bandwidth/band profile")
    erp_dbm=p["transmitter_power_dbm"]+p["antenna_gain_dbi"]-2.15-p["cable_loss_db"]
    if not math.isfinite(erp_dbm) or 10**(erp_dbm/10)>p["maximum_erp_mw"]:
        raise ValueError("Transmitter + antenna gain - cable loss exceeds ERP")
    if len(p["channels_mhz"])>1 and p["gateway_multichannel_receiver"] is not True:
        raise ValueError("Multiple channels need an explicitly capable receiver")
    if p["transport"] not in {"raw_lora","lorawan_in865"}:
        raise ValueError("Unknown transport/MAC")
    if p["transport"]=="lorawan_in865":
        dr=p["lorawan_data_rate"]
        limits={0:51,1:51,2:51,3:115,4:242,5:242}
        if dr not in limits or FRAME_BYTES+p["lorawan_fopts_bytes"]>limits[dr] or p["mac_overhead_bytes"]<13:
            raise ValueError("Frame exceeds IN865 application payload or MAC overhead is missing")
        if dr in range(6) and p["spreading_factor"]!=12-dr:
            raise ValueError("IN865 data-rate/PHY mismatch")
    elif p["mac_overhead_bytes"]!=0:
        raise ValueError("Raw transport must account routing overhead separately")
    if p["rf_enabled"] is True and (not p["equipment_type_approval_id"] or p["equipment_profile_verified"] is not True or p["adaptive_power_control_verified"] is not True):
        raise ValueError("RF_DISABLED: actual equipment type approval/APC/profile unverified")
    return {"rf_ready":p["rf_enabled"] is True,"evidence":"CONFIGURATION_ONLY_NOT_PHYSICAL_RF_VALIDATION",
            "erp_mw":10**(erp_dbm/10)}


def airtime(payload_bytes=FRAME_BYTES,*,profile=None):
    p=profile or load_profile()
    sf,bw=p["spreading_factor"],p["bandwidth_hz"]
    payload=payload_bytes+p["mac_overhead_bytes"]
    symbol=2**sf/bw
    de=int(symbol>=.016)
    symbols=8+max(math.ceil((8*payload-4*sf+28+16)/(4*(sf-2*de)))*p["coding_rate_denominator"],0)
    return (p["preamble_symbols"]+4.25+symbols)*symbol
