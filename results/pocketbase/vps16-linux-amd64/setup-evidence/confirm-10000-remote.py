#!/usr/bin/env python3
"""Three independent unchanged native CLI holds, bounded by original12slots."""
import json,os,subprocess
from pathlib import Path
ROOT=Path('/opt/twelve-dollar-baas-pocketbase-16g/src');os.chdir(ROOT)
TRACK=ROOT/'results/pocketbase/vps16-linux-amd64'
base=TRACK/'20261015T154500193682Z-standard-10000vu-k6-2cpu-8g-v3'
compact=json.loads((base/'summary.json').read_text());manifest=json.loads((base/'manifest.json').read_text())
files=lambda:set(TRACK.glob('*vu-k6-2cpu-8g-v3'))
assert len(files())==8,'Unexpected consumed attempt count; inspect before more load'
output=TRACK/'setup-evidence/confirmation10000-phase.json'
assert not output.exists(),'Confirmation phase already exists; do not overwrite'
phase={'candidate_vus':10000,'status':'in_progress','attempts_before_phase':8,'total_attempt_budget':12,'confirmation_attempts':[],'tested_software':compact['tested_software'],'serving_budget':compact['serving_budget'],'runner_budget':compact['runner_budget'],'inputs':manifest['inputs'],'scope':'Three independent full holds after canonical reset; bounded search did not resolve250VU boundary. Confirmed lower bound only, not maximum.'}
def save():output.write_text(json.dumps(phase,indent=2)+'\n')
save()
try:
 for index in range(1,4):
  before=files();assert len(before)<12
  code=subprocess.run(['bash','services/pocketbase/run.sh','bench','--vus','10000']).returncode
  after=files();new=after-before
  assert len(new)==1,'Expected one new retained attempt'
  p=new.pop();value=json.loads((p/'summary.json').read_text());m=json.loads((p/'manifest.json').read_text())
  assert value['vus']==10000 and value['mode']=='capacity' and m['inputs']==phase['inputs']
  assert code==(0 if value['outcome']=='pass' else 1)
  phase['confirmation_attempts'].append({'index':index,'path':str(p.relative_to(ROOT)),'outcome':value['outcome'],'reason':value['reason']});save()
  print('INDEPENDENT_CONFIRMATION_RETAINED',index,value['outcome'],p.name,flush=True)
  if value['outcome']=='invalid':raise RuntimeError('Invalid confirmation; stop, do not infer target failure')
 phase['status']='three_passes_pending_evidence_review' if all(v['outcome']=='pass' for v in phase['confirmation_attempts']) else 'not_confirmed'
 save()
 if phase['status']!='three_passes_pending_evidence_review':raise RuntimeError('Candidate did not pass all three independent confirmations; no score')
 print('THREE_10000VU_PASSES_PENDING_ORIGINAL_EVIDENCE_REVIEW',flush=True)
except BaseException as error:
 phase['status']='paused_unconfirmed';phase['reason']=str(error);save();raise
