#!/usr/bin/env bash
set -euo pipefail
base=/opt/twelve-dollar-baas-benchmark
test -f "$base/.benchmark-owned"
cd "$base/src"
export DOCKER_CONFIG="$base/.docker"
export BENCHMARK_PROJECT=baas-trailbase-vps
export BENCHMARK_BUILDER=baas-trailbase-vps-builder
mkdir -p .state/trailbase
builder_created=0
cleanup() {
  status=$?
  if [[ "$builder_created" == 1 ]]; then
    docker buildx stop --builder "$BENCHMARK_BUILDER" > "$base/setup-evidence/builder-stop.log" 2>&1 || true
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 143' TERM HUP
trap 'exit 130' INT
if docker buildx inspect --builder "$BENCHMARK_BUILDER" >/dev/null 2>&1; then
  echo 'Refusing to adopt an existing builder' >&2
  exit 1
fi
for id in $(docker ps -q); do
  docker inspect --format '{{.Id}} {{.State.Running}} {{.State.StartedAt}} {{.RestartCount}}' "$id"
done > "$base/setup-evidence/preexisting-before-build.txt"
docker buildx create --name "$BENCHMARK_BUILDER" --driver docker-container \
  --driver-opt image=moby/buildkit@sha256:98cc6a3fc46220d00f8224ae483f3274fc874e9be8d7dd1e2e2c5481209228b5 \
  --driver-opt memory=2g,memory-swap=2g,cpu-quota=200000,cpu-period=100000,restart-policy=no
builder_created=1
docker buildx inspect --builder "$BENCHMARK_BUILDER" --bootstrap
builder=buildx_buildkit_baas-trailbase-vps-builder0
docker exec "$builder" cat /sys/fs/cgroup/cpu.max /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.swap.max > "$base/setup-evidence/builder-cgroups.txt"
python3 - <<'PY'
from pathlib import Path
lines=Path('/opt/twelve-dollar-baas-benchmark/setup-evidence/builder-cgroups.txt').read_text().splitlines()
quota,period=map(int,lines[0].split())
assert quota/period==2 and int(lines[1])==2*1024**3 and int(lines[2])==0,lines
print('VPS_BUILDER_LIMITS_VERIFIED: 2 CPU / 2 GiB / no swap')
PY
bash services/trailbase/run.sh build > .state/trailbase/build-vps.log 2>&1
echo VPS_NATIVE_BUILD_PASSED
docker buildx stop --builder "$BENCHMARK_BUILDER"
while read -r id rest; do
  docker inspect --format '{{.Id}} {{.State.Running}} {{.State.StartedAt}} {{.RestartCount}}' "$id"
done < "$base/setup-evidence/preexisting-before-build.txt" > "$base/setup-evidence/preexisting-after-build.txt"
cmp "$base/setup-evidence/preexisting-before-build.txt" "$base/setup-evidence/preexisting-after-build.txt"
echo VPS_PREEXISTING_CONTAINERS_UNCHANGED
bash services/trailbase/run.sh test
bash services/trailbase/run.sh bench --smoke --vus 5000
echo VPS_CORRECTNESS_AND_CALIBRATION_PASSED
