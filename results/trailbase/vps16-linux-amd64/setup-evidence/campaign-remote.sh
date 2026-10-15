#!/usr/bin/env bash
set -euo pipefail
base=/opt/twelve-dollar-baas-benchmark-16g
test -f "$base/.benchmark-owned"
cd "$base/src"
export DOCKER_CONFIG="$base/.docker"
export BENCHMARK_PROJECT=baas-trailbase-vps16 BENCHMARK_RUNNER_PROFILE=k6-2cpu-8g-v3
export TIER=standard TRAILBASE_PORT=14000
test -z "$(docker ps -q --filter name=buildx_buildkit_baas-trailbase-vps16)"
logger_unit=tds-trailbase-vps16-lifecycle-20261015
logger_started=0
cleanup() {
 status=$?
 # Only our explicitly named, Compose-labelled load container may be stopped.
 if project=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' baas-trailbase-vps16-load 2>/dev/null); then
  if [[ "$project" == "$BENCHMARK_PROJECT" ]]; then
   docker stop --timeout 20 baas-trailbase-vps16-load >/dev/null || status=1
  else
   echo 'Refusing to stop an unowned load-container name' >&2; status=1
  fi
 fi
 python3 "$base/service-snapshot.py" "$base/setup-evidence/preexisting-after-campaign.json" || status=1
 if [[ "$logger_started" == 1 ]]; then systemctl stop "$logger_unit" || status=1; fi
 exit "$status"
}
trap cleanup EXIT
trap 'exit 143' TERM HUP
trap 'exit 130' INT
python3 "$base/service-snapshot.py" "$base/setup-evidence/preexisting-before-campaign.json"
systemd-run --unit="$logger_unit" --collect --property=RuntimeMaxSec=11000 \
 --property="StandardOutput=append:$base/container-lifecycle.log" \
 --property="StandardError=append:$base/container-lifecycle.log" \
 "$(command -v docker)" --config "$DOCKER_CONFIG" events --filter type=container \
 --filter event=start --filter event=stop --filter event=die --filter event=kill \
 --format '{{.TimeNano}} {{.Actor.ID}} {{.Action}} exit={{index .Actor.Attributes "exitCode"}} signal={{index .Actor.Attributes "signal"}}'
logger_started=1
python3 -u scripts/benchmark.py --campaign --max-vus 20000 --max-attempts 12 2>&1 \
 | tee --output-error=warn-nopipe "$base/campaign-job.log"
echo VPS16_CAPACITY_CAMPAIGN_FINISHED_PENDING_REVIEW
