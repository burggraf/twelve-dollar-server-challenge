"""Strict journal/identity gate cannot invent coverage or silently apply another product's exception."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import nhost_continuity as c
class Predicates(unittest.TestCase):
 def test_events_count_without_fwupd_named_exception(self):
  entries=[{'UNIT':name,'MESSAGE':message} for name in ['production.service','fwupd.service','user@0.service'] for message in ['Starting worker','Stopped worker','application message']]
  self.assertEqual(c.event_counts(entries,set(item['UNIT'] for item in entries)),{'production.service':2,'fwupd.service':2})
 def test_native_self_exit_and_reload_events_are_not_silently_ignored(self):
  for message in ['fwupd.service: Deactivated successfully.','Reloading persistent worker','Reloaded persistent worker']:
   with self.subTest(message=message):self.assertEqual(c.event_counts([{'UNIT':'fwupd.service','MESSAGE':message}],{'fwupd.service'}),{'fwupd.service':1})
 def test_only_positively_completed_nonresident_oneshots_are_transient(self):
  oneshot={'Type':'oneshot','ActiveState':'inactive','SubState':'dead','MainPID':'0','ControlPID':'0','Job':''};units={'completed.service':oneshot,'resident.service':{**oneshot,'Type':'simple'}}
  self.assertEqual(c.partition(units,{'completed.service':True}),{'persistent':['resident.service'],'transient':['completed.service']})
  with self.assertRaises(RuntimeError):c.partition(units,{})
class Window(unittest.TestCase):
 def check_case(self,case):
  context={'time':1000.,'monotonic':900.,'host':{'same':True},'services':{'production.service':'before'}}
  def run(argv,**kwargs):
   if case=='journal-failed':raise subprocess.CalledProcessError(1,argv)
   rows=[]
   if '_PID=1' in argv:
    if case in {'event','self-exit'}:rows=[{'UNIT':'production.service','MESSAGE':'production.service: Deactivated successfully.' if case=='self-exit' else 'Started worker','__REALTIME_TIMESTAMP':'1500000000'}]
   elif case!='no-anchor':rows=[{'__REALTIME_TIMESTAMP':'900000000'}]
   kwargs['stdout'].write(b''.join(json.dumps(row).encode()+b'\n' for row in rows));return subprocess.CompletedProcess(argv,0)
  with tempfile.TemporaryDirectory() as directory,patch.object(c,'host',return_value={'same':case!='host-drift'}),patch.object(c.control,'protected'),patch.object(c.control,'snapshot',return_value={'production.service':'after' if case=='identity-drift' else 'before'}),patch.object(c.time,'time',return_value=3000. if case=='clock-drift' else 2000.),patch.object(c.time,'monotonic',return_value=1900.),patch.object(c.subprocess,'run',side_effect=run):
   if case=='valid':
    result=c.finish(context,Path(directory)/'events');self.assertIsInstance(result,dict);self.assertTrue(result['valid']);self.assertTrue(result['window_complete']);self.assertEqual(result['persistent_service_event_counts'],{})
   else:
    with self.assertRaises(RuntimeError):c.finish(context,Path(directory)/'events')
 def test_complete_unchanged_window_is_valid(self):self.check_case('valid')
 def test_actual_lifecycle_event_fails(self):self.check_case('event')
 def test_deactivated_persistent_daemon_fails_complete_window(self):self.check_case('self-exit')
 def test_identity_drift_fails(self):self.check_case('identity-drift')
 def test_host_drift_fails(self):self.check_case('host-drift')
 def test_missing_coverage_anchor_fails(self):self.check_case('no-anchor')
 def test_journal_command_failure_fails(self):self.check_case('journal-failed')
 def test_clock_discontinuity_fails(self):self.check_case('clock-drift')
if __name__=='__main__':unittest.main(verbosity=2)
