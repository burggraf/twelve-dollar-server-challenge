#!/usr/bin/env python3
"""Offline app-only COPY/reset and exact canonical logical-row verification.

All API containers must be stopped. PostgreSQL remains up for its supported SQL
maintenance interface. No PostgreSQL driver or direct SQL is used by serving Edge
Functions. Supabase Auth/platform schemas and accounts are never truncated.
"""
import argparse,csv,hashlib,json,subprocess
from pathlib import Path
from import_sqlite import EXPECTED_COUNTS,EXPECTED_HASH
PROJECT='baas-supabase-vps16'
DB=PROJECT+'-db-1'
TABLES={'users':('id,username,created_at','id'),'posts':("id,user_id,encode(body,'hex'),created_at",'id'),'likes':('user_id,post_id,created_at','post_id,user_id')}
def postgres_row(table,row):
 value=list(row)
 if table=='posts':value[2]='\\x'+value[2].encode('utf-8').hex()
 return value

def logical_row(table,row):
 value=list(row)
 if table=='posts':value[2]=bytes.fromhex(value[2]).decode('utf-8')
 return value

def psql_args(sql=None):
 args=['docker','exec','-i',DB,'psql','-X','-v','ON_ERROR_STOP=1','-U','supabase_admin','-d','postgres']
 return args+(['-qAt','-c',sql] if sql is not None else ['-q'])

def query(sql):return subprocess.check_output(psql_args(sql),text=True).strip()

def require_offline():
 for service in ['db','auth','rest','functions','gateway']:
  value=json.loads(subprocess.check_output(['docker','inspect',PROJECT+'-'+service+'-1'],text=True))[0]
  if value['Config']['Labels'].get('com.docker.compose.project')!=PROJECT:raise ValueError('Container ownership mismatch')
  if value['State']['Running']!=(service=='db'):raise ValueError('Import requires only the owned database running')

def verify():
 digest=hashlib.sha256();counts={}
 for table,(columns,order) in TABLES.items():
  sql=f"COPY(SELECT {columns} FROM feed_data.{table} ORDER BY {order}) TO STDOUT WITH(FORMAT csv,DELIMITER E'\\t')"
  process=subprocess.Popen(psql_args(sql),stdout=subprocess.PIPE,text=True)
  count=0
  try:
   for row in csv.reader(process.stdout,delimiter='\t'):
    digest.update(('|'.join(logical_row(table,row))+'\n').encode('utf-8'));count+=1
  except BaseException:
   process.kill();process.wait();raise
  finally:process.stdout.close()
  if process.wait()!=0:raise ValueError('Canonical PostgreSQL export failed')
  if count!=EXPECTED_COUNTS[table]:raise ValueError(f'{table}: count {count}, expected {EXPECTED_COUNTS[table]}')
  counts[table]=count
 if digest.hexdigest()!=EXPECTED_HASH:raise ValueError('Canonical PostgreSQL logical content hash mismatch: '+digest.hexdigest())
 return {'counts':counts,'content_sha256':digest.hexdigest()}

def reset(tsv,manifest):
 require_offline()
 native_auth_before=int(query('SELECT count(*) FROM auth.users'))
 process=subprocess.Popen(psql_args(),stdin=subprocess.PIPE,text=True)
 try:
  process.stdin.write('BEGIN; TRUNCATE feed_data.likes,feed_data.posts,feed_data.users RESTART IDENTITY;\n')
  writer=csv.writer(process.stdin,delimiter='\t',lineterminator='\n')
  for table in TABLES:
   process.stdin.write(f"COPY feed_data.{table} FROM STDIN WITH(FORMAT csv,DELIMITER E'\\t');\n")
   with (tsv/(table+'.tsv')).open(newline='') as stream:
    for row in csv.reader(stream,delimiter='\t',quoting=csv.QUOTE_NONE):writer.writerow(postgres_row(table,row))
   process.stdin.write('\\.\n')
  process.stdin.write("SELECT setval(pg_get_serial_sequence('feed_data.posts','id'),(SELECT max(id) FROM feed_data.posts),true); COMMIT;\n")
  process.stdin.close()
  if process.wait()!=0:raise ValueError('Canonical PostgreSQL COPY transaction failed')
 except BaseException:
  if process.poll() is None:process.kill();process.wait()
  raise
 result=verify()
 native_auth_after=int(query('SELECT count(*) FROM auth.users'))
 if native_auth_before!=native_auth_after:raise ValueError('Native Auth accounts changed during application import')
 # Normal offline maintenance, not a response cache or precomputed aggregate.
 subprocess.run(psql_args('VACUUM ANALYZE feed_data.users;'),check=True)
 subprocess.run(psql_args('VACUUM ANALYZE feed_data.posts;'),check=True)
 subprocess.run(psql_args('VACUUM ANALYZE feed_data.likes;'),check=True)
 result.update({'engine':query('SELECT version()'),'native_auth_accounts_before':native_auth_before,'native_auth_accounts_after':native_auth_after,'body_storage':'UTF-8 bytea; base64 native RPC transport; exact logical-row hash'})
 manifest.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
 return result

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('tsv',type=Path);parser.add_argument('--manifest',type=Path,required=True);args=parser.parse_args();reset(args.tsv,args.manifest)
if __name__=='__main__':main()
