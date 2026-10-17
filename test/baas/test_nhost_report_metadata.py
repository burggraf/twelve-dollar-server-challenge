"""Evaluate the actual report dictionary with declared native pins, without lifecycle/load effects."""
import ast,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import nhost_benchmark as n
class ReportMetadata(unittest.TestCase):
 def build(self,outcome,summary,policy=None):
  tree=ast.parse(Path(n.__file__).read_text());assignments=[node for node in ast.walk(tree) if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='manifest' for target in node.targets)];self.assertEqual(len(assignments),1)
  values={'vus':25,'tier':'standard','smoke':True,'current':{},'before':{},'after':{},'deployed':{'schema':{}},'load':{},'exit_code':0,'outcome':outcome,'reason':'original diagnostic retained','continuous':{},'quiet':{},'reservation':{},'summary':summary,'cpus':4}
  with patch.object(n.b,'capture',return_value='unit-native-observation'),patch.object(n.budget,'effective_policy',return_value=policy or n.budget.POLICY,create=True):
   try:result=eval(compile(ast.Expression(assignments[0].value),n.__file__,'eval'),vars(n)|values)
   except KeyError as error:self.fail('Report construction references an undeclared input/pin: '+str(error))
  json.dumps(result,allow_nan=False);self.assertEqual(result['upstream_commit'],n.s.PINS['source_commit']);self.assertEqual(result['versions'],n.s.PINS);return result
 def test_successful_measurement_metadata_uses_declared_source_commit(self):
  result=self.build('pass',{'metrics':{'benchmark_scenario_start_ms':{'values':{'value':1792222467629}}}});self.assertEqual(result['scenario_started_epoch'],1792222467.629);self.assertEqual(result['result'],'pass')
 def test_report_records_actual_owner_extended_policy_not_base_four_smoke_cap(self):
  policy={**n.budget.POLICY,'version':2,'maximum_smoke_attempts':6,'owner_amendment_sha256':'unit-owner-hash'};result=self.build('invalid',{},policy);self.assertEqual(result['physical_attempt']['policy'],policy)
 def test_invalid_measurement_metadata_retains_original_reason_and_missing_clock(self):
  result=self.build('invalid',{});self.assertIsNone(result['scenario_started_epoch']);self.assertEqual(result['reason'],'original diagnostic retained');self.assertEqual(result['result'],'invalid')
if __name__=='__main__':unittest.main(verbosity=2)
