"""Pure scheduling/accounting regressions; execute on designated VPS, not Mac."""
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).with_name('supplemental_policy.py')
if path.exists():
 spec=importlib.util.spec_from_file_location('policy',path);policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
else:policy=None

class PolicyTests(unittest.TestCase):
 def setUp(self):self.assertTrue(policy is not None and callable(getattr(policy,'finish',None)),'Missing bounded supplemental scheduling/accounting policy')
 def run_threshold(self,cap=11000,override=None,budget=10):
  calls=[];snapshots=[]
  def attempt(vus,purpose):
   calls.append((vus,purpose));value=override(len(calls),vus,purpose) if override else None
   return {'outcome':value or ('pass' if vus<=cap else 'fail'),'run':'run-'+str(len(calls))}
  phase=policy.finish(attempt,record=snapshots.append,max_attempts=budget)
  return phase,calls,snapshots
 def test_all_five_possible_boundaries_get_three_additional_passes_and_three_adjacent_fails(self):
  for cap in [10000,10250,10500,10750,11000]:
   with self.subTest(cap=cap):
    p,c,_=self.run_threshold(cap);self.assertEqual(p['status'],'confirmed_pending_evidence_review');self.assertEqual((p['candidate_vus'],p['upper_vus']),(cap,cap+250));self.assertLessEqual(len(c),10)
    self.assertEqual(sum(v==cap and purpose=='candidate_confirmation' for v,purpose in c),3)
    self.assertEqual(sum(x['vus']==cap+250 and x['outcome']=='fail' for x in p['attempts']),3)
    self.assertTrue(all(10000<=v<=11250 and v%250==0 for v,_ in c))
 def test_lower_anchor_failure_stops_without_lowering_search_scope(self):
  p,c,_=self.run_threshold(9750);self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(c,[(10000,'lower_anchor')])
 def test_upper_anchor_pass_stops_without_expanding_search_scope(self):
  p,c,_=self.run_threshold(11250);self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(len(c),2)
 def test_invalid_at_every_physical_slot_stops_immediately_and_is_not_a_target_failure(self):
  for slot in range(1,11):
   with self.subTest(slot=slot):
    p,c,_=self.run_threshold(override=lambda n,v,purpose:'invalid' if n==slot else None);self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(len(c),slot);self.assertEqual(p['attempts'][-1]['outcome'],'invalid')
 def test_budget_nine_cannot_silently_spend_ten(self):
  p,c,_=self.run_threshold(budget=9);self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(len(c),9);self.assertIn('budget',p['reason'].lower())
 def test_owner_limit_ten_cannot_be_raised_by_caller(self):
  with self.assertRaises(ValueError):self.run_threshold(budget=11)
 def test_candidate_confirmation_failure_stops_not_step_down(self):
  p,c,_=self.run_threshold(override=lambda n,v,purpose:'fail' if purpose=='candidate_confirmation' else None);self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(c[-1][1],'candidate_confirmation');self.assertEqual(sum(purpose=='candidate_confirmation' for _,purpose in c),1)
 def test_adjacent_confirmation_pass_stops_not_claim_boundary(self):
  p,c,_=self.run_threshold(override=lambda n,v,purpose:'pass' if purpose=='upper_confirmation' else None);self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(c[-1][1],'upper_confirmation')
 def test_unknown_outcome_refused(self):
  p,c,_=self.run_threshold(override=lambda n,v,purpose:'maybe');self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(len(c),1)
 def test_slot_is_recorded_before_runner_side_effect_and_partial_runner_failure_retained(self):
  snapshots=[]
  def broken(vus,purpose):
   self.assertEqual(snapshots[-1]['attempts'][-1]['vus'],10000);self.assertIsNone(snapshots[-1]['attempts'][-1]['outcome']);raise RuntimeError('runner stopped')
  p=policy.finish(broken,record=snapshots.append);self.assertEqual(p['status'],'paused_unconfirmed');self.assertEqual(len(p['attempts']),1);self.assertIsNone(p['attempts'][0]['outcome']);self.assertIn('runner stopped',p['reason'])
 def test_confirmation_counts_never_reuse_probes_as_additional_passes(self):
  p,_,_=self.run_threshold(10000);self.assertEqual(sum(x['vus']==10000 and x['outcome']=='pass' for x in p['attempts']),4)
 def test_historical_eleven_slots_are_explicit_and_never_reset(self):
  p,c,_=self.run_threshold();self.assertEqual(p['historical_full_attempts'],11);self.assertEqual(p['supplemental_limit'],10);self.assertEqual(p['total_physical_full_attempts_accounted'],11+len(c))

if __name__=='__main__':unittest.main(verbosity=2)
