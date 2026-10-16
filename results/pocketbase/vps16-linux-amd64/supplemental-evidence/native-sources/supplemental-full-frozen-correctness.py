#!/usr/bin/env python3
"""Fresh ORIGINAL full suite on the SAME immutable executable/image; no rebuild.

The original build step combines Go tests and rebuilding. For this unchanged-image
follow-up, replace only that step with fresh offline native Go tests plus immutable
image/executable/source checks. Every original correctness assertion still runs.
"""
import fcntl,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
P=Path('/opt/twelve-dollar-baas-pocketbase-16g');R=P/'src';O=P/'supplemental-20261016';os.chdir(R)
sys.path.insert(0,str(R/'scripts'));import pocketbase as ctl;import pocketbase_profile as s;import pocketbase_benchmark as bench
ctl.require_native();ctl.ownership()
review=json.loads((O/'historical-original-raw-replay-public.json').read_text());assert len(review['attempts'])==12
old=json.loads((s.STATE/'correctness-manifest.json').read_text());expected=old['inputs'];build=s.build_manifest();image=build['image_id'];exe=build['executable_sha256'];source=s.app_hash();verification=s.verification_hash()
assert image=='sha256:489cba19771795f5378e440c7f6d83d81f8460bf31e673aff8a392b080a9b131'
assert len(list((R/'results/pocketbase/vps16-linux-amd64').glob('*vu-k6-2cpu-8g-v3')))==11
for cid in ['f6a3332784f218eae1e5afca5cd967e661ff27e551640cc378e40f3c81bdac75','164ec7fdab991f75be71168cdf1ea0b981fd3141a34bd794af4035c897b72177']:
 assert not json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0]['State']['Running']

def immutable():
 assert s.app_hash()==source and s.verification_hash()==verification and s.build_manifest()==build
 assert hashlib.sha256((s.STATE/'build/feed').read_bytes()).hexdigest()==exe
 assert subprocess.check_output(['docker','image','inspect',s.PROJECT+'-feed:0.1.0','--format','{{.Id}}'],text=True).strip()==image

builder=s.PINS['builder']['tag']+'@'+s.PINS['builder']['amd64_manifest']
assert subprocess.check_output(['docker','image','inspect',builder,'--format','{{.Os}}/{{.Architecture}}'],text=True).strip()=='linux/amd64'

def test_frozen_build(log=None):
 immutable()
 log.write('FOLLOWUP_REUSES_SAME_IMMUTABLE_SERVING_IMAGE_AND_EXECUTABLE_NO_REBUILD; FRESH_NATIVE_GO_SUITE_2CPU_4G_ZERO_SWAP\n');log.flush()
 ctl.run(['docker','run','--rm','--pull','never','--network','none','--platform','linux/amd64',
          '--name',s.PROJECT+'-supplemental-native-go-tests','--label','com.docker.compose.project='+s.PROJECT,
          '--cpus','2','--memory','4294967296','--memory-swap','4294967296',
          '-e','CGO_ENABLED=0','-e','GOMAXPROCS=2','-e','GOMEMLIMIT=3GiB','-e','GOTOOLCHAIN=local','-e','GOPROXY=off',
          '-v',str(R/'services/pocketbase/app')+':/work:ro','-v',str(s.STATE/'gopath')+':/go',
          '-v',str(s.STATE/'gocache')+':/root/.cache/go-build','-w','/work',builder,
          'bash','-euc','go version; uname -m; go mod verify; go test -count=1 -v ./...'],log)
 immutable()

with (s.STATE/'lifecycle.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 backup=O/'before-fresh-correctness';backup.mkdir(mode=0o700)
 for name in ['correctness.log','correctness-manifest.json','dataset.json','persistence.json','build-manifest.json']:
  original=s.STATE/name
  if original.exists():
   with (backup/name).open('xb') as f:f.write(original.read_bytes())
 immutable()
 # Original full suite, not a reduced duplicate: Go10, inherited42, shared/native,
 # actual DB faults/rollback, import/privacy/scoring/isolation/harness/resource,
 # real transport outage + acknowledged-write exactly-once restart/allocation.
 ctl.build=test_frozen_build
 ctl.full_test()
 fresh=json.loads((s.STATE/'correctness-manifest.json').read_text());assert fresh['inputs']==expected
 bench.validate_correctness(fresh,bench.inputs(),hashlib.sha256((s.STATE/'correctness.log').read_bytes()).hexdigest())
 with (O/'post-full-correctness-canonical-reset-original.log').open('x') as log:ctl.reset(log)
 current=bench.inputs();assert current==expected
 data=json.loads((s.STATE/'dataset.json').read_text());assert data['content_sha256']=='738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d'
 assert data['counts']=={'users':50000,'posts':500000,'likes':2016005}
 assert data['platform_rows_before_sha256']==data['platform_rows_after_sha256']
 immutable()
 for name in ['correctness.log','correctness-manifest.json','dataset.json']:
  with (O/('fresh-'+name)).open('xb') as f:f.write((s.STATE/name).read_bytes())
 result={'scope':'Fresh complete ORIGINAL native correctness suite on existing SAME immutable serving executable/image, not a rebuild; historical raw evidence preserved separately','tested_software':s.PINS,'serving_budget':{'cpus':1,'memory_bytes':4294967296,'swap_bytes':0},'runner_budget':{'software':'k6 1.3.0','cpus':2,'memory_bytes':8589934592,'swap_bytes':0,'profile':'k6-2cpu-8g-v3'},'untimed_native_go_tests':{'builder':builder,'cpus':2,'memory_bytes':4294967296,'swap_bytes':0,'offline_modules_verified':True,'go_tests_fresh_count_flag':1,'serving_image_rebuilt':False},'same_frozen_inputs':current,'old_correctness_log_sha256':old['log_sha256'],'fresh_correctness_log_sha256':fresh['log_sha256'],'canonical_restored_after_full_suite':True,'serving':s.profile(),'supplemental_full_attempts_consumed':0,'finished_time':time.time()}
 with (O/'fresh-full-correctness-result-public.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 subprocess.run(['python3',str(P/'service-snapshot.py'),str(O/'after-full-correctness-services.json')],check=True)
 print('FRESH_ORIGINAL_FULL_POCKETBASE_CORRECTNESS_SAME_IMAGE_SOURCE_EXECUTABLE_CANONICAL_RESTORED_PASSED',flush=True)
