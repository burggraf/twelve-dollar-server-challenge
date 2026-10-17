"""Versioned session ordering; fake operations NEVER deploy or generate load."""
import importlib.util
import hashlib
import inspect
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
if importlib.util.find_spec('convex_retest_session'):
    import convex_retest_session as session
else:session=None


class FakeOperations:
    def __init__(self):self.calls=[];self.budget=None;self.refuse_stage=False;self.fail_attempt=False
    def prepare(self):self.calls.append(('prepare',));return {'correctness_sha256':'b'*64}
    def restart(self,stage,operation):
        self.calls.append(('restart',stage))
        assert self.budget.state['operations'][-1]['index']==operation
        assert self.budget.state['operations'][-1]['outcome'] is None
        return {'correctness_sha256':'b'*64,'lifecycle_sha256':'c'*64}
    def check_stage(self,stage):
        self.calls.append(('check_stage',stage))
        if self.refuse_stage:raise RuntimeError('Measured stage precondition refused')
    def recheck(self,stage,gate):self.calls.append(('recheck',stage))
    def attempt(self,vus,smoke,stage):
        self.calls.append(('attempt',vus,smoke,stage))
        assert self.budget.state['operations'][-1]['outcome'] is None
        assert self.budget.state['operations'][-1]['kind']==('smoke' if smoke else 'full')
        if self.fail_attempt:raise RuntimeError('private-fake-operation-detail')
        return 'pass','retained/fake-'+str(len(self.calls))
    def freeze(self,stage):self.calls.append(('freeze',stage));return {'correctness_sha256':'b'*64,'lifecycle_sha256':'c'*64}
    def stop(self,stage,operation):
        self.calls.append(('stop',stage))
        assert self.budget.state['operations'][-1]['index']==operation
        assert self.budget.state['operations'][-1]['final_cleanup']


class VersionedSession(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name);self.ops=FakeOperations();self.now=[0.]

    def create(self):
        factory=getattr(session,'Session',None)
        self.assertTrue(callable(factory),'Missing actual versioned session ordering/accounting')
        value=factory(self.root,boot_sha256='a'*64,operations=self.ops,clock=lambda:self.now[0])
        self.ops.budget=value.budget;self.addCleanup(value.close)
        return value

    def calibrated(self):
        value=self.create();value.prepare();value.smoke(25);value.smoke(100)
        return value

    def test_explicit_setup_recovery_carry_is_wired_before_any_native_operation(self):
        self.assertIn('setup_recovery',inspect.signature(session.Session).parameters,'Missing explicit setup recovery wiring')
        prior=session.StudyBudget(self.root/'old/study-budget.json',boot_sha256='a'*64,clock=lambda:0.)
        prior.reserve('shutdown',stage='baseline',final_cleanup=True);prior.close();original=prior.path.read_bytes()
        proof={'prior_path':prior.path,'prior_sha256':hashlib.sha256(original).hexdigest(),'approval_sha256':'d'*64}
        value=session.Session(self.root/'new',boot_sha256='a'*64,operations=self.ops,clock=lambda:0.,setup_recovery=proof);self.addCleanup(value.close)
        self.assertEqual(self.ops.calls,[]);self.assertEqual(prior.path.read_bytes(),original)
        self.assertEqual(value.budget.state['setup_recovery']['carried_shutdown_reservations'],1)
        index=value.budget.reserve('shutdown',stage='baseline');self.assertEqual(value.budget.state['operations'][-1]['kind_index'],2)

    def test_construction_never_deploys_or_starts_the_diagnostic_clock(self):
        value=self.create();self.assertEqual(self.ops.calls,[])
        self.assertIsNone(value.budget.state['sequence_started_monotonic'])
        self.assertEqual(value.phase,'new')

    def test_no_smoke_or_capacity_before_actual_preparation_lifecycle_and_freeze_gates(self):
        value=self.create()
        with self.assertRaises(RuntimeError):value.smoke(25)
        with self.assertRaises(RuntimeError):value.capacity()
        self.assertEqual(self.ops.calls,[])

    def test_prepare_reserves_planned_transition_before_restart_and_does_not_start_clock(self):
        value=self.create();value.prepare()
        self.assertEqual(value.phase,'diagnostics');self.assertEqual(value.stage,'baseline')
        self.assertIsNone(value.budget.state['sequence_started_monotonic'])
        self.assertEqual(value.budget.state['operations'][0]['kind'],'shutdown')
        self.assertEqual(value.budget.state['operations'][0]['outcome'],'pass')
        with self.assertRaises(RuntimeError):value.prepare()

    def test_two_baseline_smokes_precede_tuning_and_share_one_clock(self):
        value=self.create();value.prepare()
        with self.assertRaises(RuntimeError):value.apply_stage('official')
        with self.assertRaises(RuntimeError):value.smoke(100)
        value.smoke(25);self.now[0]=100.;value.smoke(100)
        self.assertEqual(value.budget.state['sequence_started_monotonic'],0.)
        value.apply_stage('official')
        self.assertEqual(value.stage,'official')
        with self.assertRaises(RuntimeError):value.apply_stage('pg32')

    def test_stage_preconditions_are_checked_before_consuming_a_shutdown_slot(self):
        value=self.calibrated();before=len(value.budget.state['operations']);self.ops.refuse_stage=True
        with self.assertRaises(RuntimeError):value.apply_stage('official')
        self.assertEqual(len(value.budget.state['operations']),before)
        self.assertEqual(value.stage,'baseline')

    def test_unapproved_skipped_or_repeated_stages_are_not_arbitrary_restart_authority(self):
        value=self.calibrated()
        for name in ['unknown','pg32','workers64','http8','baseline']:
            with self.subTest(stage=name),self.assertRaises((RuntimeError,ValueError)):value.apply_stage(name)
        value.apply_stage('official');value.smoke(100)
        with self.assertRaises(RuntimeError):value.apply_stage('official')

    def test_pending_runtime_failure_is_preserved_and_prevents_more_operations(self):
        value=self.calibrated();value.apply_stage('official');self.ops.fail_attempt=True
        with self.assertRaises(RuntimeError):value.smoke(100)
        row=value.budget.state['operations'][-1]
        self.assertIsNone(row['outcome']);self.assertEqual(row['kind'],'smoke')
        self.assertEqual(value.phase,'paused')
        count=len(self.ops.calls)
        with self.assertRaises(RuntimeError):value.apply_stage('official')
        self.assertEqual(len(self.ops.calls),count)
        self.assertNotIn('private-fake-operation-detail',(self.root/'study-budget.json').read_text())

    def test_freeze_requires_a_measured_current_profile_and_then_prohibits_tuning(self):
        value=self.calibrated();value.apply_stage('official')
        with self.assertRaises(RuntimeError):value.freeze()
        value.smoke(100);value.freeze()
        self.assertEqual(value.phase,'capacity_ready')
        with self.assertRaises(RuntimeError):value.apply_stage('pg32')
        with self.assertRaises(RuntimeError):value.smoke(100)

    def test_fake_full_search_uses_versioned_ascending_policy_and_additional_confirmations(self):
        value=self.calibrated();value.freeze();result=value.capacity()
        full=[item[1] for item in self.ops.calls if item[0]=='attempt' and item[2] is False]
        self.assertEqual(full,[25,50,100,200,400,800,1600,2000,2000,2000,2000])
        self.assertEqual(result['status'],'confirmed_lower_bound_pending_human_review')
        self.assertFalse(result['maximum_established'])
        self.assertEqual(value.phase,'finished')
        with self.assertRaises(RuntimeError):value.capacity()

    def test_review_and_diagnostic_time_cannot_be_reset_when_capacity_begins(self):
        value=self.calibrated();self.now[0]=14100.;value.freeze();result=value.capacity()
        self.assertEqual(result['status'],'unconfirmed_time_budget')
        self.assertFalse(any(item[0]=='attempt' and item[2] is False for item in self.ops.calls))
        self.assertEqual(value.budget.state['sequence_started_monotonic'],0.)

    def test_stop_only_cleanup_is_reserved_and_never_restarts_the_backend(self):
        value=self.calibrated();before=len([item for item in self.ops.calls if item[0]=='restart'])
        value.stop();self.assertEqual(value.phase,'stopped')
        self.assertEqual(before,len([item for item in self.ops.calls if item[0]=='restart']))
        self.assertTrue(value.budget.state['operations'][-1]['final_cleanup'])
        with self.assertRaises(RuntimeError):value.smoke(25)

    def test_primitive_scope_refusal_does_not_enter_a_native_attempt(self):
        value=self.calibrated();count=len(self.ops.calls)
        with self.assertRaises(ValueError):value.smoke(1000)
        self.assertEqual(len(self.ops.calls),count)


if __name__=='__main__':unittest.main(verbosity=2)
