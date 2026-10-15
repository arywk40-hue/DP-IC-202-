from dataclasses import replace
import copy
import unittest

from ml.himachal.radio import FRAME_BYTES, airtime, decode, encode, load_profile, validate_profile
from tests.himachal_network_fixture import message, rig
from simulator.radio import Scheduler
import numpy as np
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

from ml.himachal.radio import Frame, VOTE


class RadioTests(unittest.TestCase):
    def test_actual_frame_size_quantization_missing_and_authentication(self):
        r,_,_,seq=rig()
        wire=message(r,"fixture-0",seq["fixture-0"])
        self.assertEqual(len(wire),82)
        self.assertEqual(FRAME_BYTES,82)
        key=r.entries["fixture-0"].key
        frame=decode(wire,key)
        self.assertEqual(frame.measurements,(20.,60.,900.,25.,50.,3.))
        self.assertEqual(frame.scores,(1.,1.,1.))
        for wire2,key2 in ((wire[:-1],key),(wire,b"wrong-key-not-for-this-peer-32-bytes")):
            with self.assertRaises(ValueError):
                decode(wire2,key2)
        missing=replace(frame,valid_channel_mask=7,scores=(None,None,None),event_mask=0)
        decoded=decode(encode(missing,key),key)
        self.assertEqual(decoded.measurements[3:],(None,None,None))
        self.assertEqual(decoded.scores,(None,None,None))

    def test_airtime_uses_actual_bytes_and_actual_mac_overhead(self):
        p=load_profile()
        self.assertAlmostEqual(airtime(62,profile=p),.369664)
        self.assertAlmostEqual(airtime(82,profile=p),.472064)
        mac=copy.deepcopy(p)
        mac.update(transport="lorawan_in865",lorawan_data_rate=3,mac_overhead_bytes=13)
        validate_profile(mac)
        self.assertGreater(airtime(profile=mac),airtime(profile=p))
        for dr in (0,1,2):
            bad={**mac,"lorawan_data_rate":dr,"spreading_factor":12-dr}
            with self.subTest(dr=dr),self.assertRaises(ValueError):
                validate_profile(bad)

    def test_unverified_rf_wrong_category_power_and_receiver_fail(self):
        p=load_profile()
        self.assertFalse(validate_profile(p)["rf_ready"])
        changes=[dict(rf_enabled=True),dict(device_duty_fraction=.03),dict(transmitter_power_dbm=30),
                 dict(legal_category="RFID_2W"),dict(channels_mhz=[865.2,866.2])]
        for change in changes:
            with self.subTest(change=change),self.assertRaises(ValueError):
                validate_profile({**p,**change})

    def test_real_reservations_respect_duty_budget_and_count_all_frame_roles(self):
        p=load_profile()
        p["device_duty_fraction"]=.001
        scheduler=Scheduler(p)
        kinds=("heartbeat","query","vote","ack","retry","relay","result")
        for i,kind in enumerate(kinds):
            self.assertIsNotNone(scheduler.reserve("node","gateway",kind,i,i+1,82))
        self.assertIsNone(scheduler.reserve("node","gateway","eighth",7,8,82))
        receipt=scheduler.receipt(0,3600)
        self.assertEqual(receipt["frames"],7)
        self.assertEqual(receipt["frame_bytes"],7*82)
        self.assertLessEqual(receipt["devices"]["node"]["maximum_accounted_rolling_window_tx_seconds"],3.6)
        self.assertIsNotNone(scheduler.reserve("node","gateway","after_window",3601,3602,82))

    def test_actual_overlap_and_half_duplex_drop_without_an_aloha_probability(self):
        p=load_profile()
        scheduler=Scheduler(p)
        a=scheduler.reserve("a","gateway","vote",0,10,82)
        scheduler.reserve("b","gateway","heartbeat",.1,10,82)
        self.assertEqual(scheduler.delivery(a,np.random.default_rng(1)),(False,"collision"))
        p.update(channels_mhz=[865.2,866.2],gateway_multichannel_receiver=True)
        scheduler=Scheduler(p)
        a=scheduler.reserve("a","b","query",0,10,82)
        scheduler.reserve("b","gateway","heartbeat",0,10,82,channel=1)
        self.assertEqual(scheduler.delivery(a,np.random.default_rng(1)),(False,"receiver_half_duplex"))

    def test_host_c_crypto_codec_bytes_and_consensus_policy(self):
        root=Path(__file__).resolve().parents[1]
        flags=["-DINDRA_HOST_COMMONCRYPTO"] if platform.system()=="Darwin" else ["-DINDRA_HOST_OPENSSL","-lcrypto"]
        key=bytes(range(32)) # Public synthetic test vector, never production key.
        inputs=[(-60.,0.,300.,0.,0.,0.),(85.,100.,1100.,5000.,5000.,100.),
                (18.005,90.005,895.05,100.5,200.5,3.005)]
        with tempfile.TemporaryDirectory() as tmp:
            for raw in inputs:
                frame=Frame(VOTE,1,2,3,4,5,1782864000,1782864030,1,1,63,float(np.float32(2.0001)),
                    tuple(float(np.float32(v)) for v in raw),scores=(1.,None,float(np.float32(.6999))))
                source=r'''#include <stdio.h>
#include "indra_peer_protocol.h"
#include "indra_consensus_policy.h"
int main(void){uint8_t key[32];for(int i=0;i<32;++i)key[i]=i;indra_peer_values v={0},decoded;
v.kind=2;v.peer_id=1;v.origin_id=2;v.boot_id=3;v.query_id=4;v.sequence=5;v.observed=1782864000;v.deadline=1782864030;v.profile_id=1;v.event_mask=1;v.valid_mask=63;
v.clock_uncertainty=CLOCK;float raw[6]={VALUES};for(int i=0;i<6;++i)v.raw[i]=raw[i];v.score[0]=1;v.score[1]=NAN;v.score[2]=SCORE;
indra_peer_frame wire;if(!indra_peer_pack(&v,key,32,&wire)||!indra_peer_unpack(&wire,key,32,&decoded))return 1;
if(sizeof(wire)!=82||offsetof(indra_peer_frame,tag)!=64)return 2;
for(size_t i=0;i<sizeof(wire);++i)printf("%02x",((uint8_t *)&wire)[i]);puts("");
wire.body[48]^=1;if(indra_peer_unpack(&wire,key,32,&decoded))return 3;
indra_peer_u16(wire.crc,indra_peer_crc((uint8_t *)&wire,80));if(indra_peer_unpack(&wire,key,32,&decoded))return 4;
indra_consensus_vote votes[3]={{1,1,1,1,0,2,1,1,1,1,1,63},{2,2,2,1,0,2,1,1,1,0,1,63},{3,3,2,1,0,2,1,1,1,0,1,63}};
indra_consensus_decision decision;if(!indra_consensus_policy(votes,3,63,120,&decision)||!decision.corroborated)return 5;
votes[2].physical=0;if(!indra_consensus_policy(votes,3,63,120,&decision)||decision.corroborated)return 6;
votes[2].physical=1;votes[1].failure_domain=votes[2].failure_domain=1;if(!indra_consensus_policy(votes,3,63,120,&decision)||decision.corroborated)return 7;
votes[2].failure_domain=2;votes[2].age_seconds=121;if(!indra_consensus_policy(votes,3,63,120,&decision)||decision.corroborated)return 8;
return 0;}'''
                source=source.replace("VALUES",",".join(f"{v:.9g}f" if "." in f"{v:.9g}" else f"{v:.9g}.0f" for v in frame.measurements)).replace("CLOCK",f"{frame.clock_uncertainty_seconds:.9g}f").replace("SCORE",f"{frame.scores[2]:.9g}f")
                path=Path(tmp)/"codec.c"
                path.write_text(source)
                binary=Path(tmp)/"codec"
                result=subprocess.run([shutil.which("cc"),"-std=c99","-O2","-Wall","-Wextra","-Werror",str(path),"-I"+str(root/"esp32/himachal_node/include"),*flags,"-lm","-o",str(binary)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                output=subprocess.run([str(binary)],capture_output=True,text=True,check=True).stdout.strip()
                self.assertEqual(bytes.fromhex(output),encode(frame,key))
