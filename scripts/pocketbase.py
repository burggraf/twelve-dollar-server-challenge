#!/usr/bin/env python3
"""Owned native PocketBase build/start/offline app-only reset; no global changes."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import platform
from pathlib import Path
import secrets
import shutil
import subprocess
import time
from urllib.request import urlopen

import benchmark as b
import pocketbase_profile as s

ROOT, STATE = s.ROOT, s.STATE


def require_native():
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64') or b.PROJECT != s.PROJECT or b.RUNNER_PROFILE != 'k6-2cpu-8g-v3':
        raise RuntimeError('Use services/pocketbase/run.sh on the designated native AMD64 host/profile')
    if not (ROOT.parent / '.benchmark-owned').is_file():
        raise RuntimeError('Missing owned workspace marker; refusing infrastructure operations')


def compose():
    return ['docker', 'compose', '--env-file', str(STATE / 'runtime.env'), '-p', s.PROJECT,
            '-f', str(ROOT / 'services/pocketbase/compose.yaml')]


def run(argv, log=None, **kwargs):
    return subprocess.run(argv, cwd=ROOT, check=True, stdout=log,
                          stderr=subprocess.STDOUT if log else None, **kwargs)


def ownership():
    result = subprocess.run(['docker', 'inspect', s.PROJECT + '-pocketbase-1'], capture_output=True, text=True)
    if result.returncode == 0:
        item = json.loads(result.stdout)[0]
        if (item['Config'].get('Labels') or {}).get('com.docker.compose.project') != s.PROJECT:
            raise RuntimeError('Container namespace collision; refusing changes')
    result = subprocess.run(['docker', 'volume', 'inspect', s.PROJECT + '_data'], capture_output=True, text=True)
    if result.returncode == 0:
        if (json.loads(result.stdout)[0].get('Labels') or {}).get('com.docker.compose.project') != s.PROJECT:
            raise RuntimeError('Volume namespace collision; refusing changes')


def initialize():
    require_native()
    ownership()
    memory = int(b.capture(['docker', 'info', '--format', '{{.MemTotal}}']).strip())
    cpus = int(b.capture(['docker', 'info', '--format', '{{.NCPU}}']).strip())
    b.require_vm_headroom('standard', memory, cpus)
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    for path in [STATE / 'runs', ROOT / '.state/seed']:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    envfile = STATE / 'runtime.env'
    if not envfile.exists():
        envfile.write_text('JWT_SECRET=' + secrets.token_hex(32) + '\n')
        envfile.chmod(0o600)
    if not s.GROUP.exists():
        run(['systemctl', 'set-property', '--runtime', s.SLICE,
             'CPUQuota=100%', 'MemoryMax=4294967296', 'MemorySwapMax=0'])
    else:
        parent = s.parent_sample()
        if parent['cpu.max'].split() != ['100000', '100000'] or int(parent['memory.max']) != 4294967296 or int(parent['memory.swap.max']) != 0:
            raise RuntimeError('Existing serving cgroup differs; no automatic budget changes')
    run(compose() + ['config', '--quiet'])


def build(log=None):
    initialize()
    destination = STATE / 'build'
    destination.mkdir(exist_ok=True)
    source = s.app_hash()
    builder = s.PINS['builder']['tag'] + '@' + s.PINS['builder']['amd64_manifest']
    run(['docker', 'run', '--rm', '--platform', 'linux/amd64', '--name', s.PROJECT + '-native-build',
         '--label', 'com.docker.compose.project=' + s.PROJECT,
         '--cpus', '2', '--memory', '8589934592', '--memory-swap', '8589934592',
         '-e', 'CGO_ENABLED=0', '-e', 'GOMAXPROCS=2', '-e', 'GOMEMLIMIT=6GiB', '-e', 'GOTOOLCHAIN=local',
         '-v', str(ROOT / 'services/pocketbase/app') + ':/work:ro',
         '-v', str(STATE / 'gopath') + ':/go', '-v', str(STATE / 'gocache') + ':/root/.cache/go-build',
         '-v', str(destination) + ':/out', '-w', '/work', builder, 'bash', '-euc',
         'go version; uname -m; go test -count=1 -v ./...; '
         'go build -trimpath -buildvcs=false -ldflags="-s -w" -o /out/feed .; go version -m /out/feed'], log)
    run(['docker', 'build', '--network=none', '--build-arg', 'APP_SOURCE_SHA256=' + source,
         '-t', s.PROJECT + '-feed:0.1.0', '-f', 'services/pocketbase/Dockerfile', str(destination)], log)
    item = json.loads(b.capture(['docker', 'image', 'inspect', s.PROJECT + '-feed:0.1.0']))[0]
    if item['Os'] != 'linux' or item['Architecture'] != 'amd64' or item['Config']['Labels'].get('benchmark.app-source-sha256') != source or s.app_hash() != source:
        raise RuntimeError('Native build image/source provenance differs')
    value = {'native_platform': 'linux/amd64', 'app_source_sha256': source, 'image_id': item['Id'],
             'executable_sha256': hashlib.sha256((destination / 'feed').read_bytes()).hexdigest(),
             'builder': builder, 'runtime': s.PINS['runtime']['tag'] + '@' + s.PINS['runtime']['amd64_manifest'],
             'builder_budget': {'cpus': 2, 'memory_bytes': 8589934592, 'swap_bytes': 0},
             'build_flags': ['CGO_ENABLED=0', '-trimpath', '-buildvcs=false', '-ldflags=-s -w'],
             'versions': s.PINS}
    (STATE / 'build-manifest.json').write_text(json.dumps(value, indent=2) + '\n')
    print('POCKETBASE_NATIVE_BUILD_PASSED', flush=True)


def ready():
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        try:
            with urlopen('http://127.0.0.1:14000/health', timeout=5) as response:
                value = json.load(response)
                if response.status == 200 and value.get('status') == 'ok' and value.get('db') == 'ok':
                    return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError('Native PocketBase did not become storage-ready')


def up(log=None):
    initialize()
    s.build_manifest()
    # Bootstrap logs can contain a private installer URL/token; never publish.
    with (STATE / 'bootstrap-private.log').open('a') as private:
        run(compose() + ['up', '-d', 'pocketbase'], private)
    ready()
    s.profile()


def tools(script, log=None, name='tools'):
    return run(compose() + ['run', '--rm', '--no-deps', '--name', s.PROJECT + '-' + name,
                           'tools', 'bash', '-euc',
                           'set -a; source /state/pocketbase/runtime.env; export PYTHONDONTWRITEBYTECODE=1; ' + script], log)


def seed(log=None):
    directory = ROOT / '.state/seed'
    if not (directory / 'tokens.json').exists():
        tools('node seed/generate.mjs /state/seed', log, 'seed')
    else:
        for table in ['users', 'posts', 'likes']:
            if not (directory / (table + '.tsv')).is_file():
                raise RuntimeError('Incomplete existing canonical seed; refusing silent token rotation')


def reset(log=None):
    require_native()
    ownership()
    s.profile()
    seed(log)
    run(compose() + ['stop', 'pocketbase'], log)
    tools('python3 - <<\'PY\'\n'
          'import sqlite3\nfrom pathlib import Path\n'
          'path=Path("/state/pocketbase/native-schema-fixture.db")\n'
          'if not path.exists():\n'
          ' with sqlite3.connect("/depot/data.db") as source:\n'
          '  if source.execute("SELECT COUNT(*) FROM feed_posts").fetchone()[0]!=0: raise RuntimeError("Missing original native schema fixture; refusing replacement from mutated data")\n'
          '  with sqlite3.connect(path) as target: source.backup(target)\n'
          ' path.chmod(0o600)\n'
          'PY\n'
          'python3 scripts/import_pocketbase.py /depot/data.db /state/seed --manifest /state/pocketbase/dataset.json',
          log, 'import')
    up(log)


def full_test():
    import pocketbase_benchmark as bench
    logfile = STATE / 'correctness.log'
    stamp = str(time.time_ns())
    for filename in ['correctness.log', 'correctness-manifest.json']:
        previous = STATE / filename
        if previous.exists():
            shutil.copyfile(previous, STATE / ('prior-' + stamp + '-' + filename))
    with logfile.open('w') as log:
        # Fresh real native Go tests include closed-DB failure/sanitization,
        # transactional rollback and native connection pragmas, not a fake DB.
        build(log)
        up(log)
        seed(log)
        reset(log)
        deployed = s.deployment_attestation()
        frozen = bench.inputs(deployed)
        tools('node --version; python3 --version; openssl version; '
              'bash test/test.sh "$BASE_URL"; python3 test/baas/test_api.py; '
              'python3 test/baas/pocketbase_native.py; python3 test/baas/test_seed.py; '
              'POCKETBASE_NATIVE_FIXTURE=/state/pocketbase/native-schema-fixture.db python3 test/baas/test_pocketbase_import.py; '
              'node --test bench/baas-contract.test.mjs', log, 'correctness')
        environment = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
        for filename in ['test_benchmark.py', 'test_isolation.py', 'test_supabase_harness.py',
                         'test_pocketbase_harness.py', 'test_pocketbase_config.py',
                         'test_pocketbase_budget.py', 'test_pocketbase_controller.py', 'test_pocketbase_evidence.py']:
            run(['python3', 'test/baas/' + filename], log, env=environment)
        run(['python3', '-m', 'unittest', 'discover', '-s', 'test', '-p', 'test_gitignore.py', '-v'], log, env=environment)
        tools('python3 test/baas/pocketbase_lifecycle.py prepare', log, 'persist-prepare')
        before = s.targets()['pocketbase']
        run(compose() + ['stop', 'pocketbase'], log)
        try:
            tools('python3 test/baas/pocketbase_lifecycle.py stopped', log, 'stopped-transport')
        finally:
            up(log)
        after_restart = s.targets()['pocketbase']
        if before['State']['StartedAt'] == after_restart['State']['StartedAt'] or before['State']['Pid'] == after_restart['State']['Pid']:
            raise RuntimeError('Actual native process restart proof is missing')
        tools('python3 test/baas/pocketbase_lifecycle.py verify', log, 'persist-verify')
        after = s.deployment_attestation()
        if frozen != bench.inputs(after):
            raise RuntimeError('Executable/verification/image/runtime/schema/host/token inputs changed during full correctness')
        log.write('FULL_POCKETBASE_CORRECTNESS_GATE_PASSED\n')
    attestation = {'inputs': frozen, 'deployment': after,
                   'log_sha256': hashlib.sha256(logfile.read_bytes()).hexdigest(),
                   'finished_utc': datetime.now(timezone.utc).isoformat(),
                   'auth_scope': 'Synthetic compatibility app users/JWTs; 0 regular native Auth users and 1 platform installer superuser; native signup/login/session throughput not measured',
                   'proofs': ['10 real native Go tests including strict contracts, concurrent transactions, actual closed-DB 503/500, rollback, bootstrap and native pragmas',
                              '42 inherited exact-byte checks', '6 shared concurrency/auth/Unicode tests',
                              '5 native REST/storage/permission/identity tests', '3 real-native-schema import tests',
                              'seed logging privacy', '4 fixed workload/scoring tests',
                              '24 original benchmark and 3 original isolation tests; shared Supabase harness regressions',
                              'PocketBase source-snapshot/config/budget/ownership/frozen-evidence regressions',
                              '3 repository artifact-policy regressions',
                              'actual owned transport stop and real process restart preserving acknowledged post/exactly-once like/ID sequence; not provider power-loss durability']}
    (STATE / 'correctness-manifest.json').write_text(json.dumps(attestation, indent=2) + '\n')
    print('FULL_POCKETBASE_CORRECTNESS_GATE_PASSED', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'up', 'wait-ready', 'seed', 'reset', 'test', 'bench', 'search', 'down'])
    parser.add_argument('--vus', type=int, default=2500)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--max-vus', type=int, default=20000)
    parser.add_argument('--max-attempts', type=int, default=12)
    args = parser.parse_args()
    require_native()
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE / 'lifecycle.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.command == 'build':
            with (STATE / f'build-{time.time_ns()}.log').open('w') as log:
                build(log)
        elif args.command == 'up':
            up()
        elif args.command == 'wait-ready':
            ready()
            s.profile()
        elif args.command == 'seed':
            seed()
        elif args.command == 'reset':
            reset()
        elif args.command == 'test':
            full_test()
        elif args.command in ['bench', 'search']:
            import pocketbase_benchmark as bench
            if not 1 <= args.vus <= 20000 or not 1 <= args.max_vus <= 20000 or not 4 <= args.max_attempts <= 12:
                parser.error('Stay within the approved 20,000-VU / 12-attempt bounds')
            if args.command == 'bench':
                raise SystemExit(0 if bench.attempt(args.vus, smoke=args.smoke)[0] == 'pass' else 1)
            raise SystemExit(b.campaign(args, 'standard', attempt_runner=bench.attempt,
                                       results=bench.RESULTS, campaign_file=STATE / 'campaign.json'))
        elif args.command == 'down':
            ownership()
            run(compose() + ['stop', 'pocketbase'])
            print('Only owned PocketBase serving container stopped; all volumes/evidence retained.')


if __name__ == '__main__':
    main()
