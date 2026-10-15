from pathlib import Path
import hashlib,json,os,re,shutil,sys,tarfile
os.environ['BENCHMARK_PROJECT']='baas-trailbase-vps16'
os.environ['BENCHMARK_RUNNER_PROFILE']='k6-2cpu-8g-v3'
sys.path.insert(0,'scripts')
import benchmark as b
stage=Path('.state/vps16/retained-confirmations');root=Path('results/trailbase/vps16-linux-amd64')
phase=json.loads((stage/'confirmation15000-state.json').read_text())
assert phase['status']=='confirmed_lower_bound_pending_human_review' and len(phase['attempts'])==3
assert len({a['run_id'] for a in phase['attempts']})==3
report={'scope':'15,000-VU confirmed lower bound; not a target maximum','phase':phase['status'],'runs':[],'continuity':phase['continuity']}
def percent(sample,key):return float(sample[key].rstrip('%'))
def mem_available(row):return int(next(l.split()[1] for l in row['linux_meminfo'].splitlines() if l.startswith('MemAvailable:')))
def cpu(row):return [int(x) for x in row['linux_stat'].splitlines()[0].split()[1:9]]
def pressure(row,key,kind):
 line=next(l for l in row[key].splitlines() if l.startswith(kind+' '))
 return int(dict(v.split('=') for v in line.split()[1:])['total'])
for attempt in phase['attempts']:
 p=stage/attempt['run_id'];assert attempt['run_id'] not in phase['prior_run_ids']
 for line in (p/'SHA256SUMS').read_text().splitlines():
  digest,name=line.split('  ',1);assert hashlib.sha256((p/name).read_bytes()).hexdigest()==digest,(p.name,name)
 m=json.loads((p/'manifest.json').read_text());a=json.loads((p/'correctness-manifest.json').read_text());k=json.loads((p/'k6-summary.json').read_text());s=json.loads((p/'summary.json').read_text())
 assert a['app_source_sha256']==b.app_source_hash() and a['verification_source_sha256']==b.verification_source_hash()
 assert a['log_sha256']==hashlib.sha256((p/'correctness.log').read_bytes()).hexdigest()
 assert m['result']=='pass' and m['vus']==15000 and m['tier']=='standard' and m['runner_profile']=='k6-2cpu-8g-v3'
 for name in ['target_before','target_after','load_after']:
  assert m[name]['platform']=='linux/amd64'
 assert m['load_after']['image_manifest_digest']=='sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656'
 for name in ['target_before','target_after']:
  assert m[name]['limits']=={'NanoCpus':10**9,'Memory':4*1024**3,'MemorySwap':4*1024**3}
  assert m[name]['source_sha256']==b.app_source_hash() and m[name]['State']['Running'] and not m[name]['State']['OOMKilled']
 assert m['target_before']['State']['StartedAt']==m['target_after']['State']['StartedAt']
 assert m['target_before']['RestartCount']==m['target_after']['RestartCount']==0
 assert m['load_after']['limits']==b.RUNNER_LIMITS and not m['load_after']['State']['OOMKilled']
 assert b.evaluate(k,m['k6_exit_code'])==('pass','hold gates passed')
 start=b.scenario_started(k);assert b.resource_verdict(p,start,False,m['load_after']) is None
 assert (root/'progress'/f"{p.name.split('-standard-')[0]}-standard-15000vu-summary.json").read_bytes()==(p/'summary.json').read_bytes()
 with tarfile.open(p/'source.tar.gz') as archive:
  for member in archive.getmembers():
   assert Path(member.name).name!='tokens.json' and '.state' not in Path(member.name).parts
   path=b.ROOT/member.name
   relevant=member.name.startswith(('bench/','scripts/','test/','services/trailbase/app/src/','services/trailbase/migrations/')) or member.name in ['seed/generate.mjs','services/trailbase/run.sh','services/trailbase/compose.yaml','services/trailbase/Dockerfile','services/trailbase/entrypoint.sh','services/trailbase/config.textproto','services/trailbase/app/Cargo.toml','services/trailbase/app/Cargo.lock']
   if member.isfile() and relevant: assert archive.extractfile(member).read()==path.read_bytes(),member.name
 for log in [*p.glob('*.log'),p/'manifest.json',p/'working-tree.patch']:
  assert not re.search(rb'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',log.read_bytes()),('possible issued JWT',log.name)
 rows=[json.loads(l) for l in (p/'resources.jsonl').read_text().splitlines()]
 hold=[r for r in rows if start+210<=r['time']<start+510]
 load=[r[b.LOAD] for r in hold if b.LOAD in r];target=[r[b.TARGET] for r in hold if b.TARGET in r]
 delta=[y-x for x,y in zip(cpu(hold[0]),cpu(hold[-1]))];ticks=sum(delta)
 elapsed=hold[-1]['time']-hold[0]['time']
 stats={'run_id':p.name,'requests':s['hold_requests'],'rps':s['hold_rps'],'latency_ms':s['latency_ms'],
 'runner_cpu_peak_percent':max(percent(v,'CPUPerc') for v in load),'runner_cpu_mean_percent':sum(percent(v,'CPUPerc') for v in load)/len(load),
 'runner_memory_peak_percent':max(percent(v,'MemPerc') for v in load),'target_cpu_peak_percent':max(percent(v,'CPUPerc') for v in target),
 'target_memory_peak_percent':max(percent(v,'MemPerc') for v in target),'minimum_host_available_kib':min(mem_available(r) for r in hold),
 'hold_monitor_samples':len(load),'sample_span_seconds':elapsed,'host_steal_percent':100*delta[7]/ticks,'host_iowait_percent':100*delta[4]/ticks,
 'host_swapouts_before':b.host_swapouts(rows[0]),'host_swapouts_after':b.host_swapouts(rows[-1])}
 for name in ['cpu','memory','io']:
  for kind in ['some']+([] if name=='cpu' else ['full']):
   key='linux_pressure_'+name
   stats[f'host_{name}_pressure_{kind}_percent']=100*(pressure(hold[-1],key,kind)-pressure(hold[0],key,kind))/(elapsed*1e6)
 report['runs'].append(stats)
 assert not (root/p.name).exists();shutil.move(str(p),str(root/p.name))
for name in ['confirmation15000-state.json','confirm-15000-job.log','container-lifecycle-confirm15000.log']:
 dest=root/'setup-evidence'/name;assert not dest.exists();shutil.copy2(stage/name,dest)
(root/'setup-evidence/confirmation15000-resource-review.json').write_text(json.dumps(report,indent=2)+'\n')
b.checksum_files(root/'setup-evidence')
print(json.dumps(report,indent=2))
print('VPS16_ALL_THREE_CONFIRMATIONS_RETAINED_AND_REPLAY_VERIFIED')
