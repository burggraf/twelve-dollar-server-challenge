"""Fail-closed budget contract for the owner-approved PostgreSQL-backed stack."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
if importlib.util.find_spec('convex_profile'):
    import convex_profile as profile
else:
    profile = None


class ConvexPostgresBudget(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(profile, 'Convex PostgreSQL aggregate serving validator is missing')
        pins = json.loads((ROOT / 'services/convex/versions.json').read_text())
        postgres = json.loads((ROOT / 'services/convex/postgres-versions.json').read_text())
        manifests = {'backend': pins['backend']['amd64_manifest'], 'postgres': postgres['amd64_manifest']}
        allocations = {'backend': 3221225472, 'postgres': 1073741824}
        targets = {}
        for number, (role, manifest) in enumerate(manifests.items(), 1):
            identity = str(number) * 64
            targets[role] = {
                'Id': identity, 'platform': 'linux/amd64',
                'image_manifest_digest': manifest,
                'compose_project': 'baas-convexpg-vps16',
                'cgroup_parent': 'tdsbaasconvexpgvps16.slice',
                'process_cgroup': f'0::/tdsbaasconvexpgvps16.slice/docker-{identity}.scope\n',
                'State': {'Running': True, 'OOMKilled': False, 'Health': {'Status': 'healthy'}},
                'limits': {'NanoCpus': 1000000000, 'Memory': allocations[role], 'MemorySwap': allocations[role]},
                'kernel': {'cpu.max': '100000 100000', 'memory.max': str(allocations[role]), 'memory.swap.max': '0'},
            }
        self.value = {'targets': targets, 'parent': {
            'cpu.max': '100000 100000', 'memory.max': '4294967296', 'memory.swap.max': '0',
            'children': [f'docker-{target["Id"]}.scope' for target in targets.values()],
        }}

    def test_both_native_processes_share_exact_aggregate_budget(self):
        self.assertTrue(profile.validate_stack(self.value))

    def test_each_required_server_is_mandatory(self):
        for role in ['backend', 'postgres']:
            value = copy.deepcopy(self.value)
            del value['targets'][role]
            with self.subTest(role=role), self.assertRaises(RuntimeError):
                profile.validate_stack(value)

    def test_parent_cannot_be_missing_enlarged_unlimited_or_have_swap(self):
        for field, bad in [('cpu.max', None), ('cpu.max', 'max 100000'),
                           ('cpu.max', '200000 100000'), ('memory.max', '8589934592'),
                           ('memory.swap.max', '1'), ('children', ['unaccounted.scope'])]:
            value = copy.deepcopy(self.value)
            if bad is None:
                del value['parent'][field]
            else:
                value['parent'][field] = bad
            with self.subTest(field=field, bad=bad), self.assertRaises(RuntimeError):
                profile.validate_stack(value)

    def test_image_architecture_ownership_and_actual_membership_are_required(self):
        for role in ['backend', 'postgres']:
            for field, bad in [('platform', 'linux/arm64'), ('image_manifest_digest', 'sha256:wrong'),
                               ('compose_project', 'production'), ('cgroup_parent', 'system.slice'),
                               ('process_cgroup', '0::/system.slice/unrelated.scope\n')]:
                value = copy.deepcopy(self.value)
                value['targets'][role][field] = bad
                with self.subTest(role=role, field=field), self.assertRaises(RuntimeError):
                    profile.validate_stack(value)

    def test_child_limits_and_native_health_fail_closed(self):
        for role in ['backend', 'postgres']:
            for section, field, bad in [('limits', 'Memory', 4294967296),
                                        ('limits', 'MemorySwap', 8589934592),
                                        ('limits', 'NanoCpus', 2000000000),
                                        ('kernel', 'memory.max', 'max'),
                                        ('kernel', 'memory.swap.max', 'max'),
                                        ('kernel', 'cpu.max', 'max 100000'),
                                        ('State', 'Running', False), ('State', 'OOMKilled', True),
                                        ('State', 'Health', {'Status': 'unhealthy'})]:
                value = copy.deepcopy(self.value)
                value['targets'][role][section][field] = bad
                with self.subTest(role=role, section=section, field=field), self.assertRaises(RuntimeError):
                    profile.validate_stack(value)


if __name__ == '__main__':
    unittest.main(verbosity=2)
