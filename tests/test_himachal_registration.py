import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from ml.himachal.neighbours import select
from ml.himachal.nodes import Registry
from tests.himachal_network_fixture import EPOCH, iso, registration, rig


class RegistrationTests(unittest.TestCase):
    def test_dynamic_sizes_bounded_query_and_removal(self):
        for count in (3,10,50,200):
            with self.subTest(nodes=count):
                r,h,_,_=rig(count)
                found=select(r,h,"fixture-0",iso(EPOCH))
                self.assertLessEqual(found["queried_count"],6)
                self.assertLessEqual(found["candidates_scanned"],64)
                self.assertEqual(found["search_truncated"],count>65)
                r.remove("fixture-1")
                self.assertNotIn("fixture-1",[p["node_id"] for p in select(r,h,"fixture-0",iso(EPOCH))["peers"]])

    def test_no_shared_keys_aliases_retired_ids_or_silent_relocation(self):
        r=Registry()
        key=hashlib.sha256(b"SYNTHETIC_KEY_ONLY_A").digest()
        r.register(registration(0),key)
        with self.assertRaises(ValueError):
            r.register(registration(1),key)
        changed=registration(1)
        changed["physical_site_id"]="fixture-site-0"
        with self.assertRaises(ValueError):
            r.register(changed,hashlib.sha256(b"SYNTHETIC_KEY_ONLY_B").digest())
        changed=registration(0)
        changed["longitude"]+=.01
        with self.assertRaises(ValueError):
            r.register(changed,key)
        changed["registration_id"]="new-survey"
        with self.assertRaises(ValueError):
            r.register(changed,key)
        r.register(changed,hashlib.sha256(b"SYNTHETIC_KEY_ONLY_C").digest())
        r.remove("fixture-0")
        with self.assertRaises(ValueError):
            r.register(changed,hashlib.sha256(b"SYNTHETIC_KEY_ONLY_D").digest())

    def test_virtual_and_altitude_mismatch_are_not_physical_peers(self):
        r,h,_,_=rig(4)
        for node,patch in (("fixture-1",{"source_class":"modeled_grid"}),("fixture-2",{"elevation_m":3000.})):
            item=r.public(node)
            item.update(patch,registration_id="changed-"+node)
            r.register(item,hashlib.sha256(node.encode()).digest())
        selected=select(r,h,"fixture-0",iso(EPOCH))
        self.assertEqual([p["node_id"] for p in selected["peers"]],["fixture-3"])

    def test_provisioning_rejection_preserves_registry_and_retired_history(self):
        r=Registry()
        key=hashlib.sha256(b"SYNTHETIC_RETIRED_KEY").digest()
        r.register(registration(0),key)
        r.remove("fixture-0")
        before=(r.generation,dict(r.radio_ids),dict(r._used_keys))
        rows=[registration(1),registration(0)]
        keys={"fixture-1":hashlib.sha256(b"SYNTHETIC_NEW_KEY").hexdigest(),"fixture-0":key.hex()}
        with tempfile.TemporaryDirectory() as tmp:
            records_path,keys_path=Path(tmp)/"registrations.json",Path(tmp)/"keys.json"
            records_path.write_text(json.dumps(rows))
            keys_path.write_text(json.dumps(keys))
            with self.assertRaisesRegex(ValueError,"Retired registration"):
                r.load_provisioning(records_path,keys_path)
            self.assertEqual(r.entries,{})
            self.assertEqual((r.generation,r.radio_ids,r._used_keys),before)
            records_path.write_text(json.dumps(rows[:1]))
            keys_path.write_text(json.dumps({"fixture-1":keys["fixture-1"]}))
            self.assertEqual(len(r.load_provisioning(records_path,keys_path)),1)
            self.assertIn("fixture-1",r.entries)
            self.assertIn(1,r.radio_ids)  # Removed node's radio ID stays reserved.
