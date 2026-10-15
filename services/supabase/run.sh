#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export BENCHMARK_PROJECT=baas-supabase-vps16
export BENCHMARK_PLATFORM=linux/amd64
export BENCHMARK_RUNNER_PROFILE=k6-2cpu-8g-v3
export SUPABASE_PORT=14000 RUNNER_MEMORY=8g PYTHONDONTWRITEBYTECODE=1
if [[ -z "${DOCKER_CONFIG:-}" && -d /opt/twelve-dollar-baas-benchmark-16g/.docker/cli-plugins ]]; then
  export DOCKER_CONFIG=/opt/twelve-dollar-baas-benchmark-16g/.docker
fi
exec python3 scripts/supabase.py "$@"
