"""Native-only TDD for the owner-approved fixed twelve-row study, not new scoring."""
from copy import deepcopy
import importlib.util
import itertools
from pathlib import Path
import unittest

path = Path(__file__).with_name('supplemental_repeatability_policy.py')
if path.exists():
    spec = importlib.util.spec_from_file_location('repeatability', path)
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
else:
    policy = None

EXPECTED = [10000,11000,11250, 10000,11250,11000, 10000,11000,11250, 10000,11250,11000]


def prior():
    rows = [(10000,'lower_anchor','pass'), (11250,'upper_anchor','pass'),
            (12250,'upper_anchor','fail'), (11750,'boundary_probe','fail'),
            (11500,'boundary_probe','fail'), (11250,'candidate_confirmation','pass'),
            (11250,'candidate_confirmation','fail')]
    return {'status':'paused_unconfirmed',
            'reason':'candidate_confirmation contradicted required pass; stop and investigate',
            'historical_full_attempts':11, 'supplemental_limit':10,
            'total_physical_full_attempts_accounted':18,
            'attempts':[{'vus':v,'purpose':p,'outcome':o,'run':'preserved-'+str(i)}
                        for i,(v,p,o) in enumerate(rows,1)]}


class RepeatabilityTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(policy is not None and callable(getattr(policy,'finish',None)),
                        'Missing approved fixed-study scheduling policy')

    def run_case(self, override=None, budget=12, old=None):
        calls, snapshots = [], []
        def attempt(vus, purpose):
            calls.append((vus,purpose))
            value = override(len(calls),vus,purpose) if override else None
            if isinstance(value,dict):
                return value
            return {'outcome': value or ('fail' if vus==11250 else 'pass'),
                    'run':'new-'+str(len(calls)), 'reason':'unchanged native gates'}
        phase = policy.finish(attempt, prior() if old is None else old,
                              record=snapshots.append, max_attempts=budget)
        return phase, calls, snapshots

    def test_exact_schedule_and_three_additional_candidate_passes(self):
        p,c,_ = self.run_case()
        self.assertEqual([v for v,_ in c],EXPECTED)
        self.assertEqual(p['status'],'complete_pending_human_review')
        self.assertTrue(p['boundary_confirmed_by_hold_gates'])
        self.assertEqual(p['study_result'],'observed_250vu_boundary')
        self.assertEqual(sum(v==11000 and purpose=='candidate_characterization' for v,purpose in c),1)
        self.assertEqual(sum(v==11000 and purpose=='candidate_confirmation' for v,purpose in c),3)
        self.assertEqual(sum(v==10000 for v,_ in c),4)
        self.assertEqual(sum(v==11250 for v,_ in c),4)

    def test_cumulative_budget_preserves_seven_prior_and_eighteen_physical(self):
        p,_,s = self.run_case()
        self.assertEqual(p['attempts'][:7],prior()['attempts'])
        self.assertEqual(len(p['attempts']),19)
        self.assertEqual(p['historical_full_attempts'],11)
        self.assertEqual(p['prior_supplemental_attempts'],7)
        self.assertEqual(p['supplemental_limit'],19)
        self.assertEqual(p['total_physical_full_attempts_accounted'],30)
        self.assertEqual(s[0]['total_physical_full_attempts_accounted'],18)

    def test_all_256_candidate_upper_patterns_use_all_rows_without_selecting_favorable_subset(self):
        for candidate in itertools.product(('pass','fail'),repeat=4):
            for upper in itertools.product(('pass','fail'),repeat=4):
                with self.subTest(candidate=candidate,upper=upper):
                    seen={11000:0,11250:0}
                    def choose(n,v,purpose):
                        if v==10000:
                            return 'pass'
                        i=seen[v];seen[v]+=1
                        return (candidate if v==11000 else upper)[i]
                    p,c,_=self.run_case(override=choose)
                    self.assertEqual(len(c),12)
                    self.assertEqual(p['status'],'complete_pending_human_review')
                    classify=lambda values: 'all_pass' if set(values)=={'pass'} else ('all_fail' if set(values)=={'fail'} else 'mixed')
                    self.assertEqual(p['classifications']['candidate'],classify(candidate))
                    self.assertEqual(p['classifications']['adjacent'],classify(upper))
                    self.assertEqual(p['boundary_confirmed_by_hold_gates'],set(candidate)=={'pass'} and set(upper)=={'fail'})

    def test_three_failing_upper_and_one_passing_upper_is_mixed_not_boundary(self):
        p,c,_=self.run_case(override=lambda n,v,p:'pass' if n==3 else None)
        self.assertEqual(len(c),12);self.assertEqual(p['classifications']['adjacent'],'mixed')
        self.assertFalse(p['boundary_confirmed_by_hold_gates'])

    def test_first_candidate_fail_and_three_later_passes_not_confirmed(self):
        p,c,_=self.run_case(override=lambda n,v,p:'fail' if n==2 else None)
        self.assertEqual(len(c),12);self.assertEqual(p['classifications']['candidate'],'mixed')
        self.assertFalse(p['boundary_confirmed_by_hold_gates'])

    def test_upper_all_pass_does_not_expand(self):
        p,c,_=self.run_case(override=lambda n,v,p:'pass')
        self.assertEqual([v for v,_ in c],EXPECTED);self.assertFalse(p['boundary_confirmed_by_hold_gates'])
        self.assertEqual(p['study_result'],'no_failing_adjacent_boundary')

    def test_nonmonotonic_results_are_retained_without_stepdown(self):
        p,c,_=self.run_case(override=lambda n,v,p:'fail' if v==11000 else 'pass')
        self.assertEqual([v for v,_ in c],EXPECTED);self.assertFalse(p['boundary_confirmed_by_hold_gates'])
        self.assertEqual(p['study_result'],'candidate_not_confirmed')

    def test_each_control_failure_stops_and_retains_that_slot(self):
        for slot in [1,4,7,10]:
            with self.subTest(slot=slot):
                p,c,_=self.run_case(override=lambda n,v,p:'fail' if n==slot else None)
                self.assertEqual(len(c),slot);self.assertEqual(p['status'],'paused_unconfirmed')
                self.assertIn('control',p['reason'].lower());self.assertFalse(p['boundary_confirmed_by_hold_gates'])
                self.assertEqual(p['attempts'][-1]['outcome'],'fail')

    def test_invalid_at_each_slot_preserves_all_cumulative_accounting(self):
        for slot in range(1,13):
            with self.subTest(slot=slot):
                p,c,_=self.run_case(override=lambda n,v,p:'invalid' if n==slot else None)
                self.assertEqual(len(c),slot);self.assertEqual(p['status'],'paused_unconfirmed')
                self.assertEqual(p['total_physical_full_attempts_accounted'],18+slot)
                self.assertEqual(p['attempts'][-1]['outcome'],'invalid')
                self.assertFalse(p['boundary_confirmed_by_hold_gates'])

    def test_unknown_and_malformed_results_never_count_as_failure_bound(self):
        for value in ['unknown', {'outcome':'fail'}, {'outcome':'pass','run':''}, None]:
            with self.subTest(value=value):
                def bad(v,p):
                    return value if isinstance(value,dict) or value is None else {'outcome':value,'run':'new'}
                phase=policy.finish(bad,prior())
                self.assertEqual(phase['status'],'paused_unconfirmed')
                self.assertEqual(len(phase['attempts']),8)
                self.assertFalse(phase['boundary_confirmed_by_hold_gates'])

    def test_exception_at_each_slot_preserves_pending_intent_and_does_not_retry(self):
        for slot in range(1,13):
            with self.subTest(slot=slot):
                calls=[];snaps=[]
                def attempt(v,p):
                    calls.append(v)
                    self.assertIsNone(snaps[-1]['attempts'][-1]['outcome'])
                    self.assertEqual(snaps[-1]['total_physical_full_attempts_accounted'],18+len(calls))
                    if len(calls)==slot:
                        raise RuntimeError('retained guard/runtime/partial failure')
                    return {'outcome':'fail' if v==11250 else 'pass','run':'new-'+str(len(calls))}
                p=policy.finish(attempt,prior(),record=snaps.append)
                self.assertEqual(len(calls),slot);self.assertEqual(p['status'],'paused_unconfirmed')
                self.assertIsNone(p['attempts'][-1]['outcome']);self.assertIn('retained',p['reason'])

    def test_each_smaller_budget_stops_without_replacement_or_resuming(self):
        for budget in range(1,12):
            with self.subTest(budget=budget):
                p,c,_=self.run_case(budget=budget)
                self.assertEqual(len(c),budget);self.assertEqual(p['status'],'paused_unconfirmed')
                self.assertIn('budget',p['reason'].lower())
                self.assertFalse(p['boundary_confirmed_by_hold_gates'])

    def test_budget_cannot_exceed_twelve_or_be_invalid(self):
        for value in [0,13,19,True,1.5,'12']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):self.run_case(budget=value)

    def test_missing_extra_invalid_relabelled_or_duplicate_prior_rows_rejected(self):
        cases=[]
        for key,value in [('status','complete_pending_human_review'),('reason','other'),
                          ('historical_full_attempts',12),('supplemental_limit',19),
                          ('total_physical_full_attempts_accounted',17)]:
            p=prior();p[key]=value;cases.append(p)
        p=prior();p['attempts'].pop();cases.append(p)
        p=prior();p['attempts'].append(deepcopy(p['attempts'][0]));cases.append(p)
        for key,value in [('vus',11000),('outcome','invalid'),('purpose','upper_confirmation'),('run','')]:
            p=prior();p['attempts'][-1][key]=value;cases.append(p)
        p=prior();p['attempts'][-1]['run']=p['attempts'][0]['run'];cases.append(p)
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):self.run_case(old=value)

    def test_prior_state_and_all_recorded_snapshots_are_deep_copies(self):
        old=prior();original=deepcopy(old)
        p,_,s=self.run_case(old=old)
        self.assertEqual(old,original);self.assertEqual(len(s[0]['attempts']),7)
        self.assertEqual(len(s[1]['attempts']),8);self.assertIsNone(s[1]['attempts'][-1]['outcome'])
        s[-1]['attempts'][0]['vus']=1
        self.assertEqual(p['attempts'][0]['vus'],10000)

    def test_physical_run_ids_must_be_new_and_unique(self):
        for run in ['preserved-1','same-new-run']:
            with self.subTest(run=run):
                p,c,_=self.run_case(override=lambda n,v,p:{'outcome':'fail' if v==11250 else 'pass','run':run})
                self.assertEqual(p['status'],'paused_unconfirmed')
                self.assertFalse(p['boundary_confirmed_by_hold_gates'])
                self.assertEqual(len(c),1 if run=='preserved-1' else 2)

    def test_pending_phase_cannot_be_implicitly_resumed(self):
        p,_,_=self.run_case(budget=3)
        with self.assertRaises(ValueError):self.run_case(old=p)

    def test_record_failure_prevents_first_side_effect(self):
        called=[]
        def record(p):raise OSError('ledger unavailable')
        with self.assertRaises(OSError):policy.finish(lambda *a:called.append(a),prior(),record=record)
        self.assertEqual(called,[])


if __name__=='__main__':unittest.main(verbosity=2)
