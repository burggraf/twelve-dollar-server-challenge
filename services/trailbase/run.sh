#!/usr/bin/env bash
# Lifecycle for this benchmark's named resources only; never docker prune.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export BENCHMARK_PROJECT="${BENCHMARK_PROJECT:-baas-trailbase}"
BENCHMARK_PLATFORM="$(python3 scripts/benchmark.py --native-platform)"
export BENCHMARK_PLATFORM
RUNNER_MEMORY="$(python3 scripts/benchmark.py --runner-memory)"
export RUNNER_MEMORY
case "${TIER:-small}" in
  small) export SERVICE_CPUS=1 SERVICE_MEMORY=2g SERVICE_THREADS=1 ;;
  standard) export SERVICE_CPUS=1 SERVICE_MEMORY=4g SERVICE_THREADS=1 ;;
  large) export SERVICE_CPUS=4 SERVICE_MEMORY=4g SERVICE_THREADS=4 ;;
  *) echo 'TIER must be small, standard, or large' >&2; exit 2 ;;
esac
compose() { docker compose -p "$BENCHMARK_PROJECT" -f services/trailbase/compose.yaml "$@"; }
init() {
  mkdir -p .state/trailbase .state/seed
  chmod 700 .state .state/trailbase .state/seed
  python3 - <<'PY'
from pathlib import Path
import os
p = Path('.state/trailbase/jwt-secret')
if not p.exists():
    p.write_text(os.environ.get('JWT_SECRET', 'twelve-dollar-challenge'))
    # Parent directory is 0700; the single-file Docker secret mount must be readable by uid 1000.
    p.chmod(0o444)
elif 'JWT_SECRET' in os.environ and p.read_text() != os.environ['JWT_SECRET']:
    raise SystemExit('Signing key differs from initialized state; use a separate clean benchmark checkout')
PY
}
tools() { compose run --rm -T tools "$@"; }
up() {
  # Startup can contain platform-generated admin credentials: keep logs local/private.
  compose up -d --no-build --wait --wait-timeout 120 trailbase
}
seed() {
  tools bash -euc 'export JWT_SECRET="$(< /run/secrets/jwt_secret)"; node seed/generate.mjs /state/seed'
}
reset() {
  up
  compose stop trailbase
  if [[ ! -f .state/seed/users.tsv ]]; then seed; fi
  tools python3 scripts/import_sqlite.py /depot/data/main.db /state/seed --manifest /state/trailbase/dataset.json
  up
}
case "${1:-help}" in
  build)
    init
    python3 -m unittest discover -s test/baas -p test_isolation.py -v
    build_args=(build --build-arg "APP_SOURCE_SHA=$(python3 scripts/benchmark.py --source-hash)")
    if [[ -n "${BENCHMARK_BUILDER:-}" ]]; then build_args+=(--builder "$BENCHMARK_BUILDER"); fi
    compose "${build_args[@]}" tools trailbase
    ;;
  up|wait-ready) init; up ;;
  seed) init; seed ;;
  reset) init; reset ;;
  test)
    init
    rm -f .state/trailbase/correctness-manifest.json
    if [[ -f .state/trailbase/correctness.log ]]; then
      mkdir -p .state/trailbase/test-history
      cp .state/trailbase/correctness.log ".state/trailbase/test-history/$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
    fi
    verification_hash="$(python3 scripts/benchmark.py --verification-hash)"
    test_service() {
      python3 -m unittest discover -s test/baas -p test_isolation.py -v
      reset
      tools bash -euc 'export JWT_SECRET="$(< /run/secrets/jwt_secret)"; bash test/test.sh "$BASE_URL"; python3 -m unittest discover -s test/baas -p test_api.py -v; python3 test/baas/trailbase_native.py'
      compose restart trailbase
      up
      tools bash -euc 'export JWT_SECRET="$(< /run/secrets/jwt_secret)"; python3 test/baas/trailbase_native.py --after-restart; node --test bench/baas-contract.test.mjs; python3 -m unittest discover -s test/baas -p test_seed.py -v; python3 -m unittest discover -s test/baas -p test_benchmark.py -v'
    }
    test_service > .state/trailbase/correctness.log 2>&1
    python3 scripts/benchmark.py --attest-correctness --expected-verification-hash "$verification_hash"
    echo 'TRAILBASE_CORRECTNESS_PASSED (.state/trailbase/correctness.log)'
    ;;
  down) compose down ;;
  bench) shift; exec python3 scripts/benchmark.py "$@" ;;
  *) echo 'Usage: [TIER=small|standard|large] bash services/trailbase/run.sh {build|up|wait-ready|seed|reset|test|bench|down}'; exit 2 ;;
esac
