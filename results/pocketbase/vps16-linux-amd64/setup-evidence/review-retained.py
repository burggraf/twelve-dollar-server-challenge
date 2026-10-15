#!/usr/bin/env python3
"""Read-only independent checksum/source/raw-point/resource review on designated host."""
import collections,gzip,hashlib,json,math,os,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path('/opt/twelve-dollar-baas-pocketbase-16g/src');os.chdir(ROOT)
os.environ.update(BENCHMARK_PROJECT='baas-pocketbase-vps16',BENCHMARK_PLATFORM='linux/amd64',BENCHMARK_RUNNER_PROFILE='k6-2cpu-8g-v3',RUNNER_MEMORY='8g')
sys.path.insert(0,str(ROOT/'scripts'))
import benchmark as b
import pocketbase_benchmark as bench
import pocketbase_profile as s
expected=json.loads((s.STATE/'correctness-manifest.json').read_text())['inputs'];rows=[]
def digest(names,members,base):
 h=hashlib.sha256()
 for name in sorted(names):
  raw=members.get(name)
  if raw is None:raw=subprocess.check_output(['git','show',base+':'+name],cwd=ROOT)
  h.update(name.encode()+b'\0'+raw+b'\0')
 return h.hexdigest()
for p in sorted((ROOT/'results/pocketbase/vps16-linux-amd64').glob('*vu-*')):
 if not (p/'SHA256SUMS').exists():continue
 m=json.loads((p/'manifest.json').read_text());summary=json.loads((p/'k6-summary.json').read_text()) if (p/'k6-summary.json').exists() else {}
 for line in (p/'SHA256SUMS').read_text().splitlines():
  sha,name=line.split('  ',1);assert hashlib.sha256((p/name).read_bytes()).hexdigest()==sha,(p.name,name)
 assert m['inputs']==expected
 c=json.loads((p/'correctness-manifest.json').read_text());assert c['inputs']==expected
 assert hashlib.sha256((p/'correctness.log').read_bytes()).hexdigest()==c['log_sha256']
 data=json.loads((p/'dataset.json').read_text());assert data['content_sha256']=='738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d'
 assert data['counts']=={'users':50000,'posts':500000,'likes':2016005}
 assert data['native_auth_accounts']=={'users':0,'_superusers':1}
 assert data['platform_rows_before_sha256']==data['platform_rows_after_sha256']
 with tarfile.open(p/'source.tar.gz') as t:
  members={v.name:t.extractfile(v).read() for v in t.getmembers() if v.isfile()}
 assert not any(n.startswith('/') or '..' in Path(n).parts or '.state' in Path(n).parts or n.endswith('tokens.json') or Path(n).name.startswith('.env') for n in members)
 app=[n for n in members if n.startswith('services/pocketbase/') and ((Path(n).suffix in ['.go','.mod','.sum','.json','.yaml','.sh'] and not n.endswith('_test.go')) or n=='services/pocketbase/Dockerfile')]
 assert digest(app,members,m['git_commit'])==expected['app']
 common=['seed/generate.mjs','services/trailbase/run.sh','services/trailbase/compose.yaml']+[n for n in members if n.split('/')[0] in ['scripts','bench','test'] and '__pycache__' not in Path(n).parts]
 extra=[n for n in members if n=='runner/Dockerfile' or n.startswith('services/pocketbase/app/') and n.endswith('_test.go')]
 assert hashlib.sha256((digest(common,members,m['git_commit'])+digest(extra,members,m['git_commit'])).encode()).hexdigest()==expected['verification']
 smoke=m['mode']=='smoke';replay=b.measurement_verdict(summary,m['k6_exit_code'],p,smoke,m['load_after'])
 assert replay[0]==m['result'],(p.name,replay,m['result'])
 assert m['load_after']['limits']==b.RUNNER_LIMITS and m['load_after']['platform']=='linux/amd64'
 assert m['load_after']['image_manifest_digest']==bench.K6_MANIFEST
 if m['result']=='invalid' and m['reason']=='load generator OOM (not target capacity)':
  assert replay==('invalid','load generator OOM (not target capacity)')
  assert m['load_after']['State']['OOMKilled'] and m['load_after']['State']['ExitCode']==137
  assert bench.target_issue(m['target_before']['targets'],m['target_after']['targets']) is None
  image=m['tested_software']['native_build']['image_id'];s.validate_stack(m['target_before'],image);s.validate_stack(m['target_after'],image)
  assert bench.parent_oom(m['target_before']['parent'])==bench.parent_oom(m['target_after']['parent'])
  rows.append({'run':p.name,'outcome':'invalid','reason':m['reason'],'measurement_replay':replay,'all_original_checksums_verified':True,'archive_app_and_verification_hashes_reproduced':True,'runner_exit_code':137,'runner_oom_killed':True,'target_process_and_budget_unchanged':True,'no_hold_latency_or_capacity_score_claimed':True})
  print('Original invalid OOM bundle/checksum/source/target-health replay verified:',p.name,flush=True)
  continue
 if m['result']=='invalid':
  assert replay==('invalid','load generator used >=90% of its memory budget')
  assert summary,'RAM-invalid completed run must retain its diagnostic summary'
 image=m['tested_software']['native_build']['image_id']
 if m['result'] in ['pass','fail','invalid']:
  assert bench.target_issue(m['target_before']['targets'],m['target_after']['targets']) is None
  s.validate_stack(m['target_before'],image);s.validate_stack(m['target_after'],image)
  assert bench.parent_oom(m['target_after']['parent'])==bench.parent_oom(m['target_before']['parent'])
 assert m['load_after']['image_manifest_digest']==bench.K6_MANIFEST
 records=[json.loads(line) for line in (p/'resources.jsonl').read_text().splitlines()]
 children={'docker-'+v['Id']+'.scope' for v in m['target_before']['targets'].values()}
 for r in records:
  if 'target_stack' in r:
   parent=r['target_stack'];assert parent['cpu.max'].split()==['100000','100000'] and int(parent['memory.max'])==4294967296 and int(parent['memory.swap.max'])==0 and set(parent['children'])==children
  if 'load_kernel_cgroup' in r:
   k=r['load_kernel_cgroup'];assert k['cpu.max'].split()==['200000','100000'] and int(k['memory.max'])==8589934592 and int(k['memory.swap.max'])==0
 start=b.scenario_started(summary);lo,hi=(5,25) if smoke else (210,510)
 hold=[r for r in records if start+lo<=r['time']<start+hi];assert hold and all('target_stack' in r for r in hold)
 metrics=summary['metrics'];latency=metrics['http_req_duration{phase:hold}']['values'];durations=[];counts=collections.Counter();errors=collections.Counter();statuses={};schema_errors=0
 with gzip.open(p/'samples.json.gz','rt') as stream:
  for line in stream:
   row=json.loads(line)
   if row.get('type')!='Point':continue
   point=row['data'];tags=point.get('tags',{})
   if tags.get('phase')!='hold':continue
   name=tags.get('endpoint','unknown');value=point['value'];metric=row['metric']
   if metric=='http_req_duration':durations.append(value)
   elif metric=='http_reqs':counts[name]+=value;statuses.setdefault(name,collections.Counter())[tags.get('status','unknown')]+=value
   elif metric=='request_errors':errors[name]+=value
   elif metric=='schema_errors':schema_errors+=value
 durations.sort();assert sum(counts.values())==len(durations)==metrics['http_reqs{phase:hold}']['values']['count']
 assert sum(errors.values())==metrics['request_errors{phase:hold}']['values']['passes']
 assert schema_errors==metrics['schema_errors{phase:hold}']['values']['passes']
 quantiles={'min':durations[0],'max':durations[-1]}
 for name,q in [('med',.5),('p(95)',.95),('p(99)',.99)]:
  i=(len(durations)-1)*q;low=math.floor(i);high=math.ceil(i);quantiles[name]=durations[low]+(durations[high]-durations[low])*(i-low)
 for name,value in quantiles.items():assert math.isclose(value,latency[name],rel_tol=1e-9,abs_tol=1e-6),(name,value,latency[name])
 rows.append({'run':p.name,'outcome':m['result'],'reason':m['reason'],'eligible_for_target_capacity_scoring':m['result']!='invalid','measurement_replay':replay,'all_original_checksums_verified':True,'archive_app_and_verification_hashes_reproduced':True,'raw_quantiles_reproduced':quantiles,'requests_by_endpoint':dict(counts),'errors_by_endpoint':dict(errors),'schema_errors':schema_errors,'statuses_by_endpoint':statuses,'hold_monitor_samples':len(hold),'hold_monitor_span_seconds':hold[-1]['time']-hold[0]['time'],'runner_peak_cpu_percent_one_core':max(float(r[b.LOAD]['CPUPerc'].rstrip('%')) for r in hold if b.LOAD in r),'runner_peak_memory_percent_8gib':max(float(r[b.LOAD]['MemPerc'].rstrip('%')) for r in hold if b.LOAD in r),'parent_peak_memory_bytes_including_cache':max(int(r['target_stack']['memory.current']) for r in hold),'host_swapouts_before':b.host_swapouts(records[0]),'host_swapouts_after':b.host_swapouts(records[-1])})
 print('Original checksum/source/raw quantile/resource replay verified:',p.name,flush=True)
out=ROOT/'results/pocketbase/vps16-linux-amd64/setup-evidence/retained-attempt-review.json'
out.write_text(json.dumps({'attempts':rows},indent=2)+'\n')
