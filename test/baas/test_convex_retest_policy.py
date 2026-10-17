"""Versioned low-load-first search: real policy, callback only instead of traffic."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import benchmark as historical
if importlib.util.find_spec('convex_retest_policy'):
    import convex_retest_policy as policy
else:
    policy=historical  # Exercise the actual old behavior for a meaningful native RED.


class AscendingRetest(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        self.file=self.root/'campaign.json'
        self.calls=[]
        self.args=SimpleNamespace(max_vus=2000,max_attempts=16,time_budget_seconds=14400)

    def run_study(self,callback=None,**kwargs):
        if callback is None:callback=lambda vus,tier:('pass','retained/'+str(vus))
        def record(vus,tier):
            self.calls.append(vus)
            return callback(vus,tier)
        policy.campaign(self.args,'standard',attempt_runner=record,results=self.root/'results',campaign_file=self.file,**kwargs)
        return json.loads(self.file.read_text())

    def test_ascending_starts_at25_and_doubles_without_overshooting2000(self):
        self.run_study()
        self.assertEqual(self.calls[:8],[25,50,100,200,400,800,1600,2000])
        self.assertLessEqual(max(self.calls),2000)

    def test_upper_cap_requires_three_additional_confirmations_not_just_discovery(self):
        result=self.run_study()
        self.assertEqual(self.calls,[25,50,100,200,400,800,1600,2000,2000,2000,2000])
        self.assertEqual(result.get('candidate_vus'),2000)
        self.assertEqual(result.get('status'),'confirmed_lower_bound_pending_human_review')
        self.assertIsNone(result.get('upper_failure_vus'))
        self.assertFalse(result.get('maximum_established',True))

    def test_reservation_is_durable_before_callback_even_if_callback_raises(self):
        def uncertain(vus,tier):
            self.assertTrue(self.file.exists(),'Reserve the physical slot before entering the adapter')
            pending=json.loads(self.file.read_text())
            self.assertEqual(pending.get('slots_consumed'),1)
            self.assertIsNone(pending['attempts'][0]['outcome'])
            raise RuntimeError('private-callback-detail-must-not-be-exported')
        with self.assertRaises(RuntimeError):self.run_study(uncertain)
        result=json.loads(self.file.read_text())
        self.assertEqual(len(self.calls),1)
        self.assertEqual(result.get('slots_consumed'),1)
        self.assertIsNone(result['attempts'][0]['outcome'])
        self.assertEqual(result.get('status'),'paused_unconfirmed')

    def test_exception_does_not_copy_private_callback_message_into_public_ledger(self):
        def uncertain(vus,tier):raise RuntimeError('private-callback-detail-must-not-be-exported')
        with self.assertRaises(RuntimeError):self.run_study(uncertain)
        self.assertNotIn('private-callback-detail-must-not-be-exported',self.file.read_text())
        self.assertEqual(self.calls,[25])

    def test_invalid_measurement_stops_without_a_target_failure_bracket(self):
        with self.assertRaises(RuntimeError):self.run_study(lambda vus,tier:('invalid','retained/invalid'))
        result=json.loads(self.file.read_text())
        self.assertEqual(self.calls,[25])
        self.assertEqual(result.get('status'),'paused_unconfirmed')
        self.assertIsNone(result.get('upper_failure_vus'))
        self.assertEqual(result['attempts'][0]['outcome'],'invalid')

    def test_valid25_failure_uses_predeclared10_5_1_fallback(self):
        result=self.run_study(lambda vus,tier:('pass' if vus<=1 else 'fail','retained/'+str(vus)))
        self.assertEqual(self.calls[:4],[25,10,5,1])
        self.assertEqual(result.get('candidate_vus'),1)
        self.assertEqual(result.get('resolution_vus'),1)
        self.assertEqual(self.calls[-3:],[1,1,1])

    def test_even1_failure_is_not_a_claim_of_zero_capacity_or_a_global_maximum(self):
        result=self.run_study(lambda vus,tier:('fail','retained/failure'))
        self.assertEqual(self.calls,[25,10,5,1])
        self.assertEqual(result.get('status'),'no_passing_probe')
        self.assertIsNone(result.get('candidate_vus'))
        self.assertFalse(result.get('maximum_established',True))

    def test_sub25_narrows_at1vu_resolution(self):
        result=self.run_study(lambda vus,tier:('pass' if vus<=7 else 'fail','retained/'+str(vus)))
        self.assertEqual(result.get('candidate_vus'),7)
        self.assertEqual(result.get('upper_failure_vus'),8)
        self.assertEqual(result.get('resolution_vus'),1)
        self.assertEqual(self.calls[-3:],[7,7,7])

    def test_narrowing_below250_has25vu_resolution(self):
        result=self.run_study(lambda vus,tier:('pass' if vus<=225 else 'fail','retained/'+str(vus)))
        self.assertEqual(result.get('candidate_vus'),225)
        self.assertEqual(result.get('upper_failure_vus'),250)
        self.assertEqual(result.get('resolution_vus'),25)
        self.assertEqual(self.calls[-3:],[225,225,225])

    def test_narrowing_larger_ranges_reports_actual_interval(self):
        result=self.run_study(lambda vus,tier:('pass' if vus<=1499 else 'fail','retained/'+str(vus)))
        candidate=result.get('candidate_vus')
        self.assertIsNotNone(candidate)
        self.assertLessEqual(candidate,1499)
        self.assertIsNotNone(result.get('upper_failure_vus'),'Retain the actual valid upper failure')
        self.assertLessEqual(result['upper_failure_vus']-candidate,250)
        self.assertEqual(result.get('resolution_vus'),250)
        self.assertFalse(result.get('maximum_established',True))

    def test_failed_confirmation_never_pools_other_passes_and_steps_down(self):
        count=0
        def one_failure(vus,tier):
            nonlocal count
            count+=1
            return ('fail' if count==9 else 'pass','retained/'+str(count))
        result=self.run_study(one_failure)
        self.assertEqual(result.get('candidate_vus'),1750)
        self.assertEqual(self.calls[-4:],[1750]*4)  # New probe plus three NEW confirmations.
        indices=result.get('confirmation_attempt_indices',[])
        self.assertEqual(len(indices),3)
        self.assertEqual([result['attempts'][i-1]['purpose'] for i in indices],['confirmation']*3)
        self.assertEqual([result['attempts'][i-1]['vus'] for i in indices],[1750]*3)

    def test_a_small_budget_reserves_three_confirmations_instead_of_unconfirmed_ascent(self):
        self.args.max_attempts=4
        result=self.run_study()
        self.assertEqual(self.calls,[25,25,25,25])
        self.assertEqual(result.get('candidate_vus'),25)
        self.assertEqual(result.get('status'),'confirmed_lower_bound_pending_human_review')

    def test_budget_exhaustion_is_unconfirmed_and_does_not_execute_extra_attempt(self):
        self.args.max_attempts=1
        result=self.run_study()
        self.assertEqual(self.calls,[25])
        self.assertEqual(result.get('status'),'unconfirmed_budget_exhausted')
        self.assertIsNone(result.get('candidate_vus'))
        self.assertEqual(result.get('slots_consumed'),1)

    def test_cap_and_modes_fail_closed_before_any_callback(self):
        for field,bad in [('max_attempts',17),('max_attempts',True),('max_attempts',0),('max_vus',2001),('max_vus',24),('time_budget_seconds',14401)]:
            with self.subTest(field=field,bad=bad):
                args=SimpleNamespace(**vars(self.args));setattr(args,field,bad)
                error=None
                try:policy.campaign(args,'standard',attempt_runner=lambda *a:self.fail('Must not execute'),results=self.root/'results',campaign_file=self.root/(field+str(bad)+'.json'))
                except BaseException as caught:error=caught
                self.assertIsInstance(error,ValueError)

    def test_wrong_tier_cannot_use_this_authority(self):
        error=None
        try:policy.campaign(self.args,'large',attempt_runner=lambda *a:self.fail('Must not execute'),results=self.root/'results',campaign_file=self.file)
        except BaseException as caught:error=caught
        self.assertIsInstance(error,ValueError)
        self.assertEqual(self.calls,[])

    def test_existing_campaign_is_never_implicitly_resumed_or_overwritten(self):
        original=b'{"preserve":"original"}\n';self.file.write_bytes(original)
        error=None
        try:self.run_study()
        except BaseException as caught:error=caught
        self.assertIsInstance(error,RuntimeError)
        self.assertEqual(self.calls,[])
        self.assertEqual(self.file.read_bytes(),original)

    def test_unrecognized_outcome_is_not_a_valid_slo_failure(self):
        error=None
        try:self.run_study(lambda vus,tier:('unknown','retained/unknown'))
        except BaseException as caught:error=caught
        self.assertIsInstance(error,RuntimeError)
        self.assertEqual(self.calls,[25])
        result=json.loads(self.file.read_text())
        self.assertIsNone(result.get('upper_failure_vus'))
        self.assertEqual(result.get('status'),'paused_unconfirmed')

    def test_pending_and_completed_journal_are_retained_separately(self):
        self.run_study()
        journal=self.file.with_suffix('.journal.jsonl')
        self.assertTrue(journal.is_file(),'Append-only pending/completed journal is required')
        rows=[json.loads(line) for line in journal.read_text().splitlines()]
        reservations=[r for r in rows if r.get('event')=='reserved']
        completions=[r for r in rows if r.get('event')=='completed']
        self.assertEqual(len(reservations),len(self.calls))
        self.assertEqual(len(completions),len(self.calls))
        for reservation,completion in zip(reservations,completions):
            self.assertIsNone(reservation['attempt']['outcome'])
            self.assertEqual(reservation['attempt']['index'],completion['attempt']['index'])
            self.assertEqual(completion['attempt']['outcome'],'pass')

    def test_runtime_exception_never_invokes_another_callback(self):
        def failed_runtime(vus,tier):raise RuntimeError('serving process OOM')
        with self.assertRaises(RuntimeError):self.run_study(failed_runtime)
        self.assertEqual(self.calls,[25])
        self.assertEqual(json.loads(self.file.read_text()).get('status'),'paused_unconfirmed')

    def test_last_confirmation_finishing_after_deadline_cannot_establish_a_score(self):
        self.args.max_attempts=4
        now=[0.0];count=0
        def elapsed(vus,tier):
            nonlocal count
            count+=1;now[0]=14401. if count==4 else count*600.
            return 'pass','retained/'+str(count)
        result=self.run_study(elapsed,clock=lambda:now[0])
        self.assertEqual(self.calls,[25]*4)
        self.assertEqual(result.get('status'),'unconfirmed_time_budget')
        self.assertIsNone(result.get('candidate_vus'))

    def test_time_ceiling_prevents_starting_another_full_attempt(self):
        self.assertIn('clock',__import__('inspect').signature(policy.campaign).parameters,'Explicit monotonic deadline is required')
        now=[0.0]
        def elapsed(vus,tier):now[0]=14001.;return 'pass','retained/first'
        result=self.run_study(elapsed,clock=lambda:now[0])
        self.assertEqual(self.calls,[25])
        self.assertEqual(result.get('status'),'unconfirmed_time_budget')
        self.assertIsNone(result.get('candidate_vus'))


if __name__=='__main__':unittest.main(verbosity=2)
