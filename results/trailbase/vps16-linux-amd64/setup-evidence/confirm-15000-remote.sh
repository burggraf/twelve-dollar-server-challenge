#!/usr/bin/env bash
set -euo pipefail
base=/opt/twelve-dollar-baas-benchmark-16g
test -f "$base/.benchmark-owned"
cd "$base/src"
export DOCKER_CONFIG="$base/.docker"
export BENCHMARK_PROJECT=baas-trailbase-vps16 BENCHMARK_RUNNER_PROFILE=k6-2cpu-8g-v3
export TIER=standard TRAILBASE_PORT=14000
logger_unit=tds-trailbase-vps16-confirm15000-lifecycle-20261015
logger_started=0
cleanup() {
 status=$?
 if project=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' baas-trailbase-vps16-load 2>/dev/null); then
  if [[ "$project" == "$BENCHMARK_PROJECT" ]]; then docker stop --timeout 20 baas-trailbase-vps16-load >/dev/null || status=1
  else echo 'Refusing to stop an unowned load-container name' >&2; status=1; fi
 fi
 python3 "$base/service-snapshot.py" "$base/setup-evidence/preexisting-after-confirm15000.json" || status=1
 if [[ "$logger_started" == 1 ]]; then systemctl stop "$logger_unit" || status=1; fi
 python3 - "$status" <<'PY'
from pathlib import Path
import json,sys
base=Path('/opt/twelve-dollar-baas-benchmark-16g');root=base/'src'
p=root/'.state/trailbase/confirmation15000-state.json'
if p.exists():
 state=json.loads(p.read_text());previous=set(state['prior_run_ids'])
 attempts=[]
 for m in sorted((root/'results/trailbase/vps16-linux-amd64').glob('*-standard-*k6-2cpu-8g-v3/manifest.json')):
  if m.parent.name not in previous:
   value=json.loads(m.read_text());attempts.append({'run_id':m.parent.name,'vus':value['vus'],'outcome':value['result'],'reason':value['reason']})
 state['attempts']=attempts
 before=json.loads((base/'setup-evidence/preexisting-before-setup.json').read_text())
 after=json.loads((base/'setup-evidence/preexisting-after-confirm15000.json').read_text())
 changed=sum(after['services'].get(n)!=v for n,v in before['services'].items() if n!='user@0.service')
 continuity={'changed_persistent_services':changed,'original_port4000_listener_unchanged':all(before[k]==after[k] for k in ['port4000_listener','port4000_processes'])}
 state['continuity']=continuity
 passed=len(attempts)==3 and all(a['vus']==15000 and a['outcome']=='pass' for a in attempts)
 stable=changed==0 and continuity['original_port4000_listener_unchanged']
 state['status']='confirmed_lower_bound_pending_human_review' if passed and stable and sys.argv[1]=='0' else 'paused_pending_review'
 p.write_text(json.dumps(state,indent=2)+'\n')
 print('VPS16_CONFIRMATION_FINAL_STATE',json.dumps(state))
 if not stable: raise SystemExit('Persistent service/listener identity changed; review before acceptance')
PY
 state_status=$?
 if [[ "$state_status" != 0 ]]; then status=1; fi
 exit "$status"
}
trap cleanup EXIT
trap 'exit 143' TERM HUP
trap 'exit 130' INT
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/opt/twelve-dollar-baas-benchmark-16g/src')
completed=sorted(p.parent.name for p in (root/'results/trailbase/vps16-linux-amd64').glob('*-standard-*k6-2cpu-8g-v3/manifest.json'))
assert len(completed)==5 and len(completed)+3<=12, 'Unexpected attempt history or exhausted approved budget'
p=root/'.state/trailbase/confirmation15000-state.json';assert not p.exists()
state={'status':'in_progress','role':'three additional independent passing 15,000-VU confirmation holds',
       'outcome_scope':'confirmed lower bound only; 20,000-VU generator OOM is not a target-failure bracket',
       'vus':15000,'planned_holds':3,'prior_run_ids':completed,'total_attempt_budget':12,
       'tier':'standard','runner_profile':'k6-2cpu-8g-v3','attempts':[]}
p.write_text(json.dumps(state,indent=2)+'\n')
print('VPS16_CONFIRM15000_PLAN_STARTED')
PY
python3 "$base/service-snapshot.py" "$base/setup-evidence/preexisting-before-confirm15000.json"
systemd-run --unit="$logger_unit" --collect --property=RuntimeMaxSec=3800 \
 --property="StandardOutput=append:$base/container-lifecycle-confirm15000.log" \
 --property="StandardError=append:$base/container-lifecycle-confirm15000.log" \
 "$(command -v docker)" --config "$DOCKER_CONFIG" events --filter type=container \
 --filter event=start --filter event=stop --filter event=die --filter event=kill \
 --format '{{.TimeNano}} {{.Actor.ID}} {{.Action}} exit={{index .Actor.Attributes "exitCode"}} signal={{index .Actor.Attributes "signal"}}'
logger_started=1
for hold in 1 2 3; do
 echo "VPS16_CONFIRMATION_HOLD_STARTED $hold/3"
 python3 -u scripts/benchmark.py --vus 15000 2>&1 | tee --output-error=warn-nopipe -a "$base/confirm-15000-job.log"
 echo "VPS16_CONFIRMATION_HOLD_PASSED $hold/3"
done
