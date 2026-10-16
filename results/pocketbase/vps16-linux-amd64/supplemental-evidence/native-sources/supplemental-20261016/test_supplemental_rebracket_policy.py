"""Native-only regressions for owner-approved within-budget rebracket."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
path=Path(__file__).with_name('supplemental_rebracket_policy.py')
if path.exists():
 spec=importlib.util.spec_from_file_location('rebracket',path);policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
else:policy=None


def prior():
 return {'status':'paused_unconfirmed','reason':'upper_anchor contradicted required fail; stop and investigate','attempts':[{'vus':10000,'purpose':'lower_anchor','outcome':'pass','run':'original-new-1','reason':'hold gates passed'},{'vus':11250,'purpose':'upper_anchor','outcome':'pass','run':'original-new-2','reason':'hold gates passed'}]}


class RebracketTests(unittest.TestCase):
 def setUp(self):self.assertTrue(policy is not None and callable(getattr(policy,'finish',None)),'Missing authorized bounded continuation policy')
 def run_case(self,cap=12000,override=None,budget=8,old=None):
  calls=[];snapshots=[];old=prior() if old is None else old
  def attempt(vus,purpose):
   calls.append((vus,purpose));value=override(len(calls),vus,purpose) if override else None
   return {'outcome':value or ('pass' if vus<=cap else 'fail'),'run':'continuation-'+str(len(calls))}
  return policy.finish(attempt,old,record=snapshots.append,max_attempts=budget),calls,snapshots
 def test_all_four_boundaries_preserve_two_slots_and_exact_additional_confirmations(self):
  for cap in [11250,11500,11750,12000]:
   with self.subTest(cap=cap):
    p,c,_=self.run_case(cap);self.assertEqual(p['status'],'confirmed_pending_evidence_review');self.assertEqual((p['candidate_vus'],p['upper_vus']),(cap,cap+250));self.assertEqual(len(c),8)
    self.assertEqual(p['attempts'][:2],prior()['attempts']);self.assertEqual(len(p['attempts']),10);self.assertEqual(p['total_physical_full_attempts_accounted'],21)
    self.assertEqual(c[0],(12250,'upper_anchor'));self.assertEqual(sum(v==cap and purpose=='candidate_confirmation' for v,purpose in c),3)
    self.assertEqual(sum(x['vus']==cap+250 and x['outcome']=='fail' for x in p['attempts'][2:]),3)
    self.assertTrue(all(11250<=v<=12250 and v%250==0 for v,_ in c))
 def test_upper_pass_stops_after_one_new_attempt_no_expansion(self):
  p,c,_=self.run_case(12250);self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(c,[(12250,'upper_anchor')]);self.assertEqual(p['total_physical_full_attempts_accounted'],14)
 def test_invalid_at_each_remaining_slot_stops_and_preserves_all_accounting(self):
  for slot in range(1,9):
   with self.subTest(slot=slot):
    p,c,_=self.run_case(override=lambda n,v,purpose:'invalid' if n==slot else None);self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(len(c),slot);self.assertEqual(len(p['attempts']),2+slot);self.assertEqual(p['total_physical_full_attempts_accounted'],13+slot);self.assertEqual(p['attempts'][-1]['outcome'],'invalid')
 def test_budget_seven_cannot_spend_eight(self):
  p,c,_=self.run_case(budget=7);self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(len(c),7);self.assertIn('budget',p['reason'].lower())
 def test_remaining_budget_cannot_be_raised_or_invalid(self):
  for budget in [9,10,0,True]:
   with self.subTest(budget=budget):
    with self.assertRaises(ValueError):self.run_case(budget=budget)
 def test_candidate_failure_pauses_without_stepdown(self):
  p,c,_=self.run_case(override=lambda n,v,purpose:'fail' if purpose=='candidate_confirmation' else None);self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(c[-1][1],'candidate_confirmation');self.assertEqual(sum(purpose=='candidate_confirmation' for _,purpose in c),1)
 def test_adjacent_confirmation_pass_pauses_without_score(self):
  p,c,_=self.run_case(override=lambda n,v,purpose:'pass' if purpose=='upper_confirmation' else None);self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(c[-1][1],'upper_confirmation')
 def test_pending_slot_before_side_effect_and_exception_does_not_erase_it(self):
  snapshots=[]
  def broken(vus,purpose):
   p=snapshots[-1];self.assertEqual(len(p['attempts']),3);self.assertIsNone(p['attempts'][-1]['outcome']);self.assertEqual(p['total_physical_full_attempts_accounted'],14);raise RuntimeError('retained partial launch')
  p=policy.finish(broken,prior(),record=snapshots.append);self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(len(p['attempts']),3);self.assertIsNone(p['attempts'][-1]['outcome']);self.assertIn('retained partial launch',p['reason'])
 def test_prior_phase_and_earlier_snapshots_are_not_mutated(self):
  old=prior();before=deepcopy(old);p,c,s=self.run_case(old=old);self.assertEqual(old,before);self.assertEqual(len(s[0]['attempts']),2);self.assertIsNone(s[1]['attempts'][-1]['outcome']);self.assertEqual(s[1]['total_physical_full_attempts_accounted'],14)
 def test_reject_missing_extra_invalid_or_relabelled_prior_attempts(self):
  cases=[]
  p=prior();p['attempts'].pop();cases.append(p)
  p=prior();p['attempts'].append(deepcopy(p['attempts'][0]));cases.append(p)
  for key,value in [('vus',11000),('outcome','invalid'),('purpose','candidate_confirmation'),('run','')]:
   p=prior();p['attempts'][1][key]=value;cases.append(p)
  p=prior();p['status']='confirmed_pending_evidence_review';cases.append(p)
  for old in cases:
   with self.subTest(old=old):
    with self.assertRaises(ValueError):self.run_case(old=old)
 def test_unknown_outcome_is_never_a_failure_bound(self):
  p,c,_=self.run_case(override=lambda n,v,purpose:'unknown');self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(len(c),1)
 def test_reused_anchor_is_never_counted_as_additional_confirmation(self):
  p,_,_=self.run_case(11250);self.assertEqual(sum(x['vus']==11250 and x['outcome']=='pass' for x in p['attempts']),4);self.assertEqual(p['historical_full_attempts'],11);self.assertEqual(p['supplemental_limit'],10);self.assertEqual(p['prior_supplemental_attempts'],2)

if __name__=='__main__':unittest.main(verbosity=2)
