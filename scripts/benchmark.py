#!/usr/bin/env python3
"""TrailBase local capacity runner. Keeps every attempt, including invalid/failed runs.

No credentials are included in argv, manifests, source snapshots, or output artifacts.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
import platform
import re
from pathlib import Path
import shutil
import subprocess
import tarfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def deployment_settings(system, machine, environ):
    arch = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'amd64', 'amd64': 'amd64'}.get(machine)
    if system not in ('Darwin', 'Linux') or not arch:
        raise ValueError('Unsupported native benchmark host')
    native = 'linux/' + arch
    if environ.get('BENCHMARK_PLATFORM', native) != native:
        raise ValueError('Primary benchmark requires native images, not emulation')
    project = environ.get('BENCHMARK_PROJECT', 'baas-trailbase')
    if len(project) > 63 or not re.fullmatch(r'baas-(?:trailbase|supabase|pocketbase)(?:-[a-z0-9]+)*', project):
        raise ValueError('Project must use the isolated baas-trailbase benchmark namespace')
    prefix = 'local-orbstack-' if system == 'Darwin' else ('vps16-linux-' if project in ('baas-trailbase-vps16', 'baas-supabase-vps16', 'baas-pocketbase-vps16') else 'vps-linux-')
    return {'project': project, 'platform': native, 'track': prefix + arch}


DEPLOYMENT = deployment_settings(platform.system(), platform.machine(), os.environ)
PROJECT, PLATFORM, TRACK = (DEPLOYMENT[key] for key in ['project', 'platform', 'track'])
COMPOSE = ['docker', 'compose', '-p', PROJECT, '-f', str(ROOT / 'services/trailbase/compose.yaml')]
TARGET = PROJECT + '-trailbase-1'
LOAD = PROJECT + '-load'
RESULTS = ROOT / 'results/trailbase' / TRACK
TIERS = {'small': (1, 2 * 1024**3), 'standard': (1, 4 * 1024**3), 'large': (4, 4 * 1024**3)}


def runner_settings(name='k6-2cpu-4g-v2'):
    sizes = {'k6-2cpu-4g-v2': 4, 'k6-2cpu-8g-v3': 8}
    if name not in sizes:
        raise ValueError('Unknown runner profile; select a versioned, approved budget')
    size = sizes[name]
    return {'profile': name, 'memory': f'{size}g',
            'limits': {'NanoCpus': 2 * 10**9, 'Memory': size * 1024**3, 'MemorySwap': size * 1024**3}}


RUNNER = runner_settings(os.environ.get('BENCHMARK_RUNNER_PROFILE', 'k6-2cpu-4g-v2'))
RUNNER_PROFILE, RUNNER_LIMITS, RUNNER_MEMORY = (RUNNER[key] for key in ['profile', 'limits', 'memory'])


def require_vm_headroom(tier, vm_memory, vm_cpus=None):
    # Reserve at least 1 GiB for the VM/OS outside the serving and runner cgroups.
    if vm_memory < TIERS[tier][1] + RUNNER_LIMITS['Memory'] + 1024**3:
        raise RuntimeError('Insufficient VM memory headroom for serving tier + runner + 1 GiB OS reserve; '
                           'owner action required, no automatic host settings changes')
    if vm_cpus is not None and vm_cpus < TIERS[tier][0] + RUNNER_LIMITS['NanoCpus'] // 10**9 + 1:
        raise RuntimeError('Insufficient VM CPU headroom for serving tier + runner + 1 CPU OS reserve')


def evaluate(summary, exit_code):
    try:
        metrics = summary['metrics']
        values = lambda name: metrics[name + '{phase:hold}']['values']
        count = values('http_reqs')['count']
        latency, errors, schema = values('http_req_duration'), values('request_errors'), values('schema_errors')
        numbers = [count, latency['p(95)'], latency['p(99)'], errors['rate'], schema['rate']]
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in numbers):
            return 'invalid', 'non-finite/malformed hold metrics'
        if count <= 0 or count != int(count) or any(not 0 <= v <= 1 for v in [errors['rate'], schema['rate']]):
            return 'invalid', 'empty/malformed hold'
        if any(m['passes'] + m['fails'] != count for m in [errors, schema]):
            return 'invalid', 'incomplete response-validation samples'
    except (KeyError, TypeError, ValueError):
        return 'invalid', 'missing required hold evidence'
    if exit_code not in (0, 99):
        return 'invalid', f'load runner exited {exit_code}'
    passed = latency['p(95)'] < 500 and latency['p(99)'] < 1000 and errors['rate'] < .01 and schema['rate'] == 0
    if passed and exit_code != 0:
        return 'invalid', 'unexplained k6 threshold/runner failure'
    return ('pass', 'hold gates passed') if passed else ('fail', 'hold latency/error/schema gate failed')


def scenario_started(summary):
    try:
        value = summary['metrics']['benchmark_scenario_start_ms']['values']['value']
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            raise ValueError('invalid scenario start')
        return value / 1000
    except (KeyError, TypeError) as error:
        raise ValueError('missing k6 scenario-start clock') from error


def app_source_hash():
    directory = ROOT / 'services/trailbase'
    files = [directory / name for name in ['Dockerfile', 'entrypoint.sh', 'config.textproto']]
    files += list((directory / 'migrations').glob('*.sql'))
    files += [directory / 'app/Cargo.toml', directory / 'app/Cargo.lock']
    files += list((directory / 'app/src').glob('*.rs'))
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(str(path.relative_to(ROOT)).encode() + b'\0' + path.read_bytes() + b'\0')
    return digest.hexdigest()


def verification_source_hash():
    digest = hashlib.sha256()
    files = [ROOT / 'seed/generate.mjs', ROOT / 'services/trailbase/run.sh', ROOT / 'services/trailbase/compose.yaml']
    for name in ['scripts', 'bench', 'test']:
        files.extend(p for p in (ROOT / name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for path in sorted(files):
        digest.update(str(path.relative_to(ROOT)).encode() + b'\0' + path.read_bytes() + b'\0')
    return digest.hexdigest()


def command(argv, **kwargs):
    return subprocess.run(argv, cwd=ROOT, check=True, **kwargs)


def capture(argv):
    return command(argv, capture_output=True, text=True).stdout


def compose_environment(tier, environ=None):
    return {**(os.environ if environ is None else environ), 'TIER': tier,
            'BENCHMARK_PROJECT': PROJECT, 'BENCHMARK_PLATFORM': PLATFORM,
            'BENCHMARK_RUNNER_PROFILE': RUNNER_PROFILE, 'RUNNER_MEMORY': RUNNER_MEMORY}


def selected_container_platform(container, image_platform):
    # Docker 29's .Image can identify an index; image inspect then reports the
    # daemon's native choice, NOT necessarily the manifest used by this container.
    if 'ImageManifestDescriptor' not in container:
        return image_platform  # Legacy engines use the concrete image/config ID.
    descriptor = container.get('ImageManifestDescriptor') or {}
    selected = descriptor.get('platform') or {}
    if not selected.get('os') or not selected.get('architecture'):
        return None  # Descriptor present but incomplete: cannot certify native.
    return selected['os'] + '/' + selected['architecture']


def inspect(name):
    # Whitelist only; docker inspect's Config.Env must never enter a report.
    item = json.loads(capture(['docker', 'inspect', name]))[0]
    legacy_platform = capture(['docker', 'image', 'inspect', item['Image'], '--format', '{{.Os}}/{{.Architecture}}']).strip() if 'ImageManifestDescriptor' not in item else None
    return {key: item.get(key) for key in ['Id', 'Image', 'RestartCount', 'State']} | {
        'limits': {key: item['HostConfig'].get(key) for key in ['NanoCpus', 'Memory', 'MemorySwap']},
        'source_sha256': item['Config'].get('Labels', {}).get('benchmark.source_sha256'),
        'platform': selected_container_platform(item, legacy_platform),
        'image_manifest_digest': (item.get('ImageManifestDescriptor') or {}).get('digest'),
    }


def snapshot(destination, service='trailbase'):
    if service not in ('trailbase', 'supabase', 'pocketbase'):
        raise ValueError('Unsupported benchmark service snapshot')
    paths = [ROOT / name for name in ['README.md', 'MASTER_PLAN.md', 'LICENSE', 'SPEC.md', 'schema.sql', '.gitignore', '.dockerignore']]
    for name in [f'services/{service}', 'runner', 'scripts', 'bench', 'test', 'contracts', '.github/workflows', 'seed']:
        if (ROOT / name).exists():
            paths.extend(p for p in (ROOT / name).rglob('*') if p.is_file()
                         and not any(part in ['target', '__pycache__', 'tsv'] for part in p.parts)
                         and p.name not in ['tokens.json'] and not p.name.startswith('feed.db')
                         and (not p.name.startswith('.env') or p.name == '.env.example'))
    with tarfile.open(destination / 'source.tar.gz', 'w:gz') as archive:
        for path in sorted(set(paths)):
            archive.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
    (destination / 'working-tree.patch').write_bytes(command(['git', 'diff', 'HEAD', '--binary'], capture_output=True).stdout)


def host_sample(system=None, proc=Path('/proc')):
    system = system or platform.system()
    if system == 'Linux':
        names = ['vmstat', 'stat', 'meminfo', 'diskstats', 'loadavg', 'uptime',
                 'pressure/cpu', 'pressure/memory', 'pressure/io']
        return {'linux_' + name.replace('/', '_'): (proc / name).read_text() for name in names}
    if system != 'Darwin':
        raise ValueError('Unsupported host monitoring platform')
    record = {}
    for key, argv in [('vm_stat', ['vm_stat']), ('swap', ['sysctl', 'vm.swapusage']),
                      ('thermal', ['pmset', '-g', 'therm']), ('host_cpu_io', ['top', '-l', '2', '-s', '1', '-n', '0'])]:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=5)
        record[key] = result.stdout + result.stderr
    return record


def host_swapouts(record):
    text, prefix = (record['linux_vmstat'], 'pswpout ') if 'linux_vmstat' in record else (record.get('vm_stat', ''), 'Swapouts:')
    for line in text.splitlines():
        if line.startswith(prefix):
            try:
                value = int(line[len(prefix):].strip().rstrip('.'))
                return value if value >= 0 else None
            except ValueError:
                return None
    return None


def monitor(stop, destination):
    with (destination / 'resources.jsonl').open('w') as stream:
        while not stop.is_set():
            record = {'time': time.time()}
            try:
                for name in [TARGET, LOAD]:
                    result = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{json .}}', name],
                                            capture_output=True, text=True, timeout=10)
                    if result.returncode == 0 and result.stdout.strip():
                        record[name] = json.loads(result.stdout.strip())
                # Raw OS counters only, never process arguments/environments.
                record.update(host_sample())
            except Exception as error:
                record['monitor_error'] = str(error)
            stream.write(json.dumps(record) + '\n')
            stream.flush()
            if 'monitor_error' in record: return
            stop.wait(3)


def resource_verdict(destination, started, smoke, load_after):
    records = [json.loads(line) for line in (destination / 'resources.jsonl').read_text().splitlines()]
    if not records:
        return 'missing monitoring samples'
    if any('monitor_error' in record for record in records):
        return 'resource monitor failed'
    if load_after and load_after['State'].get('OOMKilled'):
        return 'load generator OOM (not target capacity)'
    begin, end = (5, 25) if smoke else (210, 510)
    hold = [r for r in records if started + begin <= r['time'] < started + end]
    samples = [r[LOAD] for r in hold if LOAD in r]
    if not samples:
        return 'missing load-generator hold monitoring'
    times = [r['time'] for r in hold if LOAD in r]
    tolerance = 10 if smoke else 15
    if len(samples) < 3 or times[0] > started + begin + tolerance or times[-1] < started + end - tolerance or any(b - a > 15 for a, b in zip(times, times[1:])):
        return 'incomplete load-generator hold monitoring'
    saturated = 0
    for sample in samples:
        saturated = saturated + 1 if float(sample['CPUPerc'].rstrip('%')) >= 180 else 0
        if saturated >= 3:
            return 'load generator sustained >=90% of its 2-CPU budget'
        if float(sample['MemPerc'].rstrip('%')) >= 90:
            return 'load generator used >=90% of its memory budget'
    first, last = host_swapouts(records[0]), host_swapouts(records[-1])
    if first is None or last is None:
        return 'missing host swap counters'
    if last > first:
        return 'host swap-outs increased during this attempt'
    return None


def measurement_verdict(summary, exit_code, destination, smoke, load_after):
    # An OOM can prevent k6 from writing its summary/clock. Preserve the known cause.
    if load_after and load_after['State'].get('OOMKilled'):
        return 'invalid', 'load generator OOM (not target capacity)'
    if not load_after or load_after.get('limits') != RUNNER_LIMITS:
        return 'invalid', 'load-generator limits do not match the selected runner profile'
    if load_after.get('platform') != PLATFORM:
        return 'invalid', 'load-generator image is not native to the selected host'
    outcome, reason = evaluate(summary, exit_code)
    # k6's scenario clock excludes image pulls AND potentially long VU initialization.
    try:
        resource_issue = resource_verdict(destination, scenario_started(summary), smoke, load_after)
    except ValueError as error:
        resource_issue = str(error)
    return ('invalid', resource_issue) if resource_issue else (outcome, reason)


def checksum_files(directory):
    lines = [f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}' for p in sorted(directory.iterdir()) if p.is_file() and p.name != 'SHA256SUMS']
    (directory / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')


def attempt(vus, tier, smoke=False):
    vm_memory = int(capture(['docker', 'info', '--format', '{{.MemTotal}}']).strip())
    vm_cpus = int(capture(['docker', 'info', '--format', '{{.NCPU}}']).strip())
    require_vm_headroom(tier, vm_memory, vm_cpus)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + f'-{tier}-{vus}vu-{RUNNER_PROFILE}' + ('-smoke' if smoke else '')
    local = ROOT / '.state/runs' / run_id
    local.mkdir(parents=True)
    destination = RESULTS / run_id
    destination.mkdir(parents=True)
    snapshot(destination)
    env = compose_environment(tier)
    with (destination / 'reset.log').open('w') as log:
        command(['bash', 'services/trailbase/run.sh', 'reset'], env=env, stdout=log, stderr=subprocess.STDOUT)
    before = inspect(TARGET)
    cgroup_lines = capture(['docker', 'exec', TARGET, 'cat', '/sys/fs/cgroup/cpu.max', '/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory.swap.max']).splitlines()
    quota, period = map(int, cgroup_lines[0].split())
    cpus, memory = TIERS[tier]
    expected_limits = {'NanoCpus': cpus * 10**9, 'Memory': memory, 'MemorySwap': memory}
    if quota / period != cpus or int(cgroup_lines[1]) != memory or int(cgroup_lines[2]) != 0:
        raise RuntimeError('Kernel cgroup limits do not match the selected tier')
    if before['platform'] != PLATFORM:
        raise RuntimeError('Serving image is not native to the selected host')
    if before['limits'] != expected_limits or before['source_sha256'] != app_source_hash():
        raise RuntimeError('Serving image/source or enforced tier differs from the expected configuration; rebuild first')
    (destination / 'dataset.json').write_bytes((ROOT / '.state/trailbase/dataset.json').read_bytes())
    correctness = ROOT / '.state/trailbase/correctness.log'
    attestation_file = ROOT / '.state/trailbase/correctness-manifest.json'
    if not correctness.exists() or not attestation_file.exists():
        raise RuntimeError('Run the full correctness gate first')
    attestation = json.loads(attestation_file.read_text())
    if attestation['app_source_sha256'] != app_source_hash() or attestation['verification_source_sha256'] != verification_source_hash() or attestation['image'] != before['Image'] or attestation['limits'] != before['limits'] or attestation['log_sha256'] != hashlib.sha256(correctness.read_bytes()).hexdigest():
        raise RuntimeError('Correctness evidence is stale for the serving image/log')
    shutil.copyfile(correctness, destination / 'correctness.log')
    shutil.copyfile(attestation_file, destination / 'correctness-manifest.json')
    manifest = {'service': 'trailbase', 'version': '0.34.6', 'sdk': '0.6.1', 'tier': tier, 'vus': vus,
        'deployment_track': TRACK, 'platform': PLATFORM, 'compose_project': PROJECT,
        'mode': 'smoke' if smoke else 'capacity', 'workload': 'baas-v1',
        'runner_profile': RUNNER_PROFILE, 'runner_limits': RUNNER_LIMITS, 'vm_os_reserve_bytes': 1024**3,
        'vm_os_reserve_cpus': 1, 'vm_cpu_count': vm_cpus,
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'git_commit': capture(['git', 'rev-parse', 'HEAD']).strip(), 'git_status': capture(['git', 'status', '--porcelain']),
        'app_source_sha256': app_source_hash(), 'target_before': before, 'target_kernel_cgroup_limits': cgroup_lines,
        'allocated_data_kib_before': capture(['docker', 'exec', TARGET, 'du', '-sk', '/app/traildepot/data']).strip(),
        'docker': capture(['docker', 'version', '--format', 'Client={{.Client.Version}} Server={{.Server.Version}}']),
        'docker_vm': capture(['docker', 'info', '--format', 'OS={{.OperatingSystem}} Arch={{.Architecture}} CPUs={{.NCPU}} MemoryBytes={{.MemTotal}}']),
        'host': capture(['uname', '-sm']),
        'host_memory_cpu': capture(['sysctl', 'hw.ncpu', 'hw.memsize', 'machdep.cpu.brand_string']) if platform.system() == 'Darwin' else Path('/proc/meminfo').read_text() + Path('/proc/cpuinfo').read_text(),
        'orbstack_version': capture(['orb', 'version']) if platform.system() == 'Darwin' else None,
        'cost': 'local hardware; cloud monthly cost/request not applicable' if platform.system() == 'Darwin' else 'existing shared VPS; monthly price not supplied; cost/request not calculated',
        'auth': 'HS256 compatibility verification inside native WASM handlers; not native TrailBase login throughput',
        'path': 'k6 container -> TrailBase HTTP -> Rust WASM guest -> TrailBase database/transaction SDK -> SQLite',
        'limitations': ['Shared host/VM and storage cache; no dedicated-machine equivalence',
                         'Background activity requires human review; see raw resources.jsonl',
                         'VPS hardware thermals are unavailable; Linux CPU steal/pressure/I/O counters are retained' if platform.system() == 'Linux' else 'Host thermal counters retained; inspect for throttling'],
    }
    stop = threading.Event()
    thread = threading.Thread(target=monitor, args=(stop, local), daemon=True)
    thread.start()
    load_after = None
    try:
        argv = COMPOSE + ['run', '-T', '--no-deps', '--name', LOAD,
            '-e', f'VUS={vus}', '-e', f'SMOKE={int(smoke)}', '-e', 'TOKENS=/tokens.json', '-e', f'SUMMARY=/runs/{run_id}/k6-summary.json',
            'k6', 'run', '--quiet', '--out', f'json=/runs/{run_id}/samples.json.gz', '/work/bench/baas.mjs']
        with (local / 'k6.log').open('w') as log:
            result = subprocess.run(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        load_after = inspect(LOAD)
    finally:
        stop.set()
        thread.join(timeout=30)
        subprocess.run(['docker', 'rm', '-f', LOAD], cwd=ROOT, capture_output=True)
    if thread.is_alive():
        raise RuntimeError('Resource monitor did not stop')
    summary_file = local / 'k6-summary.json'
    summary = json.loads(summary_file.read_text()) if summary_file.exists() else {}
    outcome, reason = measurement_verdict(summary, result.returncode, local, smoke, load_after)
    after = inspect(TARGET)
    if outcome != 'invalid' and (after['State'].get('OOMKilled') or not after['State'].get('Running') or after['RestartCount'] != before['RestartCount']):
        outcome, reason = 'fail', 'target OOM/exit/restart during attempt'
    manifest['allocated_data_kib_after'] = capture(['docker', 'exec', TARGET, 'du', '-sk', '/app/traildepot/data']).strip() if after['State'].get('Running') else None
    manifest.update(target_after=after, load_after=load_after, k6_exit_code=result.returncode,
                    result=outcome, reason=reason, finished_utc=datetime.now(timezone.utc).isoformat())
    for path in local.iterdir():
        shutil.copyfile(path, destination / path.name)
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    metrics = summary.get('metrics', {})
    def values(name): return metrics.get(name, {}).get('values', {})
    latency = values('http_req_duration{phase:hold}')
    errors = values('request_errors{phase:hold}')
    count = values('http_reqs{phase:hold}').get('count', 0)
    compact = {'outcome': outcome, 'reason': reason, 'vus': vus, 'tier': tier, 'mode': manifest['mode'],
               'runner_profile': RUNNER_PROFILE, 'deployment_track': TRACK, 'platform': PLATFORM,
               'hold_requests': count, 'hold_rps': count / (20 if smoke else 300), 'latency_ms': latency,
               'request_errors': errors, 'schema_errors': values('schema_errors{phase:hold}')}
    (destination / 'summary.json').write_text(json.dumps(compact, indent=2) + '\n')
    (destination / 'report.md').write_text(f'''# TrailBase {tier} — {vus} VUs ({manifest['mode']})

Outcome: **{outcome}** — {reason}.

This is one `{TRACK}` / `{PLATFORM}` shared-host attempt, **not a maximum-capacity score**. {'Smoke only: shortened timing, not scored.' if smoke else 'Capacity attempt: see campaign.json for search/confirmation status.'}

- Serving tier: `{tier}` ({cpus} CPU / {memory // 1024**3} GiB RAM / no swap).
- Runner profile: `{RUNNER_PROFILE}` (2 CPU / {RUNNER_LIMITS['Memory'] // 1024**3} GiB RAM / no swap).
- Hold requests: {count}; throughput: {compact['hold_rps']:.2f} requests/s.
- Hold p50/p95/p99: {latency.get('med', 'N/A')} / {latency.get('p(95)', 'N/A')} / {latency.get('p(99)', 'N/A')} ms.
- Contract/transport/status error rate: {errors.get('rate', 'N/A')}.
- Full endpoint summaries: `k6-summary.json`; all raw metric points: `samples.json.gz`.
- CPU/RAM/I/O/network, host VM/swap/thermal evidence: `resources.jsonl`.
- Hardware, actual cgroup limits, image IDs, auth, source revision and caveats: `manifest.json`.
- Canonical data: `dataset.json`; prior full correctness gate: `correctness.log`.
- Uncommitted source is retained in `source.tar.gz` and `working-tree.patch`; verify `SHA256SUMS`.
- Cost basis: {manifest['cost']}.

Reproduction environment: `export BENCHMARK_PROJECT={PROJECT} BENCHMARK_RUNNER_PROFILE={RUNNER_PROFILE} TIER={tier} TRAILBASE_PORT={int(os.environ.get('TRAILBASE_PORT', '4000'))}`. From the source snapshot, build with the documented bounded builder, run `bash services/trailbase/run.sh test`, then `{'caffeinate -i ' if platform.system() == 'Darwin' else ''}bash services/trailbase/run.sh bench --vus {vus}{' --smoke' if smoke else ''}`. See `services/trailbase/README.md`, `services/trailbase/VPS16.md`, and `contracts/BENCHMARK.md` for setup, the frozen protocol, and limitations.

Publication is local repository artifacts only. No push, release, upload, or service progression was performed. Human review/acceptance remains required.
''')
    checksum_files(destination)
    print(f'BENCHMARK_ATTEMPT_FINISHED {outcome} {vus}vu {destination.relative_to(ROOT)}: {reason}', flush=True)
    return outcome, str(destination.relative_to(ROOT))


def campaign(args, tier, attempt_runner=None, results=None, campaign_file=None):
    attempt_runner = attempt if attempt_runner is None else attempt_runner
    results = RESULTS if results is None else results
    campaign_file = ROOT / '.state/trailbase/campaign.json' if campaign_file is None else campaign_file
    results.mkdir(parents=True, exist_ok=True)
    history = []
    def run(vus):
        if len(history) >= args.max_attempts:
            raise RuntimeError('Campaign attempt budget reached; no final score')
        outcome, path = attempt_runner(vus, tier)
        history.append({'vus': vus, 'outcome': outcome, 'path': path})
        save('in_progress')
        if outcome == 'invalid':
            raise RuntimeError('Invalid measurements: campaign paused, not treated as target capacity failure')
        return outcome == 'pass'
    def save(status, **extra):
        campaign_file.write_text(json.dumps({'tier': tier, 'runner_profile': RUNNER_PROFILE, 'deployment_track': TRACK,
                                             'status': status, 'attempts': history, **extra}, indent=2) + '\n')
    low, high = 0, min(2500, args.max_vus)
    try:
        while run(high):
            low = high
            if high == args.max_vus:
                save('upper_budget_passed_no_maximum', lower_bound_vus=low)
                return
            high = min(high * 2, args.max_vus)
        while high - low > (250 if high > 250 else 25):
            step = 250 if high > 250 else 25
            mid = ((low + high) // (2 * step)) * step
            mid = max(low + step, min(high - step, mid))
            if run(mid): low = mid
            else: high = mid
        while low > 0:
            holds = [run(low) for _ in range(3)]
            if all(holds):
                save('confirmed_pending_human_review', candidate_vus=low)
                return
            low -= 250 if low > 250 else 25
        save('no_passing_capacity')
    except BaseException as error:
        save('paused', reason=str(error))
        raise
    finally:
        if campaign_file.exists():
            destination = results / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + f'-{tier}-campaign.json')
            shutil.copyfile(campaign_file, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-platform', action='store_true')
    parser.add_argument('--runner-memory', action='store_true')
    parser.add_argument('--source-hash', action='store_true')
    parser.add_argument('--attest-correctness', action='store_true')
    parser.add_argument('--verification-hash', action='store_true')
    parser.add_argument('--expected-verification-hash')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--vus', type=int, default=25)
    parser.add_argument('--campaign', action='store_true')
    parser.add_argument('--max-vus', type=int, default=20000)
    parser.add_argument('--max-attempts', type=int, default=12)
    args = parser.parse_args()
    if args.native_platform:
        print(PLATFORM); return
    if args.runner_memory:
        print(RUNNER_MEMORY); return
    if args.source_hash:
        print(app_source_hash()); return
    if args.verification_hash:
        print(verification_source_hash()); return
    if args.attest_correctness:
        if not args.expected_verification_hash or args.expected_verification_hash != verification_source_hash():
            raise RuntimeError('Verification inputs changed during the test run; rerun without editing')
        serving = inspect(TARGET)
        if serving['source_sha256'] != app_source_hash():
            raise RuntimeError('Tests ran against a stale image; rebuild and rerun')
        log = ROOT / '.state/trailbase/correctness.log'
        attestation = {'app_source_sha256': app_source_hash(), 'verification_source_sha256': verification_source_hash(), 'image': serving['Image'], 'limits': serving['limits'],
                       'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
                       'completed_utc': datetime.now(timezone.utc).isoformat()}
        (log.parent / 'correctness-manifest.json').write_text(json.dumps(attestation, indent=2) + '\n')
        return
    if not 1 <= args.vus <= 20000 or not 25 <= args.max_vus <= 20000 or args.max_attempts < 1:
        parser.error('VU budget must be within 1..20,000 and attempt budget positive')
    if args.campaign and args.smoke:
        parser.error('Smoke runs cannot be capacity campaigns')
    tier = os.environ.get('TIER', 'small')
    if tier not in TIERS:
        parser.error('Unknown tier')
    lock_path = ROOT / '.state/trailbase/campaign.lock'
    with lock_path.open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.campaign: campaign(args, tier)
        else:
            outcome, _ = attempt(args.vus, tier, args.smoke)
            if outcome != 'pass': raise SystemExit(1)


if __name__ == '__main__':
    main()
