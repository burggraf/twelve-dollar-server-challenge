"""Fail-closed aggregate serving budget, image and ownership checks."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import supabase_profile as s
class AggregateBudget(unittest.TestCase):
 def fixture(self):
  pins=json.loads((ROOT/'services/supabase/versions.json').read_text())
  targets={}
  for i,(role,pin) in enumerate(pins['images'].items()):
   ident=str(i)*64
   targets[role]={'Id':ident,'platform':'linux/amd64','image_manifest_digest':pin['amd64_manifest'],'compose_project':s.PROJECT,'cgroup_parent':s.SLICE,'process_cgroup':f'0::/{s.SLICE}/docker-{ident}.scope\n','State':{'Running':True,'OOMKilled':False,'Health':{'Status':'healthy'}}}
  return {'targets':targets,'parent':{'cpu.max':'100000 100000','memory.max':str(4*1024**3),'memory.swap.max':'0','children':[f'docker-{v["Id"]}.scope' for v in targets.values()]}}
 def test_one_parent_enforces_entire_five_component_stack(self):self.assertTrue(s.validate_stack(self.fixture()))
 def test_missing_or_per_container_only_budget_cannot_pass(self):
  for key in ['cpu.max','memory.max','memory.swap.max']:
   p=self.fixture();del p['parent'][key]
   with self.subTest(key=key),self.assertRaises(RuntimeError):s.validate_stack(p)
 def test_wrong_quota_memory_swap_or_extra_component_fails(self):
  for key,value in [('cpu.max','400000 100000'),('cpu.max','max 100000'),('memory.max',str(8*1024**3)),('memory.swap.max','max'),('children',['unexpected.scope'])]:
   p=self.fixture();p['parent'][key]=value
   with self.subTest(key=key),self.assertRaises(RuntimeError):s.validate_stack(p)
 def test_all_components_must_be_native_owned_and_in_exact_parent(self):
  for key,value in [('platform','linux/arm64'),('image_manifest_digest','wrong'),('compose_project','production'),('cgroup_parent','system.slice'),('process_cgroup','0::/elsewhere\n')]:
   p=self.fixture();p['targets']['auth'][key]=value
   with self.subTest(key=key),self.assertRaises(RuntimeError):s.validate_stack(p)
 def test_stopped_or_missing_required_service_is_not_a_smaller_supabase_stack(self):
  p=self.fixture();del p['targets']['auth']
  with self.assertRaises(RuntimeError):s.validate_stack(p)
  p=self.fixture();p['targets']['auth']['State']['Running']=False
  with self.assertRaises(RuntimeError):s.validate_stack(p)
if __name__=='__main__':unittest.main(verbosity=2)
