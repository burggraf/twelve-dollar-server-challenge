#!/usr/bin/env python3
"""Final frozen functional/harness gate; known clean-shutdown failure stays failed."""
import hashlib,json,os,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
root=Path('/opt/twelve-dollar-baas-convexpg-16g/src');state=root/'.state/convex';out=root.parent/'setup-evidence';sys.path.insert(0,str(root/'scripts'))
import convex_profile as s
import convex_benchmark as bench
s.require_native();bench.require_headroom()
assert not (state/'correctness.log').exists() and not (state/'correctness-manifest.json').exists(), 'Exclusive final evidence already exists; preserve and inspect'
freeze=json.loads((state/'runtime-freeze.json').read_text());inventory=json.loads((state/'frozen-current/complete-current-inventory.json').read_text())
def sha(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def verify_complete_freeze():
 for name,entry in freeze['archives'].items():assert sha(state/'frozen-current'/name)==entry['sha256'], 'Frozen complete archive changed'
 for row in inventory['source']:assert sha(root/row['path'])==row['sha256'], 'Complete source changed: '+row['path']
 assert s.full_runtime_state()['sha256']==freeze['full_runtime_sha256'], 'Installed SDK/compiler/generated inputs changed'
verify_complete_freeze();before=s.deployment_attestation();current=bench.inputs(before)
import benchmark as common
host_before=common.host_sample()
external=state/'frozen-current/full-frozen-correctness.py'
with external.open('xb') as output:output.write(Path(__file__).read_bytes())
assert bench.runtime_issue(freeze['serving_profile'],before['serving_profile']) is None
baseline=json.loads((out/'native-crash-recovery-after.json').read_text())
for name in ['native.js','http.js','schema.js','contract.js','clock.js','fixtures.js','maintenance.js']:
 key='services/convex/app/convex/'+name;assert sha(root/key)==baseline['source_sha256'][key]
# These are prior original139/crash-recovery evidence, NEVER rerun exclusive phases.
prior={name:sha(out/name) for name in ['native-persistence-before.json','native-persistence-after.json','native-backend-controlled-stop-state.json','native-crash-recovery-after.json','native-crash-recovery-canonical-dataset.json','native-crash-recovery-acknowledged-after.json']}
for role,old in baseline['targets'].items():
 assert old['Id']==before['serving_profile']['targets'][role]['Id'] and old['started_at']==before['serving_profile']['targets'][role]['State']['StartedAt']
service_before=out/'native-frozen-correctness-before-services.json';service_after=out/'native-frozen-correctness-after-services.json'
subprocess.run(['python3',str(root/'.state/vps16/service-snapshot.py'),str(service_before)],check=True)
with (out/'native-frozen-correctness-before.json').open('x') as stream:json.dump(before,stream,indent=2);stream.write('\n')
started=time.time();log=state/'correctness.log'
try:
 with log.open('x') as output:
  backend_started=before['serving_profile']['targets']['backend']['State']['StartedAt']
  script='''
export CONVEX_TEST_BACKEND_STARTED_AT="'''+backend_started+'''"
python3 /work/test/baas/convex_maintenance.py
bash /work/test/test.sh "$BASE_URL"
python3 /work/test/baas/test_api.py
export CONVEX_RESET_ERROR_DIRECTORY=/state/convex/frozen-reset-private-errors
python3 /work/scripts/convex.py reset
CONVEX_WRITE_PROBE_MARKER=tds-native-write-probe:final-frozen-20261016: CONVEX_PROBE_CLEANUP=1 python3 /work/test/baas/convex_http_writes.py
CONVEX_WRITE_GUARD_MARKER=tds-native-write-probe:guard-final-frozen-20261016: CONVEX_WRITE_GUARD_CLEANUP=1 python3 /work/test/baas/convex_fixture_guards.py
CONVEX_EDGE_PROBE_MARKER=tds-native-edge-probe:edge-final-frozen-20261016: CONVEX_EDGE_PROBE_CLEANUP=1 python3 /work/test/baas/convex_stored_edges.py
python3 /work/test/baas/convex_http_auth.py
python3 /work/test/baas/convex_error_contract.py
python3 /work/test/baas/convex_health_native.py
python3 /work/test/baas/convex_http_reads.py
python3 /work/test/baas/convex_feasibility.py NativeFeasibility.test_02_native_probe_is_not_a_public_query NativeFeasibility.test_03_identical_queries_reexecute_without_result_cache
export CONVEX_SEED_DIR=/state/convex/seed CONVEX_NATIVE_DATASET_MANIFEST=/state/convex/dataset.json
python3 /work/test/baas/convex_dataset.py
python3 /work/test/baas/test_convex_import.py
python3 /work/test/baas/test_seed.py
node --test /work/bench/baas-contract.test.mjs
'''
  bench.tools(script,output,'final-frozen-tools')
  for name in ['test_convex_harness.py','test_convex_evidence.py','test_convex_freeze.py','test_convex_load_config.py','test_convex_budget.py','test_convex_postgres_config.py','test_convex_controller.py','test_benchmark.py','test_isolation.py','test_pocketbase_harness.py','test_supabase_harness.py','test_gitignore.py']:
   subprocess.run(['python3',str(root/'test/baas'/name) if name!='test_gitignore.py' else str(root/'test/test_gitignore.py')],cwd=root,stdout=output,stderr=subprocess.STDOUT,check=True)
  output.write('\nFULL_FROZEN_FUNCTIONAL_HARNESS_CHECKS_PASSED_CLEAN_SHUTDOWN_REMAINS_FAILED139_OWNER_EXCEPTION_NOT_POWERLOSS\n');output.flush()
 # Check all unabridged bytes rather than a successful wrapper alone.
 data=log.read_bytes();assert b'passed=42 failed=0' in data and b'FAILED (' not in data and b'ERROR:' not in data
 verify_complete_freeze();after=s.deployment_attestation();assert bench.inputs(after)==current
 host_after=common.host_sample();assert common.host_swapouts(host_before)==common.host_swapouts(host_after)
 assert sha(external)==sha(Path(__file__))
 assert bench.runtime_issue(before['serving_profile'],after['serving_profile']) is None
 assert s.runtime_hash()==current['runtime']
 for name,digest in prior.items():assert sha(out/name)==digest
 subprocess.run(['python3',str(root/'.state/vps16/service-snapshot.py'),str(service_after)],check=True)
 a=json.loads(service_before.read_text());z=json.loads(service_after.read_text())
 assert a['port4000_listener']==z['port4000_listener'] and a['port4000_processes']==z['port4000_processes']
 assert all(z['services'].get(name)==entry for name,entry in a['services'].items() if name!='user@0.service')
 with (out/'native-frozen-correctness-after.json').open('x') as output:json.dump(after,output,indent=2);output.write('\n')
 result={'inputs':current,'log_sha256':sha(log),'serving_targets':after['serving_profile']['targets'],'runtime_freeze_manifest_sha256':sha(state/'runtime-freeze.json'),'complete_source_and_runtime_archive_checksums_verified':True,'prior_lifecycle_evidence_sha256':prior,'clean_shutdown':{'result':'FAILED','backend_exit':139,'capacity_exception_explicit_owner_permission':True,'acknowledged_recovery':'Separate41-check original actual survivor proof, same current app7/source/images/PIDs/starts'},'completed_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.time()-started,'external_gate_source_sha256':sha(external),'host_before':host_before,'host_after':host_after}
 with (state/'correctness-manifest.json').open('x') as output:json.dump(result,output,indent=2);output.write('\n')
 with (out/'native-frozen-correctness-manifest.json').open('x') as output:json.dump(result,output,indent=2);output.write('\n')
 with (out/'native-frozen-correctness-original.log').open('xb') as output:output.write(data)
 print('FULL_CURRENT_FROZEN_ORIGINAL42_SHARED6_NATIVE_SECURITY_RUNTIME_HARNESS_GATE_PASSED_ORIGINAL_CLEANSIGINT139_STILL_FAILED_NO_K6_YET',flush=True)
finally:
 with (out/'native-frozen-correctness-final-state.json').open('x') as output:json.dump({'targets':s.targets(),'parent':s.parent_sample(),'host_vmstat':Path('/proc/vmstat').read_text(),'succeeded':(state/'correctness-manifest.json').is_file()},output,indent=2);output.write('\n')
