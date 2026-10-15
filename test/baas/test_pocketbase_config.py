"""Declared native serving/runner budgets, ownership and credential isolation."""
from pathlib import Path
import json
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PocketBaseDeployment(unittest.TestCase):
    def test_native_deployment_budget_and_isolation(self):
        path = ROOT / 'services/pocketbase/compose.yaml'
        self.assertTrue(path.is_file(), 'Native PocketBase deployment profile is missing')
        value = json.loads(subprocess.check_output([
            'docker', 'compose', '--profile', '*', '-p', 'baas-pocketbase-vps16', '-f', str(path),
            'config', '--format', 'json', '--no-env-resolution'], text=True))
        services = value['services']
        self.assertEqual(set(services), {'pocketbase', 'tools', 'k6'})
        app, runner = services['pocketbase'], services['k6']
        self.assertEqual(app['platform'], 'linux/amd64')
        self.assertEqual(float(app['cpus']), 1)
        self.assertEqual(int(app['mem_limit']), 4294967296)
        self.assertEqual(int(app['memswap_limit']), 4294967296)
        self.assertEqual(app['cgroup_parent'], 'tdsbaaspocketbasevps16.slice')
        self.assertEqual(app['user'], '1000:1000')
        self.assertTrue(app['read_only'])
        self.assertEqual(app['ports'][0]['host_ip'], '127.0.0.1')
        self.assertEqual(str(app['ports'][0]['published']), '14000')
        self.assertEqual(app['ports'][0]['target'], 4000)
        self.assertEqual(float(runner['cpus']), 2)
        self.assertEqual(int(runner['mem_limit']), 8589934592)
        self.assertEqual(int(runner['memswap_limit']), 8589934592)
        self.assertEqual(runner['platform'], 'linux/amd64')
        self.assertEqual(runner.get('environment', {}).get('BASE_URL'), 'http://pocketbase:4000',
                         'PocketBase runner must not fall back to the TrailBase URL')
        self.assertIn('@sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656', runner['image'])
        self.assertEqual({m['target'] for m in runner['volumes']},
                         {'/work/bench', '/tokens.json', '/runs'})
        self.assertNotIn('env_file', runner)
        self.assertNotIn('secrets', runner)
        self.assertEqual(services['tools']['profiles'], ['tools'])
        self.assertEqual(runner['profiles'], ['load'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
