#!/usr/bin/env python3
"""Read-only host and aggregate counter review; no interference attribution."""
import json
from pathlib import Path
ROOT=Path('/opt/twelve-dollar-baas-pocketbase-16g/src');rows=[]
def counter(raw):return {k:int(v) for k,v in (line.split() for line in raw.splitlines())}
def pressure(raw):return {line.split()[0]:{k:float(v) for k,v in (piece.split('=') for piece in line.split()[1:])} for line in raw.splitlines()}
for p in sorted((ROOT/'results/pocketbase/vps16-linux-amd64').glob('*vu-*')):
 m=json.loads((p/'manifest.json').read_text())
 if not (p/'k6-summary.json').exists():rows.append({'run':p.name,'outcome':m['result'],'no_scored_hold':True});continue
 sm=json.loads((p/'k6-summary.json').read_text())
 if 'benchmark_scenario_start_ms' not in sm.get('metrics',{}):rows.append({'run':p.name,'outcome':m['result'],'no_scored_hold':True});continue
 started=sm['metrics']['benchmark_scenario_start_ms']['values']['value']/1000
 lo,hi=(5,25) if m['mode']=='smoke' else (210,510)
 records=[json.loads(line) for line in (p/'resources.jsonl').read_text().splitlines()];hold=[r for r in records if started+lo<=r['time']<started+hi];a,z=hold[0],hold[-1];elapsed=z['time']-a['time']
 cpua=[int(v) for v in a['linux_stat'].splitlines()[0].split()[1:9]];cpuz=[int(v) for v in z['linux_stat'].splitlines()[0].split()[1:9]];delta=[end-begin for begin,end in zip(cpua,cpuz)];ticks=sum(delta)
 mem=lambda r:{k.rstrip(':'):int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in r['linux_meminfo'].splitlines())}
 ac=counter(a['target_stack']['cpu.stat']);zc=counter(z['target_stack']['cpu.stat']);periods=zc['nr_periods']-ac['nr_periods']
 rows.append({'run':p.name,'outcome':m['result'],'eligible_for_target_capacity_scoring':m['result']!='invalid','hold_samples':len(hold),'span_seconds':elapsed,'host_mean_steal_percent':100*delta[7]/ticks,'host_mean_iowait_percent':100*delta[4]/ticks,'host_min_MemAvailable_bytes':min(mem(r)['MemAvailable'] for r in hold),'host_peak_cpu_pressure_some_avg10':max(pressure(r['linux_pressure_cpu'])['some']['avg10'] for r in hold),'host_peak_memory_pressure_some_avg10':max(pressure(r['linux_pressure_memory'])['some']['avg10'] for r in hold),'host_peak_io_pressure_some_avg10':max(pressure(r['linux_pressure_io'])['some']['avg10'] for r in hold),'aggregate_serving_mean_cpu_cores':(zc['usage_usec']-ac['usage_usec'])/(elapsed*1e6),'aggregate_serving_throttled_period_percent':100*(zc['nr_throttled']-ac['nr_throttled'])/periods if periods else None,'aggregate_serving_peak_charged_memory_bytes_including_accounted_cache':max(int(r['target_stack']['memory.current']) for r in hold)})
(ROOT/'results/pocketbase/vps16-linux-amd64/setup-evidence/host-parent-review.json').write_text(json.dumps({'attempts':rows,'interpretation':'Shared-host counters, not dedicated-VPS equivalence or proof of unrelated interference. Charged cgroup memory includes accounted cache, not all preexisting shared-host page cache. No cache flush performed.'},indent=2)+'\n')
print('ORIGINAL_HOST_AND_PARENT_COUNTERS_REVIEWED',len(rows))
