#!/usr/bin/env python3
"""Approved fixed twelve-row study. Original product/CLI/scoring bytes unchanged."""
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import time

P=Path('/opt/twelve-dollar-baas-pocketbase-16g');R=P/'src';O=P/'supplemental-20261016';C=O/'repeatability-post-update-01'
os.chdir(R);os.umask(0o077)
os.environ.update(DOCKER_CONFIG='/opt/twelve-dollar-baas-benchmark-16g/.docker',BENCHMARK_PROJECT='baas-pocketbase-vps16',BENCHMARK_PLATFORM='linux/amd64',BENCHMARK_RUNNER_PROFILE='k6-2cpu-8g-v3',RUNNER_MEMORY='8g',PYTHONDONTWRITEBYTECODE='1')
sys.path[:0]=[str(C),str(R/'scripts')]
import supplemental_repeatability_policy as policy
import repeatability_guards as guards
import repeatability_transient_units as transient_units
import pocketbase as ctl
import pocketbase_profile as s
import pocketbase_benchmark as bench


def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def capture(argv):return subprocess.check_output(argv,text=True,timeout=30)


def write(name,value):
 with (C/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())


def canonical_sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def host_context():
 mem={line.split(':',1)[0]:int(line.split(':',1)[1].strip().split()[0])*1024 for line in Path('/proc/meminfo').read_text().splitlines()}
 return {'boot':sha(Path('/proc/sys/kernel/random/boot_id')),'kernel':platform.release(),
         'docker':canonical_sha(json.loads(capture(['docker','version','--format','{{json .Server}}']))),
         'memory_total':mem['MemTotal'],'cpus':os.cpu_count(),'machine':sha(Path('/etc/machine-id'))}


def dmarie_off():
 text=capture(['systemctl','show','dmarie.service','--property=ActiveState','--property=SubState','--property=UnitFileState','--property=MainPID','--property=Job'])
 value=dict(line.split('=',1) for line in text.splitlines() if '=' in line);guards.require_dmarie_off(value);return value


def snapshot(name):
 path=C/name;assert not path.exists()
 subprocess.run(['python3',str(P/'service-snapshot.py'),str(path)],capture_output=True,check=True)
 return json.loads(path.read_text())


def journal(start,end,label,baseline):
 private=C/(label+'-manager-events-PRIVATE.jsonl')
 with private.open('xb') as f:
  subprocess.run(['journalctl','-b','_PID=1','--since','@'+str(math.floor(start)),'--until','@'+str(math.ceil(end)),'--output=json','--no-pager'],stdout=f,check=True,timeout=60)
 entries=[]
 for line in private.read_bytes().splitlines():
  value=json.loads(line);timestamp=int(value['__REALTIME_TIMESTAMP'])/1e6
  if start<=timestamp<end:entries.append(value)
 # Also discover persistent services that were absent at BOTH endpoint snapshots.
 # Log normal nonpersistent oneshot jobs separately; never exempt a flapping daemon.
 names=sorted({v['UNIT'] for v in entries if isinstance(v.get('UNIT'),str) and v['UNIT'].endswith('.service') and not v['UNIT'].startswith('tds-') and v['UNIT']!='user@0.service'})
 types={}
 if names:
  properties=['Id','Type','RemainAfterExit','MainPID','ControlPID','ActiveState','SubState','Job','ControlGroup']
  command=['systemctl','show',*['--property='+p for p in properties],'--',*names]
  text=capture(command)
  for block in text.strip().split('\n\n'):
   item=dict(line.split('=',1) for line in block.splitlines() if '=' in line)
   if 'Id' in item:types[item['Id']]=item
  assert set(types)==set(names),'Persistent-service type discovery incomplete'
 # Positive no-resident-process evidence is required, not only MainPID=0.
 resident_free={};resident_proof={}
 for name,item in types.items():
  group=item.get('ControlGroup',None)
  if group=='':
   resident_free[name]=True;resident_proof[name]='systemd_no_assigned_control_group'
  elif isinstance(group,str) and group.startswith('/'):
   path=Path('/sys/fs/cgroup')/group.lstrip('/')
   assert path.resolve().is_relative_to(Path('/sys/fs/cgroup')),'Invalid kernel cgroup path'
   kernel=dict(line.split() for line in (path/'cgroup.events').read_text().splitlines())
   assert kernel.get('populated') in {'0','1'},'Resident-process observation incomplete'
   resident_free[name]=kernel['populated']=='0';resident_proof[name]='kernel_cgroup_populated_'+kernel['populated']
  else:raise RuntimeError('No complete unit cgroup observation')
 if names:assert capture(command)==text,'Unit properties changed during resident-process observation'
 partition=transient_units.partition(types,resident_free)
 watched=set(baseline['services'])|{'dmarie.service'}|set(partition['persistent'])
 counts=guards.event_counts(entries,watched)
 transient=guards.event_counts(entries,set(partition['transient'])-watched)
 value={'window_start':start,'window_end':end,'window_complete':float(Path('/proc/uptime').read_text().split()[0])>=end-start,
        'persistent_service_event_counts':counts,'nonpersistent_oneshot_event_counts_disclosed':transient,
        'oneshot_classification_authorization':'f81b2fc4-35f2-4a51-925b-aa303ea7b68d',
        'unit_classification':{name:{'type':types[name]['Type'],'active_state':types[name]['ActiveState'],'sub_state':types[name]['SubState'],'main_pid_zero':types[name]['MainPID']=='0','control_pid_zero':types[name]['ControlPID']=='0','job_pending':types[name]['Job'] not in ('','0'),'no_resident_processes':resident_free[name],'resident_evidence':resident_proof[name],'classification':'transient' if name in partition['transient'] else 'persistent'} for name in names},
        'private_raw':{'bytes':private.stat().st_size,'sha256':sha(private),'distribution':'PRIVATE VPS ONLY'},
        'scope':'Numeric metadata only; all raw messages stay private. Only existing SSH session exception and benchmark tds unit namespace; no persistent-service exclusions. No causality or isolation proof.'}
 write(label+'-service-events-public.json',value)
 return value


def verify_tree(base,rows):
 for row in rows:
  path=base/row['path']
  if 'link' in row:assert path.is_symlink() and os.readlink(path)==row['link'] and path.resolve().is_relative_to(base.resolve())
  else:assert path.is_file() and not path.is_symlink() and path.stat().st_size==row['bytes'] and path.stat().st_mode&0o777==row['mode'] and sha(path)==row['sha256'],'Actual frozen source/dependency bytes or mode changed'


def source_names():
 names=set()
 for directory,dirs,files in os.walk(R,followlinks=False):
  dirs[:]=[d for d in dirs if d not in {'.git','.state','results','__pycache__','target','node_modules'}]
  for name in files:
   if name not in {'.git','.state','results','__pycache__','target','node_modules'}:names.add(str((Path(directory)/name).relative_to(R)))
  for name in dirs:
   p=Path(directory)/name
   if p.is_symlink():names.add(str(p.relative_to(R)))
 return names


ctl.require_native();ctl.ownership()
assert capture(['hostname','-f']).strip()=='claudius.azabab.com'
clarification=json.loads((C/'transient-classification-authorization.json').read_text())
assert clarification['approved'] is True and clarification['interview']=='f81b2fc4-35f2-4a51-925b-aa303ea7b68d'
authorization=json.loads((C/'owner-authorization.json').read_text())
assert authorization['approved'] is True and authorization['interview']=='9c8b8369-0955-4a93-ad2f-a99c7b2dbcc6'
assert (authorization['fixed_further_attempts'],authorization['cap_extension'],authorization['cumulative_supplemental_cap'],authorization['cumulative_physical_cap'])==(12,9,19,30)
prior_path=O/'rebracket-01/supplemental-phase.json';prior=json.loads(prior_path.read_text())
assert sha(prior_path)=='088d3a45d630c9569e9a0a4a4aaf86fc5ade74a7a32d3db1dca7b64670700dd0'
assert len(prior['attempts'])==7 and prior['total_physical_full_attempts_accounted']==18
track=R/'results/pocketbase/vps16-linux-amd64'
original=json.loads((O/'readonly-preflight2-public.json').read_text())['original_full_attempts']
initial_names={x['run'] for x in original}|{Path(x['run']).name for x in prior['attempts']};assert len(initial_names)==18
known=set(initial_names)
expected=prior['original_frozen_inputs']
fresh=json.loads((C/'fresh-full-correctness-result-public.json').read_text());assert fresh['same_frozen_inputs']==expected
baseline=json.loads((C/'after-full-correctness-services.json').read_text())
assert baseline['port4000_processes']=={'812':{'start_ticks':'759','executable':'/opt/trailbase-server/bin/trail'}}
preflight=json.loads((O/'post-security-updates-preflight-g0pp25r8/post-update-preflight-public.json').read_text())
h=preflight['host'];expected_host={'boot':h['boot_identity_sha256'],'kernel':h['kernel'],'docker':canonical_sha(json.loads(h['docker_server'])),
 'memory_total':h['memory_total_bytes'],'cpus':h['cpus'],'machine':preflight['frozen_inputs']['host']}
freeze=json.loads((O/'complete-freeze-public.json').read_text());F=O/'complete-frozen-inputs2'
assert sha(F/'complete-inventory-private.json')==freeze['complete_inventory_sha256'];inventory=json.loads((F/'complete-inventory-private.json').read_text())
external=dict(prior['external_harness_sha256'])
for path in [prior_path,O/'rebracket-01/supplemental-phase-journal.jsonl',P/'service-snapshot.py']:
 external[str(path.relative_to(P))]=sha(path)
for name in ['post-update-repeatability-controller.py','supplemental_repeatability_policy.py','test_supplemental_repeatability_policy.py','repeatability_guards.py','test_repeatability_guards.py','repeatability-review-one.py','post-update-full-frozen-correctness.py','approved-study-plan.md','owner-authorization.json','policy-green-suite-driver.py','guard-green-suite-driver.py','native-launch-contract.json','verify-preserved18-checksums.py','runner-version-preflight-public.log','historical18-checksums-driver-private.log',
 'post-update-repeatability-controller-v2.py','native-launch-contract-v2.json','repeatability_transient_units.py','test_repeatability_transient_units.py','transient-units-green-suite-driver.py','transient-units-red-original.log','transient-units-green-original.log','transient-classification-authorization.json','approved-study-clarified-plan.md','complete-post-update-input-catalog-PRIVATE.json','controller-preflight-driver-private.log','preflight-01-services.json','preflight-01-service-events-public.json']:
 path=C/name;external[str(path.relative_to(P))]=sha(path)
for path in [P/'supplemental-retain12.py',P/'supplemental-retain13.py',P/'supplemental-retain14.py',P/'supplemental-retain15.py']:
 external[str(path.relative_to(P))]=sha(path)
for row in original:
 for name,key in [('manifest.json','manifest_sha256'),('SHA256SUMS','original_checksum_manifest_sha256')]:external[str((track/row['run']/name).relative_to(P))]=row[key]
for row in json.loads((O/'rebracket-paused-campaign-readonly-capture-public.json').read_text())['copies']:
 external[str((R/row['original']).relative_to(P))]=row['original_sha256']
for name in ['fresh-correctness.log','fresh-correctness-manifest.json','fresh-dataset.json','fresh-full-correctness-result-public.json','full-correctness-continuity-public.json','after-full-correctness-services.json','policy-red-original.log','policy-green-original.log','guard-red-original.log','guard-green-original.log']:
 path=C/name;external[str(path.relative_to(P))]=sha(path)
static_inputs={str(path.relative_to(R)):sha(path) for path in [s.STATE/'build/feed',s.STATE/'build-manifest.json',s.STATE/'runtime.env',s.STATE/'native-schema-fixture.db',s.STATE/'correctness.log',s.STATE/'correctness-manifest.json',R/'.state/seed/tokens.json',*[R/'.state/seed'/name for name in ['users.tsv','posts.tsv','likes.tsv']]]}
own_group=Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split('::',1)[1].lstrip('/')
own_caps={key:(own_group/key).read_text() for key in ['cpu.max','memory.max','memory.swap.max']}
assert own_caps['cpu.max'].split()==['200000','100000'] and int(own_caps['memory.max'])==4294967296 and int(own_caps['memory.swap.max'])==0,'Controller actual kernel limits differ'
controller_runtime={'kernel_limits':own_caps,'python_version':sys.version,'python_executable':str(Path(sys.executable).resolve()),'python_executable_sha256':sha(Path(sys.executable).resolve()),'dpkg_status_sha256':sha(Path('/var/lib/dpkg/status')),'libc':list(platform.libc_ver())}
catalog={'owner_authorization':authorization,'oneshot_classification_authorization':clarification,'host_context':expected_host,'controller_runtime':controller_runtime,'prospective_service_baseline_sha256':sha(C/'after-full-correctness-services.json'),
 'complete_prior_inventory_sha256':freeze['complete_inventory_sha256'],'source_entries':len(inventory['source']),'go_module_entries':len(inventory['go_modules']),
 'external_sources_and_preserved_evidence':external,'new_generated_and_private_input_fingerprints_only':static_inputs,'fresh_correctness_log_sha256':fresh['fresh_correctness_log_sha256'],
 'images':inventory['images'],'original_frozen_inputs':expected,'historical_identity_guard_reclassified':False}
catalog_path=C/'complete-post-update-input-catalog-v2-PRIVATE.json'
if catalog_path.exists():assert json.loads(catalog_path.read_text())==catalog,'No silent source/catalog replacement'
else:write(catalog_path.name,catalog)
catalog_digest=sha(catalog_path)


def guard():
 assert sha(catalog_path)==catalog_digest,'Frozen catalog changed'
 assert sha(Path(sys.executable).resolve())==controller_runtime['python_executable_sha256'] and sha(Path('/var/lib/dpkg/status'))==controller_runtime['dpkg_status_sha256'],'Controller interpreter/OS package state changed'
 assert {p.name for p in track.glob('*vu-k6-2cpu-8g-v3')}==known,'Unexpected physical full attempt; no accounting reset'
 for name,digest in external.items():assert sha(P/name)==digest,'Executed or preserved external inputs changed'
 for name,digest in static_inputs.items():assert sha(R/name)==digest,'New generated/private input changed'
 assert source_names()=={row['path'] for row in inventory['source']}
 verify_tree(R,inventory['source']);verify_tree(s.STATE/'gopath/pkg/mod',inventory['go_modules'])
 # Assert the installed dependency path set, not only selected known files.
 assert {str(p.relative_to(s.STATE/'gopath/pkg/mod')) for p in (s.STATE/'gopath/pkg/mod').rglob('*') if p.is_file() or p.is_symlink()}=={row['path'] for row in inventory['go_modules']}
 att=json.loads((s.STATE/'correctness-manifest.json').read_text());bench.validate_correctness(att,bench.inputs(),sha(s.STATE/'correctness.log'))
 assert att['inputs']==expected and att['log_sha256']==fresh['fresh_correctness_log_sha256']
 guards.require_host_context(expected_host,host_context());dmarie_off()
 for cid in ['f6a3332784f218eae1e5afca5cd967e661ff27e551640cc378e40f3c81bdac75','164ec7fdab991f75be71168cdf1ea0b981fd3141a34bd794af4035c897b72177']:
  assert capture(['docker','inspect',cid,'--format','{{.State.Running}}']).strip()=='false','Convex must stay stopped'
 mem={line.split(':',1)[0]:int(line.split(':',1)[1].strip().split()[0])*1024 for line in Path('/proc/meminfo').read_text().splitlines()}
 assert mem['SwapTotal']==0 and mem['MemAvailable']>=9*1024**3,'Actual runner plus host reserve insufficient'


def save(phase):
 value={**phase,'owner_authorization':'9c8b8369-0955-4a93-ad2f-a99c7b2dbcc6','time':time.time(),
  'original_frozen_inputs':expected,'input_catalog_sha256':sha(catalog_path),'host_context':expected_host,
  'accounting_scope':'11 historical+7 preserved supplemental; new pending intents conservatively consume allowance; actual full directories separately retained. Never erase partial/invalid holds or reuse prior confirmations.',
  'historical_original_listener_equality':False,'prospective_listener_baseline':baseline['port4000_processes']}
 with (C/'study-phase-journal.jsonl').open('a') as f:f.write(json.dumps(value)+'\n');f.flush();os.fsync(f.fileno())
 tmp=C/'study-phase.tmp'
 with tmp.open('w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 tmp.replace(C/'study-phase.json')


def events(parent):return {k:int(v) for k,v in (line.split() for line in parent['memory.events'].splitlines())}


def attempt(vus,purpose):
 global continuity_cursor
 guard();before_names=set(known);assert len(before_names)<30
 index=len(before_names)-11+1;assert 8<=index<=19
 label='full-attempt-'+str(index);before=snapshot(label+'-before-services.json');started=time.time()
 guards.require_continuity(baseline,before,before,{},True)
 log=C/(label+'-driver-private.log')
 with log.open('x') as f:code=subprocess.run(['bash','services/pocketbase/run.sh','bench','--vus',str(vus)],stdout=f,stderr=subprocess.STDOUT).returncode
 ended=time.time();after=snapshot(label+'-after-services.json')
 new={p.name for p in track.glob('*vu-k6-2cpu-8g-v3')}-before_names
 write(label+'-physical-accounting.json',{'expected_vus':vus,'purpose':purpose,'cli_exit_code':code,'new_full_directories':sorted(new),'before_count':len(before_names),'after_count':len(before_names|new),'pending_slot_consumed_even_if_later_guard_raises':True})
 known.update(new)
 assert len(new)==1,'Missing/ambiguous new physical run; preserve pending intent and stop'
 run=track/new.pop();m=json.loads((run/'manifest.json').read_text());value=json.loads((run/'summary.json').read_text())
 continuity=journal(continuity_cursor,ended,label,baseline)
 continuity_cursor=ended
 # Persist every measurement and guard finding before any assertion can stop us.
 write(label+'-measurement-link.json',{'run':str(run.relative_to(R)),'manifest_sha256':sha(run/'manifest.json'),'original_checksum_manifest_sha256':sha(run/'SHA256SUMS'),
  'outcome':value['outcome'],'reason':value['reason'],'input_catalog_sha256':sha(catalog_path),'host_context':expected_host,'service_events':continuity,
  'historical_original_listener_equality':False,'prospective_listener_equal_before_after':before['port4000_processes']==after['port4000_processes']})
 guards.require_continuity(baseline,before,after,continuity['persistent_service_event_counts'],continuity['window_complete'])
 assert m['vus']==vus and m['mode']=='capacity' and m['inputs']==expected and value['outcome']==m['result']
 assert code==(0 if value['outcome']=='pass' else 1),'Contradictory CLI/native result'
 assert bench.target_issue(m['target_before']['targets'],m['target_after']['targets']) is None,'Runtime failure; preserve bundle, no revival'
 a,z=events(m['target_before']['parent']),events(m['target_after']['parent'])
 assert all(a.get(k,0)==z.get(k,0) for k in ['oom','oom_kill','oom_group_kill']),'Serving OOM event; no new reset'
 summary=json.loads((run/'k6-summary.json').read_text()) if (run/'k6-summary.json').exists() else {}
 replay=bench.b.measurement_verdict(summary,m['k6_exit_code'],run,False,m['load_after'])
 assert replay==(m['result'],m['reason']),'Original native measurement verdict did not replay'
 if value['outcome']!='invalid':
  assert value['reason'] in ['hold gates passed','hold latency/error/schema gate failed']
  with (C/(label+'-raw-review-private.log')).open('x') as f:subprocess.run(['python3',str(C/'repeatability-review-one.py'),str(run)],stdout=f,stderr=subprocess.STDOUT,check=True)
  raw=json.loads((C/'raw-reviews'/(run.name+'.json')).read_text());assert len(raw['attempts'])==1 and raw['attempts'][0]['outcome']==value['outcome']
 guard()
 print('POST_UPDATE_FIXED_FULL_HOLD_RETAINED',index,purpose,vus,value['outcome'],run.name,flush=True)
 return {'outcome':value['outcome'],'reason':value['reason'],'run':str(run.relative_to(R))}


with (O/'controller.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert not (C/'study-phase.json').exists() and not (C/'study-phase-journal.jsonl').exists(),'No implicit resume or overwrite'
 guard()
 label='preflight-02' if '--preflight-only' in sys.argv else 'before-first-hold'
 before=snapshot(label+'-services.json');end=time.time();observed=journal(end-600,end,label,baseline)
 guards.require_continuity(baseline,before,before,observed['persistent_service_event_counts'],observed['window_complete'])
 if '--preflight-only' in sys.argv:
  archive=C/'complete-external-inputs-v2-PRIVATE.tar.gz'
  with archive.open('xb') as stream:
   with tarfile.open(fileobj=stream,mode='w:gz',dereference=False) as tar:
    for name in sorted(external):tar.add(P/name,arcname=name,recursive=False)
  write('controller-v2-preflight-public.json',{'scope':'Complete actual frozen product/dependency plus new external/generated/host input verification and ten-minute continuity; NO FULL SLOT USED',
   'tested_software':s.PINS,'serving_budget':{'cpus':1,'memory_bytes':4294967296,'swap_bytes':0},'runner_budget':{'software':'k6 1.3.0','cpus':2,'memory_bytes':8589934592,'swap_bytes':0,'profile':'k6-2cpu-8g-v3'},
   'owner_authorization':authorization,'source_entries':len(inventory['source']),'go_module_entries':len(inventory['go_modules']),'external_entries':len(external),'new_generated_fingerprint_entries':len(static_inputs),
   'catalog_sha256':sha(catalog_path),'private_external_archive':{'bytes':archive.stat().st_size,'sha256':sha(archive),'distribution':'PRIVATE pending privacy/license review, not a fresh build/public download'},
   'actual_preserved_physical_full_attempts':len(known),'fresh_correctness_log_sha256':fresh['fresh_correctness_log_sha256'],'host_context':expected_host,'ten_minute_service_window':observed,
   'historical_original_listener_equality':False,'prospective_listener_baseline':baseline['port4000_processes'],'new_full_slots':0})
  print('POST_UPDATE_COMPLETE_EXTERNAL_PRODUCT_MODULE_GENERATED_HOST_QUIET_PREFLIGHT_PASSED_NO_FULL_SLOT',flush=True)
 else:
  assert (C/'controller-v2-preflight-public.json').is_file(),'Human-reviewed preflight evidence required before launch'
  continuity_cursor=end
  result=policy.finish(attempt,prior,record=save,max_attempts=12)
  if result['status']=='complete_pending_human_review':
   try:
    final=snapshot('after-complete-study-services.json');last=journal(continuity_cursor,time.time(),'after-complete-study',baseline)
    guards.require_continuity(baseline,final,final,last['persistent_service_event_counts'],last['window_complete'])
   except Exception as error:
    result['status']='paused_unconfirmed';result['boundary_confirmed_by_hold_gates']=False;result['reason']='Final continuity review failed: '+str(error);save(result)
  print('POST_UPDATE_FIXED_STUDY_TERMINAL',result['status'],result.get('study_result'),flush=True)
  if result['status']!='complete_pending_human_review':raise RuntimeError('Fixed study paused: '+result.get('reason','inspect retained evidence'))
