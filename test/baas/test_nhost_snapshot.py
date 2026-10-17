"""Source reproduction includes the shared adapter dependency, never private state."""
import subprocess,sys,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import benchmark as b
class Snapshot(unittest.TestCase):
 def test_nhost_archive_contains_shared_contract_and_no_private_state(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)/'root';root.mkdir();out=Path(directory)/'out';out.mkdir()
   for name in ['README.md','MASTER_PLAN.md','LICENSE','SPEC.md','schema.sql','.gitignore','.dockerignore','services/nhost/app/server.mjs','services/supabase/functions/feed/contract.mjs','.state/nhost/stack.env','.state/seed/tokens.json']:
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('test-only fixture\n')
   with patch.object(b,'ROOT',root),patch.object(b,'command',return_value=subprocess.CompletedProcess([],0,stdout=b'public diff')):
    try:b.snapshot(out,service='nhost')
    except ValueError as error:self.fail('Approved Nhost snapshot unavailable: '+str(error))
   with tarfile.open(out/'source.tar.gz') as archive:names=archive.getnames()
   self.assertIn('services/nhost/app/server.mjs',names);self.assertIn('services/supabase/functions/feed/contract.mjs',names)
   self.assertFalse(any(name.startswith('.state/') or name.endswith('tokens.json') for name in names))
if __name__=='__main__':unittest.main(verbosity=2)
