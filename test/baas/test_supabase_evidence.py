"""A passing workload cannot certify stale inputs or a restarted stack."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import supabase_benchmark as s
class Evidence(unittest.TestCase):
 def targets(self):return {r:{'Id':r,'RestartCount':0,'State':{'Running':True,'OOMKilled':False,'StartedAt':'start'}} for r in ['db','auth','rest','functions','gateway']}
 def test_unchanged_stack_has_no_lifecycle_failure(self):self.assertIsNone(s.target_issue(self.targets(),self.targets()))
 def test_every_required_component_restart_exit_or_oom_fails(self):
  for role in self.targets():
   for field,value in [('Running',False),('OOMKilled',True),('StartedAt','new')]:
    before=self.targets();after=copy.deepcopy(before);after[role]['State'][field]=value
    with self.subTest(role=role,field=field):self.assertIsNotNone(s.target_issue(before,after))
 def test_correctness_requires_every_frozen_input_and_exact_raw_log_hash(self):
  current={'app':'a','verification':'v','runtime':'r','schema':'s','images':{'all':'native'},'host':'h','tokens':'t'}
  att={'inputs':current,'log_sha256':'log'};self.assertTrue(s.validate_correctness(att,current,'log'))
  for key in current:
   changed={**current,key:'changed'}
   with self.subTest(key=key),self.assertRaises(RuntimeError):s.validate_correctness(att,changed,'log')
  with self.assertRaises(RuntimeError):s.validate_correctness(att,current,'rewritten log')
if __name__=='__main__':unittest.main(verbosity=2)
