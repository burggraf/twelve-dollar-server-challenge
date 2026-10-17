"""Real stop control logic with only Docker replaced; no serving effects."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import nhost as n
IDS={role:char*64 for role,char in [('db','a'),('graphql','b'),('auth','c'),('adapter','d')]}
class StopSafety(unittest.TestCase):
 def exercise(self,mode,roles=n.STOP_ORDER):
  stopped=set();calls=[];self.log_timeouts=[]
  def output(argv,**kwargs):
   self.assertEqual(argv[:2],['docker','inspect']);self.assertEqual(kwargs['timeout'],10)
   role=next(role for role,cid in IDS.items() if cid==argv[-1]);running=role not in stopped
   return json.dumps([{'Id':IDS[role],'Config':{'Labels':{'com.docker.compose.project':'unrelated' if mode=='ownership' and role=='adapter' else n.s.PROJECT,'com.docker.compose.service':role}},'State':{'Running':running,'Pid':123 if running else 0,'Status':'running' if running else 'exited','ExitCode':137 if mode in ('slow_logs','log_timeout') and role=='graphql' else 2 if mode in ('slow_logs','log_timeout') and role=='auth' else 0,'OOMKilled':mode=='oom' and role=='auth'},'RestartCount':0}]).encode()
  def run(argv,**kwargs):
   self.assertIsInstance(kwargs.get('timeout'),int)
   if argv[:2]==['docker','stop']:
    role=next(role for role,cid in IDS.items() if cid==argv[-1]);calls.append(role)
    if mode=='timeout' and role=='adapter':raise n.subprocess.TimeoutExpired(argv,35)
    stopped.add(role)
   else:
    self.assertEqual(argv[:2],['docker','logs']);self.log_timeouts.append(kwargs['timeout'])
    if argv[-1]==IDS['graphql'] and (mode=='log_timeout' or mode=='slow_logs' and kwargs['timeout']<11):raise n.subprocess.TimeoutExpired(argv,kwargs['timeout'])
   return n.subprocess.CompletedProcess(argv,0,stdout=b'')
  with tempfile.TemporaryDirectory() as directory,patch.object(n.subprocess,'check_output',side_effect=output),patch.object(n.subprocess,'run',side_effect=run):
   report=n.stop_owned(IDS,Path(directory)/'evidence',roles)
   self.assertIsInstance(report,dict,'Stop helper must retain a real structured terminal report')
   self.assertTrue((Path(directory)/'evidence/result.json').is_file())
  return calls,report
 def test_stops_every_exact_id_and_proves_terminal_state(self):
  calls,value=self.exercise('ok');self.assertEqual(calls,list(n.STOP_ORDER));self.assertTrue(value['all_stopped']);self.assertEqual(value['failures'],[])
 def test_stop_timeout_cannot_skip_other_ids_or_claim_clean_stop(self):
  calls,value=self.exercise('timeout');self.assertEqual(calls,list(n.STOP_ORDER));self.assertTrue(value['failures']);self.assertFalse(value['all_stopped']);self.assertFalse(value['full_stack_clean_stop'])
 def test_oom_diagnostic_cannot_skip_later_stops(self):
  calls,value=self.exercise('oom');self.assertEqual(calls,list(n.STOP_ORDER));self.assertTrue(value['failures']);self.assertFalse(value['full_stack_clean_stop'])
 def test_never_stops_a_mismatched_project_but_continues_other_owned_roles(self):
  calls,value=self.exercise('ownership');self.assertEqual(calls,['auth','graphql','db']);self.assertTrue(value['failures']);self.assertFalse(value['all_stopped'])
 def test_complete_cumulative_logs_have_a_bounded120s_capture_budget(self):
  calls,value=self.exercise('slow_logs');self.assertEqual(calls,list(n.STOP_ORDER));self.assertTrue(value['all_stopped']);self.assertEqual(value['failures'],[]);self.assertEqual(self.log_timeouts,[120]*4)
 def test_log_capture_timeout_is_retained_and_never_claimed_successful(self):
  calls,value=self.exercise('log_timeout');self.assertEqual(calls,list(n.STOP_ORDER));self.assertTrue(value['all_stopped']);self.assertEqual(value['failures'],['graphql logs: TimeoutExpired']);self.assertFalse(value['full_stack_clean_stop'])
 def test_api_only_stop_keeps_database_running(self):
  calls,value=self.exercise('ok',('adapter','auth','graphql'));self.assertEqual(calls,['adapter','auth','graphql']);self.assertTrue(value['terminal']['db']['running']);self.assertFalse(value['all_stopped'])
if __name__=='__main__':unittest.main(verbosity=2)
