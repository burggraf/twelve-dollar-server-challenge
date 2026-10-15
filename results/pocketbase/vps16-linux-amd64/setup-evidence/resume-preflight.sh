#!/usr/bin/env bash
# Resume verification only; do not change frozen app/test/profile inputs.
set -euo pipefail
cd /opt/twelve-dollar-baas-pocketbase-16g/src
export DOCKER_CONFIG=/opt/twelve-dollar-baas-benchmark-16g/.docker
export BENCHMARK_PROJECT=baas-pocketbase-vps16 BENCHMARK_PLATFORM=linux/amd64 BENCHMARK_RUNNER_PROFILE=k6-2cpu-8g-v3 RUNNER_MEMORY=8g PYTHONDONTWRITEBYTECODE=1
python3 - <<'PY'
import hashlib,json,subprocess
from pathlib import Path
state=Path('.state/pocketbase');out=Path('results/pocketbase/vps16-linux-amd64/setup-evidence')
for unit in ['tds-pocketbase-capacity-standard-v3-20261015.service','tds-pocketbase-owner-pause-20261015.service']:
 assert subprocess.run(['systemctl','is-active','--quiet',unit]).returncode!=0,'Old campaign/pause unit still active'
assert not subprocess.check_output(['docker','ps','--filter','label=com.docker.compose.project=baas-pocketbase-vps16','--format','{{.Names}}'],text=True).strip(),'Owned containers unexpectedly active'
original=(state/'campaign.json').read_bytes();history=json.loads(original)
assert history['status']=='paused' and len(history['attempts'])==1 and history['attempts'][0]['vus']==2500 and history['attempts'][0]['outcome']=='pass'
for target in [state/'campaign-paused-before-resume-20261015T1521Z.json',out/'campaign-paused-before-resume-20261015T1521Z.json']:
 with target.open('xb') as stream:stream.write(original)
print('ORIGINAL_PAUSED_HISTORY_PRESERVED',hashlib.sha256(original).hexdigest(),flush=True)
PY
python3 ../service-snapshot.py results/pocketbase/vps16-linux-amd64/setup-evidence/pre-resume-service-continuity.json
python3 ../review-retained.py
cp results/pocketbase/vps16-linux-amd64/setup-evidence/retained-attempt-review.json results/pocketbase/vps16-linux-amd64/setup-evidence/pre-resume-retained-attempt-review.json
bash services/pocketbase/run.sh up
python3 - <<'PY'
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'scripts');import pocketbase_profile as s;import pocketbase_benchmark as b
att=json.loads((s.STATE/'correctness-manifest.json').read_text());current=b.inputs()
b.validate_correctness(att,current,hashlib.sha256((s.STATE/'correctness.log').read_bytes()).hexdigest())
Path('results/pocketbase/vps16-linux-amd64/setup-evidence/resume-frozen-input-verification.json').write_text(json.dumps({'original_correctness_inputs_still_match':True,'inputs':current,'serving':s.profile(),'remaining_scored_attempt_budget':11,'reason':'Owner authorized continuation; paused campaign preserved byte-for-byte. A separate search will repeat the initial probe and retain all old outcomes.'},indent=2)+'\n')
print('RESUME_FROZEN_INPUTS_NATIVE_IMAGE_AND_ACTUAL_BUDGET_VERIFIED',flush=True)
PY
