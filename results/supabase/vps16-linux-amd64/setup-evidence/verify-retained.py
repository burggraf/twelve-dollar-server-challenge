#!/usr/bin/env python3
"""Run on designated native host: replay retained attempts without mutating originals."""
import hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path('/opt/twelve-dollar-baas-supabase-16g/src');os.chdir(ROOT)
os.environ.update(BENCHMARK_PROJECT='baas-supabase-vps16',BENCHMARK_RUNNER_PROFILE='k6-2cpu-8g-v3',RUNNER_MEMORY='8g')
sys.path.insert(0,str(ROOT/'scripts'))
import benchmark as b
import supabase_benchmark as bench
import supabase_profile as s
track=ROOT/'results/supabase/vps16-linux-amd64'
state=json.loads((ROOT/'.state/supabase/campaign.json').read_text())
expected=json.loads((ROOT.parent/'setup-evidence/capacity-frozen-correctness-manifest.json').read_text())['inputs']
reviews=[]
for attempt in state['attempts']:
 p=ROOT/attempt['path'];m=json.loads((p/'manifest.json').read_text());summary=json.loads((p/'k6-summary.json').read_text()) if (p/'k6-summary.json').exists() else {}
 for line in (p/'SHA256SUMS').read_text().splitlines():
  digest,name=line.split('  ',1);assert hashlib.sha256((p/name).read_bytes()).hexdigest()==digest,(p.name,name)
 assert m['inputs']==expected
 assert json.loads((p/'correctness-manifest.json').read_text())['inputs']==expected
 assert hashlib.sha256((p/'correctness.log').read_bytes()).hexdigest()==json.loads((p/'correctness-manifest.json').read_text())['log_sha256']
 dataset=json.loads((p/'dataset.json').read_text());assert dataset['content_sha256']=='738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d';assert dataset['counts']=={'users':50000,'posts':500000,'likes':2016005};assert dataset['native_auth_accounts_before']==dataset['native_auth_accounts_after']==0
 with tarfile.open(p/'source.tar.gz') as t:
  members={v.name:t.extractfile(v).read() for v in t.getmembers() if v.isfile()}
  assert not any(n.startswith('/') or '..' in Path(n).parts or '/.state/' in n or n.endswith('tokens.json') or n.endswith('stack.env') for n in members)
  app=hashlib.sha256()
  for name in sorted(n for n in members if n.startswith('services/supabase/') and Path(n).suffix in ['.yaml','.json','.sql','.ts','.mjs','.sh','.py'] and not n.endswith('.test.mjs')):app.update(name.encode()+b'\0'+members[name]+b'\0')
  assert app.hexdigest()==expected['app']
  verification=hashlib.sha256()
  source_names=['seed/generate.mjs','services/trailbase/run.sh','services/trailbase/compose.yaml']+[n for n in members if n.split('/')[0] in ['scripts','bench','test'] and '__pycache__' not in Path(n).parts]
  for name in sorted(source_names):
   raw=members.get(name)
   if raw is None:raw=subprocess.check_output(['git','show',m['git_commit']+':'+name],cwd=ROOT)
   verification.update(name.encode()+b'\0'+raw+b'\0')
  additional=hashlib.sha256()
  for name in sorted(n for n in members if n=='runner/Dockerfile' or n.startswith('services/supabase/functions/') and n.endswith('.test.mjs')):additional.update(name.encode()+b'\0'+members[name]+b'\0')
  assert hashlib.sha256((verification.hexdigest()+additional.hexdigest()).encode()).hexdigest()==expected['verification']
 replay=b.measurement_verdict(summary,m['k6_exit_code'],p,False,m['load_after'])
 records=[json.loads(line) for line in (p/'resources.jsonl').read_text().splitlines()]
 expected_children={f'docker-{v["Id"]}.scope' for v in m['target_before']['targets'].values()}
 for r in records:
  parent=r.get('target_stack')
  if parent:
   assert parent['cpu.max'].split()==['100000','100000'] and int(parent['memory.max'])==4*1024**3 and int(parent['memory.swap.max'])==0
   assert set(parent['children'])==expected_children
  kernel=r.get('load_kernel_cgroup')
  if kernel:assert kernel['cpu.max'].split()==['200000','100000'] and int(kernel['memory.max'])==8*1024**3 and int(kernel['memory.swap.max'])==0
 if m['result']=='pass':
  assert replay==('pass','hold gates passed')
  assert bench.target_issue(m['target_before']['targets'],m['target_after']['targets']) is None
  s.validate_stack(m['target_before']);s.validate_stack(m['target_after'])
  assert m['load_after']['image_manifest_digest']==bench.K6_MANIFEST
  assert bench.parent_oom(m['target_after']['parent'])==bench.parent_oom(m['target_before']['parent'])
 started=b.scenario_started(summary) if summary else None
 hold=[r for r in records if started and started+210<=r['time']<started+510]
 cpu=[float(r[b.LOAD]['CPUPerc'].rstrip('%')) for r in hold if b.LOAD in r];memory=[float(r[b.LOAD]['MemPerc'].rstrip('%')) for r in hold if b.LOAD in r]
 endpoint={name:{metric:summary.get('metrics',{}).get(metric+'{phase:hold,endpoint:'+name+'}',{}).get('values',{}) for metric in ['http_req_duration','http_reqs','request_errors']} for name in ['feed','detail','like','create']}
 if summary:assert sum(v['http_reqs'].get('count',0) for v in endpoint.values())==summary['metrics']['http_reqs{phase:hold}']['values']['count']
 reviews.append({'run':p.name,'vus':m['vus'],'outcome':m['result'],'reason':m['reason'],'fixed_measurement_replay':replay,'hold_monitor_samples':len(hold),'hold_monitor_span_seconds':hold[-1]['time']-hold[0]['time'] if hold else None,'runner_peak_cpu_percent_one_core':max(cpu) if cpu else None,'runner_peak_memory_percent_eight_gib':max(memory) if memory else None,'aggregate_serving_peak_memory_bytes_including_cache':max((int(r['target_stack']['memory.current']) for r in hold if 'target_stack' in r),default=None),'host_swapouts_before':b.host_swapouts(records[0]),'host_swapouts_after':b.host_swapouts(records[-1]),'endpoint_latency_values':endpoint})
out=ROOT.parent/'setup-evidence/capacity-resource-replay-review.json';out.write_text(json.dumps({'campaign':state,'attempts':reviews},indent=2)+'\n')
print('Original source/checksum/data/image/cgroup/correctness and fixed scoring/resource replay verified for',len(reviews),'retained attempts.')
