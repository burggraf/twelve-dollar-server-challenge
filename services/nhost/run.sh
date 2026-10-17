#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export BENCHMARK_PROJECT=baas-nhost-vps16 BENCHMARK_PLATFORM=linux/amd64
export BENCHMARK_RUNNER_PROFILE=k6-2cpu-8g-v3 RUNNER_MEMORY=8g PYTHONDONTWRITEBYTECODE=1
if [[ -z "${DOCKER_CONFIG:-}" && -d /opt/twelve-dollar-baas-benchmark-16g/.docker/cli-plugins ]]; then
  export DOCKER_CONFIG=/opt/twelve-dollar-baas-benchmark-16g/.docker
fi
case "${1:-}" in
  qualify) shift; exec python3 -B scripts/nhost_qualify.py "$@" ;;
  benchmark) shift; exec python3 -B scripts/nhost_benchmark.py "$@" ;;
  *) exec python3 -B scripts/nhost.py "$@" ;;
esac
