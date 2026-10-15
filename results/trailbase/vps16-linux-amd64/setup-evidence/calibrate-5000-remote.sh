#!/usr/bin/env bash
set -euo pipefail
base=/opt/twelve-dollar-baas-benchmark-16g
test -f "$base/.benchmark-owned"
export DOCKER_CONFIG="$base/.docker"
export BENCHMARK_PROJECT=baas-trailbase-vps16 BENCHMARK_RUNNER_PROFILE=k6-2cpu-8g-v3
export TIER=standard TRAILBASE_PORT=14000
cd "$base/src"
# Keep the failed 10k calibration and original full correctness evidence intact.
python3 -u scripts/benchmark.py --smoke --vus 5000
python3 "$base/service-snapshot.py" "$base/setup-evidence/preexisting-after-5000-calibration.json"
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/opt/twelve-dollar-baas-benchmark-16g/setup-evidence')
before=json.loads((root/'preexisting-before-setup.json').read_text())
after=json.loads((root/'preexisting-after-5000-calibration.json').read_text())
# Exact known SSH-session manager is reviewed separately: Linger=no and journal
# lifecycle records confirm normal start/stop between SSH logins. No app units
# are excluded, and raw original snapshots remain unchanged/private.
session='user@0.service'
persistent={n:v for n,v in before['services'].items() if n!=session}
changed=[n for n,v in persistent.items() if after['services'].get(n)!=v]
report={'existing_persistent_service_count':len(persistent),'changed_existing_persistent_service_count':len(changed),
 'root_ssh_session_manager_identity_changed':before['services'].get(session)!=after['services'].get(session),
 'original_port4000_listener_unchanged':all(before[k]==after[k] for k in ['port4000_listener','port4000_processes'])}
(root/'continuity-5000-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print('Continuity summary:',json.dumps(report))
assert not changed and report['original_port4000_listener_unchanged'], 'Existing application/service changed; investigate before capacity'
PY
echo VPS16_5000_CALIBRATION_AND_PERSISTENT_SERVICE_CONTINUITY_PASSED
