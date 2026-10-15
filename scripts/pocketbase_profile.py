"""Native PocketBase whole-serving-stack resource and provenance checks."""
import hashlib
import json
import sqlite3
from pathlib import Path
from urllib.request import urlopen
import benchmark as b

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.state/pocketbase'
PROJECT = 'baas-pocketbase-vps16'
SLICE = 'tdsbaaspocketbasevps16.slice'
GROUP = Path('/sys/fs/cgroup') / SLICE
SERVICES = ('pocketbase',)
PINS = json.loads((ROOT / 'services/pocketbase/versions.json').read_text())


def validate_stack(value, expected_image):
    try:
        targets, parent = value['targets'], value['parent']
        if set(targets) != set(SERVICES):
            raise ValueError('required serving component set differs')
        if parent['cpu.max'].split() != ['100000', '100000'] or int(parent['memory.max']) != 4294967296 or int(parent['memory.swap.max']) != 0:
            raise ValueError('aggregate kernel budget differs')
        target = targets['pocketbase']
        scope = 'docker-' + target['Id'] + '.scope'
        if sorted(parent['children']) != [scope]:
            raise ValueError('unaccounted aggregate cgroup children')
        if target['platform'] != 'linux/amd64' or target['Image'] != expected_image:
            raise ValueError('serving image/architecture differs')
        if target['limits'] != {'NanoCpus': 10**9, 'Memory': 4294967296, 'MemorySwap': 4294967296}:
            raise ValueError('serving child budget differs')
        if target['compose_project'] != PROJECT or target['cgroup_parent'] != SLICE:
            raise ValueError('serving ownership/parent differs')
        if target['process_cgroup'].strip() != f'0::/{SLICE}/{scope}':
            raise ValueError('actual serving process is outside the aggregate budget')
        state = target['State']
        if state['Running'] is not True or state['OOMKilled'] or state.get('Paused') or state.get('Restarting'):
            raise ValueError('native serving process is not running normally')
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError('Invalid PocketBase serving profile: ' + str(error)) from error
    return True


def files_hash(files):
    digest = hashlib.sha256()
    for path in sorted(set(files)):
        digest.update(str(path.relative_to(ROOT)).encode() + b'\0' + path.read_bytes() + b'\0')
    return digest.hexdigest()


def app_hash():
    directory = ROOT / 'services/pocketbase'
    files = [p for p in directory.rglob('*') if p.is_file()
             and p.suffix in ['.go', '.mod', '.sum', '.json', '.yaml', '.sh']
             and not p.name.endswith('_test.go')]
    return files_hash([*files, directory / 'Dockerfile'])


def verification_hash():
    return hashlib.sha256((b.verification_source_hash() + files_hash([
        *(ROOT / 'services/pocketbase/app').glob('*_test.go'), ROOT / 'runner/Dockerfile'])).encode()).hexdigest()


def runtime_values():
    return dict(line.split('=', 1) for line in (STATE / 'runtime.env').read_text().splitlines())


def runtime_hash():
    values = runtime_values()
    if set(values) != {'JWT_SECRET'} or len(values['JWT_SECRET']) != 64:
        raise RuntimeError('Private PocketBase runtime key configuration differs')
    return hashlib.sha256((STATE / 'runtime.env').read_bytes()
                          + (STATE / 'native-schema-fixture.db').read_bytes()).hexdigest()


def parent_sample():
    files = ['cpu.max', 'cpu.stat', 'cpu.pressure', 'memory.max', 'memory.current',
             'memory.swap.max', 'memory.events', 'memory.stat', 'memory.pressure',
             'io.stat', 'io.pressure']
    return {name: (GROUP / name).read_text() for name in files} | {
        'children': sorted(p.name for p in GROUP.iterdir() if p.is_dir())}


def build_manifest():
    value = json.loads((STATE / 'build-manifest.json').read_text())
    if value['app_source_sha256'] != app_hash() or value['native_platform'] != 'linux/amd64':
        raise RuntimeError('Native PocketBase build provenance is stale for current source/configuration')
    return value


def targets():
    # Inspect privately, export only whitelist fields. Never serialize Config.Env.
    name = PROJECT + '-pocketbase-1'
    item = json.loads(b.capture(['docker', 'inspect', name]))[0]
    env = dict(pair.split('=', 1) for pair in item['Config']['Env'] if '=' in pair)
    expected = runtime_values() | {'GOMAXPROCS': '1', 'GOMEMLIMIT': '3GiB'}
    if any(env.get(key) != value for key, value in expected.items()):
        raise RuntimeError('Native PocketBase serving environment differs')
    if item['Config']['User'] != '1000:1000' or not item['HostConfig']['ReadonlyRootfs']:
        raise RuntimeError('Native PocketBase runtime user/filesystem policy differs')
    mounts = [m for m in item['Mounts'] if m['Destination'] == '/data']
    if len(mounts) != 1 or mounts[0].get('Name') != PROJECT + '_data' or not mounts[0]['RW']:
        raise RuntimeError('Native PocketBase data volume differs')
    if item['Config']['Labels'].get('benchmark.app-source-sha256') != app_hash():
        raise RuntimeError('Deployed executable source label differs')
    pid = item['State']['Pid']
    return {'pocketbase': b.inspect(name) | {
        'compose_project': item['Config']['Labels'].get('com.docker.compose.project'),
        'cgroup_parent': item['HostConfig']['CgroupParent'],
        'process_cgroup': Path(f'/proc/{pid}/cgroup').read_text() if pid else None}}


def profile():
    value = {'parent': parent_sample(), 'targets': targets()}
    validate_stack(value, build_manifest()['image_id'])
    with urlopen('http://127.0.0.1:14000/health', timeout=5) as response:
        health = json.load(response)
        if response.status != 200 or health.get('status') != 'ok' or health.get('db') != 'ok':
            raise RuntimeError('Native PocketBase storage is not ready')
    value['observed_health'] = health
    return value


def database_path():
    value = json.loads(b.capture(['docker', 'volume', 'inspect', PROJECT + '_data']))[0]
    if value.get('Labels', {}).get('com.docker.compose.project') != PROJECT:
        raise RuntimeError('Native data volume ownership differs')
    return Path(value['Mountpoint']) / 'data.db'


def schema_state():
    # Untimed read-only catalog inspection, not a serving SQL connection.
    # Per-connection native pragmas are tested through the pinned real Go App;
    # never infer the server's synchronous setting from this Python connection.
    with sqlite3.connect(database_path().as_uri() + '?mode=ro', uri=True) as conn:
        conn.row_factory = sqlite3.Row
        names = ['feed_users', 'feed_posts', 'feed_likes', 'feed_sequences']
        placeholders = ','.join('?' for _ in names)
        ddl = [dict(row) for row in conn.execute(
            f'SELECT type,name,tbl_name,sql FROM sqlite_master WHERE tbl_name IN ({placeholders}) ORDER BY type,name', names)]
        collections = [dict(row) for row in conn.execute(
            f'SELECT id,name,type,fields,indexes,listRule,viewRule,createRule,updateRule,deleteRule FROM _collections WHERE name IN ({placeholders}) ORDER BY name', names)]
        if {row['name'] for row in collections} != set(names):
            raise RuntimeError('Native application collection set differs')
        if any(row[key] is not None for row in collections for key in ['createRule', 'updateRule', 'deleteRule']):
            raise RuntimeError('Native direct application writes are not locked')
        sequence = next(row for row in collections if row['name'] == 'feed_sequences')
        if sequence['listRule'] is not None or sequence['viewRule'] is not None:
            raise RuntimeError('Native post allocation metadata is publicly readable')
    catalog = {'ddl': ddl, 'collections': collections,
               'native_connection_defaults': {'source': 'PocketBase v0.40.5 core/db_connect.go; real Go App pragma tests',
                                              'sqlite_engine_version': PINS['sqlite_engine_version'],
                                              'sqlite_source_id': PINS['sqlite_engine_source_id'],
                                              'journal_mode': 'wal', 'synchronous': 'NORMAL',
                                              'foreign_keys': 'ON', 'busy_timeout_ms': 10000,
                                              'temp_store': 'MEMORY', 'cache_size_kib': -32000}}
    raw = json.dumps(catalog, sort_keys=True, separators=(',', ':')).encode()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'catalog': catalog}


def deployment_attestation():
    serving = profile()
    return {'app_source_sha256': app_hash(), 'verification_source_sha256': verification_hash(),
            'runtime_inputs_sha256': runtime_hash(), 'schema': schema_state(),
            'serving_profile': serving, 'images': {role: {key: value[key] for key in
            ['Image', 'platform', 'image_manifest_digest']} for role, value in serving['targets'].items()},
            'host_identity_sha256': hashlib.sha256(Path('/etc/machine-id').read_bytes()).hexdigest(),
            'native_build': build_manifest()}
