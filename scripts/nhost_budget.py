"""One native profile's immutable physical reservations, fsynced BEFORE lifecycle actions.

Limits include failed/invalid attempts across source revisions. An explicit hash-bound
owner amendment adds two smoke slots only; no automatic refill, adoption or pooling.
"""
import hashlib,json,os,re
from pathlib import Path
import nhost_profile as s
ROOT=s.STATE/'attempt-ledger'
POLICY={'version':1,'project':s.PROJECT,'runner':'k6-2cpu-8g-v3','maximum_full_attempts':24,'maximum_smoke_attempts':4}
SMOKE_AMENDMENT_SHA256='0853e766456d1540aa4336b43966ec8327d6730a0619ab0feb1a92073041b049'
def effective_policy():
 path=ROOT/'owner-smoke-extension-v2.json'
 if path.is_symlink():raise RuntimeError('Owner smoke amendment must be an original regular file')
 if not path.exists():return POLICY
 if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=SMOKE_AMENDMENT_SHA256:raise RuntimeError('Owner smoke amendment changed; no implicit extension')
 return {**POLICY,'version':2,'maximum_smoke_attempts':6,'base_policy':POLICY,'owner_amendment_sha256':SMOKE_AMENDMENT_SHA256}
def exclusive(path,value):
 with os.fdopen(os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w') as stream:json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
 fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def rows():
 ROOT.mkdir(parents=True,exist_ok=True);policy=ROOT/'policy.json'
 if not policy.exists():exclusive(policy,POLICY)
 if json.loads(policy.read_text())!=POLICY:raise RuntimeError('Native physical attempt policy changed; no refill')
 values=[]
 for ordinal,path in enumerate(sorted(ROOT.glob('*-reserved.json')),1):
  ticket=json.loads(path.read_text())
  if path.name!=f'{ordinal:04}-reserved.json' or ticket['ordinal']!=ordinal or type(ticket['vus']) is not int or not 1<=ticket['vus']<=20000 or ticket['mode'] not in {'capacity','smoke'} or not re.fullmatch('[a-f0-9]{64}',ticket['proof_sha256']):raise RuntimeError('Physical attempt ledger malformed')
  final=ROOT/f'{ordinal:04}-finished.json';done=json.loads(final.read_text()) if final.exists() else None
  if done and (done.get('ordinal')!=ordinal or done.get('outcome') not in {'pass','fail','invalid'} or not isinstance(done.get('path'),str)):raise RuntimeError('Physical attempt completion malformed')
  values.append((ticket,done))
 if len(list(ROOT.glob('*-finished.json')))!=sum(done is not None for _,done in values):raise RuntimeError('Orphan attempt completion; no silent repair')
 limits=effective_policy()
 if any(sum(ticket['mode']==mode for ticket,_ in values)>limits[key] for mode,key in [('capacity','maximum_full_attempts'),('smoke','maximum_smoke_attempts')]):raise RuntimeError('Physical history exceeds authorized policy; no hidden extension removal')
 return values
def reserve(vus,smoke,proof_sha256):
 if type(vus) is not int or not 1<=vus<=20000 or type(smoke) is not bool or not isinstance(proof_sha256,str) or not re.fullmatch('[a-f0-9]{64}',proof_sha256):raise RuntimeError('Invalid native reservation request')
 records=rows()
 if any(done is None for _,done in records):raise RuntimeError('Unfinished physical reservation; no adoption/retry')
 mode='smoke' if smoke else 'capacity';maximum=effective_policy()['maximum_smoke_attempts' if smoke else 'maximum_full_attempts']
 if sum(ticket['mode']==mode for ticket,_ in records)>=maximum:raise RuntimeError('Physical attempt budget exhausted; invalid attempts consumed slots')
 ticket={'ordinal':len(records)+1,'vus':vus,'mode':mode,'proof_sha256':proof_sha256,'pid':os.getpid()};exclusive(ROOT/f"{ticket['ordinal']:04}-reserved.json",ticket);return ticket
def require(vus,smoke,proof_sha256):
 records=rows()
 if not records:raise RuntimeError('No durable physical reservation before lifecycle/load')
 ticket,done=records[-1]
 if done is not None or (ticket['vus'],ticket['mode'],ticket['proof_sha256'],ticket['pid'])!=(vus,'smoke' if smoke else 'capacity',proof_sha256,os.getpid()):raise RuntimeError('Physical reservation ownership/profile/qualification mismatch')
 return ticket
def finish(ticket,outcome,path):
 if outcome not in {'pass','fail','invalid'} or not isinstance(path,str):raise RuntimeError('Invalid physical attempt completion')
 expected=require(ticket['vus'],ticket['mode']=='smoke',ticket['proof_sha256'])
 if expected!=ticket:raise RuntimeError('Physical reservation mutated')
 exclusive(ROOT/f"{ticket['ordinal']:04}-finished.json",{'ordinal':ticket['ordinal'],'outcome':outcome,'path':path})
def history(proof_sha256,smoke=False):
 records=rows()
 if any(done is None for _,done in records):raise RuntimeError('Unfinished physical reservation; no campaign replay/adoption')
 return [ticket|done for ticket,done in records if ticket['proof_sha256']==proof_sha256 and ticket['mode']==('smoke' if smoke else 'capacity')]
