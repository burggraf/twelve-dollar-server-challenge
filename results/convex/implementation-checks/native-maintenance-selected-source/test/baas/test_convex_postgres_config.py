"""Real native Compose normalization, without rendering any private env values."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ConvexPostgresConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = json.loads(subprocess.check_output([
            'docker', 'compose', '-p', 'baas-convexpg-vps16',
            '-f', str(ROOT / 'services/convex/compose.yaml'),
            '-f', str(ROOT / 'services/convex/compose.postgres.yaml'),
            '--profile', '*', 'config', '--no-env-resolution', '--format', 'json',
        ], text=True))

    def test_only_two_required_servers_and_separate_profiled_tools(self):
        self.assertEqual(self.value['name'], 'baas-convexpg-vps16')
        self.assertEqual(set(self.value['services']), {'backend', 'postgres', 'tools'})
        self.assertEqual(self.value['services']['tools']['profiles'], ['tools'])
        self.assertEqual(self.value['services']['backend']['depends_on']['postgres']['condition'], 'service_healthy')

    def test_native_image_pins_and_three_plus_one_gib_children(self):
        pins = json.loads((ROOT / 'services/convex/versions.json').read_text())
        postgres = json.loads((ROOT / 'services/convex/postgres-versions.json').read_text())
        references = {'backend': pins['backend']['tag'] + '@' + pins['backend']['amd64_manifest'],
                      'postgres': postgres['tag'] + '@' + postgres['amd64_manifest']}
        for role, memory in [('backend', 3221225472), ('postgres', 1073741824)]:
            item = self.value['services'][role]
            self.assertEqual(item['image'], references[role])
            self.assertEqual(item['platform'], 'linux/amd64')
            self.assertEqual(item['cgroup_parent'], 'tdsbaasconvexpgvps16.slice')
            self.assertEqual(float(item['cpus']), 1.0)
            # Native Compose 5.5 JSON encodes canonical byte quantities as strings.
            self.assertEqual(str(item['mem_limit']), str(memory))
            self.assertEqual(str(item['memswap_limit']), str(memory))

    def test_no_database_host_port_or_new_privileges(self):
        for role in ['backend', 'postgres']:
            item = self.value['services'][role]
            self.assertTrue(item['read_only'])
            self.assertEqual(item['cap_drop'], ['ALL'])
            self.assertIn('no-new-privileges:true', item['security_opt'])
        self.assertFalse(self.value['services']['postgres'].get('ports'))
        self.assertEqual(self.value['services']['postgres']['user'], 'postgres')
        for port in self.value['services']['backend']['ports']:
            self.assertEqual(port['host_ip'], '127.0.0.1')

    def test_fresh_owned_volumes_and_uncached_native_queries(self):
        self.assertEqual(self.value['volumes']['data']['name'], 'baas-convexpg-vps16_data')
        self.assertEqual(self.value['volumes']['pgdata']['name'], 'baas-convexpg-vps16_pgdata')
        env = self.value['services']['backend']['environment']
        self.assertEqual(env['INSTANCE_NAME'], 'baas-convexpg-vps16')
        self.assertEqual(env['UDF_CACHE_MAX_SIZE'], '0')
        self.assertEqual(env['RUNTIME_WORKER_THREADS'], '1')
        self.assertEqual(env['DO_NOT_REQUIRE_SSL'], '1')
        self.assertNotIn('POSTGRES_URL', env, 'Private DSN must come from private env file, not committed YAML')
        for name in ['TRANSACTION_MAX_READ_SIZE_ROWS', 'TRANSACTION_MAX_READ_SIZE_BYTES',
                     'TRANSACTION_MAX_READ_SET_INTERVALS', 'DATABASE_UDF_SYSTEM_TIMEOUT_SECONDS',
                     'DATABASE_UDF_USER_TIMEOUT_SECONDS']:
            self.assertNotIn(name, env)


if __name__ == '__main__':
    unittest.main(verbosity=2)
