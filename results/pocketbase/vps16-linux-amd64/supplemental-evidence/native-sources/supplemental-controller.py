#!/usr/bin/env python3
"""Ten supplemental FULL attempts maximum, immutable native path, fail closed.

Scheduling policy has independent native red/green tests. Every physical hold uses
unchanged original CLI/reset/scoring, followed by independent full raw replay.
"""
import fcntl,hashlib,json,os,subprocess,sys,time
from pathlib import Path
P=Path('/opt/twelve-dollar-baas-pocketbase-16g');R=P/'src';O=P/'supplemental-20261016';os.chdir(R)
sys.path[:0]=[str(O),str(R/'scripts')]
import supplemental_policy as policy
import pocketbase as ctl
import pocketbase_profile as s
import pocketbase_benchmark as bench


def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def events(parent):return {k:int(v) for k,v in (line.split() for line in parent['memory.events'].splitlines())}


def verify_tree(base,rows):
 for row in rows:
  path=base/row['path']
  if 'link' in row:assert path.is_symlink() and os.readlink(path)==row['link'] and path.resolve().is_relative_to(base.resolve())
  else:assert path.is_file() and not path.is_symlink() and path.stat().st_size==row['bytes'] and path.stat().st_mode&0o777==row['mode'] and sha(path)==row['sha256'], 'Complete source/dependency input changed'


def sources_present():
 names=set()
 for directory,dirs,files in os.walk(R,followlinks=False):
  dirs[:]=[d for d in dirs if d not in {'.git','.state','results','__pycache__','target','node_modules'}]
  for name in files:
   if name in {'.git','.state','results','__pycache__','target','node_modules'}:continue
   names.add(str((Path(directory)/name).relative_to(R)))
  for name in dirs:
   path=Path(directory)/name
   if path.is_symlink():names.add(str(path.relative_to(R)))
 return names


def save(phase):
 # Append-only snapshots preserve pending intent BEFORE each physical side effect.
 # Pending intent is conservatively accounted, actual run IDs establish physicals.
 value={**phase,'owner_authorization':'b1938c3c-cfce-4ea8-aff2-5f6b57a1f0ce','time':time.time(),'accounting_scope':'11 historical physical holds preserved; supplemental scheduled intents <=10, including incomplete/failed launches; actual physical run IDs retained separately; never erase a full attempt because a guard raised','original_frozen_inputs':expected,'external_harness_sha256':external,'complete_freeze_report_sha256':sha(O/'complete-freeze-public.json')}
 with (O/'supplemental-phase-journal.jsonl').open('a') as f:f.write(json.dumps(value)+'\n');f.flush();os.fsync(f.fileno())
 temporary=O/'supplemental-phase.tmp'
 with temporary.open('w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 temporary.replace(O/'supplemental-phase.json')


ctl.require_native();ctl.ownership()
track=R/'results/pocketbase/vps16-linux-amd64'
original=json.loads((O/'readonly-preflight2-public.json').read_text())['original_full_attempts'];old_names={v['run'] for v in original};assert len(old_names)==11
assert {p.name for p in track.glob('*vu-k6-2cpu-8g-v3')}==old_names,'Unexpected consumed physical attempt; inspect instead of resetting accounting'
assert not (O/'supplemental-phase.json').exists() and not (O/'supplemental-phase-journal.jsonl').exists(),'No implicit resume/overwrite'
freeze=json.loads((O/'complete-freeze-public.json').read_text());F=O/'complete-frozen-inputs2'
assert sha(F/'complete-inventory-private.json')==freeze['complete_inventory_sha256'];inventory=json.loads((F/'complete-inventory-private.json').read_text())
expected=json.loads((s.STATE/'correctness-manifest.json').read_text())['inputs'];assert expected==freeze['original_attested_inputs_unchanged']
assert expected==json.loads((O/'fresh-full-correctness-result-public.json').read_text())['same_frozen_inputs']
external={str(p.relative_to(P)):sha(p) for p in sorted({Path(__file__),O/'supplemental_policy.py',O/'test_supplemental_policy.py',P/'supplemental-review-one.py',P/'supplemental-full-frozen-correctness.py',P/'supplemental-complete-freeze2.py'})}
external_path=O/'external-harness-frozen-before-first-hold.json'
if external_path.exists():assert json.loads(external_path.read_text())==external,'Preflighted external harness changed; no silent replacement'
else:
 with external_path.open('x') as f:json.dump(external,f,indent=2);f.write('\n')
for v in original:assert sha(track/v['run']/'manifest.json')==v['manifest_sha256'] and sha(track/v['run']/'SHA256SUMS')==v['original_checksum_manifest_sha256']
assert subprocess.run(['systemctl','is-active','--quiet','tds-pocketbase-supplemental-complete-input-freeze2-20261016.service']).returncode!=0,'No heavy freeze/audit during timed holds'


def guard():
 for name,value in external.items():assert sha(P/name)==value,'Executed external controller/auditor source changed'
 assert sources_present()=={v['path'] for v in inventory['source']},'Complete actual source path set changed'
 verify_tree(R,inventory['source']);verify_tree(s.STATE/'gopath/pkg/mod',inventory['go_modules'])
 att=json.loads((s.STATE/'correctness-manifest.json').read_text());bench.validate_correctness(att,bench.inputs(),sha(s.STATE/'correctness.log'));assert att['inputs']==expected
 assert sha(s.STATE/'correctness.log')==json.loads((O/'fresh-full-correctness-result-public.json').read_text())['fresh_correctness_log_sha256']
 for cid in ['f6a3332784f218eae1e5afca5cd967e661ff27e551640cc378e40f3c81bdac75','164ec7fdab991f75be71168cdf1ea0b981fd3141a34bd794af4035c897b72177']:
  assert not json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0]['State']['Running'],'Convex must remain stopped'
 mem={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in Path('/proc/meminfo').read_text().splitlines()}
 assert int(mem['SwapTotal'].split()[0])==0 and int(mem['MemAvailable'].split()[0])*1024>=9*1024**3,'Insufficient actual runner plus host memory reserve'


def snapshot(name):
 path=O/name;assert not path.exists()
 subprocess.run(['python3',str(P/'service-snapshot.py'),str(path)],capture_output=True,check=True)
 value=json.loads(path.read_text());baseline=json.loads((O/'before-any-start-services.json').read_text())
 assert value['port4000_processes']==baseline['port4000_processes']=={'811':{'start_ticks':'691','executable':'/opt/trailbase-server/bin/trail'}},'Original port4000 listener identity changed'
 return value


def attempt(vus,purpose):
 guard();before=set(track.glob('*vu-k6-2cpu-8g-v3'));assert len(before)-11<10
 index=len(before)-11+1;log=O/('full-attempt-'+str(index)+'-driver-private.log')
 services_before=snapshot('before-full-attempt-'+str(index)+'-services.json')
 with log.open('x') as f:code=subprocess.run(['bash','services/pocketbase/run.sh','bench','--vus',str(vus)],stdout=f,stderr=subprocess.STDOUT).returncode
 services_after=snapshot('after-full-attempt-'+str(index)+'-services.json')
 a={k:v for k,v in services_before['services'].items() if k!='user@0.service'};z={k:v for k,v in services_after['services'].items() if k!='user@0.service'}
 with (O/('full-attempt-'+str(index)+'-service-continuity.json')).open('x') as f:json.dump({'persistent_identity_equality':a==z,'added':sorted(set(z)-set(a)),'removed':sorted(set(a)-set(z)),'changed':[k for k in sorted(a.keys()&z.keys()) if a[k]!=z[k]],'original4000_unchanged':True,'scope':'Record EVERY persistent service difference; only established SSH-session user@0 excluded. False remains false, no full host-isolation claim or exclusion of inconvenient newly visible/flapping services.'},f,indent=2);f.write('\n')
 new=set(track.glob('*vu-k6-2cpu-8g-v3'))-before;assert len(new)==1,'Missing/ambiguous physical hold; preserve pending slot and investigate'
 p=new.pop();m=json.loads((p/'manifest.json').read_text());value=json.loads((p/'summary.json').read_text())
 assert m['vus']==vus and m['mode']=='capacity' and m['inputs']==expected and value['outcome']==m['result']
 assert code==(0 if value['outcome']=='pass' else 1)
 assert bench.target_issue(m['target_before']['targets'],m['target_after']['targets']) is None,'Runtime exit/OOM/restart: preserve bundle, no automatic revival'
 a,z=events(m['target_before']['parent']),events(m['target_after']['parent']);assert all(a.get(k,0)==z.get(k,0) for k in ['oom','oom_kill','oom_group_kill']),'Serving OOM event: preserve bundle, no automatic revival'
 if value['outcome']!='invalid':assert value['reason'] in ['hold gates passed','hold latency/error/schema gate failed'],'Unexpected target/runtime failure; stop before next reset'
 with (O/('full-attempt-'+str(index)+'-raw-review-private.log')).open('x') as f:
  subprocess.run(['python3',str(P/'supplemental-review-one.py'),str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
 replay=json.loads((O/'raw-reviews'/(p.name+'.json')).read_text());assert len(replay['attempts'])==1 and replay['attempts'][0]['outcome']==value['outcome']
 guard()
 print('SUPPLEMENTAL_FULL_HOLD_RAW_REPLAY_RETAINED',index,purpose,vus,value['outcome'],p.name,flush=True)
 return {'outcome':value['outcome'],'reason':value['reason'],'run':str(p.relative_to(R))}


if '--preflight-only' in sys.argv:
 guard();snapshot('before-controller-full-attempts-services.json')
 print('SUPPLEMENTAL_CONTROLLER_COMPLETE_INPUTS_NATIVE_GUARDS_AND_4000_PREFLIGHT_PASSED_NO_FULL_SLOT_USED',flush=True)
 raise SystemExit(0)

with (O/'controller.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 result=policy.finish(attempt,record=save,max_attempts=10)
 print('SUPPLEMENTAL_TERMINAL_STATUS',result['status'],flush=True)
 if result['status']!='confirmed_pending_evidence_review':raise RuntimeError('Supplemental campaign PAUSED: '+result.get('reason','inspect evidence'))
