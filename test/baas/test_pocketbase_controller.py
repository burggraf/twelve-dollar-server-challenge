"""Owned lifecycle rejects collisions and never silently rotates seed identities."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
spec = importlib.util.find_spec('pocketbase')
if spec:
    import pocketbase as controller
else:
    controller = None


class OwnedPocketBaseLifecycle(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(controller, 'Owned PocketBase lifecycle controller is missing')

    def test_compose_uses_only_owned_profile_and_private_environment_path(self):
        args = controller.compose()
        self.assertIn('baas-pocketbase-vps16', args)
        self.assertEqual(Path(args[args.index('-f') + 1]).name, 'compose.yaml')
        self.assertIn('services/pocketbase', args[args.index('-f') + 1])
        self.assertEqual(Path(args[args.index('--env-file') + 1]).name, 'runtime.env')
        self.assertNotIn('JWT_SECRET=', ' '.join(args))

    def test_foreign_container_collision_is_rejected_before_changes(self):
        result = SimpleNamespace(returncode=0, stdout=json.dumps([{'Config': {'Labels': {'com.docker.compose.project': 'unrelated'}}}]))
        with patch.object(controller.subprocess, 'run', return_value=result) as run:
            with self.assertRaisesRegex(RuntimeError, 'collision'):
                controller.ownership()
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][:2], ['docker', 'inspect'])

    def test_existing_partial_seed_cannot_be_silently_regenerated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = root / '.state/seed'
            seed.mkdir(parents=True)
            (seed / 'tokens.json').write_text('[]')
            with patch.object(controller, 'ROOT', root), patch.object(controller, 'tools') as tools:
                with self.assertRaisesRegex(RuntimeError, 'Incomplete existing canonical seed'):
                    controller.seed()
            tools.assert_not_called()

    def test_mac_or_other_unapproved_native_profile_is_rejected(self):
        with patch.object(controller.platform, 'system', return_value='Darwin'):
            with self.assertRaises(RuntimeError):
                controller.require_native()


if __name__ == '__main__':
    unittest.main(verbosity=2)
