#!/usr/bin/env python3
"""Explicit owner blocked/unscored choice: stop ONLY owned PG; preserve all storage."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path('/opt/twelve-dollar-baas-convexpg-16g/src');out=root.parent/'setup-evidence';sys.path.insert(0,str(root/'scripts'))
import convex_profile as s
s.require_native();review=json.loads((out/'native-standard-first-oom-raw-review.json').read_text());assert review['run']=='20261016T020607016365Z-standard-2500vu-k6-2cpu-8g-v3' and review['new_serving_backend_oom_exit137'] and review['all_original_checksums_verified']
before=s.targets();parent_before=s.parent_sample();private=s.runtime_hash();backend=before['backend'];pg=before['postgres']
assert backend['Id']=='f6a3332784f218eae1e5afca5cd967e661ff27e551640cc378e40f3c81bdac75' and not backend['State']['Running'] and backend['State']['OOMKilled'] and backend['State']['ExitCode']==137
assert pg['Id']=='164ec7fdab991f75be71168cdf1ea0b981fd3141a34bd794af4035c897b72177' and pg['State']['Pid']==2313499 and pg['State']['Running'] and pg['State']['Health']['Status']=='healthy'
for role,value in before.items():assert value['compose_project']==s.PROJECT
assert pg['Image']=='sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df'
volumes=[s.PROJECT+'_data',s.PROJECT+'_pgdata'];preserved=[]
for name in volumes:
 v=json.loads(subprocess.check_output(['docker','volume','inspect',name]))[0];assert v['Name']==name;preserved.append({'Name':v['Name'],'Driver':v['Driver'],'CreatedAt':v.get('CreatedAt')})
with (out/'native-capacity-owned-postgres-stop-before.json').open('x') as f:json.dump({'targets':before,'parent':parent_before,'private_runtime_sha256':private,'preserved_volumes':preserved,'owner_authority':'Interview3674c27d-3fe8-4cf6-adec-60668e69f3df: publish blocked/unscored, cleanly stop only owned PostgreSQL after evidence capture, preserve all volumes/inputs, then Nhost feasibility'},f,indent=2);f.write('\n')
with (out/'native-capacity-owned-postgres-stop-original.log').open('xb') as f:subprocess.run(['docker','stop','--time','30',pg['Id']],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=45)
after=s.targets();assert after['backend']['State']==backend['State'];assert after['postgres']['Id']==pg['Id'] and not after['postgres']['State']['Running'] and after['postgres']['State']['ExitCode']==0 and not after['postgres']['State']['OOMKilled'];assert s.runtime_hash()==private
for name in volumes:assert json.loads(subprocess.check_output(['docker','volume','inspect',name]))[0]['Name']==name
with (out/'native-capacity-owned-postgres-after-stop-original.log').open('xb') as f:subprocess.run(['docker','logs','--timestamps','--since','2026-10-16T02:15:00Z',pg['Id']],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=30)
subprocess.run(['python3',str(root/'.state/vps16/service-snapshot.py'),str(out/'native-capacity-owned-stop-after-services.json')],check=True,timeout=30)
with (out/'native-capacity-owned-postgres-stop-after.json').open('x') as f:json.dump({'targets':after,'parent':s.parent_sample(),'private_runtime_sha256_unchanged':True,'volumes_preserved':preserved,'backend_not_revived_oom137_preserved':True,'only_postgres_stopped_actual_process_exit0':True,'native_data_not_reseeded_or_reset_or_verified_after_oom':True,'original_clean_backend_shutdown139_still_failed':True},f,indent=2);f.write('\n')
print('OWNER_APPROVED_ONLY_OWNED_POSTGRES_CLEAN_EXIT0_BACKEND_OOM137_UNCHANGED_ALL_VOLUMES_PRIVATE_INPUTS_PRESERVED_NO_REVIVAL',flush=True)
