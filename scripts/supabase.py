#!/usr/bin/env python3
"""Owned native Supabase lifecycle; serving uses only Edge Functions and PostgREST."""
import argparse,base64,fcntl,hashlib,hmac,json,os,platform,secrets,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen
import benchmark as b
import supabase_profile as s
ROOT=s.ROOT;STATE=s.STATE

def require_native():
 if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64') or b.PROJECT!=s.PROJECT or b.RUNNER_PROFILE!='k6-2cpu-8g-v3':raise RuntimeError('Use services/supabase/run.sh on the designated native AMD64 host/profile')
 if not (ROOT.parent/'.benchmark-owned').is_file():raise RuntimeError('Missing owned workspace marker; refusing infrastructure operations')

def compose():return ['docker','compose','--env-file',str(STATE/'stack.env'),'-p',s.PROJECT,'-f',str(ROOT/'services/supabase/compose.yaml')]

def run(argv,log=None,**kwargs):return subprocess.run(argv,cwd=ROOT,check=True,stdout=log,stderr=subprocess.STDOUT if log else None,**kwargs)

def ownership():
 for role in s.SERVICES:
  result=subprocess.run(['docker','inspect',s.PROJECT+'-'+role+'-1'],capture_output=True,text=True)
  if result.returncode==0 and json.loads(result.stdout)[0]['Config']['Labels'].get('com.docker.compose.project')!=s.PROJECT:raise RuntimeError('Container namespace collision; refusing changes')

def initialize():
 require_native();ownership();STATE.mkdir(parents=True,exist_ok=True,mode=0o700);(STATE/'runs').mkdir(exist_ok=True,mode=0o700);(ROOT/'.state/seed').mkdir(exist_ok=True,mode=0o700)
 envfile=STATE/'stack.env'
 if not envfile.exists():
  values={name:secrets.token_hex(32) for name in ['POSTGRES_PASSWORD','NATIVE_JWT_SECRET','COMPAT_JWT_SECRET']}
  enc=lambda value:base64.urlsafe_b64encode(json.dumps(value,separators=(',',':')).encode()).decode().rstrip('=')
  text=enc({'alg':'HS256','typ':'JWT'})+'.'+enc({'role':'anon','iss':'supabase','iat':int(time.time()),'exp':int(time.time())+315360000})
  values['ANON_KEY']=text+'.'+base64.urlsafe_b64encode(hmac.digest(values['NATIVE_JWT_SECRET'].encode(),text.encode(),'sha256')).decode().rstrip('=')
  envfile.write_text(''.join(k+'='+v+'\n' for k,v in values.items()));envfile.chmod(0o600)
  gateway=STATE/'envoy.yaml';gateway.write_text((ROOT/'services/supabase/gateway.template.yaml').read_text().replace('@@ANON_KEY@@',values['ANON_KEY']));gateway.chmod(0o444)
 s.runtime_hash()
 if not s.GROUP.exists():run(['systemctl','set-property','--runtime',s.SLICE,'CPUQuota=100%','MemoryMax=4294967296','MemorySwapMax=0'])
 else:
  parent=s.parent_sample()
  if parent['cpu.max'].split()!=['100000','100000'] or int(parent['memory.max'])!=4*1024**3 or int(parent['memory.swap.max'])!=0:raise RuntimeError('Existing serving cgroup differs; no automatic budget changes')
 run(compose()+['config','--quiet'])

def ready():
 deadline=time.monotonic()+180
 while time.monotonic()<deadline:
  try:
   with urlopen('http://127.0.0.1:14000/health',timeout=5) as response:
    value=json.load(response)
    if response.status==200 and value.get('db')=='ok':return
  except (OSError,ValueError):pass
  time.sleep(1)
 raise RuntimeError('Native application did not become storage-ready')

def up(log=None):
 initialize();run(compose()+['up','--wait','--wait-timeout','180','db'],log)
 source=hashlib.sha256((ROOT/'services/supabase/schema.sql').read_bytes()).hexdigest();marker=STATE/'schema-source.sha256'
 if not marker.exists() or marker.read_text().strip()!=source:
  run(compose()+['stop','gateway','auth','rest','functions'],log)
  with (ROOT/'services/supabase/schema.sql').open() as sql:run(['docker','exec','-i',s.PROJECT+'-db-1','psql','-X','-v','ON_ERROR_STOP=1','-U','supabase_admin','-d','postgres'],log,stdin=sql)
  marker.write_text(source+'\n')
 run(compose()+['up','--wait','--wait-timeout','180',*s.SERVICES],log);ready();s.profile()

def tools(script,log=None,name='tools'):
 # Secret values are sourced inside the trusted correctness container, never argv.
 return run(compose()+['run','--rm','--name',s.PROJECT+'-'+name,'tools','bash','-euc','set -a; source /state/stack.env; export JWT_SECRET="$COMPAT_JWT_SECRET" PYTHONDONTWRITEBYTECODE=1; '+script],log)

def seed(log=None):
 if not (ROOT/'.state/seed/tokens.json').exists():tools('node seed/generate.mjs /seed',log,'seed')
 else:
  for table in ['users','posts','likes']:
   if not (ROOT/'.state/seed'/f'{table}.tsv').is_file():raise RuntimeError('Incomplete existing canonical seed; refusing silent token rotation')

def reset(log=None):
 require_native();ownership();s.profile();seed(log)
 run(compose()+['stop','gateway','auth','rest','functions'],log)
 run(['python3','scripts/import_postgres.py','.state/seed','--manifest',str(STATE/'dataset.json')],log)
 run(compose()+['up','--wait','--wait-timeout','180',*s.SERVICES],log);ready();s.profile()

def full_test():
 import supabase_benchmark as bench
 up();seed();logfile=STATE/'correctness.log'
 with logfile.open('w') as log:
  reset(log)
  initial=s.deployment_attestation();frozen=bench.inputs(initial)
  tools('node --version; python3 --version; openssl version; bash test/test.sh "$BASE_URL"; python3 test/baas/test_api.py; python3 test/baas/supabase_native.py; python3 test/baas/test_seed.py; node --test services/supabase/functions/feed/contract.test.mjs; node --test bench/baas-contract.test.mjs',log,'correctness')
  env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
  for file in ['test_benchmark.py','test_isolation.py','test_supabase_harness.py','test_supabase_config.py','test_supabase_import.py','test_supabase_budget.py','test_supabase_evidence.py']:
   run(['python3','test/baas/'+file],log,env=env)
  run(['python3','-m','unittest','discover','-s','test','-p','test_gitignore.py','-v'],log,env=env)
  tools('python3 test/baas/supabase_lifecycle.py prepare',log,'persist-prepare')
  before=s.targets();run(compose()+['stop','db'],log)
  try:tools('python3 test/baas/supabase_lifecycle.py unavailable',log,'storage-failure')
  finally:run(compose()+['up','--wait','--wait-timeout','180','db'],log);ready()
  run(compose()+['restart','auth','rest','functions','gateway'],log);run(compose()+['up','--wait','--wait-timeout','180',*s.SERVICES],log);ready()
  tools('python3 test/baas/supabase_lifecycle.py verify',log,'persist-verify')
  after=s.deployment_attestation()
  if any(before[role]['State']['StartedAt']==after['serving_profile']['targets'][role]['State']['StartedAt'] for role in s.SERVICES):raise RuntimeError('Actual restart proof did not restart every serving process')
  if frozen!=bench.inputs(after):raise RuntimeError('Source/image/runtime/schema/host/token inputs changed during the full correctness suite')
  log.write('FULL_SUPABASE_CORRECTNESS_GATE_PASSED\n')
 att={'inputs':frozen,'deployment':after,'log_sha256':hashlib.sha256(logfile.read_bytes()).hexdigest(),'finished_utc':datetime.now(timezone.utc).isoformat(),'auth_scope':'Compatibility users/JWTs; not native signup/login/session throughput','proofs':['42 inherited exact-byte checks','6 concurrency/auth/Unicode API tests','5 native RPC/permission/gateway/encoding tests','seed privacy regression','5 Edge contract unit tests','4 workload/scoring tests','24 original benchmark tests','3 original isolation tests','Supabase harness/config/import/budget/frozen-evidence regressions','3 repository artifact-policy regressions','native storage failure/recovery and real five-process restart persistence']}
 (STATE/'correctness-manifest.json').write_text(json.dumps(att,indent=2)+'\n');print('FULL_SUPABASE_CORRECTNESS_GATE_PASSED',flush=True)

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['build','up','wait-ready','seed','reset','test','bench','search','down']);parser.add_argument('--vus',type=int,default=2500);parser.add_argument('--smoke',action='store_true');parser.add_argument('--max-vus',type=int,default=20000);parser.add_argument('--max-attempts',type=int,default=12);args=parser.parse_args();require_native();STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
 with (STATE/'lifecycle.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if args.command=='build':
   initialize()
   for pin in s.PINS['images'].values():run(['docker','pull','--platform','linux/amd64',pin['pinned']])
  elif args.command=='up':up()
  elif args.command=='wait-ready':ready();s.profile()
  elif args.command=='seed':seed()
  elif args.command=='reset':reset()
  elif args.command=='test':full_test()
  elif args.command in ['bench','search']:
   import supabase_benchmark as bench
   if not 1<=args.vus<=20000 or not 1<=args.max_vus<=20000 or not 4<=args.max_attempts<=12:parser.error('Stay within the approved 20,000-VU / 12-attempt bounds')
   if args.command=='bench':raise SystemExit(0 if bench.attempt(args.vus,smoke=args.smoke)[0]=='pass' else 1)
   raise SystemExit(b.campaign(args,'standard',attempt_runner=bench.attempt,results=bench.RESULTS,campaign_file=STATE/'campaign.json'))
  elif args.command=='down':ownership();run(compose()+['stop',*s.SERVICES]);print('Only benchmark serving containers stopped; all volumes/evidence retained.')
if __name__=='__main__':main()
