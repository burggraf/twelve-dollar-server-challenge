"""Bounded native regressions for verified pre-qualification reviewer findings; all external effects mocked."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import nhost as n
import nhost_profile as s
import nhost_benchmark as b
import nhost_qualify as q
class Qualification(unittest.TestCase):
 def test_unchanged_original_suite_receives_adapter_base_url_as_its_positional_argument(self):
  class ReachedTools(Exception):pass
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   with patch.object(q.s,'STATE',root),patch.object(q.n,'claim'),patch.object(q.n,'evidence',return_value=root),patch.object(q.n,'up'),patch.object(q.n,'down'),patch.object(q.s,'identities',return_value={'db':'a'*64}),patch.object(q.import_nhost,'verify',return_value={}),patch.object(q.s,'deployment_attestation',return_value={}),patch.object(q.bench,'inputs',return_value={}),patch.object(q.n,'tools',side_effect=ReachedTools) as tools:
    with self.assertRaises(ReachedTools):q.qualify('endpoint-routing-test')
    self.assertIn('bash test/test.sh "$BASE_URL";',tools.call_args.args[0],'Original suite takes its endpoint as argv[1], not BASE_URL environment')
class Verification(unittest.TestCase):
 def test_every_executed_node_test_invalidates_frozen_verification(self):
  names=['services/nhost/app/native-contract.test.mjs','services/nhost/app/http.test.mjs','services/supabase/functions/feed/contract.test.mjs']
  with tempfile.TemporaryDirectory() as directory,patch.object(s,'ROOT',Path(directory)),patch.object(b.b,'verification_source_hash',return_value='shared-base'):
   for name in names:
    path=Path(directory)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('original')
   old=s.verification_hash()
   for name in names:
    path=Path(directory)/name;path.write_text('changed')
    with self.subTest(name=name):
     current=s.verification_hash();self.assertNotEqual(current,old)
     with self.assertRaises(RuntimeError):b.validate_correctness({'inputs':{'verification':old},'log_sha256':'log'},{'verification':current},'log')
    path.write_text('original')
class Ceiling(unittest.TestCase):
 def check_case(self,outcomes):
  history=[{'vus':vus,'outcome':'pass','path':'original-'+str(vus)} for vus in [2500,5000,10000,20000]]+ [{'vus':20000,'outcome':outcome,'path':'retained-confirmation-'+str(i)} for i,outcome in enumerate(outcomes)]
  with tempfile.TemporaryDirectory() as directory,patch.object(b,'STATE',Path(directory)),patch.object(b,'RESULTS',Path(directory)/'results'),patch.object(b,'frozen_proof',return_value='a'*64),patch.object(b.budget,'history',side_effect=lambda proof,smoke=False:[{'vus':25,'outcome':'pass'},{'vus':100,'outcome':'pass'}] if smoke else history),patch.object(b,'run',return_value=('pass','unexpected-new')) as run:
   with self.assertRaises(RuntimeError):b.campaign_step()
   run.assert_not_called()
 def test_invalid_ceiling_confirmation_cannot_be_retried(self):self.check_case(['invalid'])
 def test_failed_ceiling_confirmation_cannot_be_retried(self):self.check_case(['fail'])
 def test_invalid_ceiling_cannot_be_hidden_by_later_four_passes(self):self.check_case(['invalid','pass','pass','pass','pass'])
class Clock(unittest.TestCase):
 def test_invalid_missing_summary_retains_explicitly_unavailable_clock(self):self.assertIsNone(b.measurement_clock({},'invalid'))
 def test_missing_clock_never_certifies_valid_measurement(self):
  with self.assertRaises(ValueError):b.measurement_clock({},'pass')
class Tools(unittest.TestCase):
 def check_timeout(self):
  calls=[];commands=[];cid='b'*64
  def command(argv,*args):commands.append(argv);raise subprocess.TimeoutExpired(argv,1)
  def run(argv,**kwargs):
   calls.append(argv)
   if argv[:2]==['docker','inspect']:
    nonce=next((value.partition('=')[2] for value in commands[0] if value.startswith('benchmark.nhost-tools=')),None)
    return subprocess.CompletedProcess(argv,0,json.dumps([{'Id':cid,'Image':'sha256:7b35188938d0b5a3b50178d6a85e776b09db24314a2643c64b95b3da49f4f9f2','Config':{'Labels':{'com.docker.compose.project':s.PROJECT,'com.docker.compose.service':'tools','benchmark.nhost-tools':nonce}}}]),'')
   return subprocess.CompletedProcess(argv,0,'','')
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'.state').mkdir();evidence=root/'evidence';evidence.mkdir()
   with patch.object(n,'active'),patch.object(n.s,'ROOT',root),patch.object(n.s,'capture',return_value=''),patch.object(n,'evidence',return_value=evidence),patch.object(n,'command',side_effect=command),patch.object(n.subprocess,'run',side_effect=run):
    with self.assertRaises(subprocess.TimeoutExpired):n.tools('exec sleep 60','timeout-test')
  return calls,commands,cid
 def test_native_lowercase_absence_after_auto_remove_preserves_original_command_result(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'.state').mkdir();retained=root/'original.log'
   def run(argv,**kwargs):return subprocess.CompletedProcess(argv,1,'[]\n','error: no such object: '+argv[-1]+'\n')
   with patch.object(n,'active'),patch.object(n.s,'ROOT',root),patch.object(n.s,'capture',return_value=''),patch.object(n,'evidence',return_value=root),patch.object(n,'command',return_value=retained),patch.object(n.subprocess,'run',side_effect=run):self.assertEqual(n.tools('true','native-auto-remove'),retained)
 def test_failed_inspect_and_failed_independent_absence_lookup_never_certify_cleanup(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'.state').mkdir()
   with patch.object(n,'active'),patch.object(n.s,'ROOT',root),patch.object(n.s,'capture',side_effect=['',subprocess.CalledProcessError(1,['docker','ps'])]),patch.object(n,'evidence',return_value=root),patch.object(n,'command',return_value=root/'original.log'),patch.object(n.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','daemon unavailable')):
    with self.assertRaises(Exception):n.tools('true','unavailable-daemon')
 def test_client_timeout_removes_only_exact_created_owned_tools_id(self):
  calls,commands,cid=self.check_timeout();self.assertIn(['docker','rm','-f',cid],calls)
 def test_tools_have_independent_inner_execution_deadline(self):
  calls,commands,cid=self.check_timeout();self.assertIn('timeout',commands[0]);self.assertIn('--kill-after=5s',commands[0])
 def test_down_cannot_cancel_deadline_with_project_tools_remaining(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'persistent-services-before-PRIVATE.json').write_text('{}');report={'all_stopped':True,'failures':[],'terminal':{},'full_stack_clean_stop':False}
   with patch.object(n,'lease',return_value={'phase':'test','timer':'test.timer'}),patch.object(n,'evidence',return_value=root),patch.object(n,'stop_owned',return_value=report),patch.object(n.s,'identities',return_value={}),patch.object(n,'command') as command,patch.object(n,'snapshot',return_value={}),patch.object(n,'protected'),patch.object(n.s,'capture',side_effect=lambda argv,*args:'b'*64 if argv[0]=='docker' else ''):
    with self.assertRaises(RuntimeError):n.down()
    command.assert_not_called()
if __name__=='__main__':unittest.main(verbosity=2)
