"""PostgreSQL storage mapping must preserve original logical rows byte-for-byte."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from import_postgres import postgres_row,logical_row,psql_args
class StorageMapping(unittest.TestCase):
 def test_operator_uses_official_privileged_bootstrap_role_not_runtime_postgres(self):
  args=psql_args();self.assertEqual(args[args.index('-U')+1],'supabase_admin')
 def test_import_and_export_are_exact_utf8_including_nul(self):
  row=['1','2','café\x00😀','2025-01-01T00:00:00.000Z'];hexbody=row[2].encode().hex()
  self.assertEqual(postgres_row('posts',row),['1','2','\\x'+hexbody,row[3]])
  self.assertEqual(logical_row('posts',['1','2',hexbody,row[3]]),row)
 def test_nonbody_columns_and_input_objects_are_unchanged(self):
  row=['1','name','timestamp'];before=row.copy()
  self.assertEqual(postgres_row('users',row),row);self.assertEqual(logical_row('users',row),row);self.assertEqual(row,before)
if __name__=='__main__':unittest.main(verbosity=2)
