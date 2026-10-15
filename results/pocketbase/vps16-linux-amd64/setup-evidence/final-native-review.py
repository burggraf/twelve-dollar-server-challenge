#!/usr/bin/env python3
"""Native read-only attestation, actual-value privacy and continuity review."""
import hashlib,json,re,sqlite3,sys
from pathlib import Path
ROOT=Path('/opt/twelve-dollar-baas-pocketbase-16g/src');sys.path.insert(0,str(ROOT/'scripts'))
import pocketbase_profile as s
import pocketbase_benchmark as b
out=ROOT/'results/pocketbase/vps16-linux-amd64/setup-evidence'
att=json.loads((s.STATE/'correctness-manifest.json').read_text());current=s.deployment_attestation()
b.validate_correctness(att,b.inputs(current),hashlib.sha256((s.STATE/'correctness.log').read_bytes()).hexdigest())
phase=json.loads((out/'confirmation10000-phase.json').read_text());assert phase['status']=='three_passes_pending_evidence_review' and len(phase['confirmation_attempts'])==3 and all(v['outcome']=='pass' for v in phase['confirmation_attempts'])
assert len(list(out.parent.glob('*vu-k6-2cpu-8g-v3')))==11
(out/'final-deployment-attestation.json').write_text(json.dumps(current,indent=2)+'\n')
key=s.runtime_values()['JWT_SECRET'].encode();signatures={v['token'].split('.')[2].encode() for v in json.loads((ROOT/'.state/seed/tokens.json').read_text())}
with sqlite3.connect(s.database_path().as_uri()+'?mode=ro',uri=True) as db:
 native_secrets=[value.encode() for row in db.execute('SELECT password,tokenKey FROM _superusers') for value in row if isinstance(value,str) and len(value)>=15]
files=[p for folder in ['services/pocketbase','scripts','test','bench','results/pocketbase'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.gz']]
for p in files:
 raw=p.read_bytes()
 assert key not in raw and not any(secret in raw for secret in native_secrets),'Private value in publication candidate; no value exported'
 assert not any(v in signatures for v in re.findall(rb'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.([A-Za-z0-9_-]+)',raw)),'Actual issued token in publication candidate; no value exported'
(out/'final-native-input-and-privacy-review.json').write_text(json.dumps({'current_full_correctness_inputs_still_match':True,'three_passing_independent_confirmations':True,'full_attempt_slots_used':11,'total_budget':12,'actual_runtime_key_issued_signatures_and_native_password_tokenkey_scan_passed':True,'noncompressed_candidate_files_scanned':len(files),'raw_archives':'Source archive member safety/hash checks and raw stream metric validation independently performed by retained-attempt-review; no private fixture/key/token mounts in load runner.'},indent=2)+'\n')
print('FINAL_NATIVE_INPUTS_THREE_CONFIRMATIONS_AND_ACTUAL_VALUE_PRIVACY_VERIFIED',len(files))
