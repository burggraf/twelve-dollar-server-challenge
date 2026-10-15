#!/usr/bin/env bash
set -euo pipefail
base=/opt/twelve-dollar-baas-benchmark
test -f "$base/.benchmark-owned"
cd "$base/src"
export DOCKER_CONFIG="$base/.docker"
export BENCHMARK_PROJECT=baas-trailbase-vps
# Deliberately omit the platform export: validate the fixed direct-controller path.
unset BENCHMARK_PLATFORM
bash services/trailbase/run.sh test
python3 -u scripts/benchmark.py --smoke --vus 5000
echo VPS_NATIVE_BOUNDARY_REVALIDATED
