"""Actual native offline COPY/full stored-row verification; no timed application bypass."""
import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import nhost as control
import nhost_profile as s
import import_nhost as n
class CanonicalImport(unittest.TestCase):
 def test_complete_canonical_app_only_copy_and_stored_hash(self):
  ids=s.identities();n.require_offline(ids);before=s.schema_state()
  protected=s.query("SELECT jsonb_build_object('auth',(SELECT count(*) FROM auth.users),'probe_users',(SELECT count(*) FROM nhost_probe.users),'probe_posts',(SELECT count(*) FROM nhost_probe.posts),'probe_likes',(SELECT count(*) FROM nhost_probe.likes),'return_shape',(SELECT count(*) FROM feed_api.result))")
  manifest=control.evidence()/'dataset.json'
  n.reset(s.ROOT/'.state/seed',manifest,ids)
  actual=json.loads(s.query("SELECT jsonb_build_object('users',(SELECT count(*) FROM feed_data.users),'posts',(SELECT count(*) FROM feed_data.posts),'likes',(SELECT count(*) FROM feed_data.likes))"))
  print('ACTUAL_NATIVE_APP_ROWS_AFTER_IMPORT',json.dumps(actual),flush=True)
  self.assertEqual(actual,n.EXPECTED_COUNTS)
  value=n.verify(ids['db']);self.assertEqual(value['content_sha256'],n.EXPECTED_HASH)
  self.assertTrue(manifest.is_file());self.assertEqual(json.loads(manifest.read_text())['content_sha256'],n.EXPECTED_HASH)
  self.assertEqual(s.schema_state()['sha256'],before['sha256'])
  self.assertEqual(s.query("SELECT jsonb_build_object('auth',(SELECT count(*) FROM auth.users),'probe_users',(SELECT count(*) FROM nhost_probe.users),'probe_posts',(SELECT count(*) FROM nhost_probe.posts),'probe_likes',(SELECT count(*) FROM nhost_probe.likes),'return_shape',(SELECT count(*) FROM feed_api.result))"),protected)
  self.assertEqual(s.query("SELECT last_value::text||'|'||is_called::text FROM feed_data.posts_id_seq"),'500000|true')
  print('NHOST_REAL_CANONICAL_COPY_HASH_SEQUENCE_PLATFORM_PRESERVATION_PASS',json.dumps(value),flush=True)
if __name__=='__main__':unittest.main(verbosity=2)
