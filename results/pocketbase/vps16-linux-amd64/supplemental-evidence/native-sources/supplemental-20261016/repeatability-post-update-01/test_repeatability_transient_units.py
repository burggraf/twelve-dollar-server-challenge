import copy
import unittest
try:
 import repeatability_transient_units as subject
except ModuleNotFoundError:
 subject=None


def unit(**changes):
 value={'Type':'oneshot','RemainAfterExit':'yes','MainPID':'0','ControlPID':'0','ActiveState':'active','SubState':'exited','Job':''}
 value.update(changes);return value


class TransientUnitTests(unittest.TestCase):
 def classify(self,units,proof):
  self.assertIsNotNone(subject,'Approved no-resident-process oneshot classifier not implemented')
  return subject.partition(units,proof)

 def test_completed_oneshot_remain_active_without_residents_is_transient(self):
  self.assertEqual(self.classify({'runtime.service':unit()},{'runtime.service':True}),{'persistent':[],'transient':['runtime.service']})

 def test_no_named_ssh_or_dmarie_exception(self):
  for name in ['user-runtime-dir@0.service','arbitrary.service','dmarie.service']:
   with self.subTest(name=name):
    self.assertEqual(self.classify({name:unit(Type='simple')},{name:True}),{'persistent':[name],'transient':[]})
    self.assertEqual(self.classify({name:unit()},{name:True}),{'persistent':[],'transient':[name]})

 def test_completed_inactive_oneshot_is_transient_and_does_not_need_remain_active(self):
  self.assertEqual(self.classify({'job.service':unit(ActiveState='inactive',SubState='dead',RemainAfterExit='no')},{'job.service':True})['transient'],['job.service'])

 def test_main_control_or_cgroup_residents_are_never_excluded(self):
  for changes,proof in [({'MainPID':'7'},False),({'ControlPID':'8'},False),({},False)]:
   with self.subTest(changes=changes,proof=proof):
    self.assertEqual(self.classify({'job.service':unit(**changes)},{'job.service':proof})['persistent'],['job.service'])

 def test_unknown_or_missing_no_resident_proof_fails_closed(self):
  for proof in [{},{'job.service':None},{'job.service':1},{'job.service':'true'}]:
   with self.subTest(proof=proof):
    self.assertIsNotNone(subject,'Approved classifier missing')
    with self.assertRaises(RuntimeError):subject.partition({'job.service':unit()},proof)

 def test_running_failed_activating_or_pending_job_remains_watched(self):
  for changes in [{'SubState':'running'},{'ActiveState':'failed','SubState':'failed'},{'ActiveState':'activating','SubState':'start'},{'Job':'123'}]:
   with self.subTest(changes=changes):self.assertEqual(self.classify({'job.service':unit(**changes)},{'job.service':True})['persistent'],['job.service'])

 def test_malformed_unit_properties_fail_closed(self):
  self.assertIsNotNone(subject,'Approved classifier missing')
  for value in [{},unit(MainPID='-1'),unit(ControlPID=True),unit(Type=''),unit(ActiveState=None)]:
   with self.subTest(value=value):
    with self.assertRaises(RuntimeError):subject.partition({'job.service':value},{'job.service':True})

 def test_inputs_immutable_and_partition_complete(self):
  units={'one.service':unit(),'two.service':unit(Type='notify'),'three.service':unit(ActiveState='inactive',SubState='dead')};proof={name:True for name in units};before=copy.deepcopy((units,proof))
  result=self.classify(units,proof)
  self.assertEqual(result,{'persistent':['two.service'],'transient':['one.service','three.service']});self.assertEqual((units,proof),before)


if __name__=='__main__':unittest.main(verbosity=2)
