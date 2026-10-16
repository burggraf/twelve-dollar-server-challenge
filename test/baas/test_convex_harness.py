"""Native Convex reuses the original cohort/scoring; private SDK bytes stay private."""
from pathlib import Path
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import benchmark as b


class NativeConvexHarness(unittest.TestCase):
    def test_owned_postgres_namespace_uses_existing_cohort(self):
        self.assertEqual(b.deployment_settings('Linux', 'x86_64', {'BENCHMARK_PROJECT': 'baas-convexpg-vps16', 'BENCHMARK_PLATFORM': 'linux/amd64'}), {'project': 'baas-convexpg-vps16', 'platform': 'linux/amd64', 'track': 'vps16-linux-amd64'})

    def test_source_overlay_includes_native_code_but_not_private_or_dependency_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); out = root / 'out'; out.mkdir()
            for name in ['README.md', 'MASTER_PLAN.md', 'LICENSE', 'SPEC.md', 'schema.sql', '.gitignore', '.dockerignore', 'services/convex/app/convex/native.js', 'services/convex/app/convex/_generated/server.js', 'services/convex/app/node_modules/convex/private-fixture', 'services/convex/app/.env.local', 'services/supabase/marker']:
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('nonsecret fixture')
            with patch.object(b, 'ROOT', root), patch.object(b, 'command', return_value=SimpleNamespace(stdout=b'')):
                try: b.snapshot(out, service='convex')
                except ValueError as error: self.fail('Native Convex source overlay unsupported: ' + str(error))
            with tarfile.open(out / 'source.tar.gz') as archive: names = archive.getnames()
            self.assertIn('services/convex/app/convex/native.js', names)
            self.assertIn('services/convex/app/convex/_generated/server.js', names)
            self.assertFalse(any('node_modules' in name or '.env.local' in name or 'supabase/marker' in name for name in names))

    def test_unrelated_namespace_and_emulation_refused(self):
        for project, platform in [('unrelated-convex', 'linux/amd64'), ('baas-convexpg-vps16', 'linux/arm64')]:
            with self.assertRaises(ValueError): b.deployment_settings('Linux', 'x86_64', {'BENCHMARK_PROJECT': project, 'BENCHMARK_PLATFORM': platform})


if __name__ == '__main__': unittest.main(verbosity=2)
