"""Physical failures consume immutable slots; reserve before any lifecycle/load action."""
import hashlib,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import nhost_budget as b
class Budget(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'ledger';self.patch=patch.object(b,'ROOT',self.root);self.patch.start();self.addCleanup(self.patch.stop)
 def test_reserved_original_exists_before_control_and_matches_exact_owner(self):
  ticket=b.reserve(25,True,'a'*64);self.assertIsInstance(ticket,dict);self.assertEqual(ticket['ordinal'],1);self.assertEqual(json.loads((self.root/'0001-reserved.json').read_text()),ticket);self.assertEqual(b.require(25,True,'a'*64),ticket)
 def test_unfinished_reservation_cannot_be_adopted_or_refilled(self):
  b.reserve(25,True,'a'*64)
  with self.assertRaises(RuntimeError):b.reserve(100,True,'a'*64)
 def test_invalid_full_attempts_consume_all24_slots(self):
  for ordinal in range(1,25):
   ticket=b.reserve(250,False,'a'*64);self.assertIsInstance(ticket,dict);self.assertEqual(ticket['ordinal'],ordinal);b.finish(ticket,'invalid','retained-failed-'+str(ordinal))
  with self.assertRaises(RuntimeError):b.reserve(250,False,'a'*64)
  self.assertEqual(len(list(self.root.glob('*-reserved.json'))),24)
 def test_only_four_smokes_and_finish_never_overwrites_original(self):
  for ordinal in range(4):
   ticket=b.reserve(25,True,'a'*64);b.finish(ticket,'pass','retained-'+str(ordinal))
   with self.assertRaises((RuntimeError,FileExistsError)):b.finish(ticket,'invalid','overwrite')
  with self.assertRaises(RuntimeError):b.reserve(25,True,'a'*64)
 def install_test_amendment(self):
  b.rows();path=self.root/'owner-smoke-extension-v2.json';b.exclusive(path,{'test_owner_approved_maximum_smokes':6,'maximum_full':24})
  guard=patch.object(b,'SMOKE_AMENDMENT_SHA256',hashlib.sha256(path.read_bytes()).hexdigest(),create=True);guard.start();self.addCleanup(guard.stop);return path
 def test_explicit_hash_bound_amendment_adds_only_two_slots_without_refunds_or_pooling(self):
  for i in range(4):ticket=b.reserve(25,True,'a'*64);b.finish(ticket,'invalid','old-'+str(i))
  old={p.name:p.read_bytes() for p in self.root.iterdir()};self.install_test_amendment()
  for i in [5,6]:
   try:ticket=b.reserve(100,True,'b'*64)
   except RuntimeError as error:self.fail('Explicit owner extension must permit only the approved new calibration slots: '+str(error))
   self.assertEqual(ticket['ordinal'],i);b.finish(ticket,'pass','new-'+str(i))
  with self.assertRaises(RuntimeError):b.reserve(25,True,'c'*64)
  self.assertEqual(len(b.history('a'*64,True)),4);self.assertEqual(len(b.history('b'*64,True)),2)
  for name,raw in old.items():self.assertEqual((self.root/name).read_bytes(),raw)
 def test_amendment_does_not_increase24_full_slots_across_revisions(self):
  self.install_test_amendment()
  for i in range(24):ticket=b.reserve(250,False,('a' if i<12 else 'b')*64);b.finish(ticket,'invalid','retained-'+str(i))
  with self.assertRaises(RuntimeError):b.reserve(250,False,'c'*64)
 def test_changed_owner_amendment_fails_closed_before_any_reservation(self):
  path=self.install_test_amendment();path.write_text('unapproved replacement')
  with self.assertRaises(RuntimeError):b.reserve(25,True,'a'*64)
  self.assertEqual(len(list(self.root.glob('*-reserved.json'))),0)
 def test_symlink_owner_amendment_is_not_accepted(self):
  path=self.install_test_amendment();raw=path.read_bytes();path.unlink();other=self.root/'not-the-amendment';other.write_bytes(raw);path.symlink_to(other)
  with self.assertRaises(RuntimeError):b.reserve(25,True,'a'*64)
 def test_removing_used_extension_cannot_hide_over_base_budget_history(self):
  path=self.install_test_amendment()
  for i in range(5):
   try:ticket=b.reserve(25,True,'a'*64)
   except RuntimeError as error:self.fail('Approved fifth slot unavailable: '+str(error))
   b.finish(ticket,'invalid','retained-'+str(i))
  path.unlink()
  with self.assertRaises(RuntimeError):b.history('a'*64,True)
 def test_proof_vus_mode_and_process_binding_fail_closed(self):
  ticket=b.reserve(25,True,'a'*64);self.assertIsInstance(ticket,dict)
  for args in [(100,True,'a'*64),(25,False,'a'*64),(25,True,'b'*64)]:
   with self.subTest(args=args),self.assertRaises(RuntimeError):b.require(*args)
  with patch.object(b.os,'getpid',return_value=os.getpid()+1),self.assertRaises(RuntimeError):b.require(25,True,'a'*64)
 def test_unknown_outcome_and_changed_budget_policy_rejected(self):
  ticket=b.reserve(25,True,'a'*64)
  with self.assertRaises(RuntimeError):b.finish(ticket,'skip','not-an-outcome')
  (self.root/'policy.json').write_text(json.dumps({**b.POLICY,'maximum_full_attempts':999}))
  with self.assertRaises(RuntimeError):b.require(25,True,'a'*64)
if __name__=='__main__':unittest.main(verbosity=2)
