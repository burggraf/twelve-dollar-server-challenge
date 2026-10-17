#!/usr/bin/env python3
"""Exact-owned native Nhost lifecycle. No initialization/secret rotation/adoption by name."""
import argparse,hashlib,json,os,platform,re,socket,subprocess,time,uuid
from pathlib import Path
import nhost_profile as s
STOP_ORDER=('adapter','auth','graphql','db')
TOOLS_TIMEOUT=600
TOOLS_IMAGE='sha256:7b35188938d0b5a3b50178d6a85e776b09db24314a2643c64b95b3da49f4f9f2'
def stop_owned(identities,evidence,roles=STOP_ORDER):
 if set(identities)!=set(s.SERVICES) or any(type(cid) is not str or not re.fullmatch('[a-f0-9]{64}',cid) for cid in identities.values()) or len(set(identities.values()))!=4 or not set(roles)<=set(STOP_ORDER):raise ValueError('Exact Nhost stop scope required')
 failures=[];terminal={}
 try:evidence.mkdir(mode=0o700)
 except BaseException as error:failures.append('evidence directory: '+type(error).__name__)
 def owned(role):
  cid=identities[role];item=json.loads(subprocess.check_output(['docker','inspect',cid],stderr=subprocess.STDOUT,timeout=10))[0]
  labels=item['Config']['Labels']
  if item['Id']!=cid or labels.get('com.docker.compose.project')!=s.PROJECT or labels.get('com.docker.compose.service')!=role:raise ValueError('Stop ownership changed')
  return item
 for role in STOP_ORDER:
  if role not in roles:continue
  output=b''
  try:
   owned(role)
   result=subprocess.run(['docker','stop','--time',str({'adapter':20,'auth':30,'graphql':90,'db':60}[role]),identities[role]],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True,timeout={'adapter':35,'auth':45,'graphql':105,'db':75}[role]);output=result.stdout or b''
  except BaseException as error:failures.append(role+' stop: '+type(error).__name__);output=getattr(error,'stdout',None) or b''
  try:(evidence/(role+'-stop-original.log')).write_bytes(output)
  except BaseException as error:failures.append(role+' stop capture: '+type(error).__name__)
 for role,cid in identities.items():
  try:
   item=owned(role);state=item['State']
   terminal[role]={'state':state['Status'],'running':state['Running'],'pid':state['Pid'],'exit_code':state['ExitCode'],'oom':state['OOMKilled'],'restarts':item['RestartCount']}
   if state['OOMKilled'] or item['RestartCount'] or (role in roles and (state['Running'] or state['Pid'])):failures.append(role+' terminal failed')
   if role in roles and state['ExitCode'] not in {'adapter':(0,),'auth':(0,2),'graphql':(0,137),'db':(0,)}[role]:failures.append(role+' unexpected exit code')
   (evidence/(role+'-inspect-PRIVATE.json')).write_text(json.dumps(item,indent=2)+'\n')
  except BaseException as error:
   failures.append(role+' inspect: '+type(error).__name__);continue
  try:
   with (evidence/(role+'-complete-PRIVATE.log')).open('xb') as stream:subprocess.run(['docker','logs','--timestamps',cid],stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=120)
  except BaseException as error:failures.append(role+' logs: '+type(error).__name__)
 all_stopped=len(terminal)==4 and all(not item['running'] and item['pid']==0 for item in terminal.values())
 report={'terminal':terminal,'failures':failures,'all_stopped':all_stopped,'full_stack_clean_stop':all_stopped and all(item['state']=='exited' and item['exit_code']==0 and not item['oom'] and item['restarts']==0 for item in terminal.values())}
 (evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 return report

def protected():
 if platform.system()!='Linux' or platform.machine()!='x86_64' or socket.getfqdn()!='claudius.azabab.com':raise RuntimeError('Designated native AMD64 host only')
 if json.loads((s.ROOT.parent/'.benchmark-owned').read_text())['project']!=s.PROJECT:raise RuntimeError('Workspace ownership differs')
 if s.capture(['git','-C',str(s.ROOT),'rev-parse','HEAD'],10).strip()!='161af0ef353aa6842b15046090a9e1af0068632b':raise RuntimeError('Native immutable source baseline differs')
 if hashlib.sha256(Path('/proc/sys/kernel/random/boot_id').read_bytes()).hexdigest()!='77d80e459277950c488b0768305effffb0a9bf8682ca0ec55bf6aab84baa982c':raise RuntimeError('Protected boot changed')
 if Path('/proc/812/exe').resolve()!=Path('/opt/trailbase-server/bin/trail') or Path('/proc/812/stat').read_text().rsplit(')',1)[1].split()[19]!='759' or 'pid=812' not in s.capture(['ss','-H','-ltnp','sport = :4000'],10):raise RuntimeError('Protected production listener changed')

def snapshot():
 names=json.loads((s.ROOT.parent/'setup-evidence/persistent-services-before.json').read_text())
 return {name:s.capture(['systemctl','show',name,'-p','MainPID','-p','ExecMainStartTimestampMonotonic','-p','NRestarts','-p','ActiveState','-p','SubState'],10) for name in names}
def compose():return ['docker','compose','--env-file',str(s.STATE/'stack.env'),'-p',s.PROJECT,'-f',str(s.ROOT/'services/nhost/compose.yaml'),'-f',str(s.ROOT/'services/nhost/compose.benchmark.yaml'),'--profile','app']
def lease():
 value=json.loads((s.STATE/'current-lease.json').read_text())
 if not re.fullmatch('[a-z0-9-]{1,48}',value['phase']):raise RuntimeError('Invalid lease phase')
 return value
def evidence():return s.ROOT.parent/'setup-evidence'/('nhost-'+lease()['phase']+'-native-private')
def command(argv,label,timeout=210):
 directory=evidence();path=directory/(label+'-'+str(time.monotonic_ns())+'-original-PRIVATE.log')
 with path.open('xb') as stream:subprocess.run(argv,cwd=s.ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=timeout)
 return path

def claim(phase):
 protected()
 if not re.fullmatch('[a-z0-9-]{1,48}',phase):raise ValueError('Invalid exclusive phase')
 if (s.STATE/'current-lease.json').exists():
  previous=evidence();closed=json.loads((previous/'closure.json').read_text())
  if not closed['all_stopped'] or closed['failures']:raise RuntimeError('Prior phase not successfully closed; no retry/adoption')
  if subprocess.run(['systemctl','is-active','--quiet',lease()['timer']]).returncode==0:raise RuntimeError('Prior deadline still active')
 history=s.ROOT.parent/'setup-evidence/application-integration-v1-native-private';ids=json.loads((history/'identities.json').read_text())
 expected={'db':'01006a40bffb52b75c0f4ac7f209ce6e4e79de6c6c999796aae3c058570cd2f7','graphql':'0b4e613ab6f99cee1cc1cdf20f47b42851d05e30f658d857cf1c3cf5e88d36ee','auth':'7d36c386c99dbfc933353758ce54c268d6ce58753fe88b43eb5e0ccc4ed15d70'}
 if set(ids)!=set(s.SERVICES) or any(ids[role]!=cid for role,cid in expected.items()):raise RuntimeError('Historical exact IDs differ')
 if set(s.capture(['docker','ps','-aq','--no-trunc','--filter','label=com.docker.compose.project='+s.PROJECT],10).split())!=set(ids.values()):raise RuntimeError('Namespace identity set differs')
 containers={}
 for role,cid in ids.items():
  item=json.loads(s.capture(['docker','inspect',cid],10))[0];old=json.loads((history/'finish'/(role+'-before-PRIVATE.json')).read_text())
  if item['Id']!=cid or item['Config']!=old['Config'] or item['HostConfig']!=old['HostConfig'] or item['Image']!=old['Image']:raise RuntimeError('Retained configuration differs')
  state=item['State']
  if state['Running'] or state['Pid'] or state['OOMKilled'] or item['RestartCount'] or state['Status']!='exited' or state['ExitCode'] not in {'db':(0,),'adapter':(0,),'auth':(0,2),'graphql':(0,137)}[role]:raise RuntimeError('Stopped baseline differs; no recovery start')
  containers[role]=item
 for cid in s.capture(['docker','ps','-q','--filter','label=com.docker.compose.project'],10).split():
  item=json.loads(s.capture(['docker','inspect',cid],10))[0]
  if item['Config']['Labels']['com.docker.compose.project'].startswith('baas-'):raise RuntimeError('Another live BaaS workload')
 mem={key:int(value.split()[0])*1024 for key,value in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
 if os.cpu_count()!=4 or mem['MemTotal']!=16770064384 or mem['SwapTotal'] or mem['MemAvailable']<13*1024**3:raise RuntimeError('Insufficient/changed host headroom')
 parent=s.parent_sample()
 if parent['children'] or parent['cpu.max'].split()!=['100000','100000'] or int(parent['memory.max'])!=4294967296 or int(parent['memory.swap.max'])!=0:raise RuntimeError('Serving parent drift')
 if s.capture(['ss','-H','-ltn','sport = :14000'],10).strip() or (s.STATE/'stack.env').stat().st_mode&0o777!=0o600:raise RuntimeError('Listener/private input guard failed')
 s.runtime_hash();directory=s.ROOT.parent/'setup-evidence'/('nhost-'+phase+'-native-private');directory.mkdir(mode=0o700)
 own=s.STATE/'ownership-PRIVATE.json'
 if own.exists():
  old=json.loads(own.read_text())
  if old['identities']!=ids or any(old['containers'][role]['Config']!=containers[role]['Config'] or old['containers'][role]['HostConfig']!=containers[role]['HostConfig'] for role in ids):raise RuntimeError('Existing immutable ownership differs')
 else:own.write_text(json.dumps({'identities':ids,'containers':containers},indent=2)+'\n');own.chmod(0o600)
 timer='tds-nhost-'+phase+'-deadline.timer';record={'phase':phase,'monotonic_start':time.monotonic(),'deadline_seconds':2700,'timer':timer,'identities':ids,'protected_boot_sha256':'77d80e459277950c488b0768305effffb0a9bf8682ca0ec55bf6aab84baa982c','runtime_sha256':s.runtime_hash(),'app_sha256':s.app_hash(),'verification_sha256':s.verification_hash()}
 (directory/'claim.json').write_text(json.dumps(record,indent=2)+'\n');(directory/'persistent-services-before-PRIVATE.json').write_text(json.dumps(snapshot(),indent=2)+'\n')
 (s.STATE/'current-lease.json').write_text(json.dumps(record)+'\n')
 command(['systemd-run','--quiet','--unit='+timer.removesuffix('.timer'),'--on-active=2700s','--timer-property=AccuracySec=1s','-p','CPUQuota=100%','-p','MemoryMax=536870912','-p','MemorySwapMax=0','-p','RuntimeMaxSec=600','-p','WorkingDirectory='+str(s.ROOT),'-p','Environment=DOCKER_CONFIG=/opt/twelve-dollar-baas-benchmark-16g/.docker','python3','-B',str(s.ROOT/'scripts/nhost.py'),'deadline',phase],'deadline-arm')
 print('NHOST_EXCLUSIVE_QUALIFICATION_LEASE_ARMED; no serving start yet',flush=True)

def active():
 protected();value=lease()
 if time.monotonic()-value['monotonic_start']>=value['deadline_seconds']-600:raise RuntimeError('Lease reserve exhausted; no new serving action')
 if s.runtime_hash()!=value['runtime_sha256'] or s.app_hash()!=value['app_sha256'] or s.verification_hash()!=value['verification_sha256'] or subprocess.run(['systemctl','is-active','--quiet',value['timer']]).returncode:raise RuntimeError('Source/runtime inputs/deadline changed')
 if json.loads((evidence()/'claim.json').read_text())!=value:raise RuntimeError('Lease pointer differs')
 for role in s.SERVICES:s.raw(role)
 return value

def up(roles=s.SERVICES):
 for role in roles:
  active();command(compose()+['up','--no-recreate','--no-deps','--wait','--wait-timeout','180',role],'up-'+role)
 for role in s.SERVICES:
  item=s.raw(role)
  if role in roles and (not item['State']['Running'] or item['State'].get('Health',{}).get('Status')!='healthy' or item['State']['OOMKilled'] or item['RestartCount']):raise RuntimeError('Started role unhealthy')
 parent=s.parent_sample()
 if parent['cpu.max'].split()!=['100000','100000'] or int(parent['memory.max'])!=4294967296 or int(parent['memory.swap.max'])!=0:raise RuntimeError('Actual serving parent budget drift')
 expected=set()
 for role in s.SERVICES:
  item=s.raw(role);pid=item['State']['Pid']
  if not pid:continue
  expected.add('docker-'+item['Id']+'.scope')
  if Path(f'/proc/{pid}/cgroup').read_text().strip()!=f'0::/{s.SLICE}/docker-{item["Id"]}.scope':raise RuntimeError('Actual serving process escaped aggregate parent')
  group=s.GROUP/('docker-'+item['Id']+'.scope')
  if int((group/'memory.max').read_text())!=s.MEMORY[role] or int((group/'memory.swap.max').read_text())!=0:raise RuntimeError('Actual child memory/swap drift')
 if set(parent['children'])!=expected:raise RuntimeError('Unexpected serving parent child')
 print('NHOST_EXACT_OWNED_ROLES_HEALTHY '+','.join(roles),flush=True)

def reset(manifest):
 import import_nhost
 active();s.profile();before={'schema':s.schema_state(),'metadata':s.metadata_state()}
 (evidence()/('before-reset-'+str(time.monotonic_ns())+'-PRIVATE.json')).write_text(json.dumps(before,indent=2)+'\n')
 stopped=stop_owned(s.identities(),evidence()/('api-stop-'+str(time.monotonic_ns())),roles=STOP_ORDER[:-1])
 if stopped['failures']:raise RuntimeError('API stop failed; no COPY permitted')
 value=import_nhost.reset(s.ROOT/'.state/seed',manifest,s.identities())
 if s.schema_state()['sha256']!=before['schema']['sha256']:raise RuntimeError('Catalog changed during reset; no API restart')
 up();s.profile()
 if s.metadata_state()['sha256']!=before['metadata']['sha256']:raise RuntimeError('Native permission metadata changed during reset')
 return value

def down(phase=None):
 value=lease()
 if phase is not None and value['phase']!=phase:raise RuntimeError('Deadline phase does not own current lease')
 directory=evidence();report=stop_owned(s.identities(),directory/('stop-'+str(time.monotonic_ns())))
 report['remaining_untimed_tools']=s.capture(['docker','ps','-aq','--no-trunc','--filter','label=com.docker.compose.project='+s.PROJECT,'--filter','label=com.docker.compose.service=tools'],10).split()
 if report['remaining_untimed_tools']:report['all_stopped']=False;report['failures'].append('Owned untimed tools remain; independent deadline retained')
 if report['all_stopped']:
  command(['systemctl','stop',value['timer']],'deadline-cancel',30)
  before=json.loads((directory/'persistent-services-before-PRIVATE.json').read_text());after=snapshot();(directory/'persistent-services-after-PRIVATE.json').write_text(json.dumps(after,indent=2)+'\n')
  report['changed_persistent_services']=[name for name in before if before[name]!=after[name]]
  if report['changed_persistent_services']:report['failures'].append('Persistent-service identity continuity failed')
  protected()
  if s.capture(['ss','-H','-ltn','sport = :14000'],10).strip():report['failures'].append('Benchmark listener remains')
 (directory/'closure.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report),flush=True)
 if not report['all_stopped'] or report['failures']:raise RuntimeError('Failed terminal checks; originals retained, no implicit retry')
 return report

def tools(script,label):
 active();(s.ROOT/'.state/seed').mkdir(mode=0o700,exist_ok=True);nonce=uuid.uuid4().hex;name=s.PROJECT+'-'+label+'-'+nonce;directory=evidence()
 if s.capture(['docker','ps','-aq','--filter','name=^'+name+'$'],10).strip():raise RuntimeError('Untimed tools name occupied; no adoption')
 try:
  return command(compose()+['run','--rm','--no-deps','--name',name,'--label','benchmark.nhost-tools='+nonce,'tools','timeout','--signal=TERM','--kill-after=5s',str(TOOLS_TIMEOUT)+'s','bash','-euc','set -a; source /state/stack.env; export JWT_SECRET="$COMPAT_JWT_SECRET" PYTHONDONTWRITEBYTECODE=1; '+script],label,TOOLS_TIMEOUT+10)
 finally:
  probe=subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=10)
  if probe.returncode==0:
   item=json.loads(probe.stdout)[0];labels=item['Config']['Labels']
   if not re.fullmatch('[a-f0-9]{64}',item['Id']) or item['Image']!=TOOLS_IMAGE or labels.get('com.docker.compose.project')!=s.PROJECT or labels.get('com.docker.compose.service')!='tools' or labels.get('benchmark.nhost-tools')!=nonce:raise RuntimeError('Untimed tools identity/creator/image drift; no removal by name')
   (directory/(nonce+'-tools-before-cleanup-PRIVATE.json')).write_text(json.dumps(item,indent=2)+'\n')
   subprocess.run(['docker','rm','-f',item['Id']],capture_output=True,check=True,timeout=30)
  elif s.capture(['docker','ps','-aq','--no-trunc','--filter','name=^'+name+'$'],10).strip():raise RuntimeError('Untimed tools termination could not be proved; retain deadline')
def seed():
 active();path=s.ROOT/'.state/seed'
 if (path/'tokens.json').exists():
  if not all((path/(name+'.tsv')).is_file() for name in ['users','posts','likes']):raise RuntimeError('Incomplete seed; no token rotation')
 else:tools('node seed/generate.mjs /seed','canonical-seed')
 print('NHOST_NATIVE_CANONICAL_SEED_PRESENT',flush=True)

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['claim','db','up','seed','down','deadline']);parser.add_argument('phase',nargs='?');args=parser.parse_args()
 if args.command=='claim':claim(args.phase)
 elif args.command=='deadline':down(args.phase)
 elif args.command=='down':down()
 else:
  try:
   if args.command=='db':up(('db',))
   elif args.command=='up':up();s.profile()
   elif args.command=='seed':seed()
  except BaseException:
   try:down()
   except BaseException as cleanup_error:print('NHOST_CLEANUP_FAILED_DEADLINE_RETAINED '+type(cleanup_error).__name__,flush=True)
   raise
if __name__=='__main__':main()
