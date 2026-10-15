#!/usr/bin/env python3
"""Native-host read-only raw hold-sample/status/host-counter audit; preserve original files."""
import collections,gzip,json,math
from pathlib import Path
ROOT=Path('/opt/twelve-dollar-baas-supabase-16g/src');state=json.loads((ROOT/'.state/supabase/campaign.json').read_text());rows=[]
for entry in state['attempts']:
 p=ROOT/entry['path'];sm=json.loads((p/'k6-summary.json').read_text());metrics=sm['metrics'];counts=collections.Counter();statuses={};durations=[];errors=collections.Counter()
 with gzip.open(p/'samples.json.gz','rt') as stream:
  for line in stream:
   row=json.loads(line)
   if row.get('type')!='Point':continue
   data=row['data'];tags=data.get('tags',{})
   if tags.get('phase')!='hold':continue
   metric=row['metric'];endpoint=tags.get('endpoint','unknown')
   if metric=='http_reqs':
    counts[endpoint]+=data['value'];statuses.setdefault(endpoint,collections.Counter())[tags.get('status','unknown')]+=data['value']
   elif metric=='http_req_duration':durations.append(data['value'])
   elif metric=='request_errors':errors[endpoint]+=data['value']
 expected=metrics['http_reqs{phase:hold}']['values']['count'];latency=metrics['http_req_duration{phase:hold}']['values'];durations.sort()
 assert sum(counts.values())==len(durations)==expected
 assert sum(errors.values())==metrics['request_errors{phase:hold}']['values']['passes']
 def percentile(p):
  index=(len(durations)-1)*p;lo=math.floor(index);hi=math.ceil(index)
  return durations[lo]+(durations[hi]-durations[lo])*(index-lo)
 quantiles={'med':percentile(.5),'p(95)':percentile(.95),'p(99)':percentile(.99),'min':durations[0],'max':durations[-1]}
 for name,value in quantiles.items():assert math.isclose(value,latency[name],rel_tol=1e-9,abs_tol=1e-6),(p.name,name,value,latency[name])
 resources=[json.loads(line) for line in (p/'resources.jsonl').read_text().splitlines()]
 # Report available raw host and parent counter keys without guessing their schema.
 rows.append({'run':p.name,'hold_requests':expected,'raw_quantiles_reproduced':quantiles,'request_errors_by_endpoint':dict(errors),'http_status_counts_by_endpoint':statuses,'resource_record_keys':list(resources[0]),'raw_stream_complete':True})
 print('Verified original raw request/error counts and exact quantiles:',p.name,flush=True)
out=ROOT.parent/'setup-evidence/raw-sample-audit.json';out.write_text(json.dumps({'attempts':rows},indent=2)+'\n')
