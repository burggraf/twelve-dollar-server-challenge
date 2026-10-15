"""PocketBase uses the fixed common scoring/search and frozen-evidence contract."""
import base64
import csv
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import threading
import time
from urllib.error import HTTPError, URLError

import benchmark as b
import pocketbase_profile as s

ROOT, STATE = s.ROOT, s.STATE
RESULTS = ROOT / 'results/pocketbase' / b.TRACK
K6_MANIFEST = 'sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656'


def validate_correctness(attestation, current, log_sha256):
    if attestation.get('inputs') != current or attestation.get('log_sha256') != log_sha256:
        raise RuntimeError('Full correctness evidence is stale for current source, verification, runtime, schema, image, host, tokens or raw log')
    return True


def target_issue(before, after):
    if set(before) != set(s.SERVICES) or set(after) != set(s.SERVICES):
        return 'required serving component set changed'
    for role in s.SERVICES:
        a, z = before[role], after[role]
        state = z['State']
        if not state.get('Running') or state.get('OOMKilled') or state.get('Paused') or state.get('Restarting') or a['Id'] != z['Id'] or a['RestartCount'] != z['RestartCount'] or a['State']['StartedAt'] != state['StartedAt']:
            return 'serving process OOM/exit/restart: ' + role
    return None


def report_header():
    return f'''## Tested software and VPS slice

- **PocketBase {s.PINS['version']}**, upstream `{s.PINS['upstream_commit']}`; **Go {s.PINS['go_version']}**; upstream default **SQLite {s.PINS['sqlite_engine_version']} / modernc.org/sqlite v1.60.1**. Immutable builder/runtime pins, native executable/image IDs and source hashes are in `manifest.json`.
- **Entire serving stack: 1 vCPU quota / 4 GiB RAM (4,294,967,296 bytes) / no swap**, including native HTTP/routes/Auth/REST/admin APIs and embedded main/auxiliary databases, under one kernel-enforced parent budget.
- **Separate runner: k6 1.3.0 / 2 vCPU quota / 8 GiB RAM (8,589,934,592 bytes) / no swap**, `k6-2cpu-8g-v3`.
- This is a quota-limited **shared-host slice** on native AMD64 `azabab.com`, not a dedicated 1-vCPU VPS or a measured $12/month offering.
'''


def token_hash():
    raw = (ROOT / '.state/seed/tokens.json').read_bytes()
    entries = json.loads(raw)
    if len(entries) != 20000:
        raise RuntimeError('Expected 20,000 compatibility token identities')
    key = s.runtime_values()['JWT_SECRET'].encode()
    checked = 0
    with (ROOT / '.state/seed/users.tsv').open(newline='', encoding='utf-8') as stream:
        for index, (entry, user) in enumerate(zip(entries, csv.reader(stream, delimiter='\t', quoting=csv.QUOTE_NONE)), 1):
            try:
                head, payload, signature = entry['token'].split('.')
                decode = lambda text: json.loads(base64.urlsafe_b64decode(text + '=' * (-len(text) % 4)))
                claims = decode(payload)
                expected = base64.urlsafe_b64encode(hmac.digest(key, (head + '.' + payload).encode(), 'sha256')).decode().rstrip('=')
                valid = (decode(head)['alg'] == 'HS256' and entry['id'] == index and user[0] == str(index)
                         and entry['username'] == user[1] and claims['sub'] == str(index)
                         and claims['username'] == user[1] and type(claims['exp']) in (int, float)
                         and claims['exp'] > time.time() + 3600 and hmac.compare_digest(signature, expected))
            except (KeyError, TypeError, ValueError, IndexError):
                valid = False
            if not valid:
                raise RuntimeError('Compatibility fixture validation failed at identity ' + str(index))
            checked = index
    if checked != 20000:
        raise RuntimeError('Compatibility fixture has incomplete canonical user input')
    return hashlib.sha256(raw).hexdigest()


def inputs(attestation=None):
    value = s.deployment_attestation() if attestation is None else attestation
    return {'app': value['app_source_sha256'], 'verification': value['verification_source_sha256'],
            'runtime': value['runtime_inputs_sha256'], 'schema': value['schema']['sha256'],
            'images': value['images'], 'host': value['host_identity_sha256'],
            'tokens': token_hash(), 'executable': value['native_build']['executable_sha256'],
            'tools_image': b.capture(['docker', 'image', 'inspect', 'baas-trailbase-vps16-tools:0.1.0',
                                     '--format', '{{.Id}} {{.Os}}/{{.Architecture}}']).strip()}


def monitor(stop, destination):
    names = [s.PROJECT + '-pocketbase-1', b.LOAD]
    kernel = None
    with (destination / 'resources.jsonl').open('w') as stream:
        while not stop.is_set():
            record = {'time': time.time()}
            try:
                result = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{json .}}', *names],
                                        capture_output=True, text=True, timeout=12)
                for line in result.stdout.splitlines():
                    item = json.loads(line)
                    record[item['Name']] = item
                if b.LOAD in record and kernel is None:
                    item = json.loads(b.capture(['docker', 'inspect', b.LOAD]))[0]
                    pid = item['State']['Pid']
                    if pid:
                        group = Path('/sys/fs/cgroup') / Path(f'/proc/{pid}/cgroup').read_text().strip().split('::', 1)[1].lstrip('/')
                        kernel = {key: (group / key).read_text() for key in ['cpu.max', 'memory.max', 'memory.swap.max']}
                if kernel:
                    record['load_kernel_cgroup'] = kernel
                try:
                    record['target_stack'] = s.parent_sample()
                except FileNotFoundError:
                    record['target_stack_unavailable'] = True
                record.update(b.host_sample())
            except Exception as error:
                record['monitor_error'] = str(error)
            stream.write(json.dumps(record) + '\n')
            stream.flush()
            if 'monitor_error' in record:
                return
            stop.wait(3)


def parent_oom(value):
    return int(dict(line.split() for line in value['memory.events'].splitlines()).get('oom_kill', 0))


def attempt(vus, tier='standard', smoke=False):
    from pocketbase import compose, reset, require_native
    require_native()
    if tier != 'standard':
        raise ValueError('PocketBase cohort requires the standard 1-vCPU/4-GiB aggregate profile')
    total = int(b.capture(['docker', 'info', '--format', '{{.MemTotal}}']).strip())
    cpus = int(b.capture(['docker', 'info', '--format', '{{.NCPU}}']).strip())
    b.require_vm_headroom(tier, total, cpus)
    if b.capture(['docker', 'ps', '-aq', '--filter', 'name=^' + b.LOAD + '$']).strip():
        raise RuntimeError('Owned load-container name is occupied; inspect before cleanup')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + f'-standard-{vus}vu-{b.RUNNER_PROFILE}' + ('-smoke' if smoke else '')
    local = STATE / 'runs' / run_id
    local.mkdir(parents=True)
    destination = RESULTS / run_id
    destination.mkdir(parents=True)
    b.snapshot(destination, service='pocketbase')
    correctness = STATE / 'correctness.log'
    attestation = json.loads((STATE / 'correctness-manifest.json').read_text())
    log_hash = hashlib.sha256(correctness.read_bytes()).hexdigest()
    validate_correctness(attestation, inputs(), log_hash)
    with (destination / 'reset.log').open('w') as log:
        reset(log=log)
    deployed = s.deployment_attestation()
    current = inputs(deployed)
    validate_correctness(attestation, current, log_hash)
    before = deployed['serving_profile']
    manifest = {'service': 'pocketbase', 'upstream_commit': s.PINS['upstream_commit'], 'versions': s.PINS,
                'tested_software': {'product': s.PINS['version'], 'go': s.PINS['go_version'],
                                    'sqlite_driver': s.PINS['sqlite_driver'], 'sqlite_engine': s.PINS['sqlite_engine_version'],
                                    'sqlite_source_id': s.PINS['sqlite_engine_source_id'], 'native_build': deployed['native_build']},
                'tier': tier, 'vus': vus, 'mode': 'smoke' if smoke else 'capacity',
                'deployment_track': b.TRACK, 'platform': b.PLATFORM, 'compose_project': s.PROJECT,
                'runner_profile': b.RUNNER_PROFILE, 'runner_limits': b.RUNNER_LIMITS,
                'aggregate_limits': {'cpus': 1, 'memory_bytes': 4294967296, 'swap_bytes': 0},
                'serving_budget': {'cpus': 1, 'memory_gib': 4, 'memory_bytes': 4294967296, 'swap_bytes': 0,
                                   'allocation_type': 'Quota-limited shared-host slice; entire serving stack'},
                'runner_budget': {'software': 'k6', 'version': '1.3.0', 'cpus': 2, 'memory_gib': 8,
                                  'memory_bytes': 8589934592, 'swap_bytes': 0, 'profile': b.RUNNER_PROFILE},
                'inputs': current, 'target_before': before, 'schema_before': deployed['schema'],
                'started_utc': datetime.now(timezone.utc).isoformat(),
                'git_commit': b.capture(['git', 'rev-parse', 'HEAD']).strip(),
                'git_status': b.capture(['git', 'status', '--porcelain']), 'host': b.capture(['uname', '-sm']),
                'host_memory_cpu': Path('/proc/meminfo').read_text() + Path('/proc/cpuinfo').read_text(),
                'docker': b.capture(['docker', 'version', '--format', 'Client={{.Client.Version}} Server={{.Server.Version}}']),
                'docker_vm': b.capture(['docker', 'info', '--format', 'OS={{.OperatingSystem}} Arch={{.Architecture}} CPUs={{.NCPU}} MemoryBytes={{.MemTotal}}']),
                'vm_cpu_count': cpus, 'vm_os_reserve_cpus': 1, 'vm_os_reserve_bytes': 1024**3,
                'auth': 'Synthetic base-collection app users and per-write HS256 compatibility JWTs; 0 regular native Auth users and 1 platform installer superuser; native signup/login/session throughput NOT measured',
                'path': 'k6 -> native PocketBase Go routes -> supported DB query builder / native Record transactions -> embedded SQLite WAL/NORMAL',
                'cost': 'Existing shared VPS; price/region unknown; no cost/request or dedicated-$12 equivalence claim',
                'limitations': ['Native extension, not standalone SQLite serving driver',
                                'Native Text IDs/numeric order; extra platform like IDs; native relation validation rather than physical FK declarations',
                                'Ordinary buffers/plans/platform metadata caches enabled; no response/query-result/like-count/JWT-verification caches',
                                'Shared host/storage/page caches/background services; provider thermals unavailable',
                                'Normal process restart verified, not provider power-loss durability'],
                'allocated_data_kib_before': b.capture(['docker', 'exec', s.PROJECT + '-pocketbase-1', 'du', '-sk', '/data']).strip()}
    for name, source in [('dataset.json', STATE / 'dataset.json'), ('correctness.log', correctness),
                         ('correctness-manifest.json', STATE / 'correctness-manifest.json')]:
        shutil.copyfile(source, destination / name)
    stop = threading.Event()
    thread = threading.Thread(target=monitor, args=(stop, local), daemon=True)
    thread.start()
    load, exit_code = None, 255
    try:
        argv = compose() + ['run', '-T', '--no-deps', '--name', b.LOAD, '-e', f'VUS={vus}',
                            '-e', f'SMOKE={int(smoke)}', '-e', 'TOKENS=/tokens.json',
                            '-e', f'SUMMARY=/runs/{run_id}/k6-summary.json', 'k6', 'run', '--quiet',
                            '--out', f'json=/runs/{run_id}/samples.json.gz', '/work/bench/baas.mjs']
        with (local / 'k6.log').open('w') as log:
            exit_code = subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
        if subprocess.run(['docker', 'inspect', b.LOAD], capture_output=True).returncode == 0:
            load = b.inspect(b.LOAD)
    finally:
        stop.set()
        thread.join(timeout=30)
        check = subprocess.run(['docker', 'inspect', b.LOAD], capture_output=True, text=True)
        if check.returncode == 0:
            item = json.loads(check.stdout)[0]
            if item['Config']['Labels'].get('com.docker.compose.project') != s.PROJECT:
                raise RuntimeError('Load ownership changed; refusing cleanup')
            subprocess.run(['docker', 'rm', '-f', item['Id']], capture_output=True, check=True)
    if thread.is_alive():
        raise RuntimeError('Resource monitor did not stop')
    summary = json.loads((local / 'k6-summary.json').read_text()) if (local / 'k6-summary.json').exists() else {}
    outcome, reason = b.measurement_verdict(summary, exit_code, local, smoke, load)
    records = [json.loads(line) for line in (local / 'resources.jsonl').read_text().splitlines()]
    kernels = [r['load_kernel_cgroup'] for r in records if 'load_kernel_cgroup' in r]
    if outcome != 'invalid':
        if not kernels or any(k['cpu.max'].split() != ['200000', '100000'] or int(k['memory.max']) != 8589934592 or int(k['memory.swap.max']) != 0 for k in kernels):
            outcome, reason = 'invalid', 'missing or incorrect actual runner kernel budget'
        elif load['image_manifest_digest'] != K6_MANIFEST:
            outcome, reason = 'invalid', 'load-generator selected manifest differs from frozen pin'
    after_targets = s.targets()
    issue = target_issue(before['targets'], after_targets)
    if outcome != 'invalid' and issue:
        outcome, reason = 'fail', issue
    try:
        after = s.profile()
        if parent_oom(after['parent']) > parent_oom(before['parent']) and outcome != 'invalid':
            outcome, reason = 'fail', 'aggregate serving cgroup OOM kill'
    except (HTTPError, URLError, TimeoutError):
        after = {'targets': after_targets, 'parent': s.parent_sample()}
        if outcome != 'invalid':
            outcome, reason = 'fail', 'native storage/application readiness failed after hold'
    except (RuntimeError, FileNotFoundError) as error:
        try:
            parent_after = s.parent_sample()
        except FileNotFoundError:
            parent_after = None
        after = {'targets': after_targets, 'parent': parent_after}
        if outcome != 'invalid' and not issue:
            outcome, reason = 'invalid', str(error)
    after_images = {role: {key: value[key] for key in ['Image', 'platform', 'image_manifest_digest']}
                    for role, value in after_targets.items()}
    try:
        schema_changed = not issue and s.schema_state()['sha256'] != current['schema']
    except (RuntimeError, sqlite3.Error):
        schema_changed = True
    if s.app_hash() != current['app'] or s.verification_hash() != current['verification'] or s.runtime_hash() != current['runtime'] or schema_changed or after_images != current['images'] or token_hash() != current['tokens']:
        outcome, reason = 'invalid', 'frozen source/verification/runtime/schema/image/token inputs changed during attempt'
    for record in records:
        parent = record.get('target_stack')
        if parent and any(parent[key].strip() != before['parent'][key].strip() for key in ['cpu.max', 'memory.max', 'memory.swap.max']):
            outcome, reason = 'invalid', 'aggregate serving limits changed during monitoring'
    manifest.update(target_after=after, load_after=load, k6_exit_code=exit_code, result=outcome, reason=reason,
                    finished_utc=datetime.now(timezone.utc).isoformat(),
                    allocated_data_kib_after=b.capture(['docker', 'exec', s.PROJECT + '-pocketbase-1', 'du', '-sk', '/data']).strip() if after_targets['pocketbase']['State']['Running'] else None)
    for path in local.iterdir():
        shutil.copyfile(path, destination / path.name)
    metrics = summary.get('metrics', {})
    values = lambda name: metrics.get(name + '{phase:hold}', {}).get('values', {})
    latency, count = values('http_req_duration'), values('http_reqs').get('count', 0)
    compact = {'outcome': outcome, 'reason': reason, 'vus': vus, 'tier': tier, 'mode': manifest['mode'],
               'runner_profile': b.RUNNER_PROFILE, 'deployment_track': b.TRACK, 'platform': b.PLATFORM,
               'hold_requests': count, 'hold_rps': count / (20 if smoke else 300),
               'latency_ms': latency, 'request_errors': values('request_errors'), 'schema_errors': values('schema_errors'),
               'tested_software': manifest['tested_software'], 'serving_budget': manifest['serving_budget'],
               'runner_budget': manifest['runner_budget']}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (destination / 'summary.json').write_text(json.dumps(compact, indent=2) + '\n')
    (destination / 'report.md').write_text(f'''# PocketBase standard — {vus} VUs ({manifest['mode']})

{report_header()}

Outcome: **{outcome}** — {reason}.

One attempt, **not a maximum-capacity score**. {'Short calibration only; not scored.' if smoke else 'Full 300-second hold; see search and independent confirmations.'}

- Hold requests: {count}; throughput: {compact['hold_rps']:.2f} requests/s.
- p50/p95/p99: {latency.get('med', 'N/A')} / {latency.get('p(95)', 'N/A')} / {latency.get('p(99)', 'N/A')} ms; maximum: {latency.get('max', 'N/A')} ms.
- Request/schema errors: {values('request_errors').get('rate', 'N/A')} / {values('schema_errors').get('rate', 'N/A')}.
- Supported native Go extension/DB/Record transaction path; compatibility JWTs checked per write, not native Auth throughput.
- Original canonical logical data/hash: `dataset.json`; complete native correctness: `correctness.log`, `correctness-manifest.json`.
- Native Text IDs/numeric ordering, extra like IDs, platform metadata and native relation validation mapping are disclosed in source/profile and manifest.
- Original samples, quantiles/statuses/endpoint metrics and raw target/runner/parent/host counters: `samples.json.gz`, `k6-summary.json`, `resources.jsonl`.
- Immutable image/build IDs, actual kernel budgets, lifecycle identities, source/runtime/schema fingerprints and caveats: `manifest.json`.
- Source reproduction overlay: `source.tar.gz`, `working-tree.patch`, base commit in manifest. Verify **SHA256SUMS**; private keys/tokens/runtime database files excluded.
- Ordinary restart persistence is not a provider power-loss test. Shared-host price/region unknown; no dedicated-$12 or cost/request claim.
''')
    b.checksum_files(destination)
    progress = RESULTS / 'progress'
    progress.mkdir(exist_ok=True)
    for filename in ['summary.json', 'report.md']:
        shutil.copyfile(destination / filename, progress / (run_id + '-' + filename))
    print(json.dumps({'run': run_id, **compact}), flush=True)
    return outcome, str(destination.relative_to(ROOT))
