#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path('/opt/twelve-dollar-baas-supabase-16g/src');state=json.loads((ROOT/'.state/supabase/campaign.json').read_text());rows=[]
def counter(raw):return {k:int(v) for k,v in (line.split() for line in raw.splitlines())}
def pressure(raw):return {line.split()[0]:{k:float(v) for k,v in (piece.split('=') for piece in line.split()[1:])} for line in raw.splitlines()}
for entry in state['attempts']:
 p=ROOT/entry['path'];sm=json.loads((p/'k6-summary.json').read_text());started=sm['metrics']['benchmark_scenario_start_ms']['values']['value']/1000
 records=[json.loads(line) for line in (p/'resources.jsonl').read_text().splitlines()];hold=[r for r in records if started+210<=r['time']<started+510];a,z=hold[0],hold[-1];elapsed=z['time']-a['time']
 cpua=[int(v) for v in a['linux_stat'].splitlines()[0].split()[1:9]];cpuz=[int(v) for v in z['linux_stat'].splitlines()[0].split()[1:9]];delta=[end-begin for begin,end in zip(cpua,cpuz)];ticks=sum(delta)
 mem=lambda r:{k.rstrip(':'):int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in r['linux_meminfo'].splitlines())}
 ac=counter(a['target_stack']['cpu.stat']);zc=counter(z['target_stack']['cpu.stat']);periods=zc['nr_periods']-ac['nr_periods']
 rows.append({'run':p.name,'hold_samples':len(hold),'span_seconds':elapsed,'host_mean_steal_percent':100*delta[7]/ticks,'host_mean_iowait_percent':100*delta[4]/ticks,'host_mean_nonidle_non_iowait_percent':100*(ticks-delta[3]-delta[4])/ticks,'host_min_MemAvailable_bytes':min(mem(r)['MemAvailable'] for r in hold),'host_peak_cpu_pressure_some_avg10':max(pressure(r['linux_pressure_cpu'])['some']['avg10'] for r in hold),'host_peak_memory_pressure_some_avg10':max(pressure(r['linux_pressure_memory'])['some']['avg10'] for r in hold),'host_peak_io_pressure_some_avg10':max(pressure(r['linux_pressure_io'])['some']['avg10'] for r in hold),'aggregate_serving_mean_cpu_cores':(zc['usage_usec']-ac['usage_usec'])/(elapsed*1e6),'aggregate_serving_throttled_period_percent':100*(zc['nr_throttled']-ac['nr_throttled'])/periods if periods else None,'aggregate_serving_peak_memory_bytes_including_cache':max(int(r['target_stack']['memory.current']) for r in hold)})
(ROOT.parent/'setup-evidence/host-parent-review.json').write_text(json.dumps({'attempts':rows,'interpretation':'Shared-host raw counter review; CPU pressure/throttling describes the quota-limited workload and is not proof of unrelated interference or dedicated-machine equivalence. Storage/thermal/provider interference is not fully attributable.'},indent=2)+'\n')
print('Raw Linux host and aggregate serving counters reviewed for',len(rows),'attempts.')
