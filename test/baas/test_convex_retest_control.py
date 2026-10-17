"""Blocking command protocol contract; fake session, no serving effects."""
import importlib.util
import io
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
if importlib.util.find_spec('convex_retest_native'):
    import convex_retest_native as native
else:native=None


class FakeSession:
    def __init__(self):self.calls=[];self.phase='new';self.stage='baseline';self.closed=False
    def prepare(self):self.calls.append('prepare');self.phase='diagnostics'
    def smoke(self,vus):self.calls.append(('smoke',vus));return 'pass','private/never-export'
    def apply_stage(self,stage):self.calls.append(('stage',stage));self.stage=stage
    def freeze(self):self.calls.append('freeze');self.phase='capacity_ready';return {'private':'never-export'}
    def capacity(self):self.calls.append('capacity');self.phase='finished';return {'status':'confirmed_lower_bound_pending_human_review','candidate_vus':25,'private':'never-export'}
    def stop(self):self.calls.append('stop');self.phase='stopped'
    def close(self):self.closed=True


class ControlProtocol(unittest.TestCase):
    def setUp(self):self.session=FakeSession();self.output=[]
    def run_control(self,commands):
        serve=getattr(native,'serve',None)
        self.assertTrue(callable(serve),'Missing concrete-controller blocking command dispatch/cleanup')
        return serve(self.session,io.StringIO(commands),self.output.append)

    def test_eof_stops_the_owned_session_and_releases_its_lock(self):
        self.run_control('');self.assertEqual(self.session.calls,['stop']);self.assertTrue(self.session.closed)

    def test_explicit_stop_is_terminal_and_does_not_double_stop(self):
        self.run_control('{"action":"stop"}\n{"action":"prepare"}\n')
        self.assertEqual(self.session.calls,['stop']);self.assertTrue(self.session.closed)

    def test_only_predeclared_structured_actions_are_dispatched(self):
        self.run_control('{"action":"prepare"}\n{"action":"smoke","vus":25}\n{"action":"stage","stage":"official"}\n{"action":"freeze"}\n{"action":"capacity"}\n{"action":"stop"}\n')
        self.assertEqual(self.session.calls,['prepare',('smoke',25),('stage','official'),'freeze','capacity','stop'])

    def test_scope_or_extra_arguments_are_rejected_before_any_load_callback(self):
        with self.assertRaises(RuntimeError):self.run_control('{"action":"smoke","vus":25,"command":"unapproved"}\n')
        self.assertEqual(self.session.calls,['stop'])

    def test_unknown_or_malformed_command_stops_instead_of_retrying(self):
        with self.assertRaises(RuntimeError):self.run_control('{"action":"shell","command":"private-untrusted-input"}\n')
        self.assertEqual(self.session.calls,['stop']);self.assertTrue(self.session.closed)

    def test_native_callback_failure_is_not_echoed_or_implicitly_replaced(self):
        def failing():raise RuntimeError('private-untrusted-input')
        self.session.prepare=failing
        with self.assertRaises(RuntimeError):self.run_control('{"action":"prepare"}\n{"action":"prepare"}\n')
        self.assertEqual(self.session.calls,['stop']);self.assertNotIn('private-untrusted-input',str(self.output))

    def test_return_values_are_not_copied_into_numeric_control_stdout(self):
        self.run_control('{"action":"prepare"}\n{"action":"smoke","vus":25}\n{"action":"freeze"}\n{"action":"capacity"}\n')
        self.assertNotIn('never-export',str(self.output));self.assertNotIn('private',str(self.output))
        self.assertTrue(any(row.get('candidate_vus')==25 for row in self.output))

    def test_invalid_traffic_scope_is_rejected_before_the_session_callback(self):
        with self.assertRaises(RuntimeError):self.run_control('{"action":"smoke","vus":2000}\n')
        self.assertEqual(self.session.calls,['stop'])


if __name__=='__main__':unittest.main(verbosity=2)
