#!/usr/bin/env python3
"""Bounded read-only evidence only. NO server start/stop/reset/import/SQL/deploy."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path('/opt/twelve-dollar-baas-convexpg-16g/src');state=root/'.state/convex';out=root.parent/'setup-evidence';sys.path.insert(0,str(root/'scripts'))
import convex_profile as s
import benchmark as b
s.require_native();run=root/'results/convex/vps16-linux-amd64/20261016T020607016365Z-standard-2500vu-k6-2cpu-8g-v3';m=json.loads((run/'manifest.json').read_text());assert m['target_after']['targets']['backend']['State']['OOMKilled']
def save_command(name,argv):
 with (out/name).open('xb') as f:result=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,timeout=60)
 return {'name':name,'exit_code':result.returncode,'bytes':(out/name).stat().st_size,'sha256':sha(out/name)}
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
records=[]
records.append(save_command('native-capacity-oom-backend-original.log',['docker','logs','--timestamps','--since','2026-10-16T02:06:00Z',s.PROJECT+'-backend-1']))
records.append(save_command('native-capacity-oom-kernel-original.log',['journalctl','-k','--since','2026-10-16 02:09:00 UTC','--until','2026-10-16 02:20:00 UTC','--no-pager','--output','short-iso-precise']))
records.append(save_command('native-capacity-oom-docker-events-original.jsonl',['docker','events','--since','2026-10-16T02:09:00Z','--until','2026-10-16T02:20:00Z','--filter','container='+m['target_before']['targets']['backend']['Id'],'--format','{{json .}}']))
service=out/'native-capacity-oom-after-services.json';subprocess.run(['python3',str(root/'.state/vps16/service-snapshot.py'),str(service)],check=True,timeout=30)
a=json.loads((out/'native-frozen-correctness2-after-services.json').read_text());z=json.loads(service.read_text());services_same=all(z['services'].get(name)==value for name,value in a['services'].items() if name!='user@0.service');listener_same=a['port4000_listener']==z['port4000_listener'] and a['port4000_processes']==z['port4000_processes']
freeze=json.loads((state/'runtime-freeze.json').read_text());inventory=json.loads((state/'frozen-current/complete-current-inventory.json').read_text());archives={name:sha(state/'frozen-current'/name)==entry['sha256'] for name,entry in freeze['archives'].items()};source_same=all(sha(root/row['path'])==row['sha256'] for row in inventory['source']);runtime_same=s.full_runtime_state()['sha256']==freeze['full_runtime_sha256'];private_same=s.runtime_hash()==m['inputs']['runtime'];host=b.host_sample();targets=s.targets();parent=s.parent_sample()
result={'scope':'Read-only NEW serving-backend OOM evidence; no recovery/reseed/cleanup of app rows; original clean-SIGINT139 separately failed','run':run.name,'physical_full_attempts_consumed':1,'campaign_history_empty_is_exception_before_append_not_zero_runs':True,'records':records,'archives_sha256_match':archives,'all_complete_source_files_equal':source_same,'installed_sdk_compiler_generated_equal':runtime_same,'private_files_native_runtime_configuration_hash_equal':private_same,'targets':targets,'parent':parent,'host':host,'persistent_services_equal':services_same,'port4000_listener_and_process_identities_equal':listener_same,'no_native_api_post_crash_canonical_or_persistence_certification':True,'volumes_preserved':True,'no_server_restart_or_revival_performed':True}
with (out/'native-capacity-oom-read-only-postmortem.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
assert all(archives.values()) and source_same and runtime_same and private_same and services_same and listener_same
assert not targets['backend']['State']['Running'] and targets['backend']['State']['OOMKilled'] and targets['backend']['State']['ExitCode']==137
assert targets['postgres']['State']['Pid']==m['target_before']['targets']['postgres']['State']['Pid'] and targets['postgres']['State']['Health']['Status']=='healthy'
print('NEW_BACKEND_OOM_ORIGINAL_LOGS_KERNEL_EVENTS_FULL_FREEZE_PRIVATE_CONFIGURATION_NATIVE_EPOCH_AND_SERVICES_PRESERVED_READONLY_NO_REVIVAL',flush=True)
