"""Shared diagnostic/full deadline and durable physical-operation reservations."""
import importlib.util
import hashlib
import inspect
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
if importlib.util.find_spec('convex_retest_budget'):
    import convex_retest_budget as budget
else:budget=None


class SharedBudget(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'study-budget.json';self.now=[0.0]

    def create(self,path=None):
        factory=getattr(budget,'StudyBudget',None)
        self.assertTrue(callable(factory),'Missing shared durable native study budget')
        value=factory(path or self.path,boot_sha256='a'*64,clock=lambda:self.now[0])
        self.addCleanup(value.close)
        return value

    def start(self,value):value.begin_sequence(correctness_sha256='b'*64,lifecycle_sha256='c'*64)

    def closed_setup(self):
        old=self.create();old.reserve('shutdown',stage='baseline',final_cleanup=True);old.close()
        return {'prior_path':self.path,'prior_sha256':hashlib.sha256(self.path.read_bytes()).hexdigest(),'approval_sha256':'d'*64}

    def recover(self,proof,path=None):
        self.assertIn('setup_recovery',inspect.signature(budget.StudyBudget).parameters,'Missing explicit setup-only recovery accounting')
        value=budget.StudyBudget(path or self.path.with_name('recovery.json'),boot_sha256='a'*64,clock=lambda:self.now[0],setup_recovery=proof)
        self.addCleanup(value.close);return value

    def test_explicit_setup_recovery_carries_spent_shutdown_and_reserves_original_eighth_cleanup_slot(self):
        value=self.recover(self.closed_setup())
        for ordinal in range(2,8):
            index=value.reserve('shutdown',stage='baseline');self.assertEqual(value.state['operations'][-1]['kind_index'],ordinal);value.complete(index,'pass')
        with self.assertRaises(RuntimeError):value.reserve('shutdown',stage='baseline')
        index=value.reserve('shutdown',stage='baseline',final_cleanup=True);self.assertEqual(value.state['operations'][-1]['kind_index'],8)
        value.complete(index,'pass')
        with self.assertRaises(RuntimeError):value.reserve('shutdown',stage='baseline',final_cleanup=True)

    def test_setup_recovery_preserves_original_null_row_and_records_actual_prior_and_approval_hashes(self):
        proof=self.closed_setup();original=self.path.read_bytes();value=self.recover(proof)
        self.assertEqual(self.path.read_bytes(),original);self.assertIsNone(json.loads(original)['operations'][0]['outcome'])
        self.assertEqual(value.state['setup_recovery']['prior_budget_sha256'],proof['prior_sha256']);self.assertEqual(value.state['setup_recovery']['approval_sha256'],'d'*64)
        self.assertIsNone(value.state['sequence_started_monotonic']);self.assertEqual(value.state['limits'],{'smoke':6,'full':16,'shutdown':8})

    def test_setup_recovery_cannot_reset_an_already_started_diagnostic_clock(self):
        proof=self.closed_setup();old=json.loads(self.path.read_text());old['sequence_started_monotonic']=0.;self.path.write_text(json.dumps(old));proof['prior_sha256']=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaises(RuntimeError):self.recover(proof)

    def test_setup_recovery_cannot_replace_any_prior_load_or_extra_operation(self):
        proof=self.closed_setup();old=json.loads(self.path.read_text());old['operations'][0]['kind']='full';self.path.write_text(json.dumps(old));proof['prior_sha256']=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaises(RuntimeError):self.recover(proof)

    def test_setup_recovery_requires_exact_prior_bytes_and_explicit_approval_fingerprint(self):
        proof=self.closed_setup()
        with self.assertRaises((RuntimeError,ValueError)):self.recover(proof|{'prior_sha256':'e'*64})
        with self.assertRaises((RuntimeError,ValueError)):self.recover(proof|{'approval_sha256':None})

    def test_setup_recovery_is_exclusive_across_distinct_new_ledger_paths(self):
        proof=self.closed_setup();value=self.recover(proof);value.close()
        with self.assertRaises(RuntimeError):self.recover(proof,self.path.with_name('another-recovery.json'))

    def test_setup_recovery_rejects_a_different_boot_or_nonterminal_prior_shutdown(self):
        proof=self.closed_setup();old=json.loads(self.path.read_text());old['boot_sha256']='e'*64;self.path.write_text(json.dumps(old));proof['prior_sha256']=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaises(RuntimeError):self.recover(proof)

    def test_setup_recovery_prior_drift_blocks_new_effects_instead_of_changing_history(self):
        proof=self.closed_setup();value=self.recover(proof);self.path.write_text(self.path.read_text()+'\n')
        with self.assertRaises(RuntimeError):value.reserve('shutdown',stage='baseline')
        self.assertEqual(value.state['operations'],[])

    def test_prestart_preflight_correction_carries_both_closed_ledgers_without_resuming_either(self):
        root=self.closed_setup();first=self.recover(root)
        index=first.reserve('shutdown',stage='baseline',final_cleanup=True);first.complete(index,'pass');first.close()
        original=self.path.read_bytes();prior=first.path.read_bytes()
        proof={'prior_path':first.path,'prior_sha256':hashlib.sha256(prior).hexdigest(),'approval_sha256':'d'*64,'previous':root}
        second=None
        try:second=self.recover(proof,self.path.with_name('preflight-correction.json'))
        except RuntimeError:pass
        self.assertIsNotNone(second,'Explicit pre-start correction must carry every closed terminal reservation')
        self.assertEqual(second.state['setup_recovery']['carried_shutdown_reservations'],2)
        self.assertEqual(self.path.read_bytes(),original);self.assertEqual(first.path.read_bytes(),prior)
        index=second.reserve('shutdown',stage='baseline');self.assertEqual(second.state['operations'][-1]['kind_index'],3)

    def test_full_load_cannot_precede_explicit_diagnostic_clock_and_frozen_gate_links(self):
        value=self.create()
        with self.assertRaises(RuntimeError):value.reserve('full',vus=25,stage='baseline')
        self.assertEqual(json.loads(self.path.read_text())['operations'],[])
        self.start(value)
        state=json.loads(self.path.read_text())
        self.assertEqual(state['sequence_started_monotonic'],0.)
        self.assertEqual(state['correctness_sha256'],'b'*64)
        self.assertEqual(state['lifecycle_sha256'],'c'*64)

    def test_six_smokes_are_shared_across_stages_and_cannot_be_replaced(self):
        value=self.create();self.start(value)
        for stage in ['baseline','baseline','official','pg32','workers64','http8']:
            index=value.reserve('smoke',vus=100,stage=stage);value.complete(index,'pass')
        with self.assertRaises(RuntimeError):value.reserve('smoke',vus=25,stage='baseline')
        self.assertEqual(len(json.loads(self.path.read_text())['operations']),6)

    def test_sixteen_full_reservations_include_pending_and_invalid_operations(self):
        value=self.create();self.start(value)
        for _ in range(15):index=value.reserve('full',vus=25,stage='baseline');value.complete(index,'pass')
        last=value.reserve('full',vus=25,stage='baseline')
        state=json.loads(self.path.read_text());self.assertEqual(len(state['operations']),16)
        self.assertIsNone(state['operations'][-1]['outcome'])
        value.complete(last,'invalid')
        with self.assertRaises(RuntimeError):value.reserve('full',vus=25,stage='baseline')
        self.assertEqual(len(json.loads(self.path.read_text())['operations']),16)

    def test_restart_budget_includes_pre_diagnostic_transitions_and_reserves_final_cleanup(self):
        value=self.create()
        for _ in range(7):index=value.reserve('shutdown',stage='baseline');value.complete(index,'pass')
        with self.assertRaises(RuntimeError):value.reserve('shutdown',stage='baseline')
        index=value.reserve('shutdown',stage='baseline',final_cleanup=True);value.complete(index,'pass')
        self.assertEqual(index,8)
        with self.assertRaises(RuntimeError):value.reserve('shutdown',stage='baseline',final_cleanup=True)

    def test_full_campaign_does_not_reset_time_spent_on_diagnostics(self):
        value=self.create();self.start(value)
        index=value.reserve('smoke',vus=25,stage='baseline');self.now[0]=14000.;value.complete(index,'pass')
        with self.assertRaises(RuntimeError):value.reserve('full',vus=25,stage='baseline')
        with self.assertRaises(RuntimeError):self.start(value)
        self.assertEqual(json.loads(self.path.read_text())['sequence_started_monotonic'],0.)

    def test_returning_after_the_deadline_cannot_leave_permission_for_another_operation(self):
        value=self.create();self.start(value)
        index=value.reserve('full',vus=25,stage='baseline');self.now[0]=14401.
        with self.assertRaises(RuntimeError):value.complete(index,'pass')
        state=json.loads(self.path.read_text());self.assertTrue(state['blocked'])
        self.assertEqual(state['operations'][0]['outcome'],'pass')
        with self.assertRaises(RuntimeError):value.reserve('smoke',vus=25,stage='baseline')

    def test_pending_operation_prevents_implicit_replacement_but_allows_stop_only_cleanup(self):
        value=self.create();self.start(value);value.reserve('full',vus=25,stage='baseline')
        with self.assertRaises(RuntimeError):value.reserve('full',vus=25,stage='baseline')
        cleanup=value.reserve('shutdown',stage='baseline',final_cleanup=True)
        state=json.loads(self.path.read_text())
        self.assertTrue(state['operations'][-1]['final_cleanup'])
        self.assertIsNone(state['operations'][0]['outcome'])
        value.complete(cleanup,'pass')

    def test_runtime_failure_blocks_more_work_and_cannot_be_cleared_by_cleanup(self):
        value=self.create();self.start(value)
        index=value.reserve('smoke',vus=25,stage='baseline');value.complete(index,'runtime_failure')
        cleanup=value.reserve('shutdown',stage='baseline',final_cleanup=True);value.complete(cleanup,'pass')
        with self.assertRaises(RuntimeError):value.reserve('full',vus=25,stage='baseline')
        self.assertTrue(json.loads(self.path.read_text())['blocked'])

    def test_retained_or_symlinked_state_is_not_implicitly_resumed_or_overwritten(self):
        value=self.create();before=self.path.read_bytes()
        with self.assertRaises(RuntimeError):self.create()
        self.assertEqual(self.path.read_bytes(),before)
        link=self.path.parent/'link.json';link.symlink_to(self.path)
        with self.assertRaises(RuntimeError):self.create(link)
        self.assertEqual(self.path.read_bytes(),before)

    def test_unknown_stage_kind_or_out_of_scope_vus_fail_before_a_reservation(self):
        value=self.create();self.start(value)
        for kind,vus,stage in [('full',2001,'baseline'),('smoke',1000,'baseline'),('full',25,'unknown'),('unknown',25,'baseline')]:
            with self.subTest(kind=kind,vus=vus,stage=stage),self.assertRaises((ValueError,RuntimeError)):value.reserve(kind,vus=vus,stage=stage)
        self.assertEqual(json.loads(self.path.read_text())['operations'],[])

    def test_only_the_current_pending_index_can_be_completed_once(self):
        value=self.create();self.start(value);index=value.reserve('full',vus=25,stage='baseline')
        with self.assertRaises(RuntimeError):value.complete(index+1,'pass')
        with self.assertRaises(ValueError):value.complete(index,'unrecognized')
        value.complete(index,'fail')
        with self.assertRaises(RuntimeError):value.complete(index,'pass')
        self.assertEqual(json.loads(self.path.read_text())['operations'][0]['outcome'],'fail')

    def test_clock_regression_and_missing_gate_fingerprints_fail_closed(self):
        value=self.create()
        with self.assertRaises(ValueError):value.begin_sequence(correctness_sha256=None,lifecycle_sha256='c'*64)
        self.start(value);self.now[0]=-1.
        with self.assertRaises(RuntimeError):value.reserve('smoke',vus=25,stage='baseline')
        self.assertEqual(json.loads(self.path.read_text())['operations'],[])


if __name__=='__main__':unittest.main(verbosity=2)
