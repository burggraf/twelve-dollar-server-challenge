#!/usr/bin/env python3
"""Read-only ORIGINAL serving-OOM failure replay; not healthy-capacity acceptance."""
import collections,gzip,hashlib,json,math,os,re,sys,tarfile
from pathlib import Path
ROOT=Path('/opt/twelve-dollar-baas-convexpg-16g/src');os.chdir(ROOT);sys.path.insert(0,str(ROOT/'scripts'))
import benchmark as b
import convex_benchmark as bench
import convex_profile as s
s.require_native();name=sys.argv[1];prefix=sys.argv[2]
assert re.fullmatch(r'[0-9]{8}T[0-9]{12}Z-standard-[0-9]+vu-k6-2cpu-8g-v3(?:-smoke)?',name)
assert re.fullmatch(r'native-[a-z0-9-]+',prefix)
p=bench.RESULTS/name;m=json.loads((p/'manifest.json').read_text());k=json.loads((p/'k6-summary.json').read_text());summary=json.loads((p/'summary.json').read_text());smoke=m['mode']=='smoke'
for line in (p/'SHA256SUMS').read_text().splitlines():
 sha,path=line.split('  ',1);assert Path(path).name==path;assert hashlib.sha256((p/path).read_bytes()).hexdigest()==sha
expected=json.loads((s.STATE/'correctness-manifest.json').read_text())['inputs'];assert m['inputs']==expected
c=json.loads((p/'correctness-manifest.json').read_text());assert c['inputs']==expected and hashlib.sha256((p/'correctness.log').read_bytes()).hexdigest()==c['log_sha256']
data=json.loads((p/'dataset.json').read_text());assert data['content_sha256']=='738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d' and data['counts']=={'users':50000,'posts':500000,'likes':2016005}
source_count=0
with tarfile.open(p/'source.tar.gz') as archive:
 for entry in archive.getmembers():
  path=Path(entry.name);assert not path.is_absolute() and '..' not in path.parts and '.state' not in path.parts and not path.name.startswith('.env') and 'node_modules' not in path.parts
  if not entry.isfile():continue
  assert (ROOT/path).is_file() and archive.extractfile(entry).read()==(ROOT/path).read_bytes(), entry.name
  source_count+=1
replay=b.measurement_verdict(k,m['k6_exit_code'],p,smoke,m['load_after']);runtime_issue=bench.runtime_issue(m['target_before'],m['target_after'])
assert replay[0]==m['result']=='fail' and runtime_issue
backend=m['target_after']['targets']['backend']['State'];assert backend['OOMKilled'] and backend['ExitCode']==137 and not backend['Running']
def events(profile):return dict(line.split() for line in profile['parent']['memory.events'].splitlines())
before_events=events(m['target_before']);after_events=events(m['target_after']);assert int(after_events['oom_kill'])-int(before_events['oom_kill'])==1 and int(after_events['oom'])>int(before_events['oom'])
pg_child='docker-'+m['target_before']['targets']['postgres']['Id']+'.scope'
assert m['load_after']['limits']==b.RUNNER_LIMITS and m['load_after']['platform']=='linux/amd64' and m['load_after']['image_manifest_digest']==bench.K6_MANIFEST
records=[json.loads(line) for line in (p/'resources.jsonl').read_text().splitlines()];children={'docker-'+v['Id']+'.scope' for v in m['target_before']['targets'].values()};kernels=[]
for record in records:
 parent=record['target_stack'];assert parent['cpu.max'].split()==['100000','100000'] and int(parent['memory.max'])==4294967296 and int(parent['memory.swap.max'])==0 and set(parent['children']).issubset(children) and pg_child in parent['children']
 if 'load_kernel_cgroup' in record:
  kernel=record['load_kernel_cgroup'];assert kernel['cpu.max'].split()==['200000','100000'] and int(kernel['memory.max'])==8589934592 and int(kernel['memory.swap.max'])==0;kernels.append(kernel)
assert kernels
start=b.scenario_started(k);lo,hi=(5,25) if smoke else (210,510);hold=[r for r in records if start+lo<=r['time']<start+hi];assert len(hold)>=3
metrics=k['metrics'];latency=metrics['http_req_duration{phase:hold}']['values'];durations=[];counts=collections.Counter();errors=collections.Counter();statuses={};schema_errors=0;raw_rows=0
with gzip.open(p/'samples.json.gz','rt') as stream:
 for line in stream:
  raw_rows+=1;row=json.loads(line)
  if row.get('type')!='Point':continue
  point=row['data'];tags=point.get('tags',{})
  if tags.get('phase')!='hold':continue
  endpoint=tags.get('endpoint','unknown');value=point['value'];metric=row['metric']
  if metric=='http_req_duration':durations.append(value)
  elif metric=='http_reqs':counts[endpoint]+=value;statuses.setdefault(endpoint,collections.Counter())[tags.get('status','unknown')]+=value
  elif metric=='request_errors':errors[endpoint]+=value
  elif metric=='schema_errors':schema_errors+=value
assert sum(counts.values())==len(durations)==metrics['http_reqs{phase:hold}']['values']['count']==summary['hold_requests']
assert sum(errors.values())==metrics['request_errors{phase:hold}']['values']['passes']==summary['request_errors']['passes']
assert schema_errors==metrics['schema_errors{phase:hold}']['values']['passes']==summary['schema_errors']['passes']
durations.sort();quantiles={'min':durations[0],'max':durations[-1]}
for key,q in [('med',.5),('p(95)',.95),('p(99)',.99)]:
 i=(len(durations)-1)*q;low=math.floor(i);high=math.ceil(i);quantiles[key]=durations[low]+(durations[high]-durations[low])*(i-low)
for key,value in quantiles.items():assert math.isclose(value,latency[key],rel_tol=1e-9,abs_tol=1e-6) and math.isclose(value,summary['latency_ms'][key],rel_tol=1e-9,abs_tol=1e-6)
result={'run':name,'mode':m['mode'],'outcome':m['result'],'reason':m['reason'],'all_original_checksums_verified':True,'raw_rows':raw_rows,'raw_counts_and_quantiles_reproduced':True,'raw_quantiles_ms':quantiles,'requests_by_endpoint':dict(counts),'errors_by_endpoint':dict(errors),'statuses_by_endpoint':statuses,'schema_errors':schema_errors,'original_source_archive_files_compared_to_current_frozen_vps_bytes':source_count,'complete_frozen_inputs_match_correctness':True,'measurement_replay':replay,'runtime_issue':runtime_issue,'new_serving_backend_oom_exit137':True,'parent_events_before':before_events,'parent_events_after':after_events,'physical_full_attempts_consumed':1,'campaign_history_empty_does_not_erase_attempt':True,'not_capacity_confirmation':True,'actual_runner_kernel_sample_count':len(kernels),'hold_monitor_samples':len(hold),'hold_monitor_span_seconds':hold[-1]['time']-hold[0]['time'],'runner_peak_cpu_percent_one_core':max(float(r[b.LOAD]['CPUPerc'].rstrip('%')) for r in hold if b.LOAD in r),'runner_peak_memory_percent_8gib':max(float(r[b.LOAD]['MemPerc'].rstrip('%')) for r in hold if b.LOAD in r),'parent_max_observed_current_bytes':max(int(r['target_stack']['memory.current']) for r in records),'parent_lifetime_peak_after':int(m['target_after']['parent']['memory.peak']),'host_swapouts_before':b.host_swapouts(records[0]),'host_swapouts_after':b.host_swapouts(records[-1]),'clean_shutdown':m['clean_shutdown'],'not_capacity_bound':smoke}
with (ROOT.parent/'setup-evidence'/f'{prefix}-raw-review.json').open('x') as output:json.dump(result,output,indent=2);output.write('\n')
print('ORIGINAL_SERVING_OOM_FAILURE_ALL_RAW_POINTS_SOURCE_KERNEL_AND_COMMON_VERDICT_REPLAYED_NOT_CAPACITY_ACCEPTANCE_NO_REVIVAL',flush=True)
