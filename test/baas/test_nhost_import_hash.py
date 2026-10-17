"""Actual stream hashing/validation, with only the external psql process replaced."""
import csv,hashlib,io,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import import_nhost as n
CID='a'*64
ROWS={'users':[['1','user1','2025-01-01T00:00:00.000Z']], 'posts':[['9007199254740993','1','\ufeffx\x00🦄','2025-01-01T00:00:00.000Z']], 'likes':[['1','9007199254740993','2025-01-01T00:00:00.000Z']]}
EXPECTED=hashlib.sha256(''.join('|'.join(row)+'\n' for rows in ROWS.values() for row in rows).encode()).hexdigest()
class StoredHash(unittest.TestCase):
 def verify(self,mode='ok'):
  streams=[]
  class Process:
   def __init__(self,argv,**kwargs):
    assert argv[:4]==['docker','exec','-i',CID]
    table=next(table for table in ROWS if 'FROM feed_data.'+table in argv[-1])
    rows=[row.copy() for row in ROWS[table]]
    if table=='posts':rows[0][2]=rows[0][2].encode().hex()
    if mode=='tamper' and table=='posts':rows[0][2]='78'
    if mode=='count' and table=='likes':rows=[]
    self.stdout=io.StringIO();csv.writer(self.stdout,delimiter='\t',lineterminator='\n').writerows(rows);self.stdout.seek(0);streams.append(self.stdout)
   def wait(self):return 1 if mode=='export-error' else 0
   def kill(self):pass
  with patch.object(n,'EXPECTED_COUNTS',{key:len(rows) for key,rows in ROWS.items()}),patch.object(n,'EXPECTED_HASH',EXPECTED),patch.object(n.subprocess,'Popen',Process):
   result=n.verify(CID)
  self.assertTrue(all(stream.closed for stream in streams))
  return result
 def test_exact_stored_rows_hash_not_manifest_or_rounded_ids(self):
  self.assertEqual(self.verify(),{'counts':{'users':1,'posts':1,'likes':1},'content_sha256':EXPECTED})
 def test_rejects_correct_counts_with_changed_body(self):
  with self.assertRaises(ValueError):self.verify('tamper')
 def test_rejects_wrong_row_counts(self):
  with self.assertRaises(ValueError):self.verify('count')
 def test_rejects_native_export_failure(self):
  with self.assertRaises(ValueError):self.verify('export-error')
 def test_rejects_nonexact_container_id_before_constructing_exec(self):
  with self.assertRaises(ValueError):n.psql_args('--privileged')
if __name__=='__main__':unittest.main(verbosity=2)
