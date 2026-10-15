"""The canonical generator must not leak its signing key into build/test logs."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SeedSafety(unittest.TestCase):
    def test_generator_does_not_log_signing_key(self):
        marker = 'NONSECRET_SEED_LOGGING_REGRESSION_CANARY'
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(['node', str(ROOT / 'seed/generate.mjs'), directory],
                                    env={**os.environ, 'JWT_SECRET': marker}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(marker, result.stdout + result.stderr)
            self.assertTrue((Path(directory) / 'tokens.json').is_file())


if __name__ == '__main__':
    unittest.main(verbosity=2)
