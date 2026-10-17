"""Real native Compose rendering only; no builds/container creation or secret-bearing assertion output."""
import json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import nhost as n
import nhost_profile as s
class Configuration(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.services=json.loads(subprocess.check_output(n.compose()+['--profile','tools','--profile','benchmark','config','--format','json'],stderr=subprocess.STDOUT))['services']
 def test_separate_runner_exact_budget_and_native_manifest(self):
  runner=self.services.get('k6');self.assertIsInstance(runner,dict,'Approved Nhost runner not yet configured')
  self.assertEqual(runner['platform'],'linux/amd64');self.assertEqual(runner['cpus'],2);self.assertEqual(runner['mem_limit'],'8589934592');self.assertEqual(runner['memswap_limit'],'8589934592');self.assertNotEqual(runner.get('cgroup_parent'),s.SLICE);self.assertTrue(runner['image'].endswith('sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656'))
 def test_runner_only_has_read_only_bench_tokens_and_writable_output(self):
  runner=self.services.get('k6');self.assertIsInstance(runner,dict,'Approved isolated Nhost runner not yet configured')
  volumes={item['target']:item for item in runner['volumes']};self.assertEqual(set(volumes),{'/work/bench','/tokens.json','/runs'})
  self.assertTrue(volumes['/work/bench']['read_only']);self.assertTrue(volumes['/tokens.json']['read_only']);self.assertFalse(volumes['/runs'].get('read_only',False))
  self.assertEqual(Path(volumes['/tokens.json']['source']),s.ROOT/'.state/seed/tokens.json');self.assertEqual(Path(volumes['/work/bench']['source']),s.ROOT/'bench')
  self.assertFalse(set(runner.get('environment',{}))&{'JWT_SECRET','NATIVE_JWT_SECRET','COMPAT_JWT_SECRET','GRAPHQL_ADMIN_SECRET','POSTGRES_PASSWORD'})
 def test_tools_node_fixture_has_the_same_read_only_shared_contract_path(self):
  volumes={item['target']:item for item in self.services['tools']['volumes']};self.assertIn('/shared',volumes,'Server imports absolute /shared/contract.mjs; qualification tools must reproduce its path')
  self.assertEqual(Path(volumes['/shared']['source']),s.ROOT/'services/supabase/functions/feed');self.assertTrue(volumes['/shared']['read_only'])
 def test_tools_use_retained_immutable_image_and_stay_outside_serving(self):
  tools=self.services['tools'];self.assertEqual(tools['image'],'sha256:7b35188938d0b5a3b50178d6a85e776b09db24314a2643c64b95b3da49f4f9f2');self.assertEqual(tools['platform'],'linux/amd64');self.assertEqual(tools['cpus'],1);self.assertEqual(tools['mem_limit'],'1073741824');self.assertEqual(tools['memswap_limit'],'1073741824');self.assertNotEqual(tools.get('cgroup_parent'),s.SLICE)
if __name__=='__main__':unittest.main(verbosity=2)
