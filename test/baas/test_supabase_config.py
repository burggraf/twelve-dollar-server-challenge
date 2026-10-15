"""Configuration regressions run natively before serving/correctness."""
from pathlib import Path
import json,subprocess,unittest
ROOT=Path(__file__).resolve().parents[2]
class SupabaseProfile(unittest.TestCase):
 def test_real_resolved_stack_and_runner_are_isolated(self):
  config=json.loads(subprocess.check_output(['docker','compose','--env-file',str(ROOT/'.state/supabase/stack.env'),'-p','baas-supabase-vps16','-f',str(ROOT/'services/supabase/compose.yaml'),'--profile','load','--profile','tools','config','--format','json'],text=True))
  core={'db','auth','rest','functions','gateway'};self.assertEqual(set(config['services']),core|{'tools','k6'})
  for role in core:
   service=config['services'][role];self.assertEqual(service['cgroup_parent'],'tdsbaassupabasevps16.slice');self.assertEqual(service['platform'],'linux/amd64')
   if role!='gateway':self.assertFalse(service.get('ports'))
  ports=config['services']['gateway']['ports'];self.assertEqual([(p['host_ip'],str(p['published']),p['target']) for p in ports],[('127.0.0.1','14000',8000)])
  load=config['services']['k6'];self.assertEqual(float(load['cpus']),2);self.assertEqual(int(load['mem_limit']),8*1024**3);self.assertEqual(load['memswap_limit'],load['mem_limit'])
  mounts={m['target']:m for m in load['volumes']};self.assertEqual(set(mounts),{'/work/bench','/tokens.json','/runs'})
  self.assertTrue(mounts['/work/bench']['read_only']);self.assertTrue(mounts['/tokens.json']['read_only']);self.assertFalse(load.get('secrets'));self.assertFalse(load.get('privileged'))
  self.assertEqual(set(load['environment']),{'BASE_URL'});self.assertNotIn('POSTGRES_PASSWORD',config['services']['functions']['environment'])
 def test_official_webhooks_bootstrap_precedes_roles_password_setup(self):
  compose=(ROOT/'services/supabase/compose.yaml').read_text()
  self.assertIn('./bootstrap/webhooks.sql:/docker-entrypoint-initdb.d/init-scripts/98-webhooks.sql:ro',compose)
  self.assertIn('./bootstrap/roles.sql:/docker-entrypoint-initdb.d/init-scripts/99-roles.sql:ro',compose)
  self.assertIn('supabase_functions_admin',(ROOT/'services/supabase/bootstrap/webhooks.sql').read_text())
if __name__=='__main__':unittest.main(verbosity=2)
