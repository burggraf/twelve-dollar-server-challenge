"""Shared harness additions preserve the TrailBase defaults and isolate Supabase."""
from pathlib import Path
from types import SimpleNamespace
import json,sys,tarfile,tempfile,unittest
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import benchmark as b
class SupabaseHarness(unittest.TestCase):
 def test_native_supabase_project_has_distinct_vps16_track(self):
  try: value=b.deployment_settings('Linux','x86_64',{'BENCHMARK_PROJECT':'baas-supabase-vps16'})
  except ValueError:value=None
  self.assertIsNotNone(value,'Native Supabase namespace must be supported')
  self.assertEqual(value,{'project':'baas-supabase-vps16','platform':'linux/amd64','track':'vps16-linux-amd64'})
 def test_snapshot_includes_selected_backend_not_trailbase(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);out=root/'out';out.mkdir()
   for name in ['README.md','MASTER_PLAN.md','LICENSE','SPEC.md','schema.sql','.gitignore','.dockerignore','services/supabase/marker','services/trailbase/marker']:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture')
   with patch.object(b,'ROOT',root),patch.object(b,'command',return_value=SimpleNamespace(stdout=b'')):
    b.snapshot(out,service='supabase')
   with tarfile.open(out/'source.tar.gz') as t:names=t.getnames()
   self.assertIn('services/supabase/marker',names)
   self.assertNotIn('services/trailbase/marker',names)
 def test_campaign_uses_injected_backend_and_private_state_path(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'.state/trailbase').mkdir(parents=True);(root/'.state/supabase').mkdir()
   selected=root/'supabase-results';legacy=root/'trailbase-results';state=root/'.state/supabase/campaign.json'
   callback=Mock(return_value=('pass','supabase/run'));wrong=Mock(return_value=('pass','trailbase/run'))
   with patch.object(b,'ROOT',root),patch.object(b,'RESULTS',legacy),patch.object(b,'attempt',wrong):
    b.campaign(SimpleNamespace(max_attempts=12,max_vus=2500),'standard',attempt_runner=callback,results=selected,campaign_file=state)
   callback.assert_called_once_with(2500,'standard');wrong.assert_not_called()
   self.assertEqual(json.loads(state.read_text())['lower_bound_vus'],2500)
   self.assertEqual(len(list(selected.glob('*campaign.json'))),1)
   self.assertFalse(legacy.exists())
if __name__=='__main__':unittest.main(verbosity=2)
