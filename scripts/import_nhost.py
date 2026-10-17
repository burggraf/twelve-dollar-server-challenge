#!/usr/bin/env python3
"""Exact-owned offline application-only COPY, retained pre-reset dump and full stored-row verification."""
import argparse,csv,hashlib,itertools,json,re,subprocess
from pathlib import Path
from import_postgres import EXPECTED_COUNTS,EXPECTED_HASH,TABLES,postgres_row,logical_row
PROJECT='baas-nhost-vps16'
ROLES=('db','graphql','auth','adapter')
def psql_args(db_id,sql=None):
 if type(db_id) is not str or not re.fullmatch('[a-f0-9]{64}',db_id):raise ValueError('Exact native database ID required')
 args=['docker','exec','-i',db_id,'psql','-X','-v','ON_ERROR_STOP=1','-U','postgres','-d','postgres']
 return args+(['-qAt','-c',sql] if sql is not None else ['-q'])
def require_offline(identities):
 if type(identities) is not dict or set(identities)!=set(ROLES) or any(type(cid) is not str or not re.fullmatch('[a-f0-9]{64}',cid) for cid in identities.values()) or len(set(identities.values()))!=4:raise ValueError('Exact four distinct Nhost container IDs required')
 for role in ROLES:
  cid=identities[role];item=json.loads(subprocess.check_output(['docker','inspect',cid],stderr=subprocess.STDOUT,timeout=10))[0]
  labels=item['Config']['Labels'];state=item['State']
  if item['Id']!=cid or labels.get('com.docker.compose.project')!=PROJECT or labels.get('com.docker.compose.service')!=role:raise ValueError('Nhost container identity/ownership mismatch')
  if state['Running']!=(role=='db') or state['OOMKilled'] or item['RestartCount']:raise ValueError('Import requires only owned healthy DB running, no OOM/restarts')
  if role=='db':
   if state['Pid']<=0 or state['Health']['Status']!='healthy':raise ValueError('Nhost database not ready')
  elif state['Pid']!=0:raise ValueError('Nhost API process remains live during import')
 return identities['db']

def verify(db_id):
 digest=hashlib.sha256();counts={}
 for table,(columns,order) in TABLES.items():
  sql=f"COPY(SELECT {columns} FROM feed_data.{table} ORDER BY {order}) TO STDOUT WITH(FORMAT csv,DELIMITER E'\\t')"
  process=subprocess.Popen(psql_args(db_id,sql),stdout=subprocess.PIPE,text=True);count=0
  try:
   for row in csv.reader(process.stdout,delimiter='\t'):
    digest.update(('|'.join(logical_row(table,row))+'\n').encode('utf-8'));count+=1
  except BaseException:
   process.kill();process.wait();raise
  finally:process.stdout.close()
  if process.wait()!=0:raise ValueError('Native canonical export failed')
  if count!=EXPECTED_COUNTS[table]:raise ValueError(f'{table}: count {count}, expected {EXPECTED_COUNTS[table]}')
  counts[table]=count
 if digest.hexdigest()!=EXPECTED_HASH:raise ValueError('Native canonical logical hash differs: '+digest.hexdigest())
 return {'counts':counts,'content_sha256':digest.hexdigest()}

def input_rows(tsv,table):
 path=tsv/(table+'.tsv')
 if not path.is_file() or path.is_symlink():raise ValueError('Missing/unsafe canonical TSV: '+table)
 with path.open(encoding='utf-8',newline='') as stream:
  for row in csv.reader(stream,delimiter='\t',quoting=csv.QUOTE_NONE):
   if len(row)!={'users':3,'posts':4,'likes':3}[table]:raise ValueError('Invalid canonical TSV columns: '+table)
   yield row

def verify_inputs(tsv):
 digest=hashlib.sha256()
 for table in TABLES:
  rows=input_rows(tsv,table);count=0
  # The unchanged generator groups likes by post, but emits users in random order within each group.
  if table=='likes':rows=(row for _,group in itertools.groupby(rows,key=lambda row:int(row[1])) for row in sorted(group,key=lambda row:int(row[0])))
  for row in rows:digest.update(('|'.join(row)+'\n').encode('utf-8'));count+=1
  if count!=EXPECTED_COUNTS[table]:raise ValueError('Canonical input count differs: '+table)
 if digest.hexdigest()!=EXPECTED_HASH:raise ValueError('Canonical input logical hash differs')

def reset(tsv,manifest,identities):
 db_id=require_offline(identities);tsv=Path(tsv);manifest=Path(manifest)
 if manifest.exists():raise ValueError('Dataset manifest already exists; retain history')
 verify_inputs(tsv)
 dump=manifest.with_name(manifest.stem+'-before-reset-PRIVATE.dump')
 with dump.open('xb') as output,dump.with_suffix('.log').open('xb') as errors:
  subprocess.run(['docker','exec',db_id,'pg_dump','-U','postgres','-d','postgres','-Fc'],stdout=output,stderr=errors,check=True,timeout=300)
 if dump.stat().st_size==0:raise ValueError('Empty pre-reset native dump')
 before=subprocess.check_output(psql_args(db_id,'SELECT count(*) FROM auth.users'),text=True).strip()
 process=subprocess.Popen(psql_args(db_id),stdin=subprocess.PIPE,text=True,encoding='utf-8')
 try:
  process.stdin.write('BEGIN; TRUNCATE feed_data.likes,feed_data.posts,feed_data.users RESTART IDENTITY;\n')
  writer=csv.writer(process.stdin,delimiter='\t',lineterminator='\n')
  for table in TABLES:
   process.stdin.write(f"COPY feed_data.{table} FROM STDIN WITH(FORMAT csv,DELIMITER E'\\t');\n")
   for row in input_rows(tsv,table):writer.writerow(postgres_row(table,row))
   process.stdin.write('\\.\n')
  process.stdin.write("SELECT setval(pg_get_serial_sequence('feed_data.posts','id'),(SELECT max(id) FROM feed_data.posts),true); COMMIT;\n")
  process.stdin.close()
  if process.wait()!=0:raise ValueError('Native canonical COPY transaction failed')
 except BaseException:
  if process.poll() is None:process.kill();process.wait()
  raise
 result=verify(db_id)
 after=subprocess.check_output(psql_args(db_id,'SELECT count(*) FROM auth.users'),text=True).strip()
 if before!=after:raise ValueError('Native Auth accounts changed during app import')
 for table in TABLES:subprocess.run(psql_args(db_id,'VACUUM ANALYZE feed_data.'+table),check=True,timeout=180)
 with dump.open('rb') as stream:dump_sha256=hashlib.file_digest(stream,'sha256').hexdigest()
 result.update({'pre_reset_dump_sha256':dump_sha256,'native_auth_accounts_before':int(before),'native_auth_accounts_after':int(after),'body_storage':'UTF-8 bytea; native GraphQL transport; full stored logical-row hash'})
 with manifest.open('x') as output:output.write(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result),flush=True);return result

def main():
 import nhost,nhost_profile
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('tsv',type=Path);parser.add_argument('--manifest',type=Path,required=True);args=parser.parse_args()
 nhost.active();reset(args.tsv,args.manifest,nhost_profile.identities())
if __name__=='__main__':main()
