"""Keep bulky generated artifacts out of Git without hiding required inputs.

Run with: python3 -m unittest discover -s test -p test_gitignore.py -v
"""
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryIgnores(unittest.TestCase):
    def assert_ignored(self, path, expected):
        result = subprocess.run(
            ['git', 'check-ignore', '--no-index', '-q', path], cwd=ROOT,
            capture_output=True, text=True,
        )
        self.assertIn(result.returncode, (0, 1), result.stderr)
        self.assertEqual(result.returncode == 0, expected, path)

    def test_bulk_run_artifacts_are_ignored_across_services_and_tracks(self):
        for directory in ('results/trailbase/run',
                          'results/trailbase/vps16-linux-amd64/run',
                          'results/supabase/track/run'):
            for name in ('samples.json', 'samples.json.gz', 'source.tar.gz'):
                with self.subTest(directory=directory, name=name):
                    self.assert_ignored(f'{directory}/{name}', True)

    def test_runtime_dependencies_and_caches_are_ignored(self):
        for path in ('.state/trailbase/feed.db', 'seed/feed.db-wal',
                     'seed/tokens.json', 'seed/tsv/users.tsv',
                     'services/trailbase/app/target/debug/app',
                     'services/example/node_modules/module/index.js',
                     'services/example/.venv/bin/python',
                     'test/__pycache__/test_gitignore.pyc',
                     'test/standalone.pyc', '.pytest_cache/README.md',
                     'services/trailbase/.env'):
            with self.subTest(path=path):
                self.assert_ignored(path, True)

    def test_source_inputs_and_small_benchmark_evidence_remain_visible(self):
        for path in ('services/trailbase/app/Cargo.lock',
                     'services/trailbase/app/src/lib.rs',
                     'services/trailbase/.env.example',
                     'seed/generate.mjs', 'test/golden/feed.json',
                     'services/example/package-lock.json',
                     'services/example/src/bin/server.rs',
                     'test/fixtures/samples.json',
                     'results/trailbase/run/report.md',
                     'results/trailbase/run/SHA256SUMS',
                     'results/trailbase/run/summary.json',
                     'results/trailbase/run/k6-summary.json',
                     'results/trailbase/run/resources.jsonl',
                     'results/trailbase/run/correctness.log',
                     'results/trailbase/run/working-tree.patch'):
            with self.subTest(path=path):
                self.assert_ignored(path, False)


if __name__ == '__main__':
    unittest.main(verbosity=2)
