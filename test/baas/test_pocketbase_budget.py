"""Fail closed on aggregate/native/ownership drift, using retained real-runtime data."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.find_spec('pocketbase_profile')
if spec:
    import pocketbase_profile as profile
else:
    profile = None


class PocketBaseBudget(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(profile, 'Formal PocketBase whole-stack budget validator is missing')
        self.value = json.loads((ROOT / 'results/pocketbase/vps16-linux-amd64/setup-evidence/initial-native-serving-profile.json').read_text())
        target = self.value.pop('target')
        target.update(compose_project='baas-pocketbase-vps16',
                      cgroup_parent='tdsbaaspocketbasevps16.slice',
                      process_cgroup=self.value['actual_process_cgroup'])
        self.value['targets'] = {'pocketbase': target}
        self.value['parent']['children'] = ['docker-' + target['Id'] + '.scope']
        self.image = target['Image']

    def test_real_native_slice_is_accepted(self):
        self.assertTrue(profile.validate_stack(self.value, self.image))

    def test_budget_and_unaccounted_children_drift_fail_closed(self):
        for field, bad in [('cpu.max', '200000 100000'),
                           ('memory.max', '8589934592'), ('memory.swap.max', '1'),
                           ('children', ['unaccounted.service'])]:
            value = copy.deepcopy(self.value)
            value['parent'][field] = bad
            with self.assertRaises(RuntimeError):
                profile.validate_stack(value, self.image)

    def test_wrong_native_image_owner_or_actual_process_membership_is_rejected(self):
        for field, bad in [('platform', 'linux/arm64'), ('Image', 'sha256:wrong'),
                           ('compose_project', 'unrelated'), ('cgroup_parent', 'system.slice'),
                           ('process_cgroup', '0::/system.slice/unrelated.scope\n')]:
            value = copy.deepcopy(self.value)
            value['targets']['pocketbase'][field] = bad
            with self.assertRaises(RuntimeError):
                profile.validate_stack(value, self.image)

    def test_wrong_child_limit_and_failed_native_runtime_are_rejected(self):
        for mutate in [lambda t: t['limits'].update(Memory=8589934592),
                       lambda t: t['State'].update(Running=False),
                       lambda t: t['State'].update(OOMKilled=True)]:
            value = copy.deepcopy(self.value)
            mutate(value['targets']['pocketbase'])
            with self.assertRaises(RuntimeError):
                profile.validate_stack(value, self.image)


if __name__ == '__main__':
    unittest.main(verbosity=2)
