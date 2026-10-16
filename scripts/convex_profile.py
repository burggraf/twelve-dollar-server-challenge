#!/usr/bin/env python3
"""Fail-closed aggregate attestation for the native PostgreSQL-backed candidate."""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'baas-convexpg-vps16'
SLICE = 'tdsbaasconvexpgvps16.slice'
MEMORY = {'backend': 3221225472, 'postgres': 1073741824}
STATE = ROOT / '.state/convex'
SERVICES = ('backend', 'postgres')
PINS = json.loads((ROOT / 'services/convex/versions.json').read_text())
POSTGRES = json.loads((ROOT / 'services/convex/postgres-versions.json').read_text())


def validate_stack(value):
    """Require both native servers and their actual shared parent/child limits."""
    def require(condition, message):
        if not condition:
            raise RuntimeError(message)

    try:
        backend = json.loads((ROOT / 'services/convex/versions.json').read_text())
        postgres = json.loads((ROOT / 'services/convex/postgres-versions.json').read_text())
        expected = {'backend': backend['backend']['amd64_manifest'], 'postgres': postgres['amd64_manifest']}
        targets = value['targets']
        require(set(targets) == set(expected), 'Both native serving processes must be accounted for')
        parent = value['parent']
        require(parent['cpu.max'].split() == ['100000', '100000'], 'Entire serving CPU quota must be one core')
        require(parent['memory.max'].strip() == '4294967296', 'Entire serving memory must be exactly 4 GiB')
        require(parent['memory.swap.max'].strip() == '0', 'Serving swap must be zero')
        children = []
        for role, manifest in expected.items():
            target = targets[role]
            identity = target['Id']
            require(bool(re.fullmatch(r'[0-9a-f]{64}', identity)), 'Missing full native container identity')
            require(target['platform'] == 'linux/amd64', 'Serving images must be native Linux AMD64')
            require(target['image_manifest_digest'] == manifest, 'Pinned serving image differs: ' + role)
            require(target['compose_project'] == PROJECT, 'Serving project ownership differs: ' + role)
            require(target['cgroup_parent'] == SLICE, 'Serving parent differs: ' + role)
            scope = 'docker-' + identity + '.scope'
            require(target['process_cgroup'].strip() == f'0::/{SLICE}/{scope}', 'Actual process is outside serving parent: ' + role)
            children.append(scope)
            state = target['State']
            require(state['Running'] is True and state['OOMKilled'] is False, 'Native serving process is not healthy/running: ' + role)
            require(state['Health']['Status'] == 'healthy', 'Native serving health failed: ' + role)
            limits = target['limits']
            require(limits['NanoCpus'] == 1000000000, 'Child CPU quota differs: ' + role)
            require(limits['Memory'] == MEMORY[role] and limits['MemorySwap'] == MEMORY[role], 'Child memory/swap allocation differs: ' + role)
            kernel = target['kernel']
            require(kernel['cpu.max'].split() == ['100000', '100000'], 'Actual child CPU quota differs: ' + role)
            require(kernel['memory.max'].strip() == str(MEMORY[role]), 'Actual child memory differs: ' + role)
            require(kernel['memory.swap.max'].strip() == '0', 'Actual child swap differs: ' + role)
        require(sorted(parent['children']) == sorted(children), 'Unaccounted serving cgroup children')
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise RuntimeError('Malformed or incomplete native serving attestation') from error
    return True


def capture(argv):
    return subprocess.check_output(argv, text=True)


def require_native():
    if os.uname().sysname != 'Linux' or os.uname().machine != 'x86_64' or socket.getfqdn() != 'claudius.azabab.com':
        raise RuntimeError('Use the designated native AMD64 VPS only')
    if json.loads((ROOT.parent / '.benchmark-owned').read_text())['project'] != PROJECT:
        raise RuntimeError('Owned Convex workspace required')


def tree_inventory(directory):
    directory = directory.resolve()
    rows = []
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            if not path.resolve().is_relative_to(directory):
                raise RuntimeError('Frozen dependency symlink escapes its root')
            rows.append({'path': str(path.relative_to(directory)), 'link': os.readlink(path)})
        elif path.is_file():
            with path.open('rb') as stream: digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            rows.append({'path': str(path.relative_to(directory)), 'bytes': path.stat().st_size, 'sha256': digest, 'mode': path.stat().st_mode & 0o777})
    return rows


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def files_hash(files):
    result = hashlib.sha256()
    for path in sorted(set(files)):
        result.update(str(path.relative_to(ROOT)).encode() + b'\0' + path.read_bytes() + b'\0')
    return result.hexdigest()


def full_runtime_state():
    app = ROOT / 'services/convex/app'
    required = ['node_modules/convex/package.json', 'convex/_generated/server.js', 'convex/_generated/api.js']
    if not all((app / name).is_file() for name in required):
        raise RuntimeError('Complete installed SDK/generated runtime is required')
    if json.loads((app / required[0]).read_text())['version'] != '1.46.0':
        raise RuntimeError('Installed SDK differs from pinned 1.46.0')
    # Each complete tree, including native esbuild/compiler binary and symlinks.
    value = {name: tree_inventory(app / name) for name in ['node_modules', 'convex/_generated']}
    value['tools_image'] = capture(['docker', 'image', 'inspect', 'baas-trailbase-vps16-tools:0.1.0', '--format', '{{.Id}} {{.Os}}/{{.Architecture}}']).strip()
    return {'sha256': digest(value), 'inventory': value}


def app_hash():
    directory = ROOT / 'services/convex'
    return files_hash(p for p in directory.rglob('*') if p.is_file() and 'node_modules' not in p.parts and not p.name.startswith('.env') and p.suffix in ['.js', '.ts', '.json', '.yaml'])


def verification_hash():
    files = [ROOT / 'SPEC.md', ROOT / 'schema.sql', ROOT / 'runner/Dockerfile']
    for name in ['scripts', 'bench', 'test', 'seed', 'contracts']:
        files.extend(p for p in (ROOT / name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return files_hash(files)


def runtime_values():
    value = dict(line.split('=', 1) for line in (STATE / 'compat-jwt.env').read_text().splitlines())
    if set(value) != {'JWT_SECRET'} or not re.fullmatch(r'[0-9a-f]{64}', value['JWT_SECRET']):
        raise RuntimeError('Unchanged private compatibility key required')
    return value


def runtime_hash():
    # Private values/configuration are hashed in memory, never serialized to artifacts.
    files = [STATE / name for name in ['cli.env', 'backend.env', 'postgres.env', 'compat-jwt.env']]
    local = ROOT / 'services/convex/app/.env.local'
    if local.exists(): files.append(local)
    config = {}
    for role in SERVICES:
        item = json.loads(capture(['docker', 'inspect', PROJECT + '-' + role + '-1']))[0]
        config[role] = {key: item['Config'].get(key) for key in ['Env', 'Entrypoint', 'Cmd', 'User', 'WorkingDir']}
        config[role]['host'] = {key: item['HostConfig'].get(key) for key in ['ReadonlyRootfs', 'CapDrop', 'SecurityOpt', 'CgroupParent', 'NanoCpus', 'Memory', 'MemorySwap']}
        config[role]['mounts'] = item['Mounts']
    return digest({'files': files_hash(files), 'native_config': config})


def parent_sample():
    group = Path('/sys/fs/cgroup') / SLICE
    names = ['cpu.max', 'cpu.stat', 'cpu.pressure', 'memory.max', 'memory.current', 'memory.peak', 'memory.swap.max', 'memory.events', 'memory.stat', 'memory.pressure', 'io.stat', 'io.pressure']
    return {name: (group / name).read_text() for name in names} | {'children': sorted(p.name for p in group.iterdir() if p.is_dir())}


def targets():
    # Import lazily: existing budget tests do not require a deployment environment.
    import benchmark as b
    result = {}
    for role in SERVICES:
        name = PROJECT + '-' + role + '-1'
        item = json.loads(capture(['docker', 'inspect', name]))[0]
        env = dict(entry.split('=', 1) for entry in item['Config']['Env'])
        if role == 'backend':
            if env.get('UDF_CACHE_MAX_SIZE') != '0' or env.get('RUNTIME_WORKER_THREADS') != '1':
                raise RuntimeError('Serving cache/thread configuration differs')
            for key in ['TRANSACTION_MAX_READ_SIZE_ROWS', 'TRANSACTION_MAX_READ_SIZE_BYTES', 'TRANSACTION_MAX_READ_SET_INTERVALS', 'TRANSACTION_MAX_NUM_USER_WRITES', 'TRANSACTION_MAX_USER_WRITE_SIZE_BYTES', 'DATABASE_UDF_USER_TIMEOUT_SECONDS', 'DATABASE_UDF_SYSTEM_TIMEOUT_SECONDS']:
                if key in env: raise RuntimeError('Native serving defaults overridden')
        pid = item['State']['Pid']; process = Path('/proc', str(pid), 'cgroup')
        cgroup = process.read_text() if pid and process.exists() else ''
        group = Path('/sys/fs/cgroup' + cgroup.strip().split('::')[1]) if cgroup else None
        result[role] = b.inspect(name) | {'compose_project': item['Config']['Labels'].get('com.docker.compose.project'), 'cgroup_parent': item['HostConfig']['CgroupParent'], 'process_cgroup': cgroup, 'kernel': {key: (group / key).read_text() for key in ['cpu.max', 'cpu.stat', 'memory.max', 'memory.current', 'memory.peak', 'memory.swap.max', 'memory.events', 'memory.stat', 'io.stat']} if group else {}}
    return result


def profile():
    require_native()
    value = {'targets': targets(), 'parent': parent_sample()}
    validate_stack(value)
    with urllib.request.urlopen('http://127.0.0.1:14000/health', timeout=15) as response:
        health = json.load(response)
    if health.get('status') != 'ok' or health.get('db') != 'ok':
        raise RuntimeError('Native storage health is not ready')
    value['observed_health'] = health
    return value


def admin_query(path):
    if path not in ['_system/frontend/getSchemas', '_system/cli/modules:apiSpec']:
        raise ValueError('Unsupported native deployment catalog')
    from convex import _NoRedirect
    values = dict(line.split('=', 1) for line in (STATE / 'cli.env').read_text().splitlines())
    request = urllib.request.Request('http://127.0.0.1:13210/api/query', data=json.dumps({'path': path, 'args': {}, 'format': 'json'}).encode(), headers={'Content-Type': 'application/json', 'Authorization': 'Convex ' + values['CONVEX_SELF_HOSTED_ADMIN_KEY']})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect()).open(request, timeout=30) as response: value = json.load(response)
        if value.get('status') != 'success': raise ValueError()
        return value['value']
    except (urllib.error.URLError, ValueError, KeyError):
        raise RuntimeError('Native deployment catalog unavailable; preserve state') from None


def schema_state():
    schema = admin_query('_system/frontend/getSchemas')
    if not schema.get('active') or schema.get('inProgress'):
        raise RuntimeError('Stable active native schema required')
    active = json.loads(schema['active'])
    if {table['tableName'] for table in active['tables']} != {'users', 'posts', 'likes', 'feed_sequences'}:
        raise RuntimeError('Native application schema set differs')
    value = {'active_schema': active, 'function_spec': admin_query('_system/cli/modules:apiSpec')}
    return {'sha256': digest(value), 'catalog': value, 'scope': 'Actual supported native CLI/MCP catalog queries; not physical SQL FK/UNIQUE declarations'}


def deployment_attestation():
    serving = profile()
    return {'app_source_sha256': app_hash(), 'verification_source_sha256': verification_hash(), 'runtime_inputs_sha256': runtime_hash(), 'full_runtime': full_runtime_state()['sha256'], 'schema': schema_state(), 'serving_profile': serving, 'images': {role: {key: target[key] for key in ['Image', 'platform', 'image_manifest_digest']} for role, target in serving['targets'].items()}, 'host_identity_sha256': hashlib.sha256(Path('/etc/machine-id').read_bytes()).hexdigest()}
