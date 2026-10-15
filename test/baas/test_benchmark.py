"""Scoring must fail closed on incomplete or contradictory k6 evidence."""
import json
import tempfile
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import benchmark
from benchmark import evaluate, resource_verdict, scenario_started


def summary():
    return {'metrics': {
        'http_reqs{phase:hold}': {'values': {'count': 100}},
        'http_req_duration{phase:hold}': {'values': {'p(95)': 100, 'p(99)': 200}},
        'request_errors{phase:hold}': {'values': {'rate': 0, 'passes': 0, 'fails': 100}},
        'schema_errors{phase:hold}': {'values': {'rate': 0, 'passes': 0, 'fails': 100}},
    }}


class Scoring(unittest.TestCase):
    def test_resource_clock_uses_k6_scenario_start_not_container_creation(self):
        data = {'metrics': {'benchmark_scenario_start_ms': {'values': {'value': 1700000123456}}}}
        self.assertEqual(scenario_started(data), 1700000123.456)
        for invalid in [{}, {'metrics': {'benchmark_scenario_start_ms': {'values': {'value': float('nan')}}}}]:
            with self.assertRaises(ValueError): scenario_started(invalid)

    def test_oom_remains_primary_reason_when_k6_loses_summary_and_clock(self):
        self.assertTrue(callable(getattr(benchmark, 'measurement_verdict', None)),
                        'Attempt classification must combine runner state and metric evidence')
        with tempfile.TemporaryDirectory() as directory:
            verdict = benchmark.measurement_verdict({}, 137, Path(directory), False,
                                                     {'State': {'OOMKilled': True}})
        self.assertEqual(verdict, ('invalid', 'load generator OOM (not target capacity)'))

    def test_missing_clock_still_invalidates_non_oom_attempt(self):
        self.assertTrue(callable(getattr(benchmark, 'measurement_verdict', None)),
                        'Attempt classification must combine runner state and metric evidence')
        with tempfile.TemporaryDirectory() as directory:
            verdict = benchmark.measurement_verdict(summary(), 0, Path(directory), False,
                                                     {'State': {'OOMKilled': False}, 'platform': getattr(benchmark, 'PLATFORM', 'linux/arm64'),
                                                      'limits': benchmark.RUNNER_LIMITS})
        self.assertEqual(verdict, ('invalid', 'missing k6 scenario-start clock'))

    def test_runner_profile_is_versioned_and_matches_the_approved_budget(self):
        self.assertTrue(callable(getattr(benchmark, 'runner_settings', None)))
        self.assertEqual(benchmark.runner_settings(),
                         {'profile': 'k6-2cpu-4g-v2', 'memory': '4g',
                          'limits': {'NanoCpus': 2 * 10**9, 'Memory': 4 * 1024**3, 'MemorySwap': 4 * 1024**3}})

    def test_owner_approved_eight_gib_runner_has_distinct_verified_limits(self):
        self.assertTrue(callable(getattr(benchmark, 'runner_settings', None)))
        self.assertEqual(benchmark.runner_settings('k6-2cpu-8g-v3'),
                         {'profile': 'k6-2cpu-8g-v3', 'memory': '8g',
                          'limits': {'NanoCpus': 2 * 10**9, 'Memory': 8 * 1024**3, 'MemorySwap': 8 * 1024**3}})
        for name in ['arbitrary-32g', '', 'k6-4cpu-8g-v3']:
            with self.assertRaises(ValueError): benchmark.runner_settings(name)

    def test_standard_tier_is_one_cpu_four_gib_with_memory_reserve(self):
        self.assertIn('standard', benchmark.TIERS)
        self.assertEqual(benchmark.TIERS['standard'], (1, 4 * 1024**3))
        required = 5 * 1024**3 + benchmark.RUNNER_LIMITS['Memory']
        benchmark.require_vm_headroom('standard', required)
        with self.assertRaisesRegex(RuntimeError, 'headroom'):
            benchmark.require_vm_headroom('standard', required - 1)

    def test_cpu_reserve_rejects_four_cpu_serving_with_two_cpu_runner_on_four_cpu_host(self):
        import inspect
        self.assertIn('vm_cpus', inspect.signature(benchmark.require_vm_headroom).parameters)
        benchmark.require_vm_headroom('small', 32 * 1024**3, vm_cpus=4)
        with self.assertRaisesRegex(RuntimeError, 'CPU headroom'):
            benchmark.require_vm_headroom('large', 32 * 1024**3, vm_cpus=4)
        benchmark.require_vm_headroom('large', 32 * 1024**3, vm_cpus=7)

    def test_mismatched_actual_runner_budget_cannot_claim_the_new_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            verdict = benchmark.measurement_verdict(summary(), 0, Path(directory), False,
                         {'State': {'OOMKilled': False},
                          'limits': {'NanoCpus': 2 * 10**9, 'Memory': 2 * 1024**3, 'MemorySwap': 2 * 1024**3}})
        self.assertEqual(verdict, ('invalid', 'load-generator limits do not match the selected runner profile'))

    def test_vm_headroom_accepts_small_but_rejects_large_on_current_vm(self):
        self.assertTrue(callable(getattr(benchmark, 'require_vm_headroom', None)))
        runner_memory = benchmark.RUNNER_LIMITS['Memory']
        benchmark.require_vm_headroom('small', runner_memory + 3 * 1024**3)
        with self.assertRaisesRegex(RuntimeError, 'headroom'):
            benchmark.require_vm_headroom('large', runner_memory + 3 * 1024**3)
        with self.assertRaisesRegex(RuntimeError, 'headroom'):
            benchmark.require_vm_headroom('small', runner_memory + 3 * 1024**3 - 1)
        benchmark.require_vm_headroom('large', runner_memory + 5 * 1024**3)

    def test_accepts_complete_passing_hold(self):
        self.assertEqual(evaluate(summary(), 0)[0], 'pass')

    def test_limits_are_strict_and_bad_success_bodies_fail(self):
        for metric, key, value in [('http_req_duration{phase:hold}', 'p(95)', 500),
                                   ('http_req_duration{phase:hold}', 'p(99)', 1000),
                                   ('request_errors{phase:hold}', 'rate', .01),
                                   ('schema_errors{phase:hold}', 'rate', .001)]:
            data = summary()
            data['metrics'][metric]['values'][key] = value
            self.assertEqual(evaluate(data, 99)[0], 'fail')

    def test_incomplete_or_nonfinite_evidence_is_invalid(self):
        cases = [{}, summary(), summary(), summary()]
        cases[1]['metrics']['http_reqs{phase:hold}']['values']['count'] = 0
        cases[2]['metrics']['http_req_duration{phase:hold}']['values']['p(95)'] = float('nan')
        cases[3]['metrics']['request_errors{phase:hold}']['values']['fails'] = 99
        for data in cases:
            self.assertEqual(evaluate(data, 0)[0], 'invalid')

    def test_runner_crash_and_unexplained_exit_are_not_target_capacity_failures(self):
        self.assertEqual(evaluate(summary(), 137)[0], 'invalid')
        self.assertEqual(evaluate(summary(), 99)[0], 'invalid')

    def test_monitor_errors_fail_closed_even_with_other_samples_present(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            rows = [{'time': i, 'vm_stat': 'Swapouts: 0.',
                     benchmark.LOAD: {'CPUPerc': '10%', 'MemPerc': '10%'}} for i in [10, 15, 20]]
            log = path / 'resources.jsonl'
            log.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            self.assertIsNone(resource_verdict(path, 0, True, None))
            rows[-1]['monitor_error'] = 'stats command timed out'
            log.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            self.assertEqual(resource_verdict(path, 0, True, None), 'resource monitor failed')

    def test_sparse_monitoring_cannot_certify_a_hold(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            rows = [{'time': 10, 'vm_stat': 'Swapouts: 0.',
                     benchmark.LOAD: {'CPUPerc': '10%', 'MemPerc': '10%'}}]
            (path / 'resources.jsonl').write_text(json.dumps(rows[0]) + '\n')
            self.assertEqual(resource_verdict(path, 0, True, None), 'incomplete load-generator hold monitoring')

    def test_generator_cpu_saturation_and_host_swap_are_not_target_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            rows = [{'time': i, 'vm_stat': 'Swapouts: 0.',
                     benchmark.LOAD: {'CPUPerc': '190%', 'MemPerc': '10%'}} for i in [10, 15, 20]]
            log = path / 'resources.jsonl'
            log.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            self.assertIn('CPU budget', resource_verdict(path, 0, True, None))
            for row in rows: row[benchmark.LOAD]['CPUPerc'] = '10%'
            rows[-1]['vm_stat'] = 'Swapouts: 1.'
            log.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            self.assertIn('swap-outs', resource_verdict(path, 0, True, None))


class HostPortability(unittest.TestCase):
    def test_direct_controller_exports_inferred_platform_and_namespace_to_compose(self):
        self.assertTrue(callable(getattr(benchmark, 'compose_environment', None)))
        self.assertEqual(benchmark.compose_environment('small', {}),
                         {'TIER': 'small', 'BENCHMARK_PROJECT': benchmark.PROJECT,
                          'BENCHMARK_PLATFORM': benchmark.PLATFORM,
                          'BENCHMARK_RUNNER_PROFILE': benchmark.RUNNER_PROFILE,
                          'RUNNER_MEMORY': getattr(benchmark, 'RUNNER_MEMORY', 'unconfigured')})
        env = benchmark.compose_environment('large', {'OTHER': 'preserved'})
        self.assertEqual(env['TIER'], 'large')
        self.assertEqual(env['OTHER'], 'preserved')
        self.assertEqual(env['BENCHMARK_PLATFORM'], benchmark.PLATFORM)

    def test_selected_container_manifest_overrides_ambiguous_multiarch_image_inspect(self):
        self.assertTrue(callable(getattr(benchmark, 'selected_container_platform', None)))
        container = {'ImageManifestDescriptor': {'platform': {'os': 'linux', 'architecture': 'arm64'}}}
        self.assertEqual(benchmark.selected_container_platform(container, 'linux/amd64'), 'linux/arm64')
        self.assertEqual(benchmark.selected_container_platform({}, 'linux/amd64'), 'linux/amd64')
        for bad in [None, {}, {'platform': {}}]:
            self.assertIsNone(benchmark.selected_container_platform({'ImageManifestDescriptor': bad}, 'linux/amd64'))

    def test_native_platforms_and_result_tracks_are_separate(self):
        self.assertTrue(callable(getattr(benchmark, 'deployment_settings', None)))
        self.assertEqual(benchmark.deployment_settings('Darwin', 'arm64', {}),
                         {'project': 'baas-trailbase', 'platform': 'linux/arm64', 'track': 'local-orbstack-arm64'})
        self.assertEqual(benchmark.deployment_settings('Linux', 'x86_64', {'BENCHMARK_PROJECT': 'baas-trailbase-vps'}),
                         {'project': 'baas-trailbase-vps', 'platform': 'linux/amd64', 'track': 'vps-linux-amd64'})

    def test_new_host_track_cannot_pool_with_original_vps(self):
        settings = benchmark.deployment_settings('Linux', 'x86_64', {'BENCHMARK_PROJECT': 'baas-trailbase-vps16'})
        self.assertEqual(settings, {'project': 'baas-trailbase-vps16', 'platform': 'linux/amd64',
                                    'track': 'vps16-linux-amd64'})

    def test_foreign_platforms_and_unrelated_project_names_are_rejected(self):
        self.assertTrue(callable(getattr(benchmark, 'deployment_settings', None)))
        for env in [{'BENCHMARK_PLATFORM': 'linux/arm64'},
                    {'BENCHMARK_PROJECT': 'trailbasehost-control-data'},
                    {'BENCHMARK_PROJECT': '../escape'}]:
            with self.assertRaises(ValueError):
                benchmark.deployment_settings('Linux', 'x86_64', env)

    def test_linux_samples_preserve_raw_proc_evidence_without_mac_commands(self):
        self.assertTrue(callable(getattr(benchmark, 'host_sample', None)))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = {'vmstat': 'pswpin 1\npswpout 12\n', 'stat': 'cpu 1 2 3 4 5 6 7 8\n',
                        'meminfo': 'MemTotal: 8122016 kB\nMemAvailable: 6000000 kB\n',
                        'diskstats': '8 0 sda 1 2 3\n', 'loadavg': '0.10 0.20 0.30 1/100 123\n',
                        'uptime': '300.0 900.0\n', 'pressure/cpu': 'some avg10=0.00 total=0\n',
                        'pressure/memory': 'some avg10=0.00 total=0\n',
                        'pressure/io': 'some avg10=0.00 total=0\n'}
            for name, text in evidence.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            sample = benchmark.host_sample('Linux', root)
            for name, text in evidence.items():
                self.assertEqual(sample['linux_' + name.replace('/', '_')], text)
            self.assertNotIn('vm_stat', sample)
            (root / 'vmstat').unlink()
            with self.assertRaises(FileNotFoundError): benchmark.host_sample('Linux', root)

    def test_linux_swapouts_are_checked_without_weakening_mac_checks(self):
        self.assertTrue(callable(getattr(benchmark, 'host_swapouts', None)))
        self.assertEqual(benchmark.host_swapouts({'linux_vmstat': 'pswpout 42\n'}), 42)
        self.assertEqual(benchmark.host_swapouts({'vm_stat': 'Swapouts: 42.'}), 42)
        for row in [{}, {'linux_vmstat': 'pswpout NaN\n'}, {'linux_vmstat': 'pswpout -1\n'}]:
            self.assertIsNone(benchmark.host_swapouts(row))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            rows = [{'time': i, 'linux_vmstat': f'pswpout {int(i == 20)}\n',
                     benchmark.LOAD: {'CPUPerc': '10%', 'MemPerc': '10%'}} for i in [10, 15, 20]]
            (path / 'resources.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
            self.assertIn('swap-outs', resource_verdict(path, 0, True, None))

    def test_foreign_architecture_load_image_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            verdict = benchmark.measurement_verdict(summary(), 0, Path(directory), False,
                {'State': {'OOMKilled': False}, 'limits': benchmark.RUNNER_LIMITS, 'platform': 'linux/386'})
        self.assertEqual(verdict, ('invalid', 'load-generator image is not native to the selected host'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
