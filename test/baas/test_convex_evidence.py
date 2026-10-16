"""Changed full runtime/source evidence and native process loss must fail closed."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
if importlib.util.find_spec('convex_benchmark'):
    import convex_benchmark as benchmark
else:
    benchmark = None


class FrozenConvexEvidence(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(benchmark, 'Convex benchmark/frozen evidence adapter missing')
        self.inputs = {key: 'original-' + key for key in ['app', 'verification', 'runtime', 'schema', 'images', 'host', 'tokens', 'tools_image', 'full_runtime']}
        self.attestation = {'inputs': self.inputs, 'log_sha256': 'original-log'}

    def test_versions_exact_slices_and_failed_shutdown_are_prominent(self):
        text = benchmark.report_header()
        for required in ['Tested software and VPS slice', 'a3538c6', '1.46.0', '17.11', '1 vCPU', '4,294,967,296', '3,221,225,472', '1,073,741,824', 'k6 1.3.0', '2 vCPU', '8,589,934,592', 'no swap', 'shared', 'FAILED', '139']:
            self.assertIn(required, text)

    def test_matching_full_frozen_correctness_accepted(self):
        self.assertTrue(benchmark.validate_correctness(self.attestation, self.inputs, 'original-log'))

    def test_every_changed_input_and_log_refused(self):
        for key in self.inputs:
            changed = dict(self.inputs, **{key: 'changed'})
            with self.assertRaises(RuntimeError): benchmark.validate_correctness(self.attestation, changed, 'original-log')
        with self.assertRaises(RuntimeError): benchmark.validate_correctness(self.attestation, self.inputs, 'changed-log')

    def test_aggregate_oom_without_pid1_exit_still_stops_campaign(self):
        self.assertTrue(callable(getattr(benchmark, 'runtime_issue', None)), 'Aggregate OOM must stop, not continue searching/recovering')
        target = {'Id': 'owned', 'RestartCount': 0, 'State': {'Running': True, 'OOMKilled': False, 'StartedAt': 'initial', 'Health': {'Status': 'healthy'}}}
        before = {'targets': {role: copy.deepcopy(target) for role in ['backend', 'postgres']}, 'parent': {'memory.events': 'oom 0\noom_kill 0\noom_group_kill 0\n'}}
        self.assertIsNone(benchmark.runtime_issue(before, before))
        for event in ['oom', 'oom_kill', 'oom_group_kill']:
            after = copy.deepcopy(before); after['parent']['memory.events'] = before['parent']['memory.events'].replace(event+' 0', event+' 1')
            self.assertIsNotNone(benchmark.runtime_issue(before, after))

    def test_either_server_restart_exit_oom_pause_unhealthy_or_missing_refused(self):
        target = {'Id': 'owned', 'RestartCount': 0, 'State': {'Running': True, 'OOMKilled': False, 'StartedAt': 'initial', 'Health': {'Status': 'healthy'}}}
        before = {role: copy.deepcopy(target) for role in ['backend', 'postgres']}
        self.assertIsNone(benchmark.target_issue(before, before))
        for role in before:
            for mutate in [lambda t: t['State'].update(StartedAt='restarted'), lambda t: t['State'].update(OOMKilled=True), lambda t: t['State'].update(Running=False), lambda t: t['State'].update(Paused=True), lambda t: t['State'].update(Restarting=True), lambda t: t['State'].update(Health={'Status': 'unhealthy'}), lambda t: t.update(RestartCount=1), lambda t: t.update(Id='recreated')]:
                after = copy.deepcopy(before); mutate(after[role]); self.assertIsNotNone(benchmark.target_issue(before, after))
            after = dict(before); del after[role]; self.assertIsNotNone(benchmark.target_issue(before, after))


if __name__ == '__main__': unittest.main(verbosity=2)
