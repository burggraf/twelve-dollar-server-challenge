#!/usr/bin/env python3
"""Preserve complete ACTUAL source/modules and immutable compiler/runtime inputs.

Private archives, no public-download/license claim. tree_inventory/digest are reused
unchanged from the already native-tested common Convex complete-freeze helpers.
"""
import hashlib,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
P=Path('/opt/twelve-dollar-baas-pocketbase-16g');R=P/'src';O=P/'supplemental-20261016';F=O/'complete-frozen-inputs2'
sys.path.insert(0,str(R/'scripts'));import pocketbase_profile as s;import pocketbase_benchmark as bench

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

def file_hash(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def image(reference):
 item=json.loads(subprocess.check_output(['docker','image','inspect',reference],text=True))[0]
 assert item['Os']=='linux' and item['Architecture']=='amd64'
 return {'reference':reference,'image_id':item['Id'],'platform':'linux/amd64','rootfs_layers':item['RootFS']['Layers']}

def registry_runtime():
 # BuildKit retained the final serving image, not a separately named base object.
 # Read ONLY immutable registry manifest/config metadata; no image pull/build.
 reference=s.PINS['runtime']['tag']+'@'+s.PINS['runtime']['amd64_manifest']
 metadata=json.loads(subprocess.check_output(['docker','buildx','imagetools','inspect',reference,'--format','{{json .}}'],text=True))
 assert metadata['manifest']['digest']==s.PINS['runtime']['amd64_manifest']
 config=metadata['image'];assert config['os']=='linux' and config['architecture']=='amd64'
 layers=config['rootfs']['diff_ids'];assert layers and image(s.PROJECT+'-feed:0.1.0')['rootfs_layers'][:len(layers)]==layers
 return {'reference':reference,'manifest_digest':metadata['manifest']['digest'],'platform':'linux/amd64','rootfs_layers':layers,'base_layers_verified_as_prefix_of_actual_serving_image':True,'verification':'Read-only registry manifest/config metadata; separate local base-image object absent, no pull or rebuild'}

att=json.loads((s.STATE/'correctness-manifest.json').read_text());before=bench.inputs();bench.validate_correctness(att,before,file_hash(s.STATE/'correctness.log'))
assert json.loads((O/'fresh-full-correctness-result-public.json').read_text())['same_frozen_inputs']==before
F.mkdir(mode=0o700)
# Preserve all actual filesystem source, not merely a selected source overlay.
# Exclusions are private runtime/results/Git/compiled caches, not used PB SDK code.
source=F/'complete-current-source'
shutil.copytree(R,source,symlinks=True,ignore=shutil.ignore_patterns('.git','.state','results','__pycache__','target','node_modules'))
sources=tree_inventory(source)
assert not any(Path(row['path']).name.startswith('.env') and Path(row['path']).name!='.env.example' for row in sources),'Unexpected private source-root configuration; refuse archive'
modules=s.STATE/'gopath/pkg/mod';assert modules.is_dir();dependencies=tree_inventory(modules)
images={'serving':image(s.PROJECT+'-feed:0.1.0'),'compiler':image(s.PINS['builder']['tag']+'@'+s.PINS['builder']['amd64_manifest']),'runtime_base':registry_runtime(),'tools':image('baas-trailbase-vps16-tools:0.1.0'),'runner':image('grafana/k6:1.3.0@'+bench.K6_MANIFEST)}
generated={str(path.relative_to(R)):{'bytes':path.stat().st_size,'sha256':file_hash(path)} for path in [s.STATE/'build/feed',s.STATE/'runtime.env',s.STATE/'native-schema-fixture.db',s.STATE/'build-manifest.json',s.STATE/'correctness-manifest.json',s.STATE/'correctness.log',R/'.state/seed/tokens.json',*[R/'.state/seed'/name for name in ['users.tsv','posts.tsv','likes.tsv']]]}
inventory={'source':sources,'go_modules':dependencies,'images':images,'generated_and_private_inputs_fingerprints_only':generated}
with (F/'complete-inventory-private.json').open('x') as f:json.dump(inventory,f,indent=2);f.write('\n')
archives={}
for name,base,rows in [('complete-current-source.tar.gz',source,sources),('complete-installed-go-module-inputs.tar.gz',modules,dependencies)]:
 path=F/name
 with path.open('xb') as output:
  with tarfile.open(fileobj=output,mode='w:gz',dereference=False) as archive:
   for row in rows:archive.add(base/row['path'],arcname=row['path'],recursive=False)
 archives[name]={'bytes':path.stat().st_size,'sha256':file_hash(path)}
assert tree_inventory(source)==sources and tree_inventory(modules)==dependencies and bench.inputs()==before
value={'scope':'Complete ACTUAL unchanged PocketBase source/Go module/compiler/runtime/generated-input freeze before supplemental holds; all archives private pending license/privacy/distribution review, no public-download/fresh-build claim','tested_software':s.PINS,'serving_budget':{'cpus':1,'memory_bytes':4294967296,'swap_bytes':0},'runner_budget':{'software':'k6 1.3.0','cpus':2,'memory_bytes':8589934592,'swap_bytes':0,'profile':'k6-2cpu-8g-v3'},'source_entries':len(sources),'go_module_entries':len(dependencies),'source_inventory_sha256':digest(sources),'go_module_inventory_sha256':digest(dependencies),'complete_inventory_sha256':file_hash(F/'complete-inventory-private.json'),'images':images,'generated_input_fingerprints_only':generated,'archives':archives,'original_attested_inputs_unchanged':before,'external_controller_source_scope':'Outside the source root; exact controller/policy/auditor bytes separately frozen before first hold and checked every attempt. Not falsely included in these actual product/source/module archives.'}
with (O/'complete-freeze-public.json').open('x') as f:json.dump(value,f,indent=2);f.write('\n')
print('COMPLETE_ACTUAL_SOURCE_GO_MODULES_COMPILER_RUNTIME_GENERATED_FREEZE_PASSED',len(sources),len(dependencies),flush=True)
