"""Every measured component and every full-qualification fingerprint must remain bound."""
import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import nhost_benchmark as n
class Evidence(unittest.TestCase):
 def targets(self):return {role:{'Id':role,'RestartCount':0,'State':{'Running':True,'OOMKilled':False,'StartedAt':'start','Health':{'Status':'healthy'}}} for role in n.s.SERVICES}
 def test_unchanged_complete_stack_is_valid(self):self.assertIsNone(n.target_issue(self.targets(),self.targets()))
 def test_every_required_role_lifecycle_and_health_drift_fails(self):
  for role in n.s.SERVICES:
   for key,value in [('Running',False),('OOMKilled',True),('StartedAt','new'),('Health',{'Status':'unhealthy'})]:
    before=self.targets();after=copy.deepcopy(before);after[role]['State'][key]=value
    with self.subTest(role=role,key=key):self.assertIsNotNone(n.target_issue(before,after))
   for key,value in [('Id','replacement'),('RestartCount',1)]:
    before=self.targets();after=copy.deepcopy(before);after[role][key]=value
    with self.subTest(role=role,key=key):self.assertIsNotNone(n.target_issue(before,after))
   after=self.targets();del after[role]
   with self.subTest(missing=role):self.assertIsNotNone(n.target_issue(self.targets(),after))
 def test_qualification_inputs_bind_owner_amended_budget(self):
  import nhost_continuity
  deployed={'app_source_sha256':'app','verification_source_sha256':'verification','runtime_inputs_sha256':'runtime','schema':{'sha256':'schema'},'metadata_sha256':'metadata','images':{},'host_identity_sha256':'host'};policy={**n.budget.POLICY,'version':2,'maximum_smoke_attempts':6,'owner_amendment_sha256':'unit-owner-hash'}
  with patch.object(n.budget,'effective_policy',return_value=policy,create=True),patch.object(n,'token_hash',return_value='tokens'),patch.object(n.b,'capture',return_value='tools'),patch.object(nhost_continuity,'host',return_value='native'):
   current=n.inputs(deployed)
  self.assertIn('physical_attempt_policy',current);self.assertEqual(current['physical_attempt_policy'],policy)
 def test_complete_correctness_binds_metadata_tokens_tools_source_and_original_log(self):
  current={key:key for key in ['app','verification','runtime','schema','metadata','images','host','tokens','tools_image','physical_attempt_policy']};att={'inputs':current,'log_sha256':'original'}
  self.assertTrue(n.validate_correctness(att,current,'original'))
  for key in current:
   with self.subTest(key=key),self.assertRaises(RuntimeError):n.validate_correctness(att,{**current,key:'changed'},'original')
  with self.assertRaises(RuntimeError):n.validate_correctness(att,current,'rewritten')
if __name__=='__main__':unittest.main(verbosity=2)
