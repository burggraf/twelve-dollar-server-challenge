"""Reset rejects invalid inputs and failed COPY/export without false manifests; external effects mocked."""
import hashlib,io,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import import_nhost as n
class Sink(io.StringIO):
 def close(self):pass
class Process:
 def __init__(self,code):self.stdin=Sink();self.code=code
 def wait(self):return self.code
 def poll(self):return self.code
 def kill(self):pass
class Reset(unittest.TestCase):
 def check_case(self,case):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);rows={'users':[['1','alice','2026']],'posts':[['9','1','\ufeffbody\0','2026']],'likes':[['1','9','2026']]};digest=hashlib.sha256()
   for table,items in rows.items():
    (root/(table+'.tsv')).write_text(''.join('\t'.join(row)+'\n' for row in items))
    for row in items:digest.update(('|'.join(row)+'\n').encode())
   if case=='changed-body':(root/'posts.tsv').write_text('9\t1\tchanged\t2026\n')
   if case=='wrong-count':(root/'likes.tsv').write_text('')
   if case=='missing-file':(root/'users.tsv').unlink()
   process=Process(1 if case=='copy-failed' else 0);manifest=root/'dataset.json'
   def run(argv,**kwargs):
    if argv[3:4]==['pg_dump']:kwargs['stdout'].write(b'PGDMP-test-only-fixture')
    return subprocess.CompletedProcess(argv,0)
   with patch.object(n,'EXPECTED_COUNTS',{table:1 for table in rows}),patch.object(n,'EXPECTED_HASH',digest.hexdigest()),patch.object(n,'require_offline',return_value='a'*64),patch.object(n.subprocess,'Popen',return_value=process) as spawn,patch.object(n.subprocess,'run',side_effect=run),patch.object(n.subprocess,'check_output',return_value='0'),patch.object(n,'verify',side_effect=ValueError('stored rows differ')) as verify:
    with self.assertRaises(ValueError):n.reset(root,manifest,{})
    self.assertFalse(manifest.exists())
    if case in ['changed-body','wrong-count','missing-file']:spawn.assert_not_called()
    if case=='copy-failed':verify.assert_not_called();self.assertIn('BEGIN;',process.stdin.getvalue());self.assertIn('TRUNCATE feed_data.likes,feed_data.posts,feed_data.users',process.stdin.getvalue())
    if case=='export-failed':verify.assert_called_once_with('a'*64);self.assertIn('COMMIT;',process.stdin.getvalue())
 def test_rejects_changed_body_with_correct_input_counts(self):self.check_case('changed-body')
 def test_rejects_wrong_input_count(self):self.check_case('wrong-count')
 def test_rejects_missing_input_before_sql(self):self.check_case('missing-file')
 def test_rejects_copy_failure_without_manifest(self):self.check_case('copy-failed')
 def test_rejects_stored_export_failure_without_manifest(self):self.check_case('export-failed')
if __name__=='__main__':unittest.main(verbosity=2)
