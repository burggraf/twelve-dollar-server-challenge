"""Native-only reds/greens for prospective host continuity; no history rewriting."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).with_name('repeatability_guards.py')
if path.exists():
 spec=importlib.util.spec_from_file_location('guards',path);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
else:g=None


def snapshot():
 return {'services':{'docker.service':{'MainPID':'10','ActiveEnterTimestampMonotonic':'100','NRestarts':'0'},'ssh.service':{'MainPID':'11','ActiveEnterTimestampMonotonic':'101','NRestarts':'0'},'user@0.service':{'MainPID':'12'}},
         'port4000_processes':{'812':{'start_ticks':'759','executable':'/opt/trailbase-server/bin/trail'}}}


class GuardTests(unittest.TestCase):
 def setUp(self):self.assertTrue(g is not None and callable(getattr(g,'require_continuity',None)),'Missing prospective continuity guard implementation')
 def test_approved_new_epoch_is_not_a_historical_equality_claim(self):
  a=snapshot();before=deepcopy(a)
  g.require_continuity(a,before,deepcopy(a),{},True)
  self.assertEqual(a,snapshot());self.assertNotIn('811',a['port4000_processes'])
 def test_only_existing_ssh_session_exception(self):
  a=snapshot();b=deepcopy(a);b['services']['user@0.service']={'MainPID':'999'}
  g.require_continuity(a,a,b,{},True)
  for name in ['docker.service','ssh.service']:
   b=deepcopy(a);b['services'][name]['MainPID']='999'
   with self.assertRaises(RuntimeError):g.require_continuity(a,a,b,{},True)
 def test_added_removed_changed_persistent_units_stay_failed(self):
  for mode in ['added','removed','changed']:
   a=snapshot();b=deepcopy(a)
   if mode=='added':b['services']['dmarie.service']={'MainPID':'123'}
   elif mode=='removed':del b['services']['docker.service']
   else:b['services']['docker.service']['NRestarts']='1'
   with self.subTest(mode=mode):
    with self.assertRaises(RuntimeError):g.require_continuity(a,a,b,{},True)
 def test_unchanged_endpoints_cannot_hide_dmarie_or_other_restart_events(self):
  for name in ['dmarie.service','docker.service']:
   a=snapshot()
   with self.assertRaises(RuntimeError):g.require_continuity(a,a,a,{name:1},True)
 def test_before_snapshot_must_also_match_frozen_baseline(self):
  a=snapshot();b=deepcopy(a);b['services']['docker.service']['MainPID']='99'
  with self.assertRaises(RuntimeError):g.require_continuity(a,b,a,{},True)
 def test_listener_pid_ticks_or_executable_change_fail(self):
  for key,value in [('start_ticks','760'),('executable','/other')]:
   a=snapshot();b=deepcopy(a);b['port4000_processes']['812'][key]=value
   with self.assertRaises(RuntimeError):g.require_continuity(a,a,b,{},True)
  a=snapshot();b=deepcopy(a);b['port4000_processes']['813']=b['port4000_processes'].pop('812')
  with self.assertRaises(RuntimeError):g.require_continuity(a,a,b,{},True)
 def test_incomplete_or_malformed_journal_counts_refused(self):
  a=snapshot()
  with self.assertRaises(RuntimeError):g.require_continuity(a,a,a,{},False)
  for count in [-1,True,'0',None]:
   with self.subTest(count=count):
    with self.assertRaises(RuntimeError):g.require_continuity(a,a,a,{'docker.service':count},True)
 def test_lifecycle_classifier_restricts_output_to_numeric_watched_units(self):
  entries=[{'UNIT':'dmarie.service','MESSAGE':'Scheduled restart job, private arbitrary detail'},
           {'UNIT':'docker.service','MESSAGE':'Started private arbitrary detail'},
           {'UNIT':'unwatched.service','MESSAGE':'Started unexported'},
           {'UNIT':'user@0.service','MESSAGE':'Started normal SSH session'},
           {'UNIT':'docker.service','MESSAGE':'private non-lifecycle detail'},
           {'UNIT':'docker.service','MESSAGE':[1,2,3]}]
  self.assertEqual(g.event_counts(entries,{'docker.service','dmarie.service','user@0.service'}),{'dmarie.service':1,'docker.service':1})
 def test_disabled_inactive_dead_is_required_without_pending_job(self):
  good={'ActiveState':'inactive','SubState':'dead','UnitFileState':'disabled','MainPID':'0','Job':''}
  g.require_dmarie_off(good)
  for key,value in [('ActiveState','active'),('SubState','auto-restart'),('UnitFileState','enabled'),('MainPID','1'),('Job','123')]:
   b=deepcopy(good);b[key]=value
   with self.subTest(key=key):
    with self.assertRaises(RuntimeError):g.require_dmarie_off(b)
 def test_host_context_reboot_kernel_docker_memory_or_cpu_drift_refused(self):
  a={'boot':'b','kernel':'k','docker':'d','memory_total':16770064384,'cpus':4,'machine':'m'}
  g.require_host_context(a,deepcopy(a))
  for key in a:
   b=deepcopy(a);b[key]='changed'
   with self.subTest(key=key):
    with self.assertRaises(RuntimeError):g.require_host_context(a,b)

if __name__=='__main__':unittest.main(verbosity=2)
