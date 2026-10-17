"""Nhost evidence/attempt adapter for the unchanged shared scoring protocol."""
import argparse,base64,csv,hashlib,hmac,json,shutil,subprocess,threading,time
import nhost_budget as budget
from datetime import datetime,timezone
from pathlib import Path
import benchmark as b
import nhost_profile as s
import nhost as control
ROOT=s.ROOT;STATE=s.STATE;RESULTS=ROOT/'results/nhost'/b.TRACK
K6_MANIFEST='sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656'
TOOLS_IMAGE='sha256:7b35188938d0b5a3b50178d6a85e776b09db24314a2643c64b95b3da49f4f9f2'
def target_issue(before,after):
 if set(before)!=set(s.SERVICES) or set(after)!=set(s.SERVICES):return 'required serving component set changed'
 for role in s.SERVICES:
  a,z=before[role],after[role];state=z['State']
  if not state.get('Running') or state.get('OOMKilled') or state.get('Health',{}).get('Status')!='healthy' or a['Id']!=z['Id'] or a['RestartCount']!=z['RestartCount'] or a['State']['StartedAt']!=state['StartedAt']:return 'serving stack OOM/exit/restart/unhealthy: '+role
 return None

def validate_correctness(attestation,current,log_sha256):
 if attestation.get('inputs')!=current or attestation.get('log_sha256')!=log_sha256:raise RuntimeError('Full qualification stale for current source/runtime/schema/metadata/images/host/tokens/tools/original log')
 return True

def token_hash():
 raw=(ROOT/'.state/seed/tokens.json').read_bytes();entries=json.loads(raw)
 if type(entries) is not list or len(entries)!=20000:raise RuntimeError('Expected exactly20,000 compatibility identities')
 key=s.runtime_values()['COMPAT_JWT_SECRET'].encode()
 decode=lambda text:json.loads(base64.urlsafe_b64decode(text+'='*(-len(text)%4)))
 with (ROOT/'.state/seed/users.tsv').open(encoding='utf-8',newline='') as stream:
  users=csv.reader(stream,delimiter='\t',quoting=csv.QUOTE_NONE)
  for index,entry in enumerate(entries,1):
   try:
    user=next(users);head,payload,signature=entry['token'].split('.');header=decode(head);claims=decode(payload)
    expected=base64.urlsafe_b64encode(hmac.digest(key,(head+'.'+payload).encode(),'sha256')).decode().rstrip('=')
    valid=header=={'alg':'HS256','typ':'JWT'} and type(entry['id']) is int and entry['id']==index and user[0]==str(index) and entry['username']==user[1] and claims['sub']==str(index) and claims['username']==user[1] and type(claims['exp']) is int and claims['exp']>time.time()+3600 and hmac.compare_digest(signature,expected)
   except (KeyError,TypeError,ValueError,IndexError,StopIteration):valid=False
   if not valid:raise RuntimeError('Compatibility fixture invalid at identity '+str(index))
 return hashlib.sha256(raw).hexdigest()

def inputs(attestation=None):
 import nhost_continuity
 a=s.deployment_attestation() if attestation is None else attestation
 return {'app':a['app_source_sha256'],'verification':a['verification_source_sha256'],'runtime':a['runtime_inputs_sha256'],'schema':a['schema']['sha256'],'metadata':a['metadata_sha256'],'images':a['images'],'host':{'identity_sha256':a['host_identity_sha256'],'native':nhost_continuity.host()},'tokens':token_hash(),'physical_attempt_policy':budget.effective_policy(),'tools_image':b.capture(['docker','image','inspect',TOOLS_IMAGE,'--format','{{.Id}} {{.Os}}/{{.Architecture}}']).strip()}

def measurement_clock(summary,outcome):
 try:return b.scenario_started(summary)
 except ValueError:
  if outcome!='invalid':raise
  return None

def parent_oom(value):return int(dict(line.split() for line in value['memory.events'].splitlines()).get('oom_kill',0))

def monitor(stop,directory):
 names=[s.PROJECT+'-'+role+'-1' for role in s.SERVICES]+[b.LOAD];kernel=None
 with (directory/'resources.jsonl').open('x') as output:
  while not stop.is_set():
   record={'time':time.time()}
   try:
    result=subprocess.run(['docker','stats','--no-stream','--format','{{json .}}',*names],capture_output=True,text=True,timeout=12)
    record['docker_stats_exit_code']=result.returncode
    for line in result.stdout.splitlines():
     item=json.loads(line);record[item['Name']]=item
    if b.LOAD in record and kernel is None:
     item=json.loads(b.capture(['docker','inspect',b.LOAD]))[0];pid=item['State']['Pid']
     if pid:
      group=Path('/sys/fs/cgroup')/Path(f'/proc/{pid}/cgroup').read_text().strip().split('::',1)[1].lstrip('/')
      kernel={key:(group/key).read_text() for key in ['cpu.max','memory.max','memory.swap.max']}
    if kernel:record['load_kernel_cgroup']=kernel
    record['target_stack']=s.parent_sample();record.update(b.host_sample())
   except Exception as error:record['monitor_error']=type(error).__name__
   output.write(json.dumps(record)+'\n');output.flush()
   if 'monitor_error' in record:return
   stop.wait(3)

def attempt(vus,tier='standard',smoke=False):
 if type(vus) is not int or not 1<=vus<=20000 or tier!='standard' or type(smoke) is not bool:raise ValueError('Native standard profile, Boolean smoke and1..20,000 VUs required')
 if (b.PROJECT,b.PLATFORM,b.RUNNER_PROFILE)!=(s.PROJECT,'linux/amd64','k6-2cpu-8g-v3'):raise RuntimeError('Wrong native Nhost project/platform/runner namespace')
 control.active();correctness=STATE/'correctness.log';att=json.loads((STATE/'correctness-manifest.json').read_text());log_sha=hashlib.sha256(correctness.read_bytes()).hexdigest()
 validate_correctness(att,inputs(),log_sha)
 reservation=budget.require(vus,smoke,hashlib.sha256((STATE/'correctness-manifest.json').read_bytes()).hexdigest())
 total=int(b.capture(['docker','info','--format','{{.MemTotal}}']).strip());cpus=int(b.capture(['docker','info','--format','{{.NCPU}}']).strip());b.require_vm_headroom(tier,total,cpus)
 if b.capture(['docker','ps','-aq','--filter','name=^'+b.LOAD+'$']).strip():raise RuntimeError('Load name occupied before creation; no adoption/cleanup')
 run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+f'-standard-{vus}vu-{b.RUNNER_PROFILE}'+('-smoke' if smoke else '')
 local=STATE/'runs'/run_id;local.mkdir(parents=True);destination=RESULTS/run_id;destination.mkdir(parents=True)
 import nhost_continuity as continuity
 quiet=continuity.quiet(local/'pre-load-quiet')
 dataset=control.evidence()/(run_id+'-dataset.json');control.reset(dataset)
 deployed=s.deployment_attestation();current=inputs(deployed);validate_correctness(att,current,hashlib.sha256(correctness.read_bytes()).hexdigest());before=deployed['serving_profile']
 b.snapshot(destination,service='nhost')
 for name,source in [('dataset.json',dataset),('correctness.log',correctness),('correctness-manifest.json',STATE/'correctness-manifest.json')]:shutil.copyfile(source,destination/name)
 value=control.active();limit=180 if smoke else 900
 if value['deadline_seconds']-(time.monotonic()-value['monotonic_start'])<limit+600:raise RuntimeError('Insufficient lease reserve for bounded load and cleanup')
 context=continuity.begin();stop=threading.Event();thread=threading.Thread(target=monitor,args=(stop,local),daemon=True);thread.start();load=None;exit_code=255
 try:
  argv=control.compose()+['run','-T','--no-deps','--name',b.LOAD,'-e',f'VUS={vus}','-e',f'SMOKE={int(smoke)}','-e','TOKENS=/tokens.json','-e',f'SUMMARY=/runs/{run_id}/k6-summary.json','k6','run','--quiet','--out',f'json=/runs/{run_id}/samples.json.gz','/work/bench/baas.mjs']
  with (local/'k6.log').open('x') as output:
   try:exit_code=subprocess.run(argv,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,timeout=limit).returncode
   except subprocess.TimeoutExpired:exit_code=255
 finally:
  stop.set();thread.join(timeout=30)
  probe=subprocess.run(['docker','inspect',b.LOAD],capture_output=True,text=True,timeout=10)
  if probe.returncode==0:
   item=json.loads(probe.stdout)[0]
   if item['Config']['Labels'].get('com.docker.compose.project')!=s.PROJECT or item['Config']['Labels'].get('com.docker.compose.service')!='k6':raise RuntimeError('Runner ownership changed; refusing removal')
   load=b.inspect(item['Id']);subprocess.run(['docker','rm','-f',item['Id']],capture_output=True,check=True,timeout=30)
 if thread.is_alive():raise RuntimeError('Resource monitor failed to stop')
 summary=json.loads((local/'k6-summary.json').read_text()) if (local/'k6-summary.json').exists() else {};outcome,reason=b.measurement_verdict(summary,exit_code,local,smoke,load)
 records=[json.loads(line) for line in (local/'resources.jsonl').read_text().splitlines()];kernels=[record['load_kernel_cgroup'] for record in records if 'load_kernel_cgroup' in record]
 if outcome!='invalid':
  if not kernels or any(k['cpu.max'].split()!=['200000','100000'] or int(k['memory.max'])!=8589934592 or int(k['memory.swap.max'])!=0 for k in kernels):outcome,reason='invalid','missing/incorrect actual runner kernel budget'
  elif load['image_manifest_digest']!=K6_MANIFEST or load['RestartCount']:outcome,reason='invalid','runner native manifest/restart drift'
 after_targets=s.targets();issue=target_issue(before['targets'],after_targets)
 if outcome!='invalid' and issue:outcome,reason='fail',issue
 try:
  after=s.profile()
  if parent_oom(after['parent'])>parent_oom(before['parent']) and outcome!='invalid':outcome,reason='fail','aggregate serving cgroup OOM kill'
 except (RuntimeError,FileNotFoundError) as error:
  after={'targets':after_targets,'parent':s.parent_sample()}
  if outcome!='invalid' and not issue:outcome,reason='invalid',str(error)
 if outcome!='invalid':
  started=b.scenario_started(summary);begin,end=(5,25) if smoke else (210,510);hold=[record for record in records if started+begin<=record['time']<started+end]
  names={s.PROJECT+'-'+role+'-1' for role in s.SERVICES}
  if any('target_stack' not in record or (not issue and not names<=set(record)) for record in hold):outcome,reason='invalid','incomplete aggregate/component hold monitoring'
 for record in records:
  parent=record.get('target_stack')
  if outcome!='invalid' and parent and any(parent[key].strip()!=before['parent'][key].strip() for key in ['cpu.max','memory.max','memory.swap.max']):outcome,reason='invalid','serving kernel limits changed during monitoring'
 images={role:{'manifest':item['image_manifest_digest'],'platform':item['platform']} for role,item in after_targets.items()}
 schema_changed=not issue and s.schema_state()['sha256']!=current['schema'];metadata_changed=not issue and s.metadata_state()['sha256']!=current['metadata']
 if outcome!='invalid' and (s.app_hash()!=current['app'] or s.verification_hash()!=current['verification'] or s.runtime_hash()!=current['runtime'] or images!=current['images'] or schema_changed or metadata_changed or token_hash()!=current['tokens']):outcome,reason='invalid','frozen source/runtime/schema/metadata/images/token inputs changed'
 try:continuous=continuity.finish(context,local/'continuity')
 except RuntimeError as error:
  path=local/'continuity/summary.json';continuous=json.loads(path.read_text()) if path.exists() else {'valid':False,'reason':str(error)}
  if outcome!='invalid':outcome,reason='invalid','persistent-service/host continuity failed: '+str(error)
 manifest={'service':'nhost','upstream_commit':s.PINS['source_commit'],'versions':s.PINS,'tier':tier,'vus':vus,'mode':'smoke' if smoke else 'capacity','deployment_track':b.TRACK,'platform':b.PLATFORM,'compose_project':s.PROJECT,'runner_profile':b.RUNNER_PROFILE,'runner_limits':b.RUNNER_LIMITS,'aggregate_limits':{'cpus':1,'memory_bytes':4294967296,'swap_bytes':0},'inputs':current,'target_before':before,'target_after':after,'schema_before':deployed['schema'],'load_after':load,'k6_exit_code':exit_code,'result':outcome,'reason':reason,'continuity':continuous,'pre_load_quiet':quiet,'physical_attempt':{'policy':budget.effective_policy(),'reservation':reservation},'scenario_started_epoch':measurement_clock(summary,outcome),'git_commit':b.capture(['git','rev-parse','HEAD']).strip(),'git_status':b.capture(['git','status','--porcelain']),'host':b.capture(['uname','-sm']),'host_memory_cpu':Path('/proc/meminfo').read_text()+Path('/proc/cpuinfo').read_text(),'docker':b.capture(['docker','version','--format','Client={{.Client.Version}} Server={{.Server.Version}}']),'vm_cpu_count':cpus,'vm_os_reserve_cpus':1,'vm_os_reserve_bytes':1073741824,'finished_utc':datetime.now(timezone.utc).isoformat(),'auth':'Per-write compatibility HS256 verification and fresh restricted native JWT; native Auth measured but signup/login throughput not measured','path':'k6 -> measured HTTP adapter -> packaged Hasura GraphQL -> tracked native SQL transaction -> PostgreSQL','cost':'Shared VPS; price/region unknown; not dedicated-$12 or cloud-equivalent proof'}
 for path in local.iterdir():
  if path.is_file():shutil.copyfile(path,destination/path.name)
 metrics=summary.get('metrics',{});values=lambda name:metrics.get(name+'{phase:hold}',{}).get('values',{});latency=values('http_req_duration');count=values('http_reqs').get('count',0)
 compact={'outcome':outcome,'reason':reason,'vus':vus,'tier':tier,'mode':manifest['mode'],'runner_profile':b.RUNNER_PROFILE,'deployment_track':b.TRACK,'platform':b.PLATFORM,'hold_requests':count,'hold_rps':count/(20 if smoke else 300),'latency_ms':latency,'request_errors':values('request_errors'),'schema_errors':values('schema_errors')}
 (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(destination/'summary.json').write_text(json.dumps(compact,indent=2)+'\n')
 (destination/'report.md').write_text(f'''Tested software and VPS slice
=============================

Nhost GraphQL + measured HTTP adapter, standard shared-host slice, {vus} VUs ({manifest['mode']}).
Outcome **{outcome}**: {reason}. One attempt, NOT a maximum-capacity claim.

Four serving components (PostgreSQL, Hasura GraphQL, native Auth, adapter) share one kernel-enforced1CPU/4GiB/no-swap parent. Separate native k6 runner:2CPU/8GiB/no-swap, {b.RUNNER_PROFILE}.
Compatibility authentication is measured; native signup/login/session throughput is not. No adapter DB driver, response/count/JWT-verification cache or development Functions simulator. The disclosed packaged serving subset is not a cloud/default-whole-platform equivalence claim.

Hold requests {count}; requests/s {compact['hold_rps']}; unrounded latency/error observations: summary.json and original k6-summary.json. {'Short calibration only, unscored.' if smoke else 'Full300-second scored hold; capacity needs bounded search and independent confirmations.'}
Raw start-tagged endpoint samples: samples.json.gz. Aggregate/component/runner/host metrics: resources.jsonl. Continuity, identities, actual budgets and source/runtime/schema/metadata/image/token fingerprints: manifest.json. Canonical dataset/full frozen qualification: dataset.json, correctness.log and correctness-manifest.json.
Reproduction overlay source.tar.gz and working-tree.patch bind the recorded base commit; verify SHA256SUMS. Native private runtime inputs, JWT fixtures and pre-reset database dumps are deliberately excluded.
Shared VPS price/region unknown. No cost/request, dedicated-$12 or power-loss certification claim. Stock GraphQL137(nonOOM)/Auth2 shutdown history is retained; do not call it a clean full-stack exit.
''')
 b.checksum_files(destination);print(json.dumps({'run':run_id,**compact}),flush=True);return outcome,str(destination.relative_to(ROOT))

def frozen_proof():
 if (b.PROJECT,b.PLATFORM,b.RUNNER_PROFILE)!=(s.PROJECT,'linux/amd64','k6-2cpu-8g-v3'):raise RuntimeError('Wrong native Nhost namespace/platform/runner')
 import nhost_continuity
 raw=(STATE/'correctness-manifest.json').read_bytes();proof=json.loads(raw)
 if proof['inputs']['host']['native']!=nhost_continuity.host():raise RuntimeError('Frozen host/kernel/Docker/package identity changed before lifecycle')
 if proof.get('original_contract_checks')!=42 or proof.get('node_tests')!=19 or proof.get('shared_contract_methods')!=6 or proof.get('native_methods')!=7 or proof.get('acknowledged_http_write_restart') is not True or proof.get('storage_failure_contract') is not True:raise RuntimeError('Complete original/shared/native/dependency/acknowledged-restart qualification required')
 if proof['log_sha256']!=hashlib.sha256((STATE/'correctness.log').read_bytes()).hexdigest():raise RuntimeError('Original full qualification log changed')
 for key,actual in [('app',s.app_hash()),('verification',s.verification_hash()),('runtime',s.runtime_hash()),('tokens',token_hash())]:
  if proof['inputs'].get(key)!=actual:raise RuntimeError('Full qualification stale before reservation/lifecycle: '+key)
 return hashlib.sha256(raw).hexdigest()

def run(vus,tier='standard',smoke=False):
 if type(vus) is not int or not 1<=vus<=20000 or tier!='standard' or type(smoke) is not bool:raise ValueError('Native standard1..20,000 VU profile required')
 proof=frozen_proof();ticket=budget.reserve(vus,smoke,proof);phase=f"attempt-{ticket['ordinal']:04}"
 try:
  control.claim(phase)
  try:
   control.up();result=attempt(vus,tier,smoke)
  finally:control.down()
 except BaseException:
  budget.finish(ticket,'invalid','setup-evidence/nhost-'+phase+'-native-private');raise
 budget.finish(ticket,*result);return result

class NextMeasurement(RuntimeError):pass

def campaign_step():
 # Replay ONLY immutable observations from this exact qualification through the
 # unchanged shared search. At most one new physical attempt per finite native job.
 proof=frozen_proof();smokes=budget.history(proof,True)
 if not all(any(item['vus']==vus and item['outcome']=='pass' for item in smokes) for vus in [25,100]):raise RuntimeError('Current-source25/100VU smokes must pass before full capacity search')
 history=budget.history(proof);used=0;measured=False
 directory=STATE/'campaign-replays';directory.mkdir(exist_ok=True);record=directory/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 def observation(vus,tier):
  nonlocal used,measured
  if used<len(history):
   item=history[used];used+=1
   if item['vus']!=vus:raise RuntimeError('Immutable observations disagree with unchanged shared search; no pooling/adoption')
   return item['outcome'],item['path']
  if measured:raise NextMeasurement(str(vus))
  measured=True;return run(vus,tier)
 args=argparse.Namespace(max_attempts=24,max_vus=20000)
 try:b.campaign(args,'standard',attempt_runner=observation,results=RESULTS,campaign_file=record)
 except NextMeasurement as pending:state={'status':'ready_for_next_attempt','next_vus':int(str(pending)),'one_physical_attempt_per_invocation':True}
 else:
  state=json.loads(record.read_text())
  if state['status']=='upper_budget_passed_no_maximum':
   if any(item['vus']!=20000 or item['outcome']!='pass' for item in history[used:]):raise RuntimeError('Nonpassing/invalid unconsumed ceiling confirmation; campaign paused, no retry or rolling-window certification')
   ceiling=[item for item in history if item['vus']==20000]
   if len(ceiling)>=4 and all(item['outcome']=='pass' for item in ceiling):state={'status':'confirmed_lower_bound_pending_human_review','lower_bound_vus':20000,'maximum_not_established':True}
   else:
    if not measured:
     outcome,_=run(20000)
     if outcome!='pass':raise RuntimeError('Upper-budget confirmation failed; no lower-bound certification')
    state={'status':'ready_for_next_attempt','next_vus':20000,'reason':'Need three independent ceiling confirmations, not a maximum claim'}
 (record.with_suffix('.step.json')).write_text(json.dumps({'proof_sha256':proof,**state},indent=2)+'\n');print('NHOST_CAMPAIGN_STEP',json.dumps(state),flush=True);return state

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--vus',type=int,default=25);parser.add_argument('--smoke',action='store_true');parser.add_argument('--campaign-step',action='store_true');args=parser.parse_args()
 if args.campaign_step:
  if args.smoke:parser.error('Smoke is not a capacity campaign')
  campaign_step()
 else:
  outcome,_=run(args.vus,smoke=args.smoke)
  if outcome!='pass':raise SystemExit(1)
if __name__=='__main__':main()
