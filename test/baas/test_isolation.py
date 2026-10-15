"""Host-side validation of real resolved Compose mounts; never prints secret values."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import benchmark


class ContainerIsolation(unittest.TestCase):
    def test_k6_cannot_read_signing_keys_or_private_service_state(self):
        config = json.loads(subprocess.check_output(
            ['docker', 'compose', '-f', str(ROOT / 'services/trailbase/compose.yaml'), '--profile', 'load', 'config', '--format', 'json'], text=True))
        load = config['services']['k6']
        mounts = {mount['target']: mount for mount in load['volumes']}
        self.assertEqual(set(mounts), {'/work/bench', '/tokens.json', '/runs'})
        self.assertTrue(mounts['/work/bench']['read_only'])
        self.assertTrue(mounts['/tokens.json']['read_only'])
        self.assertFalse(load.get('secrets'))
        self.assertFalse(load.get('privileged', False))
        self.assertEqual(float(load['cpus']), 2)
        self.assertEqual(int(load['mem_limit']), benchmark.RUNNER_LIMITS['Memory'])
        self.assertEqual(load['mem_limit'], load['memswap_limit'])
        self.assertNotIn(str(ROOT), [mount['source'] for mount in load['volumes']])


    def test_new_host_standard_tier_and_eight_gib_runner_are_loopback_isolated(self):
        env = {**os.environ, 'BENCHMARK_PROJECT': 'baas-trailbase-vps16',
               'BENCHMARK_PLATFORM': 'linux/amd64', 'SERVICE_CPUS': '1', 'SERVICE_MEMORY': '4g',
               'RUNNER_MEMORY': '8g', 'TRAILBASE_PORT': '14000'}
        config = json.loads(subprocess.check_output(
            ['docker', 'compose', '-f', str(ROOT / 'services/trailbase/compose.yaml'), '--profile', 'load',
             'config', '--format', 'json'], text=True, env=env))
        self.assertEqual(config['name'], 'baas-trailbase-vps16')
        serving, load = (config['services'][name] for name in ['trailbase', 'k6'])
        self.assertEqual(float(serving['cpus']), 1)
        self.assertEqual(int(serving['mem_limit']), 4 * 1024**3)
        self.assertEqual(int(load['mem_limit']), 8 * 1024**3)
        self.assertEqual(load['memswap_limit'], load['mem_limit'])
        self.assertEqual(float(load['cpus']), 2)
        self.assertEqual([(p['host_ip'], str(p['published']), p['target']) for p in serving['ports']],
                         [('127.0.0.1', '14000', 4000)])
        self.assertEqual(config['volumes']['data']['name'], 'baas-trailbase-vps16_data')

    def test_vps_platform_and_resources_are_isolated_from_existing_projects(self):
        config = json.loads(subprocess.check_output(
            ['docker', 'compose', '-f', str(ROOT / 'services/trailbase/compose.yaml'), '--profile', 'load',
             '--profile', 'tools', 'config', '--format', 'json'], text=True,
            env={**os.environ, 'BENCHMARK_PROJECT': 'baas-trailbase-vps', 'BENCHMARK_PLATFORM': 'linux/amd64'}))
        self.assertEqual(config['name'], 'baas-trailbase-vps')
        for name in ['trailbase', 'tools', 'k6']:
            self.assertEqual(config['services'][name]['platform'], 'linux/amd64')
        self.assertEqual(config['services']['trailbase']['image'], 'baas-trailbase-vps-feed:0.1.0')
        self.assertEqual(config['services']['tools']['image'], 'baas-trailbase-vps-tools:0.1.0')
        self.assertEqual(config['volumes']['data']['name'], 'baas-trailbase-vps_data')
        ports = config['services']['trailbase']['ports']
        self.assertTrue(all(p['host_ip'] == '127.0.0.1' for p in ports))
        self.assertEqual([p['target'] for p in ports], [4000])


if __name__ == '__main__':
    unittest.main(verbosity=2)
