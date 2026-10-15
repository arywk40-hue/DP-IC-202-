from dataclasses import replace
import unittest

from ml.himachal.radio import VOTE, decode, encode
from tests.himachal_network_fixture import EPOCH, iso, message, open_default, rig, vote_all


class ConsensusTests(unittest.TestCase):
    def test_two_nodes_cannot_quorum_three_distinct_physical_nodes_can(self):
        for count in (2,3,10):
            with self.subTest(nodes=count):
                r,h,c,seq=rig(count)
                q=open_default(r,c,seq,event_mask=7)
                vote_all(r,c,seq,q,event_mask=7)
                result=c.finalize(q["query_id"],iso(EPOCH+10))
                for outcome in result["event_results"].values():
                    self.assertEqual(outcome["corroborated"],count>=3)
                    self.assertFalse(outcome["public_dispatch"])
                    self.assertIsNone(outcome["probability"])

    def test_query_membership_is_locked_and_result_idempotent(self):
        r,_,c,seq=rig(3)
        q=open_default(r,c,seq)
        external=c.snapshot(q["query_id"])
        external["membership"][1]["weight"]=100000
        self.assertNotEqual(c.snapshot(q["query_id"])["membership"][1]["weight"],100000)
        vote_all(r,c,seq,q)
        a=c.finalize(q["query_id"],iso(EPOCH+10))
        self.assertEqual(a,c.finalize(q["query_id"],iso(EPOCH+31)))
        requests=c.peer_requests(q["query_id"])
        self.assertEqual(len(requests),2)
        for node,wire in requests:
            self.assertEqual(decode(wire,r.entries[node].key).query_id,q["query_id"])

    def test_duplicates_wrong_window_version_and_replayed_boot_do_not_add_votes(self):
        r,_,c,seq=rig(3)
        q=open_default(r,c,seq)
        n=q["membership"][1]["node_id"]
        wire=message(r,n,seq[n],kind=VOTE,query=q)
        c.accept_vote(wire,iso(EPOCH+2))
        self.assertEqual(c.accept_vote(wire,iso(EPOCH+3))["status"],"DUPLICATE_RETRY")
        for field,value in (("profile_id",2),("observed_epoch",EPOCH-60),("deadline_epoch",EPOCH+60),("boot_id",999)):
            changed=replace(decode(wire,r.entries[n].key),**{field:value,"sequence":seq[n]+1})
            with self.subTest(field=field),self.assertRaises(ValueError):
                c.accept_vote(encode(changed,r.entries[n].key),iso(EPOCH+4))
        self.assertEqual(len(c.queries[q["query_id"]]["votes"]),2)

    def test_timeout_failure_domain_common_fault_and_clock_failure_are_unknown(self):
        r,h,c,seq=rig(3)
        q=open_default(r,c,seq)
        result=c.finalize(q["query_id"],iso(q["deadline_epoch"]),force_timeout=True)
        self.assertTrue(result["timed_out"])
        self.assertFalse(result["event_results"]["rain"]["corroborated"])
        r,h,c,seq=rig(3)
        for entry in r.entries.values():
            entry.public["failure_domain"]="known-shared-batch"
        q=open_default(r,c,seq)
        vote_all(r,c,seq,q)
        self.assertFalse(c.finalize(q["query_id"],iso(EPOCH+10))["event_results"]["rain"]["corroborated"])

    def test_unknown_or_spoofed_identity_does_not_create_queries(self):
        r,_,c,seq=rig()
        q=open_default(r,c,seq)
        n="fixture-1"
        wire=message(r,n,seq[n],kind=VOTE,query=q)
        bad=wire[:-20]+b"x"+wire[-19:]
        with self.assertRaises(ValueError):
            c.accept_vote(bad,iso(EPOCH+2))
        self.assertEqual(len(c.queries),1)
