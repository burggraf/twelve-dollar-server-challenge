from pathlib import Path
import json
root=Path('results/trailbase/vps16-linux-amd64')
review=json.loads((root/'setup-evidence/confirmation15000-resource-review.json').read_text())
state=json.loads((root/'setup-evidence/confirmation15000-state.json').read_text())
assert len(review['runs'])==3 and all(a['outcome']=='pass' for a in state['attempts'])
runs=[];endpoint_lines=[]
for number,entry in enumerate(review['runs'],1):
 p=root/entry['run_id'];s=json.loads((p/'summary.json').read_text());m=json.loads((p/'manifest.json').read_text());k=json.loads((p/'k6-summary.json').read_text())['metrics']
 endpoints={}
 for endpoint in ['feed','detail','like','create']:
  suffix='{phase:hold,endpoint:'+endpoint+'}'
  count=k['http_reqs'+suffix]['values']['count'];errors=k['request_errors'+suffix]['values']
  assert errors['rate']==0 and errors['passes']+errors['fails']==count
  latency=k['http_req_duration'+suffix]['values']
  endpoints[endpoint]={'requests':count,'rps':count/300,'request_error_rate':errors['rate'],'latency_ms':latency}
  endpoint_lines.append(f"| {number} | {endpoint} | {count:,} | {count/300:,.2f} | {latency['med']:.2f} / {latency['p(95)']:.2f} / {latency['p(99)']:.2f} | 0% |")
 assert sum(e['requests'] for e in endpoints.values())==s['hold_requests']
 runs.append({'run_id':p.name,'hold_seconds':300,'summary':s,'endpoints':endpoints,'resources':entry})
a=json.loads((root/runs[0]['run_id']/'correctness-manifest.json').read_text())
summary={'outcome':'blocked','blocker':'Maximum discovery blocked by 20,000-VU load-generator OOM; no failing target bracket',
 'confirmed_lower_bound_vus':15000,'maximum_passing_vus':None,'owner_acceptance':'pending','publication':'local artifacts only; no commit/push/release',
 'serving':{'cpus':1,'memory_bytes':4*1024**3,'swap_bytes':0},'runner':{'profile':'k6-2cpu-8g-v3','cpus':2,'memory_bytes':8*1024**3,'swap_bytes':0},
 'host':{'name':'azabab.com','cpus':4,'memory_bytes':16770072576,'platform':'linux/amd64','os':'Ubuntu 24.04.5 LTS','docker':'29.8.1','monthly_price':None,'region':None},
 'service':{'name':'TrailBase','version':'0.34.6','sdk':'0.6.1','compiler':'Rust 1.91.1','timed_path':'k6 -> native TrailBase WASM routes -> TrailBase database APIs -> SQLite WAL/NORMAL'},
 'correctness':a,'canonical_data':{'users':50000,'posts':500000,'likes':2016005,'sha256':'738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d'},
 'total_confirmation_hold_requests':sum(r['summary']['hold_requests'] for r in runs),'total_scored_seconds':900,
 'confirmation_rps_range':[min(r['summary']['hold_rps'] for r in runs),max(r['summary']['hold_rps'] for r in runs)],
 'confirmations':runs,'continuity':state['continuity'],
 'limitations':['No target maximum: 20,000-VU attempt invalid on generator OOM','Shared-host CPU pressure and small nonzero steal; no dedicated-machine equivalence','Generator brief quota-level CPU spikes and up to 87.54% RAM; no frozen invalidation gate triggered','Maximum latency outliers retained, including 2,522.26 ms; percentiles are not maxima','Native login throughput and power-loss durability not measured','Monthly cost/region unknown; no $12 or cost/request equivalence','Native AMD64 images reused from previous host; fresh correctness/holds, not a fresh compilation claim']}
(root/'confirmed-lower-bound.json').write_text(json.dumps(summary,indent=2)+'\n')
(root/'endpoint-confirmations.md').write_text('# Confirmation endpoint breakdowns\n\nEach row covers a separate 300-second scored hold at 15,000 VUs. No quantiles are pooled or averaged. All successful-response schema checks passed; aggregate schema-error rate is zero for every hold. Full precision, maxima, and all-phase metrics remain in each raw `k6-summary.json`.\n\n| Hold | Endpoint | Requests | Requests/s | p50 / p95 / p99 ms | Request errors |\n|---|---|---:|---:|---:|---:|\n'+'\n'.join(endpoint_lines)+'\n')
print('Verified derived totals:',summary['total_confirmation_hold_requests'],'requests / 900 scored seconds; rps range',summary['confirmation_rps_range'])
