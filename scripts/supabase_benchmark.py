"""Supabase attempts reuse the fixed scoring/search protocol, not TrailBase deployment assumptions."""
import base64,csv,hashlib,hmac,json,os,shutil,subprocess,threading,time
from datetime import datetime,timezone
from pathlib import Path
import benchmark as b
import supabase_profile as s
ROOT=s.ROOT;STATE=s.STATE;RESULTS=ROOT/'results/supabase'/b.TRACK
K6_MANIFEST='sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656'

def target_issue(before,after):
 if set(before)!=set(s.SERVICES) or set(after)!=set(s.SERVICES):return 'required serving component set changed'
 for role in s.SERVICES:
  a,z=before[role],after[role];state=z['State']
  if not state.get('Running') or state.get('OOMKilled') or state.get('Health',{}).get('Status','healthy')!='healthy' or a['Id']!=z['Id'] or a['RestartCount']!=z['RestartCount'] or a['State']['StartedAt']!=state['StartedAt']:return 'serving stack OOM/exit/restart/unhealthy: '+role
 return None

def validate_correctness(attestation,current,log_sha256):
 if attestation.get('inputs')!=current or attestation.get('log_sha256')!=log_sha256:raise RuntimeError('Full correctness evidence is stale for the current sources, images, runtime, schema, host, tokens or raw log')
 return True

def token_hash():
 raw=(ROOT/'.state/seed/tokens.json').read_bytes();entries=json.loads(raw)
 if len(entries)!=20000:raise RuntimeError('Expected 20,000 compatibility token identities')
 key=s.runtime_values()['COMPAT_JWT_SECRET'].encode()
 with (ROOT/'.state/seed/users.tsv').open(newline='') as stream:
  users=csv.reader(stream,delimiter='\t',quoting=csv.QUOTE_NONE)
  for index,(entry,user) in enumerate(zip(entries,users),1):
   try:
    head,payload,sig=entry['token'].split('.');claims=json.loads(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4)))
    expected=base64.urlsafe_b64encode(hmac.digest(key,(head+'.'+payload).encode(),'sha256')).decode().rstrip('=')
    valid=entry['id']==index and user[0]==str(index) and entry['username']==user[1] and claims['sub']==str(index) and claims['username']==user[1] and claims['exp']>time.time()+3600 and hmac.compare_digest(sig,expected)
   except (KeyError,TypeError,ValueError):valid=False
   if not valid:raise RuntimeError('Compatibility token fixture validation failed at identity '+str(index))
 return hashlib.sha256(raw).hexdigest()

def inputs(attestation=None):
 a=s.deployment_attestation() if attestation is None else attestation
 return {'app':a['app_source_sha256'],'verification':a['verification_source_sha256'],'runtime':a['runtime_inputs_sha256'],'schema':a['schema']['sha256'],'images':a['images'],'host':a['host_identity_sha256'],'tokens':token_hash(),'tools_image':b.capture(['docker','image','inspect','baas-trailbase-vps16-tools:0.1.0','--format','{{.Id}} {{.Os}}/{{.Architecture}}']).strip()}

def monitor(stop,destination):
 names=[s.PROJECT+'-'+role+'-1' for role in s.SERVICES]+[b.LOAD]
 kernel=None
 with (destination/'resources.jsonl').open('w') as stream:
  while not stop.is_set():
   record={'time':time.time()}
   try:
    result=subprocess.run(['docker','stats','--no-stream','--format','{{json .}}',*names],capture_output=True,text=True,timeout=12)
    for line in result.stdout.splitlines():
     item=json.loads(line);record[item['Name']]=item
    if b.LOAD in record and kernel is None:
     item=json.loads(b.capture(['docker','inspect',b.LOAD]))[0];pid=item['State']['Pid']
     if pid:
      group=Path('/sys/fs/cgroup')/Path(f'/proc/{pid}/cgroup').read_text().strip().split('::',1)[1].lstrip('/')
      kernel={key:(group/key).read_text() for key in ['cpu.max','memory.max','memory.swap.max']}
    if kernel:record['load_kernel_cgroup']=kernel
    try:record['target_stack']=s.parent_sample()
    except FileNotFoundError:record['target_stack_unavailable']=True
    record.update(b.host_sample())
   except Exception as error:record['monitor_error']=str(error)
   stream.write(json.dumps(record)+'\n');stream.flush()
   if 'monitor_error' in record:return
   stop.wait(3)

def parent_oom(value):return int(dict(line.split() for line in value['memory.events'].splitlines()).get('oom_kill',0))

def attempt(vus,tier='standard',smoke=False):
 from supabase import compose,reset,require_native
 require_native()
 if tier!='standard':raise ValueError('Supabase cohort requires standard 1-CPU/4-GiB aggregate profile')
 total=int(b.capture(['docker','info','--format','{{.MemTotal}}']).strip());cpus=int(b.capture(['docker','info','--format','{{.NCPU}}']).strip())
 b.require_vm_headroom(tier,total,cpus)
 if b.capture(['docker','ps','-aq','--filter','name=^'+b.LOAD+'$']).strip():raise RuntimeError('Owned load-container name is already occupied; inspect before cleanup')
 run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+f'-standard-{vus}vu-{b.RUNNER_PROFILE}'+('-smoke' if smoke else '')
 local=STATE/'runs'/run_id;local.mkdir(parents=True);destination=RESULTS/run_id;destination.mkdir(parents=True)
 b.snapshot(destination,service='supabase')
 correctness=STATE/'correctness.log';att=json.loads((STATE/'correctness-manifest.json').read_text())
 validate_correctness(att,inputs(),hashlib.sha256(correctness.read_bytes()).hexdigest())
 with (destination/'reset.log').open('w') as log:reset(log=log)
 deployed=s.deployment_attestation();current=inputs(deployed)
 validate_correctness(att,current,hashlib.sha256(correctness.read_bytes()).hexdigest())
 before=deployed['serving_profile'];manifest={'service':'supabase','upstream_commit':s.PINS['upstream_commit'],'versions':s.PINS,'tier':tier,'vus':vus,'mode':'smoke' if smoke else 'capacity','deployment_track':b.TRACK,'platform':b.PLATFORM,'compose_project':s.PROJECT,'runner_profile':b.RUNNER_PROFILE,'runner_limits':b.RUNNER_LIMITS,'aggregate_limits':{'cpus':1,'memory_bytes':4*1024**3,'swap_bytes':0},'inputs':current,'target_before':before,'schema_before':deployed['schema'],'started_utc':datetime.now(timezone.utc).isoformat(),'git_commit':b.capture(['git','rev-parse','HEAD']).strip(),'git_status':b.capture(['git','status','--porcelain']),'host':b.capture(['uname','-sm']),'host_memory_cpu':Path('/proc/meminfo').read_text()+Path('/proc/cpuinfo').read_text(),'docker':b.capture(['docker','version','--format','Client={{.Client.Version}} Server={{.Server.Version}}']),'docker_vm':b.capture(['docker','info','--format','OS={{.OperatingSystem}} Arch={{.Architecture}} CPUs={{.NCPU}} MemoryBytes={{.MemTotal}}']),'vm_cpu_count':cpus,'vm_os_reserve_cpus':1,'vm_os_reserve_bytes':1024**3,'auth':'Synthetic app users and per-request HS256 compatibility JWT verification; scoped native JWT bridge; native Auth runs but signup/login/session throughput is NOT measured','path':'k6 -> Envoy -> native Edge Runtime user worker -> Envoy native API-key layer -> PostgREST RPC/JWT -> PostgreSQL','excluded_services':['Studio','Storage','Realtime','analytics/logging','Vector','Supavisor','imgproxy'],'cost':'Existing shared VPS; price/region not supplied; no cost/request or $12-equivalence claim','limitations':['API-serving subset, not the default full Supabase platform','Shared host, storage/page caches and background workload; not dedicated-machine equivalence','Raw host pressure, steal, swap, I/O and component/parent cgroup evidence retained; provider thermals unavailable'],'allocated_data_kib_before':b.capture(['docker','exec',s.PROJECT+'-db-1','du','-sk','/var/lib/postgresql/data']).strip()}
 for name,source in [('dataset.json',STATE/'dataset.json'),('correctness.log',correctness),('correctness-manifest.json',STATE/'correctness-manifest.json')]:shutil.copyfile(source,destination/name)
 stop=threading.Event();thread=threading.Thread(target=monitor,args=(stop,local),daemon=True);thread.start();load=None;exit_code=255
 try:
  argv=compose()+['run','-T','--no-deps','--name',b.LOAD,'-e',f'VUS={vus}','-e',f'SMOKE={int(smoke)}','-e','TOKENS=/tokens.json','-e',f'SUMMARY=/runs/{run_id}/k6-summary.json','k6','run','--quiet','--out',f'json=/runs/{run_id}/samples.json.gz','/work/bench/baas.mjs']
  with (local/'k6.log').open('w') as log:exit_code=subprocess.run(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
  probe=subprocess.run(['docker','inspect',b.LOAD],capture_output=True)
  if probe.returncode==0:load=b.inspect(b.LOAD)
 finally:
  stop.set();thread.join(timeout=30)
  # This name was absent before creation; remove only our Compose-labelled runner.
  check=subprocess.run(['docker','inspect',b.LOAD],capture_output=True,text=True)
  if check.returncode==0:
   item=json.loads(check.stdout)[0]
   if item['Config']['Labels'].get('com.docker.compose.project')!=s.PROJECT:raise RuntimeError('Load ownership changed; refusing cleanup')
   subprocess.run(['docker','rm','-f',item['Id']],capture_output=True,check=True)
 if thread.is_alive():raise RuntimeError('Resource monitor did not stop')
 summary=json.loads((local/'k6-summary.json').read_text()) if (local/'k6-summary.json').exists() else {}
 outcome,reason=b.measurement_verdict(summary,exit_code,local,smoke,load)
 records=[json.loads(line) for line in (local/'resources.jsonl').read_text().splitlines()]
 kernels=[r['load_kernel_cgroup'] for r in records if 'load_kernel_cgroup' in r]
 if outcome!='invalid':
  if not kernels or any(k['cpu.max'].split()!=['200000','100000'] or int(k['memory.max'])!=8*1024**3 or int(k['memory.swap.max'])!=0 for k in kernels):outcome,reason='invalid','missing or incorrect actual runner kernel cgroup budget'
  elif load['image_manifest_digest']!=K6_MANIFEST:outcome,reason='invalid','load-generator selected manifest differs from frozen pin'
 after_targets=s.targets();issue=target_issue(before['targets'],after_targets)
 if outcome!='invalid' and issue:outcome,reason='fail',issue
 try:
  after=s.profile()
  if parent_oom(after['parent'])>parent_oom(before['parent']) and outcome!='invalid':outcome,reason='fail','aggregate serving cgroup OOM kill'
 except (RuntimeError,FileNotFoundError) as error:
  try:parent_after=s.parent_sample()
  except FileNotFoundError:parent_after=None
  after={'targets':after_targets,'parent':parent_after}
  if outcome!='invalid' and not issue:outcome,reason='invalid',str(error)
 schema_changed=not issue and after_targets['db']['State']['Running'] and s.schema_state()['sha256']!=current['schema']
 after_images={role:{k:v[k] for k in ['Image','platform','image_manifest_digest']} for role,v in after_targets.items()}
 if s.app_hash()!=current['app'] or s.verification_hash()!=current['verification'] or s.runtime_hash()!=current['runtime'] or schema_changed or after_images!=current['images'] or token_hash()!=current['tokens']:outcome,reason='invalid','frozen executable/verification/runtime/schema/image/token inputs changed during attempt'
 for record in records:
  parent=record.get('target_stack')
  if parent and any(parent[k].strip()!=before['parent'][k].strip() for k in ['cpu.max','memory.max','memory.swap.max']):outcome,reason='invalid','aggregate serving limits changed during monitoring'
 manifest.update(target_after=after,load_after=load,k6_exit_code=exit_code,result=outcome,reason=reason,finished_utc=datetime.now(timezone.utc).isoformat(),allocated_data_kib_after=b.capture(['docker','exec',s.PROJECT+'-db-1','du','-sk','/var/lib/postgresql/data']).strip() if after_targets['db']['State']['Running'] else None)
 for path in local.iterdir():shutil.copyfile(path,destination/path.name)
 metrics=summary.get('metrics',{});values=lambda name:metrics.get(name+'{phase:hold}',{}).get('values',{})
 latency=values('http_req_duration');count=values('http_reqs').get('count',0)
 compact={'outcome':outcome,'reason':reason,'vus':vus,'tier':tier,'mode':manifest['mode'],'runner_profile':b.RUNNER_PROFILE,'deployment_track':b.TRACK,'platform':b.PLATFORM,'hold_requests':count,'hold_rps':count/(20 if smoke else 300),'latency_ms':latency,'request_errors':values('request_errors'),'schema_errors':values('schema_errors')}
 (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(destination/'summary.json').write_text(json.dumps(compact,indent=2)+'\n')
 (destination/'report.md').write_text(f"""# Supabase standard — {vus} VUs ({manifest['mode']})

Outcome: **{outcome}** — {reason}.

One shared-host attempt, **not a maximum-capacity score**. {'Short calibration only, not scored.' if smoke else 'Full 300-second scored hold; see campaign search and independent confirmations.'}

- Entire five-component serving stack: **1 CPU / 4 GiB / no swap**, one kernel-enforced parent cgroup.
- Separate runner: **2 CPU / 8 GiB / no swap**, `{b.RUNNER_PROFILE}`.
- Hold requests: {count}; throughput: {compact['hold_rps']:.2f} requests/s.
- p50/p95/p99: {latency.get('med','N/A')} / {latency.get('p(95)','N/A')} / {latency.get('p(99)','N/A')} ms; maximum: {latency.get('max','N/A')} ms.
- Request/schema errors: {values('request_errors').get('rate','N/A')} / {values('schema_errors').get('rate','N/A')}.
- Compatibility identities/JWTs, **not native signup/login/session throughput**; native Auth included in serving budget.
- Native path: Envoy → Edge Functions → Envoy → PostgREST RPC → PostgreSQL. No direct driver, result/like-count/JWT-verification caches.
- API-serving subset: unused dashboard/storage/realtime/analytics/pooler services excluded, not a full default-stack claim.
- Canonical logical data/hash: `dataset.json`; original complete correctness: `correctness.log`, `correctness-manifest.json`.
- Raw samples and endpoint metrics: `samples.json.gz`, `k6-summary.json`; all six containers, aggregate cgroup and raw host counters: `resources.jsonl`.
- Images, actual budgets, lifecycle identities, source/runtime/schema fingerprints and caveats: `manifest.json`.
- Reproduction overlay: `source.tar.gz`, `working-tree.patch`, base commit in manifest. Verify **SHA256SUMS**. Private keys/tokens/runtime data are intentionally excluded.
- Shared VPS price/region unknown; no cost/request or dedicated-$12 equivalence claim.
""")
 b.checksum_files(destination);progress=RESULTS/'progress';progress.mkdir(exist_ok=True)
 for filename in ['summary.json','report.md']:shutil.copyfile(destination/filename,progress/(run_id+'-'+filename))
 print(json.dumps({'run':run_id,**compact}),flush=True)
 return outcome,str(destination.relative_to(ROOT))
