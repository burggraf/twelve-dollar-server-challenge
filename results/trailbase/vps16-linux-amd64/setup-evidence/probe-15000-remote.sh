#!/usr/bin/env bash
set -euo pipefail
base=/opt/twelve-dollar-baas-benchmark-16g
test -f "$base/.benchmark-owned"
cd "$base/src"
export DOCKER_CONFIG="$base/.docker"
export BENCHMARK_PROJECT=baas-trailbase-vps16 BENCHMARK_RUNNER_PROFILE=k6-2cpu-8g-v3
export TIER=standard TRAILBASE_PORT=14000
logger_unit=tds-trailbase-vps16-probe15000-lifecycle-20261015
logger_started=0
cleanup() {
 status=$?
 if project=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' baas-trailbase-vps16-load 2>/dev/null); then
  if [[ "$project" == "$BENCHMARK_PROJECT" ]]; then docker stop --timeout 20 baas-trailbase-vps16-load >/dev/null || status=1
  else echo 'Refusing to stop an unowned load-container name' >&2; status=1; fi
 fi
 python3 "$base/service-snapshot.py" "$base/setup-evidence/preexisting-after-probe15000.json" || status=1
 if [[ "$logger_started" == 1 ]]; then systemctl stop "$logger_unit" || status=1; fi
 exit "$status"
}
trap cleanup EXIT
trap 'exit 143' TERM HUP
trap 'exit 130' INT
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/opt/twelve-dollar-baas-benchmark-16g/src')
completed=list((root/'results/trailbase/vps16-linux-amd64').glob('*-standard-*k6-2cpu-8g-v3/manifest.json'))
assert len(completed)==4, 'Unexpected attempt history; review before another run'
plan={'role':'generator-validity backoff probe after 20,000-VU runner OOM','probe_vus':15000,
      'prior_completed_capacity_attempts':4,'total_attempt_budget':12,
      'note':'20,000 runner OOM is not a failing target bracket; no code/resource/threshold change; full capacity timing'}
(root/'.state/trailbase/probe15000-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print('VPS16_PROBE15000_PLAN',json.dumps(plan))
PY
python3 "$base/service-snapshot.py" "$base/setup-evidence/preexisting-before-probe15000.json"
systemd-run --unit="$logger_unit" --collect --property=RuntimeMaxSec=1400 \
 --property="StandardOutput=append:$base/container-lifecycle-15000.log" \
 --property="StandardError=append:$base/container-lifecycle-15000.log" \
 "$(command -v docker)" --config "$DOCKER_CONFIG" events --filter type=container \
 --filter event=start --filter event=stop --filter event=die --filter event=kill \
 --format '{{.TimeNano}} {{.Actor.ID}} {{.Action}} exit={{index .Actor.Attributes "exitCode"}} signal={{index .Actor.Attributes "signal"}}'
logger_started=1
python3 -u scripts/benchmark.py --vus 15000 2>&1 | tee --output-error=warn-nopipe "$base/probe-15000-job.log"
echo VPS16_FULL_15000_PROBE_FINISHED_PENDING_REVIEW
