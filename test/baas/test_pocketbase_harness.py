"""PocketBase uses the same bounded native cohort, not a silently different track."""
from pathlib import Path
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import benchmark as b


class NativePocketBaseHarness(unittest.TestCase):
    def test_owned_native_namespace_selects_existing_vps16_track(self):
        result = b.deployment_settings('Linux', 'x86_64', {
            'BENCHMARK_PROJECT': 'baas-pocketbase-vps16',
            'BENCHMARK_PLATFORM': 'linux/amd64',
        })
        self.assertEqual(result, {'project': 'baas-pocketbase-vps16',
                                  'platform': 'linux/amd64',
                                  'track': 'vps16-linux-amd64'})

    def test_source_snapshot_includes_pocketbase_and_excludes_private_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'out'
            output.mkdir()
            for name in ['README.md', 'MASTER_PLAN.md', 'LICENSE', 'SPEC.md',
                         'schema.sql', '.gitignore', '.dockerignore',
                         'services/pocketbase/app/main.go', 'services/pocketbase/.env',
                         'services/supabase/marker', 'services/trailbase/marker']:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('nonsecret fixture')
            with patch.object(b, 'ROOT', root), patch.object(b, 'command', return_value=SimpleNamespace(stdout=b'')):
                try:
                    b.snapshot(output, service='pocketbase')
                except ValueError as error:
                    self.fail('Native PocketBase source snapshot is unsupported: ' + str(error))
            with tarfile.open(output / 'source.tar.gz') as archive:
                names = archive.getnames()
            self.assertIn('services/pocketbase/app/main.go', names)
            self.assertNotIn('services/pocketbase/.env', names)
            self.assertNotIn('services/supabase/marker', names)
            self.assertNotIn('services/trailbase/marker', names)

    def test_generalization_does_not_allow_unrelated_namespace_or_emulation(self):
        for project, platform in [('unrelated-pocketbase', 'linux/amd64'),
                                  ('baas-pocketbase-vps16', 'linux/arm64')]:
            with self.assertRaises(ValueError):
                b.deployment_settings('Linux', 'x86_64', {
                    'BENCHMARK_PROJECT': project, 'BENCHMARK_PLATFORM': platform})


if __name__ == '__main__':
    unittest.main(verbosity=2)
