"""Bounded, read-only source/checksum audit and privacy-screened metadata/source export."""
import hashlib,json,os,pathlib,sqlite3,subprocess,sys,tarfile
from closure_privacy import issues
P=pathlib.Path('/opt/twelve-dollar-baas-pocketbase-16g');R=P/'src';O=P/'supplemental-20261016';C=O/'repeatability-post-update-01';D=O/'publication-close-20261016';F=O/'complete-frozen-inputs2';E=D/'screened-export'
os.environ['DOCKER_CONFIG']='/opt/twelve-dollar-baas-benchmark-16g/.docker'

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

red=(D/'privacy-red-original.log').read_bytes();assert b'FAILED (failures=15)' in red and b'Ran 11 tests' in red and b'ERROR:' not in red
with (D/'privacy-green-original.log').open('xb') as f:
 subprocess.run(['python3','-B',str(D/'test_closure_privacy.py')],stdout=f,stderr=subprocess.STDOUT,check=True)
assert sha(F/'complete-inventory-private.json')=='d9ae4b36b01c5bc2cead534be3e55c8a080fcc25ed8ad11993ee893203abca22'
assert sha(C/'complete-post-update-input-catalog-v2-PRIVATE.json')=='043a6c0d00f897053f224ff298ac4c95d391c565fb0e27d5164af9789901c567'
inv=json.loads((F/'complete-inventory-private.json').read_text());cat=json.loads((C/'complete-post-update-input-catalog-v2-PRIVATE.json').read_text())
assert set(inv)=={'source','go_modules','images','generated_and_private_inputs_fingerprints_only'} and len(inv['source'])==107 and len(inv['go_modules'])==14330
for base,rows in [(R,inv['source']),(R/'.state/pocketbase/gopath/pkg/mod',inv['go_modules'])]:
 for row in rows:
  path=base/row['path'];assert path.resolve().is_relative_to(base.resolve())
  if 'link' in row:assert path.is_symlink() and os.readlink(path)==row['link']
  else:assert set(row)=={'path','bytes','sha256','mode'} and path.is_file() and not path.is_symlink() and path.stat().st_size==row['bytes'] and path.stat().st_mode&0o777==row['mode'] and sha(path)==row['sha256']
 if base==R:
  names=set()
  for directory,dirs,files in os.walk(base,followlinks=False):
   dirs[:]=[x for x in dirs if x not in {'.git','.state','results','__pycache__','target','node_modules'}]
   names.update(str((pathlib.Path(directory)/x).relative_to(base)) for x in files)
   names.update(str((pathlib.Path(directory)/x).relative_to(base)) for x in dirs if (pathlib.Path(directory)/x).is_symlink())
 else:names={str(p.relative_to(base)) for p in base.rglob('*') if p.is_file() or p.is_symlink()}
 assert names=={row['path'] for row in rows}
for name,digest in cat['external_sources_and_preserved_evidence'].items():assert sha(P/name)==digest
for name,digest in cat['new_generated_and_private_input_fingerprints_only'].items():assert sha(R/name)==digest
track=R/'results/pocketbase/vps16-linux-amd64';full=sorted(track.glob('*vu-k6-2cpu-8g-v3'));assert len(full)==25
for run in full:
 subprocess.run(['sha256sum','--check','SHA256SUMS'],cwd=run,stdout=subprocess.DEVNULL,check=True)
# Read actual private candidates without printing/exporting any value.
values={line.partition(b'=')[2] for line in (R/'.state/pocketbase/runtime.env').read_bytes().splitlines() if line.partition(b'=')[1] and line.partition(b'=')[2]}
v=json.loads(subprocess.check_output(['docker','volume','inspect','baas-pocketbase-vps16_data']))[0];assert v['Labels']['com.docker.compose.project']=='baas-pocketbase-vps16'
with sqlite3.connect(pathlib.Path(v['Mountpoint'],'data.db').as_uri()+'?mode=ro',uri=True) as db:
 for row in db.execute('SELECT password,tokenKey FROM _superusers'):values.update(x.encode() for x in row if isinstance(x,str) and x)
signatures={v['token'].split('.')[2].encode() for v in json.loads((R/'.state/seed/tokens.json').read_text())};assert len(values)==3 and len(signatures)==20000
E.mkdir(mode=0o700);records=[];omitted=[]

def export(name,raw,original):
 findings=issues('results/pocketbase/vps16-linux-amd64/supplemental-evidence/'+name,raw,values,signatures)
 assert not findings,'Export byte/path screen failed; no contents exported'
 dest=E/name;dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb') as f:f.write(raw)
 records.append({'public_relative_path':name,'native_source':original,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})

export('input-identities/complete-frozen-input-identities.json',(F/'complete-inventory-private.json').read_bytes(),'supplemental-20261016/complete-frozen-inputs2/complete-inventory-private.json')
export('input-identities/post-update-frozen-catalog.json',(C/'complete-post-update-input-catalog-v2-PRIVATE.json').read_bytes(),'supplemental-20261016/repeatability-post-update-01/complete-post-update-input-catalog-v2-PRIVATE.json')
for name,digest in cat['external_sources_and_preserved_evidence'].items():
 if not name.endswith('.py'):continue
 if pathlib.Path(name).name.startswith('supplemental-retain'):
  omitted.append({'native_source':name,'sha256':digest,'reason':'Original retention helpers remain native; exact identities retained in complete catalog. No original contents claimed publicly available.'});continue
 raw=(P/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
 export('native-sources/'+name,raw,name)
for name in ['closure_privacy.py','test_closure_privacy.py','export-closure-native-inputs.py','privacy-red-original.log','privacy-green-original.log']:
 export('publication-tools/'+name,(D/name).read_bytes(),'supplemental-20261016/publication-close-20261016/'+name)
report={'scope':'Fresh native checksum/source/private-input identity validation only; historical raw replays and full correctness are not falsely described as newly rerun tests. No build/install/pull/reset/load/service change. Metadata inventories contain identities only, not source/dependency archives, private values or fixture contents.','native_full_attempt_checksum_sets_verified':25,'actual_complete_source_entries_verified':107,'actual_installed_go_module_entries_verified':14330,'external_source_evidence_entries_verified':len(cat['external_sources_and_preserved_evidence']),'generated_private_fingerprints_verified':len(cat['new_generated_and_private_input_fingerprints_only']),'actual_private_candidates_checked':3,'actual_issued_signatures_checked':20000,'new_privacy_tests':{'native_red_assertion_failures':15,'native_red_import_errors':0,'native_green_tests':11},'omitted_original_retention_sources':omitted,'exported_files':records}
export('input-identities/native-publication-input-verification.json',(json.dumps(report,indent=2)+'\n').encode(),'generated read-only publication verification; not a scored artifact')
with (D/'screened-export-manifest.json').open('x') as f:json.dump({'files':records},f,indent=2);f.write('\n')
with tarfile.open(D/'screened-export.tar','w') as tar:
 for row in records:tar.add(E/row['public_relative_path'],arcname=row['public_relative_path'],recursive=False)
print(json.dumps({'native_identity_and_25_checksum_sets_passed':True,'privacy_green_tests':11,'export_files':len(records),'archive_sha256':sha(D/'screened-export.tar'),'archive_bytes':(D/'screened-export.tar').stat().st_size,'manifest_sha256':sha(D/'screened-export-manifest.json')}))
