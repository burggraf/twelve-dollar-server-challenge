"""Reject wrong budget, malformed VU count or stale qualification before any reset/load effects."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import nhost_benchmark as n
class AttemptAdmission(unittest.TestCase):
 def test_invalid_vu_count_rejected(self):
  for value in [0,-1,20001,True,'25']:
   with self.subTest(vus=value),self.assertRaises(ValueError):n.attempt(value)
 def test_nonstandard_tier_rejected(self):
  with self.assertRaises(ValueError):n.attempt(25,tier='large')
 def test_wrong_project_platform_or_runner_rejected(self):
  for field,value in [('PROJECT','foreign'),('PLATFORM','linux/arm64'),('RUNNER_PROFILE','k6-2cpu-4g-v2')]:
   with patch.object(n.b,'PROJECT',n.s.PROJECT),patch.object(n.b,'PLATFORM','linux/amd64'),patch.object(n.b,'RUNNER_PROFILE','k6-2cpu-8g-v3'),patch.object(n.b,field,value),self.subTest(field=field),self.assertRaises(RuntimeError):n.attempt(25)
 def test_stale_full_qualification_is_rejected_before_any_reset(self):
  with tempfile.TemporaryDirectory() as directory:
   state=Path(directory);log=b'complete untouched full qualification original\n';(state/'correctness.log').write_bytes(log);(state/'correctness-manifest.json').write_text(json.dumps({'inputs':{'app':'old'},'log_sha256':hashlib.sha256(log).hexdigest()}))
   with patch.object(n,'STATE',state),patch.object(n.b,'PROJECT',n.s.PROJECT),patch.object(n.b,'PLATFORM','linux/amd64'),patch.object(n.b,'RUNNER_PROFILE','k6-2cpu-8g-v3'),patch.object(n.control,'active'),patch.object(n,'inputs',return_value={'app':'new'}),patch.object(n.control,'reset') as reset,patch.object(n.subprocess if hasattr(n,'subprocess') else n.control.subprocess,'run') as run:
    with self.assertRaises(RuntimeError):n.attempt(25)
    reset.assert_not_called();run.assert_not_called()
if __name__=='__main__':unittest.main(verbosity=2)
