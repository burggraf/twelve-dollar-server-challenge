"""Native-only importer boundary units; every Docker call is mocked, no live SQL."""
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import import_nhost as native
IDS={role:character*64 for role,character in [('db','a'),('graphql','b'),('auth','c'),('adapter','d')]}
class NativeImportBoundary(unittest.TestCase):
 def containers(self):
  return {role:{'Id':cid,'Config':{'Labels':{'com.docker.compose.project':native.PROJECT,'com.docker.compose.service':role}},'State':{'Running':role=='db','Pid':123 if role=='db' else 0,'Health':{'Status':'healthy'},'OOMKilled':False},'RestartCount':0} for role,cid in IDS.items()}
 def output(self,items):
  def inspected(argv,**kwargs):
   self.assertEqual(argv[:2],['docker','inspect']);self.assertIn(argv[-1],IDS.values());self.assertEqual(kwargs.get('timeout'),10)
   role=next(role for role,cid in IDS.items() if cid==argv[-1]);return json.dumps([items[role]]).encode()
  return inspected
 def test_untimed_operator_targets_exact_native_id_and_postgres_role(self):
  args=native.psql_args(IDS['db'],'SELECT 1')
  self.assertEqual(args[:4],['docker','exec','-i',IDS['db']]);self.assertIn('psql',args)
  self.assertEqual(args[args.index('-U')+1],'postgres');self.assertEqual(args[args.index('-d')+1],'postgres')
  self.assertIn('ON_ERROR_STOP=1',args);self.assertEqual(args[-2:],['-c','SELECT 1']);self.assertNotIn('supabase_admin',args)
 def test_shared_exact_utf8_mapping_remains_unchanged(self):
  row=['9007199254740993','1','\ufeffcafé\x00🦄','2025-01-01T00:00:00.000Z'];before=row.copy()
  self.assertEqual(native.postgres_row('posts',row)[2],'\\x'+row[2].encode().hex())
  self.assertEqual(native.logical_row('posts',[row[0],row[1],row[2].encode().hex(),row[3]]),row);self.assertEqual(row,before)
 def test_accepts_only_exact_owned_database_running(self):
  with patch.object(native.subprocess,'check_output',side_effect=self.output(self.containers())) as inspect:
   self.assertEqual(native.require_offline(IDS),IDS['db']);self.assertEqual(inspect.call_count,4)
 def test_rejects_missing_extra_duplicate_or_malformed_id_before_docker(self):
  cases=[{key:value for key,value in IDS.items() if key!='adapter'},dict(IDS,other='e'*64),dict(IDS,adapter=IDS['auth']),dict(IDS,db='not-an-exact-id')]
  for value in cases:
   with self.subTest(value=value),patch.object(native.subprocess,'check_output') as inspect:
    with self.assertRaises(ValueError):native.require_offline(value)
    inspect.assert_not_called()
 def test_rejects_project_service_or_exact_identity_drift(self):
  for drift in ['project','service','identity']:
   with self.subTest(drift=drift):
    items=self.containers()
    if drift=='identity':items['db']['Id']='e'*64
    else:items['db']['Config']['Labels']['com.docker.compose.'+drift]='unrelated'
    with patch.object(native.subprocess,'check_output',side_effect=self.output(items)):
     with self.assertRaises(ValueError):native.require_offline(IDS)
 def test_rejects_every_live_api_and_stale_api_pid(self):
  for role in ['graphql','auth','adapter']:
   for running,pid in [(True,123),(False,123)]:
    with self.subTest(role=role,running=running):
     items=self.containers();items[role]['State'].update(Running=running,Pid=pid)
     with patch.object(native.subprocess,'check_output',side_effect=self.output(items)):
      with self.assertRaises(ValueError):native.require_offline(IDS)
 def test_rejects_database_down_unhealthy_oom_or_restart(self):
  for drift in ['down','unhealthy','oom','restart']:
   with self.subTest(drift=drift):
    items=self.containers()
    if drift=='down':items['db']['State'].update(Running=False,Pid=0)
    if drift=='unhealthy':items['db']['State']['Health']['Status']='unhealthy'
    if drift=='oom':items['db']['State']['OOMKilled']=True
    if drift=='restart':items['db']['RestartCount']=1
    with patch.object(native.subprocess,'check_output',side_effect=self.output(items)):
     with self.assertRaises(ValueError):native.require_offline(IDS)
if __name__=='__main__':unittest.main(verbosity=2)
