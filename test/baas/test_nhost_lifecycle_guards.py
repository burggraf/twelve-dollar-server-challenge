"""Actual admission and closure logic; all native/serving effects replaced."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import nhost as n
class LifecycleGuards(unittest.TestCase):
 def test_rechecks_admission_before_each_start_not_only_before_the_sequence(self):
  starts=[]
  with patch.object(n,'active',side_effect=[{},RuntimeError('admission expired')]),patch.object(n,'command',side_effect=lambda argv,*args:starts.append(argv[-1])),patch.object(n.s,'raw',side_effect=RuntimeError('stop after unchecked starts')):
   with self.assertRaises(RuntimeError):n.up()
  self.assertEqual(starts,['db'],'No later component may start after deadline admission expires')
 def test_changed_persistent_service_fails_closure_and_next_claim(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);phase=root/'phase';phase.mkdir();state=root/'state';state.mkdir()
   value={'phase':'old','timer':'tds-nhost-old-deadline.timer'};(state/'current-lease.json').write_text(json.dumps(value));(phase/'persistent-services-before-PRIVATE.json').write_text(json.dumps({'production.service':'before'}))
   report={'all_stopped':True,'failures':[],'terminal':{},'full_stack_clean_stop':False}
   with patch.object(n,'lease',return_value=value),patch.object(n,'evidence',return_value=phase),patch.object(n,'stop_owned',return_value=report),patch.object(n.s,'identities',return_value={}),patch.object(n,'command'),patch.object(n,'snapshot',return_value={'production.service':'after'}),patch.object(n,'protected'),patch.object(n.s,'capture',return_value=''),patch.object(n.s,'STATE',state),patch.object(n.s,'ROOT',root),patch.object(n.subprocess,'run',return_value=subprocess.CompletedProcess([],1)):
    with self.assertRaises(RuntimeError):n.down()
    saved=json.loads((phase/'closure.json').read_text());self.assertEqual(saved['changed_persistent_services'],['production.service']);self.assertTrue(saved['failures'])
    with self.assertRaises(RuntimeError):n.claim('next')
 def test_active_lease_rejects_application_or_verification_source_drift(self):
  for drift in ['application','verification']:
   with self.subTest(drift=drift),tempfile.TemporaryDirectory() as directory:
    root=Path(directory);value={'monotonic_start':0,'deadline_seconds':2700,'runtime_sha256':'runtime','app_sha256':'app','verification_sha256':'verification','timer':'timer'};(root/'claim.json').write_text(json.dumps(value))
    with patch.object(n,'protected'),patch.object(n,'lease',return_value=value),patch.object(n,'evidence',return_value=root),patch.object(n.time,'monotonic',return_value=100),patch.object(n.s,'runtime_hash',return_value='runtime'),patch.object(n.s,'app_hash',return_value='changed' if drift=='application' else 'app'),patch.object(n.s,'verification_hash',return_value='changed' if drift=='verification' else 'verification'),patch.object(n.s,'raw',return_value={}),patch.object(n.subprocess,'run',return_value=subprocess.CompletedProcess([],0)):
     with self.assertRaises(RuntimeError):n.active()
if __name__=='__main__':unittest.main(verbosity=2)
