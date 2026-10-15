"""Supabase native image, shared-cgroup and deployed-source attestations."""
import hashlib,json,subprocess
from pathlib import Path
import benchmark as b
from import_postgres import query
ROOT=Path(__file__).resolve().parents[1]
PROJECT='baas-supabase-vps16'
SLICE='tdsbaassupabasevps16.slice'
GROUP=Path('/sys/fs/cgroup')/SLICE
SERVICES=('db','auth','rest','functions','gateway')
STATE=ROOT/'.state/supabase'
PINS=json.loads((ROOT/'services/supabase/versions.json').read_text())

def validate_stack(profile):
 try:
  targets,parent=profile['targets'],profile['parent']
  if set(targets)!=set(SERVICES):raise ValueError('required serving component set differs')
  quota,period=map(int,parent['cpu.max'].split())
  if quota!=period or period<=0 or int(parent['memory.max'])!=4*1024**3 or int(parent['memory.swap.max'])!=0:raise ValueError('aggregate kernel budget differs')
  expected={f'docker-{value["Id"]}.scope' for value in targets.values()}
  if set(parent['children'])!=expected:raise ValueError('unaccounted parent cgroup children')
  for role,value in targets.items():
   if value['platform']!='linux/amd64' or value['image_manifest_digest']!=PINS['images'][role]['amd64_manifest']:raise ValueError('serving image/architecture differs')
   if value['compose_project']!=PROJECT or value['cgroup_parent']!=SLICE:raise ValueError('serving ownership/parent differs')
   if value['process_cgroup'].strip()!=f'0::/{SLICE}/docker-{value["Id"]}.scope':raise ValueError('actual process is outside the aggregate budget')
   state=value['State']
   if not state['Running'] or state['OOMKilled'] or state.get('Health',{}).get('Status')!='healthy':raise ValueError('required serving component is not healthy')
 except (ValueError,TypeError,KeyError) as error:raise RuntimeError('Invalid Supabase serving profile: '+str(error)) from error
 return True

def parent_sample():
 files=['cpu.max','cpu.stat','cpu.pressure','memory.max','memory.current','memory.swap.max','memory.events','memory.stat','memory.pressure','io.stat','io.pressure']
 return {name:(GROUP/name).read_text() for name in files}|{'children':sorted(p.name for p in GROUP.iterdir() if p.is_dir())}

def runtime_values():return dict(line.split('=',1) for line in (STATE/'stack.env').read_text().splitlines())

def targets():
 # Never export Config.Env, complete inspect objects, command arguments or startup logs.
 result={};values=runtime_values()
 wanted={'db':{'POSTGRES_PASSWORD':values['POSTGRES_PASSWORD']},'auth':{'GOTRUE_JWT_SECRET':values['NATIVE_JWT_SECRET']},'rest':{'PGRST_JWT_SECRET':values['NATIVE_JWT_SECRET'],'PGRST_JWT_CACHE_MAX_LIFETIME':'0','PGRST_DB_TX_END':'commit'},'functions':{'COMPAT_JWT_SECRET':values['COMPAT_JWT_SECRET'],'NATIVE_JWT_SECRET':values['NATIVE_JWT_SECRET'],'SUPABASE_ANON_KEY':values['ANON_KEY'],'REST_URL':'http://gateway:8000/rest/v1'}}
 for role in SERVICES:
  name=PROJECT+'-'+role+'-1';item=json.loads(b.capture(['docker','inspect',name]))[0]
  env=dict(v.split('=',1) for v in item['Config']['Env'] if '=' in v)
  if any(env.get(key)!=value for key,value in wanted.get(role,{}).items()):raise RuntimeError('Serving runtime environment differs for '+role)
  needed={'functions':(str(ROOT/'services/supabase/functions'),'/home/deno/functions'),'gateway':(str(STATE/'envoy.yaml'),'/etc/envoy/envoy.yaml')}.get(role)
  if needed and not any(m.get('Type')=='bind' and m.get('Source')==needed[0] and m.get('Destination')==needed[1] and m.get('RW') is False for m in item['Mounts']):raise RuntimeError('Deployed read-only source binding differs for '+role)
  pid=item['State']['Pid']
  result[role]=b.inspect(name)|{'compose_project':item['Config']['Labels'].get('com.docker.compose.project'),'cgroup_parent':item['HostConfig']['CgroupParent'],'process_cgroup':Path(f'/proc/{pid}/cgroup').read_text() if pid else None}
 return result

def profile():
 value={'parent':parent_sample(),'targets':targets()};validate_stack(value);return value

def files_hash(files):
 digest=hashlib.sha256()
 for path in sorted(set(files)):
  digest.update(str(path.relative_to(ROOT)).encode()+b'\0'+path.read_bytes()+b'\0')
 return digest.hexdigest()

def app_hash():
 files=[p for p in (ROOT/'services/supabase').rglob('*') if p.is_file() and p.suffix in ['.yaml','.json','.sql','.ts','.mjs','.sh','.py'] and not p.name.endswith('.test.mjs')]
 return files_hash(files)

def verification_hash():
 return hashlib.sha256((b.verification_source_hash()+files_hash([*(ROOT/'services/supabase/functions').rglob('*.test.mjs'),ROOT/'runner/Dockerfile'])).encode()).hexdigest()

def runtime_hash():
 # High-entropy private inputs are fingerprinted, never copied to artifacts.
 values=runtime_values()
 if len({values[k] for k in ['POSTGRES_PASSWORD','NATIVE_JWT_SECRET','COMPAT_JWT_SECRET']})!=3:raise RuntimeError('Database, native and compatibility keys must be distinct')
 expected=(ROOT/'services/supabase/gateway.template.yaml').read_text().replace('@@ANON_KEY@@',values['ANON_KEY'])
 if (STATE/'envoy.yaml').read_text()!=expected:raise RuntimeError('Deployed gateway does not match source template/runtime inputs')
 return hashlib.sha256((STATE/'stack.env').read_bytes()+(STATE/'envoy.yaml').read_bytes()).hexdigest()

SCHEMA_QUERY="""SELECT jsonb_build_object(
 'functions',(SELECT jsonb_agg(jsonb_build_object('definition',pg_get_functiondef(p.oid),'owner',pg_get_userbyid(p.proowner),'acl',p.proacl) ORDER BY n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('feed_data','feed_api')),
 'relations',(SELECT jsonb_agg(jsonb_build_object('schema',n.nspname,'name',c.relname,'kind',c.relkind,'persistence',c.relpersistence,'owner',pg_get_userbyid(c.relowner),'acl',c.relacl,'rls',c.relrowsecurity) ORDER BY n.nspname,c.relname) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('feed_data','feed_api')),
 'columns',(SELECT jsonb_agg(row_to_json(v) ORDER BY v.table_name,v.ordinal_position) FROM (SELECT table_name,column_name,data_type,column_default,is_nullable,ordinal_position,collation_name FROM information_schema.columns WHERE table_schema='feed_data')v),
 'constraints',(SELECT jsonb_agg(pg_get_constraintdef(x.oid) ORDER BY c.relname,x.conname) FROM pg_constraint x JOIN pg_class c ON c.oid=x.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='feed_data'),
 'indexes',(SELECT jsonb_agg(indexdef ORDER BY indexname) FROM pg_indexes WHERE schemaname='feed_data'),
 'durability',(SELECT jsonb_object_agg(name,setting) FROM pg_settings WHERE name IN ('fsync','synchronous_commit','full_page_writes','wal_level','shared_buffers','max_connections')))
"""

def schema_state():
 raw=query(SCHEMA_QUERY);value=json.loads(raw)
 if value['durability']['fsync']!='on' or value['durability']['synchronous_commit']!='on' or value['durability']['full_page_writes']!='on':raise RuntimeError('Required committed-write durability settings differ')
 return {'sha256':hashlib.sha256(raw.encode()).hexdigest(),'catalog':value}

def deployment_attestation():
 value=profile()
 return {'app_source_sha256':app_hash(),'verification_source_sha256':verification_hash(),'runtime_inputs_sha256':runtime_hash(),'schema':schema_state(),'serving_profile':value,'images':{role:{k:v[k] for k in ['Image','platform','image_manifest_digest']} for role,v in value['targets'].items()},'host_identity_sha256':hashlib.sha256(Path('/etc/machine-id').read_bytes()).hexdigest()}
