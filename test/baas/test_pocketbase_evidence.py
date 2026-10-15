"""Correctness and lifecycle evidence cannot certify changed executable inputs."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
spec = importlib.util.find_spec('pocketbase_benchmark')
if spec:
    import pocketbase_benchmark as benchmark
else:
    benchmark = None


class FrozenPocketBaseEvidence(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(benchmark, 'PocketBase frozen-input evidence checker is missing')
        self.inputs = {key: 'original-' + key for key in
                       ['app', 'verification', 'runtime', 'schema', 'images', 'host', 'tokens', 'tools_image']}
        self.attestation = {'inputs': self.inputs, 'log_sha256': 'original-log'}

    def test_every_attempt_report_prominently_names_exact_software_and_slices(self):
        self.assertTrue(callable(getattr(benchmark, 'report_header', None)),
                        'PocketBase per-attempt software/allocation header is missing')
        text = benchmark.report_header()
        for required in ['Tested software and VPS slice', 'v0.40.5', '1.27.2', '3.53.4', 'v1.60.1',
                         '1 vCPU', '4,294,967,296', 'k6 1.3.0', '2 vCPU', '8,589,934,592', 'no swap', 'shared']:
            self.assertIn(required, text)

    def test_unchanged_complete_correctness_evidence_is_accepted(self):
        self.assertTrue(benchmark.validate_correctness(self.attestation, self.inputs, 'original-log'))

    def test_any_changed_attested_input_or_raw_log_is_rejected(self):
        for key in self.inputs:
            value = copy.deepcopy(self.inputs)
            value[key] = 'changed'
            with self.assertRaises(RuntimeError):
                benchmark.validate_correctness(self.attestation, value, 'original-log')
        with self.assertRaises(RuntimeError):
            benchmark.validate_correctness(self.attestation, self.inputs, 'changed-log')

    def test_restart_oom_or_missing_component_cannot_be_accepted_as_same_target(self):
        target = {'Id': 'owned', 'RestartCount': 0,
                  'State': {'Running': True, 'OOMKilled': False, 'StartedAt': 'initial'}}
        before = {'pocketbase': target}
        self.assertIsNone(benchmark.target_issue(before, before))
        for mutate in [lambda t: t['State'].update(StartedAt='restarted'),
                       lambda t: t['State'].update(OOMKilled=True),
                       lambda t: t.update(RestartCount=1)]:
            after = copy.deepcopy(before)
            mutate(after['pocketbase'])
            self.assertIsNotNone(benchmark.target_issue(before, after))
        self.assertIsNotNone(benchmark.target_issue(before, {}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
