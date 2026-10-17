"""Offline reset orchestration executes actual control code with all native effects mocked."""
import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import nhost as n
import import_nhost as importer
class ResetFlow(unittest.TestCase):
 def run_case(self,case):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);ids={role:role for role in n.s.SERVICES};schema=[{'sha256':'schema'},{'sha256':'changed' if case=='schema-drift' else 'schema'}];metadata=[{'sha256':'metadata'},{'sha256':'changed' if case=='metadata-drift' else 'metadata'}]
   with patch.object(n,'active'),patch.object(n,'evidence',return_value=root),patch.object(n.s,'identities',return_value=ids),patch.object(n.s,'schema_state',side_effect=schema),patch.object(n.s,'metadata_state',side_effect=metadata),patch.object(n,'stop_owned',return_value={'failures':['stop failed'] if case=='stop-failed' else []}) as stop,patch.object(importer,'reset',return_value={'counts':'canonical'}) as copy,patch.object(n,'up') as up,patch.object(n.s,'profile'):
    if case=='valid':n.reset(root/'dataset.json');copy.assert_called_once();up.assert_called_once();self.assertEqual(stop.call_args.kwargs['roles'],('adapter','auth','graphql'))
    else:
     with self.assertRaises(RuntimeError):n.reset(root/'dataset.json')
     if case=='stop-failed':copy.assert_not_called();up.assert_not_called()
     if case=='schema-drift':copy.assert_called_once();up.assert_not_called()
 def test_stop_only_apis_then_copy_and_start_with_unchanged_catalog(self):self.run_case('valid')
 def test_failed_api_stop_never_reaches_copy(self):self.run_case('stop-failed')
 def test_catalog_drift_prevents_start(self):self.run_case('schema-drift')
 def test_native_permission_metadata_drift_cannot_pass_reset(self):self.run_case('metadata-drift')
if __name__=='__main__':unittest.main(verbosity=2)
