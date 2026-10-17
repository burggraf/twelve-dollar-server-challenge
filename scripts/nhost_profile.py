"""Native Nhost aggregate/profile validation (deployment helpers follow qualification)."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROJECT='baas-nhost-vps16';SLICE='tdsbaasnhostvps16.slice';GROUP=Path('/sys/fs/cgroup')/SLICE
STATE=ROOT/'.state/nhost';SERVICES=('db','graphql','auth','adapter')
PINS=json.loads((ROOT/'services/nhost/versions.json').read_text())
MEMORY={'db':1073741824,'graphql':2147483648,'auth':536870912,'adapter':536870912}
def validate_stack(value):
 try:
  targets,parent=value['targets'],value['parent']
  if set(targets)!=set(SERVICES):raise ValueError('required serving set differs')
  quota,period=map(int,parent['cpu.max'].split())
  if quota!=period or period<=0 or int(parent['memory.max'])!=4294967296 or int(parent['memory.swap.max'])!=0:raise ValueError('aggregate kernel budget differs')
  if set(parent['children'])!={f'docker-{item["Id"]}.scope' for item in targets.values()}:raise ValueError('unaccounted parent children')
  for role,item in targets.items():
   if item['platform']!='linux/amd64' or item['image_manifest_digest']!=PINS['images'][role]['amd64_manifest']:raise ValueError('native image differs')
   if item['compose_project']!=PROJECT or item['cgroup_parent']!=SLICE or item['process_cgroup'].strip()!=f'0::/{SLICE}/docker-{item["Id"]}.scope':raise ValueError('ownership/process parent differs')
   if item['limits']['Memory']!=MEMORY[role] or item['limits']['MemorySwap']!=MEMORY[role]:raise ValueError('child memory/swap differs')
   state=item['State']
   if not state['Running'] or state['Pid']<=0 or state['OOMKilled'] or state.get('Health',{}).get('Status')!='healthy' or item['RestartCount']:raise ValueError('serving component unhealthy/OOM/restarted')
 except (KeyError,TypeError,ValueError) as error:raise RuntimeError('Invalid Nhost serving profile: '+str(error)) from error
 return True

def capture(argv,timeout=210):return subprocess.check_output(argv,stderr=subprocess.STDOUT,timeout=timeout).decode()
def runtime_values():return dict(line.split('=',1) for line in (STATE/'stack.env').read_text().splitlines())
def ownership():return json.loads((STATE/'ownership-PRIVATE.json').read_text())
def identities():return ownership()['identities']
def raw(role):
 owned=ownership();cid=owned['identities'][role];item=json.loads(capture(['docker','inspect',cid],10))[0];old=owned['containers'][role]
 if item['Id']!=cid or item['Config']!=old['Config'] or item['HostConfig']!=old['HostConfig'] or item['Image']!=old['Image']:raise RuntimeError('Retained Nhost configuration/identity drift; no adoption')
 return item

def parent_sample():
 names=['cpu.max','cpu.stat','cpu.pressure','memory.max','memory.current','memory.swap.max','memory.events','memory.stat','memory.pressure','io.stat','io.pressure']
 return {name:(GROUP/name).read_text() for name in names}|{'children':sorted(path.name for path in GROUP.iterdir() if path.is_dir())}

def targets():
 result={}
 for role in SERVICES:
  item=raw(role);image=json.loads(capture(['docker','image','inspect',item['Config']['Image']],10))[0];pid=item['State']['Pid']
  if item['Image']!=PINS['images'][role]['amd64_manifest'] or image['Descriptor']['digest']!=item['Image']:raise RuntimeError('Native manifest identity differs')
  result[role]={key:item[key] for key in ['Id','Image','RestartCount','State']}|{'platform':image['Os']+'/'+image['Architecture'],'image_manifest_digest':item['Image'],'compose_project':item['Config']['Labels']['com.docker.compose.project'],'cgroup_parent':item['HostConfig']['CgroupParent'],'process_cgroup':Path(f'/proc/{pid}/cgroup').read_text() if pid else None,'limits':{key:item['HostConfig'][key] for key in ['NanoCpus','Memory','MemorySwap']}}
 return result

def profile():
 value={'parent':parent_sample(),'targets':targets()};validate_stack(value);return value

def files_hash(files):
 digest=hashlib.sha256()
 for path in sorted(set(files)):digest.update(str(path.relative_to(ROOT)).encode()+b'\0'+path.read_bytes()+b'\0')
 return digest.hexdigest()
def app_hash():return files_hash([path for path in (ROOT/'services/nhost').rglob('*') if path.is_file() and not path.name.endswith('.test.mjs')]+[ROOT/'services/supabase/functions/feed/contract.mjs'])
def verification_hash():
 import benchmark as b
 node=files_hash([ROOT/name for name in ['services/nhost/app/native-contract.test.mjs','services/nhost/app/http.test.mjs','services/supabase/functions/feed/contract.test.mjs']])
 return hashlib.sha256((b.verification_source_hash()+'\0'+node).encode()).hexdigest()
def runtime_hash():
 values=runtime_values()
 if len({values[key] for key in ['POSTGRES_PASSWORD','GRAPHQL_ADMIN_SECRET','NATIVE_JWT_SECRET','COMPAT_JWT_SECRET']})!=4 or json.loads(values['NATIVE_JWT_CONFIG'])['key']!=values['NATIVE_JWT_SECRET']:raise RuntimeError('Runtime secret separation/native JWT config differs')
 return hashlib.sha256((STATE/'stack.env').read_bytes()).hexdigest()

def query(sql):
 from import_nhost import psql_args
 return capture(psql_args(identities()['db'],sql)).strip()
def schema_state():
 sql="""SELECT jsonb_build_object(
 'functions',(SELECT jsonb_agg(jsonb_build_object('definition',pg_get_functiondef(p.oid),'owner',pg_get_userbyid(p.proowner),'acl',p.proacl) ORDER BY n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('feed_data','feed_api') OR (n.nspname='public' AND p.proname LIKE 'nhost_%')),
 'relations',(SELECT jsonb_agg(jsonb_build_object('schema',n.nspname,'name',c.relname,'kind',c.relkind,'persistence',c.relpersistence,'owner',pg_get_userbyid(c.relowner),'acl',c.relacl,'rls',c.relrowsecurity) ORDER BY n.nspname,c.relname) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('feed_data','feed_api')),
 'columns',(SELECT jsonb_agg(row_to_json(v) ORDER BY v.table_name,v.ordinal_position) FROM (SELECT table_name,column_name,data_type,column_default,is_nullable,ordinal_position,collation_name FROM information_schema.columns WHERE table_schema='feed_data')v),
 'constraints',(SELECT jsonb_agg(pg_get_constraintdef(x.oid) ORDER BY c.relname,x.conname) FROM pg_constraint x JOIN pg_class c ON c.oid=x.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='feed_data'),
 'indexes',(SELECT jsonb_agg(indexdef ORDER BY indexname) FROM pg_indexes WHERE schemaname='feed_data'),
 'durability',(SELECT jsonb_object_agg(name,setting) FROM pg_settings WHERE name IN ('fsync','synchronous_commit','full_page_writes','wal_level','shared_buffers','max_connections')))"""
 text=query(sql);value=json.loads(text)
 if any(value['durability'][key]!='on' for key in ['fsync','synchronous_commit','full_page_writes']):raise RuntimeError('Required native PostgreSQL committed-write durability differs')
 return {'sha256':hashlib.sha256(text.encode()).hexdigest(),'catalog':value}

def metadata_state():
 import urllib.request
 item=raw('graphql');ip=item['NetworkSettings']['Networks'][PROJECT+'_default']['IPAddress']
 request=urllib.request.Request('http://'+ip+':8080/v1/metadata',data=b'{"type":"export_metadata","args":{}}',headers={'Content-Type':'application/json','x-hasura-admin-secret':runtime_values()['GRAPHQL_ADMIN_SECRET']})
 with urllib.request.urlopen(request,timeout=10) as response:value=json.load(response)
 text=json.dumps(value,sort_keys=True,separators=(',',':'))
 return {'sha256':hashlib.sha256(text.encode()).hexdigest(),'private_metadata':value}

def deployment_attestation():
 metadata=metadata_state()
 return {'app_source_sha256':app_hash(),'verification_source_sha256':verification_hash(),'runtime_inputs_sha256':runtime_hash(),'schema':schema_state(),'metadata_sha256':metadata['sha256'],'serving_profile':profile(),'images':{role:{'manifest':pin['amd64_manifest'],'platform':pin['platform']} for role,pin in PINS['images'].items()},'host_identity_sha256':hashlib.sha256(Path('/etc/machine-id').read_bytes()).hexdigest()}
