#!/usr/bin/env python3
"""Convex native HTTP attempts; unchanged common workload, search and scoring.

Clean SIGINT shutdown FAILED139. Owner explicitly approved serving-path capacity
with that limitation disclosed. Never restart/revive/reseed serving processes.
"""
import argparse
import base64
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time

import benchmark as b
import convex_profile as s

ROOT, STATE = s.ROOT, s.STATE
RESULTS = ROOT / 'results/convex' / b.TRACK
K6_MANIFEST = 'sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656'


def validate_correctness(attestation, current, log_sha256):
    if attestation.get('inputs') != current or attestation.get('log_sha256') != log_sha256:
        raise RuntimeError('Full frozen correctness evidence is stale for source/runtime/SDK/generated/schema/image/host/tokens/log')
    return True


def target_issue(before, after):
    if set(before) != set(s.SERVICES) or set(after) != set(s.SERVICES): return 'required serving component set changed'
    for role in s.SERVICES:
        a, z = before[role], after[role]; state = z['State']
        if not state.get('Running') or state.get('OOMKilled') or state.get('Paused') or state.get('Restarting') or state.get('Health', {}).get('Status') != 'healthy' or a['Id'] != z['Id'] or a['RestartCount'] != z['RestartCount'] or a['State']['StartedAt'] != state['StartedAt']:
            return 'serving process OOM/exit/restart/unhealthy: ' + role
    return None


def runtime_issue(before, after):
    issue = target_issue(before['targets'], after['targets'])
    if issue: return issue
    events = lambda value: dict(line.split() for line in value['parent']['memory.events'].splitlines())
    a, z = events(before), events(after)
    if any(int(z[key]) > int(a[key]) for key in ['oom', 'oom_kill', 'oom_group_kill']):
        return 'aggregate serving cgroup OOM event; no automatic continuation/revival'
    return None


def report_header():
    return '''# Tested software and VPS slice

- **Convex precompiled-2026-10-06-a3538c6**, upstream `a3538c6d212948f20726868e41d155d2534cd130`, SDK/CLI **1.46.0**, bundled Node **22.22.2**, tools Node **22.20.0**; PostgreSQL **17.11-bookworm / Debian17.11-1.pgdg12+2**. Immutable native image IDs/digests in manifest; backend `/version` literally `unknown`.
- Entire serving allocation **1 vCPU / 4 GiB (4,294,967,296 bytes) / no swap**, one aggregate parent: backend/executor **3 GiB (3,221,225,472 bytes)** plus PostgreSQL **1 GiB (1,073,741,824 bytes)**. Child CPU ceilings do not grant two cores.
- Separate runner **k6 1.3.0 / 2 vCPU / 8 GiB (8,589,934,592 bytes) / no swap**, `k6-2cpu-8g-v3`.
- Quota-limited **shared-host** slice, not dedicated or a measured $12/month VPS; price/region unknown.
- **Clean SIGINT shutdown FAILED139** after native teardown panic/fault. Explicit owner exception permits capacity; acknowledged crash recovery passed separately. Not clean lifecycle or provider power-loss proof.
'''


def compose():
    files = s.compose_files(s.DEPLOYMENT_NAME, s.STAGE)
    return ['docker', 'compose', '-p', s.PROJECT] + [arg for path in files for arg in ['-f', str(path)]]


def token_hash():
    raw = (STATE / 'benchmark-tokens.json').read_bytes(); entries = json.loads(raw)
    if len(entries) != 20000: raise RuntimeError('Expected 20,000 compatibility token identities')
    key = s.runtime_values()['JWT_SECRET'].encode(); checked = 0
    with (STATE / 'seed/users.tsv').open(newline='', encoding='utf-8') as stream:
        for index, (entry, user) in enumerate(zip(entries, csv.reader(stream, delimiter='\t', quoting=csv.QUOTE_NONE)), 1):
            try:
                head, payload, sig = entry['token'].split('.')
                decode = lambda text: json.loads(base64.urlsafe_b64decode(text + '=' * (-len(text) % 4)))
                claims = decode(payload); expected = base64.urlsafe_b64encode(hmac.digest(key, (head + '.' + payload).encode(), 'sha256')).decode().rstrip('=')
                valid = decode(head)['alg'] == 'HS256' and entry['id'] == index and user[0] == str(index) and entry['username'] == user[1] and claims['sub'] == str(index) and claims['username'] == user[1] and type(claims['exp']) in (float, int) and claims['exp'] > time.time() + 3600 and hmac.compare_digest(sig, expected)
            except (KeyError, TypeError, ValueError, IndexError): valid = False
            if not valid: raise RuntimeError('Compatibility fixture validation failed at identity ' + str(index))
            checked = index
    if checked != 20000: raise RuntimeError('Incomplete canonical fixture users')
    return hashlib.sha256(raw).hexdigest()


def inputs(attestation=None):
    a = s.deployment_attestation() if attestation is None else attestation
    return {'app': a['app_source_sha256'], 'verification': a['verification_source_sha256'], 'runtime': a['runtime_inputs_sha256'], 'schema': a['schema']['sha256'], 'images': a['images'], 'host': a['host_identity_sha256'], 'tokens': token_hash(), 'full_runtime': a['full_runtime'], 'tools_image': b.capture(['docker', 'image', 'inspect', 'baas-trailbase-vps16-tools:0.1.0', '--format', '{{.Id}} {{.Os}}/{{.Architecture}}']).strip()}


def tools(script, log, name):
    # Admin key comes from existing private env_file; compatibility key via env,
    # never argv. No serving stop/start/deploy/import here.
    env = dict(os.environ, **s.runtime_values())
    subprocess.run(compose() + ['run', '--rm', '-T', '--no-deps', '--name', s.PROJECT + '-' + name, '-e', 'JWT_SECRET', '-e', 'PYTHONDONTWRITEBYTECODE=1', 'tools', 'bash', '-euc', script], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)


def reset(log):
    tools('export CONVEX_RESET_ERROR_DIRECTORY=/state/convex/reset-private-errors; python3 /work/scripts/convex.py reset; export CONVEX_NATIVE_DATASET_MANIFEST=/state/convex/dataset.json CONVEX_SEED_DIR=/state/convex/seed; python3 /work/test/baas/convex_dataset.py', log, 'reset-tools')


def require_headroom():
    s.require_native()
    if b.PROJECT != s.PROJECT or b.PLATFORM != 'linux/amd64' or b.RUNNER_PROFILE != 'k6-2cpu-8g-v3': raise RuntimeError('Wrong native campaign namespace/platform/runner')
    b.require_vm_headroom('standard', int(b.capture(['docker', 'info', '--format', '{{.MemTotal}}'])), os.cpu_count())
    mem = {key: int(value.split()[0]) * 1024 for key, value in (line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())}
    if mem['MemAvailable'] < 9 * 1024**3 or mem['SwapTotal'] != 0: raise RuntimeError('Insufficient actual runner+reserve headroom; preserve unrelated workloads')


def monitor(stop, destination):
    names = [s.PROJECT + '-' + role + '-1' for role in s.SERVICES] + [b.LOAD]; kernel = None
    with (destination / 'resources.jsonl').open('x') as stream:
        while not stop.is_set():
            record = {'time': time.time()}
            try:
                result = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{json .}}', *names], capture_output=True, text=True, timeout=12)
                for line in result.stdout.splitlines():
                    item = json.loads(line); record[item['Name']] = item
                if b.LOAD in record and kernel is None:
                    item = json.loads(b.capture(['docker', 'inspect', b.LOAD]))[0]; pid = item['State']['Pid']
                    if pid:
                        group = Path('/sys/fs/cgroup') / Path(f'/proc/{pid}/cgroup').read_text().strip().split('::', 1)[1].lstrip('/')
                        kernel = {key: (group / key).read_text() for key in ['cpu.max', 'memory.max', 'memory.swap.max']}
                if kernel: record['load_kernel_cgroup'] = kernel
                record['target_stack'] = s.parent_sample()
                record.update(b.host_sample())
            except Exception as error: record['monitor_error'] = str(error)
            stream.write(json.dumps(record) + '\n'); stream.flush()
            if 'monitor_error' in record: return
            stop.wait(3)


def attempt(vus, tier='standard', smoke=False):
    if s.DEPLOYMENT_NAME == 'retest-v1':
        from convex_retest_safety import validate_attempt
        validate_attempt(vus, tier, smoke)
        raise RuntimeError('Fresh serving attempts require their versioned adapter and actual new lifecycle/budget/monitoring evidence')
    require_headroom()
    if tier != 'standard' or not 1 <= vus <= 20000: raise ValueError('Only approved standard tier and1..20000VUs')
    if b.capture(['docker', 'ps', '-aq', '--filter', 'name=^' + b.LOAD + '$']).strip(): raise RuntimeError('Owned runner name occupied; inspect before cleanup')
    correctness = STATE / 'correctness.log'; attestation = json.loads((STATE / 'correctness-manifest.json').read_text()); log_hash = hashlib.sha256(correctness.read_bytes()).hexdigest()
    validate_correctness(attestation, inputs(), log_hash)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + f'-standard-{vus}vu-{b.RUNNER_PROFILE}' + ('-smoke' if smoke else '')
    local = STATE / 'runs' / run_id; local.mkdir(parents=True); destination = RESULTS / run_id; destination.mkdir(parents=True)
    b.snapshot(destination, service='convex')
    with (destination / 'reset.log').open('x') as log: reset(log)
    require_headroom(); deployed = s.deployment_attestation(); current = inputs(deployed)
    validate_correctness(attestation, current, log_hash); before = deployed['serving_profile']
    # No prior runtime failure may be hidden by a later manual restart.
    issue = target_issue(attestation['serving_targets'], before['targets'])
    if issue: raise RuntimeError(issue + '; no automatic revival/re-attestation')
    manifest = {'service': 'convex', 'versions': s.PINS, 'postgres_versions': s.POSTGRES, 'tier': tier, 'vus': vus, 'mode': 'smoke' if smoke else 'capacity', 'deployment_track': b.TRACK, 'platform': b.PLATFORM, 'compose_project': s.PROJECT, 'runner_profile': b.RUNNER_PROFILE, 'runner_limits': b.RUNNER_LIMITS, 'inputs': current, 'target_before': before, 'schema_before': deployed['schema'], 'started_utc': datetime.now(timezone.utc).isoformat(), 'git_commit': b.capture(['git', 'rev-parse', 'HEAD']).strip(), 'git_status': b.capture(['git', 'status', '--porcelain']), 'serving_budget': {'cpus': 1, 'memory_gib': 4, 'memory_bytes': 4294967296, 'swap_bytes': 0, 'backend_bytes': 3221225472, 'postgres_bytes': 1073741824, 'allocation_type': 'Quota-limited shared-host slice; entire serving stack'}, 'runner_budget': {'software': 'k6', 'version': '1.3.0', 'cpus': 2, 'memory_gib': 8, 'memory_bytes': 8589934592, 'swap_bytes': 0, 'profile': b.RUNNER_PROFILE}, 'tested_software': {'convex': 'precompiled-2026-10-06-a3538c6', 'sdk_cli': '1.46.0', 'bundled_node': '22.22.2', 'tools_node': '22.20.0', 'postgres': '17.11-bookworm', 'backend_version_endpoint': 'unknown', 'images': deployed['images']}, 'clean_shutdown': {'result': 'FAILED', 'backend_exit': 139, 'capacity_exception': 'Explicit owner permission after separate acknowledged crash-recovery proof; no lifecycle or power-loss certification'}, 'path': 'k6 -> native HTTP actions -> private native queries/mutations -> official PostgreSQL persistence; bundled executor included', 'auth': 'Fresh per-request synthetic HS256 compatibility verification; not native signup/login/session throughput', 'cost': 'Shared VPS; price/region unknown; not dedicated/measured $12/month equivalence', 'limitations': ['Native decimalText signed64/schema/logical relations, not baseline SQLite physical storage/FK/UNIQUE', 'Native defaults unchanged; no response/query-result/precomputed count/JWT verification caches', 'Ordinary native DB/index/module/page caches enabled', 'Clean SIGINT backend shutdown FAILED139; acknowledged recovery not provider power-loss proof', 'Shared host/storage/background workload; provider thermals unavailable'], 'host_before': b.host_sample()}
    for name in ['dataset.json', 'correctness.log', 'correctness-manifest.json', 'runtime-freeze.json']:
        shutil.copyfile(STATE / name, destination / name)
    (destination / 'manifest-before.json').write_text(json.dumps(manifest, indent=2) + '\n')
    stop = threading.Event(); thread = threading.Thread(target=monitor, args=(stop, local), daemon=True); thread.start(); load = None; exit_code = 255
    try:
        argv = compose() + ['run', '-T', '--no-deps', '--name', b.LOAD, '-e', f'VUS={vus}', '-e', f'SMOKE={int(smoke)}', '-e', 'TOKENS=/tokens.json', '-e', f'SUMMARY=/runs/{run_id}/k6-summary.json', 'k6', 'run', '--quiet', '--out', f'json=/runs/{run_id}/samples.json.gz', '/work/bench/baas.mjs']
        with (local / 'k6.log').open('x') as log: exit_code = subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
        if subprocess.run(['docker', 'inspect', b.LOAD], capture_output=True).returncode == 0: load = b.inspect(b.LOAD)
    finally:
        stop.set(); thread.join(timeout=30)
        probe = subprocess.run(['docker', 'inspect', b.LOAD], capture_output=True, text=True)
        if probe.returncode == 0:
            item = json.loads(probe.stdout)[0]
            if item['Config']['Labels'].get('com.docker.compose.project') != s.PROJECT: raise RuntimeError('Runner ownership changed; refusing cleanup')
            subprocess.run(['docker', 'rm', '-f', item['Id']], capture_output=True, check=True)
    if thread.is_alive(): raise RuntimeError('Resource monitor did not stop')
    summary = json.loads((local / 'k6-summary.json').read_text()) if (local / 'k6-summary.json').exists() else {}
    outcome, reason = b.measurement_verdict(summary, exit_code, local, smoke, load)
    records = [json.loads(line) for line in (local / 'resources.jsonl').read_text().splitlines()]; kernels = [r['load_kernel_cgroup'] for r in records if 'load_kernel_cgroup' in r]
    if outcome != 'invalid':
        if not kernels or any(k['cpu.max'].split() != ['200000', '100000'] or int(k['memory.max']) != 8589934592 or int(k['memory.swap.max']) != 0 for k in kernels): outcome, reason = 'invalid', 'missing or incorrect actual runner kernel budget'
        elif load['image_manifest_digest'] != K6_MANIFEST: outcome, reason = 'invalid', 'runner selected manifest differs from frozen pin'
    after_targets = s.targets()
    after = {'targets': after_targets, 'parent': s.parent_sample()}; issue = runtime_issue(before, after)
    if outcome != 'invalid' and issue: outcome, reason = 'fail', issue
    if not issue:
        after = s.profile()
        if inputs() != current: outcome, reason = 'invalid', 'frozen source/runtime/SDK/generated/schema/image/token inputs changed'
    for record in records:
        parent = record.get('target_stack')
        if parent and any(parent[key].strip() != before['parent'][key].strip() for key in ['cpu.max', 'memory.max', 'memory.swap.max']): outcome, reason = 'invalid', 'aggregate serving limits changed during monitoring'
    manifest.update(target_after=after, load_after=load, k6_exit_code=exit_code, result=outcome, reason=reason, finished_utc=datetime.now(timezone.utc).isoformat())
    for path in local.iterdir(): shutil.copyfile(path, destination / path.name)
    values = lambda name: summary.get('metrics', {}).get(name + '{phase:hold}', {}).get('values', {})
    latency = values('http_req_duration'); count = values('http_reqs').get('count', 0)
    compact = {'outcome': outcome, 'reason': reason, 'vus': vus, 'tier': tier, 'mode': manifest['mode'], 'runner_profile': b.RUNNER_PROFILE, 'deployment_track': b.TRACK, 'platform': b.PLATFORM, 'hold_requests': count, 'hold_rps': count / (20 if smoke else 300), 'latency_ms': latency, 'request_errors': values('request_errors'), 'schema_errors': values('schema_errors'), 'tested_software': manifest['tested_software'], 'serving_budget': manifest['serving_budget'], 'runner_budget': manifest['runner_budget'], 'clean_shutdown': manifest['clean_shutdown']}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n'); (destination / 'summary.json').write_text(json.dumps(compact, indent=2) + '\n')
    (destination / 'report.md').write_text(report_header() + f'''\n## Convex standard — {vus} VUs ({manifest['mode']})

Outcome: **{outcome}** — {reason}. One attempt, not a maximum-capacity score. {'Short calibration only, not scored.' if smoke else 'Full300-second scored hold; independent confirmations still required.'}

- Hold requests{count}; throughput{compact['hold_rps']:.6f} requests/s.
- p50/p95/p99/max ms: {latency.get('med', 'N/A')} / {latency.get('p(95)', 'N/A')} / {latency.get('p(99)', 'N/A')} / {latency.get('max', 'N/A')}.
- Request/schema errors: {values('request_errors').get('rate', 'N/A')} / {values('schema_errors').get('rate', 'N/A')}.
- Source overlay/patch and raw complete dependency/generated inventory retained; immutable runtime/compiler/image pins inmanifest. Original full source/dependency archive staysprivate pending distribution/license/privacy handling, not falsely represented as a public download.
- Original raw samples, endpoint metrics/statuses/outliers, parent/child/host/runner counters retained; SHA256SUMS. No pooled quantiles or cost/request claim.
- Canonical full native hash restoration beforemeasurement, full frozen correctness evidence copied; no serving restart/reseed/cache flush. Compatibility JWTs are NOT nativeAuththroughput.
- Native clean-shutdown gate remains FAILED139 regardless of measured serving outcome.
''')
    b.checksum_files(destination); progress = RESULTS / 'progress'; progress.mkdir(exist_ok=True)
    for name in ['summary.json', 'report.md']: shutil.copyfile(destination / name, progress / (run_id + '-' + name))
    print(json.dumps({'run': run_id, **compact}), flush=True)
    if issue: raise RuntimeError('Serving runtime failure preserved; no new attempt/revival: ' + issue)
    return outcome, str(destination.relative_to(ROOT))


def main():
    if s.DEPLOYMENT_NAME == 'retest-v1':
        raise RuntimeError('Fresh retest requires its versioned shared-budget controller, not the historical CLI')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true'); parser.add_argument('--vus', type=int, default=1000); parser.add_argument('--campaign', action='store_true'); parser.add_argument('--max-vus', type=int, default=20000); parser.add_argument('--max-attempts', type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.vus <= 20000 or not 25 <= args.max_vus <= 20000 or not 1 <= args.max_attempts <= 12 or (args.campaign and args.smoke): parser.error('Approved bounded VU/attempt/mode constraints required')
    with (STATE / 'campaign.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.campaign:
            if (STATE / 'campaign.json').exists(): raise RuntimeError('Campaign evidence exists; inspect before explicit continuation')
            b.campaign(args, 'standard', attempt_runner=attempt, results=RESULTS, campaign_file=STATE / 'campaign.json')
        elif attempt(args.vus, smoke=args.smoke)[0] != 'pass': raise SystemExit(1)


if __name__ == '__main__': main()
