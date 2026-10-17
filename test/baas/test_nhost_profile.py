"""Aggregate resource/security contracts; no container or native service effects."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import nhost_profile as n
import benchmark as b
class Profile(unittest.TestCase):
 def profile(self):
  targets={role:{'Id':str(index)*64,'platform':'linux/amd64','image_manifest_digest':n.PINS['images'][role]['amd64_manifest'],'compose_project':n.PROJECT,'cgroup_parent':n.SLICE,'limits':{'Memory':n.MEMORY[role],'MemorySwap':n.MEMORY[role]},'RestartCount':0,'State':{'Running':True,'Pid':index+1,'OOMKilled':False,'Health':{'Status':'healthy'}},'process_cgroup':f'0::/{n.SLICE}/docker-{str(index)*64}.scope'} for index,role in enumerate(n.SERVICES,1)}
  return {'targets':targets,'parent':{'cpu.max':'100000 100000','memory.max':'4294967296','memory.swap.max':'0','children':sorted('docker-'+item['Id']+'.scope' for item in targets.values())}}
 def test_complete_native_four_component_budget(self):self.assertTrue(n.validate_stack(self.profile()))
 def test_rejects_missing_auth_or_extra_parent_processes(self):
  for mode in ['auth','child']:
   value=self.profile()
   if mode=='auth':del value['targets']['auth']
   else:value['parent']['children'].append('unaccounted.scope')
   with self.subTest(mode=mode),self.assertRaises(RuntimeError):n.validate_stack(value)
 def test_rejects_parent_budget_drift(self):
  for key,value in [('cpu.max','200000 100000'),('memory.max','8589934592'),('memory.swap.max','1')]:
   data=self.profile();data['parent'][key]=value
   with self.subTest(key=key),self.assertRaises(RuntimeError):n.validate_stack(data)
 def test_rejects_each_component_identity_health_and_child_budget_drift(self):
  for role in n.SERVICES:
   for drift in ['image','platform','project','cgroup','health','oom','restart','memory','swap']:
    data=self.profile();item=data['targets'][role]
    if drift=='image':item['image_manifest_digest']='wrong'
    if drift=='platform':item['platform']='linux/arm64'
    if drift=='project':item['compose_project']='unrelated'
    if drift=='cgroup':item['process_cgroup']='0::/outside'
    if drift=='health':item['State']['Health']['Status']='unhealthy'
    if drift=='oom':item['State']['OOMKilled']=True
    if drift=='restart':item['RestartCount']=1
    if drift=='memory':item['limits']['Memory']*=2
    if drift=='swap':item['limits']['MemorySwap']+=1
    with self.subTest(role=role,drift=drift),self.assertRaises(RuntimeError):n.validate_stack(data)
 def test_shared_runner_accepts_native_nhost_namespace(self):
  try:value=b.deployment_settings('Linux','x86_64',{'BENCHMARK_PROJECT':n.PROJECT})
  except ValueError as error:self.fail('Approved Nhost namespace not supported: '+str(error))
  self.assertEqual(value,{'project':n.PROJECT,'platform':'linux/amd64','track':'vps16-linux-amd64'})
if __name__=='__main__':unittest.main(verbosity=2)
