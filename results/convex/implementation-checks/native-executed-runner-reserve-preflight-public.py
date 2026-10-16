#!/usr/bin/env python3
"""Actual approved image/version/headroom evidence, no load/workload invocation."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path('/opt/twelve-dollar-baas-convexpg-16g/src');state=root/'.state/convex';out=root.parent/'setup-evidence';sys.path.insert(0,str(root/'scripts'))
import benchmark as b
import convex_profile as s
import convex_benchmark as bench
s.require_native();bench.require_headroom()
att=json.loads((state/'correctness-manifest.json').read_text());assert bench.validate_correctness(att,bench.inputs(),hashlib.sha256((state/'correctness.log').read_bytes()).hexdigest())
before=s.profile();assert bench.target_issue(att['serving_targets'],before['targets']) is None
assert bench.runtime_issue(json.loads((state/'runtime-freeze.json').read_text())['serving_profile'],before) is None
name=s.PROJECT+'-runner-version'
assert not b.capture(['docker','ps','-aq','--filter','name=^'+name+'$']).strip(), 'Exclusive runner-version name occupied'
with (out/'native-runner-version-original.log').open('x') as output:
 result=subprocess.run(bench.compose()+['run','-T','--no-deps','--name',name,'k6','version'],cwd=root,stdout=output,stderr=subprocess.STDOUT)
assert result.returncode==0
version=(out/'native-runner-version-original.log').read_text();assert 'k6 v1.3.0' in version
item=json.loads(b.capture(['docker','inspect',name]))[0];selected=b.inspect(name)
assert selected['limits']==b.RUNNER_LIMITS and selected['platform']=='linux/amd64' and selected['image_manifest_digest']==bench.K6_MANIFEST
assert item['Config']['Labels']['com.docker.compose.project']==s.PROJECT and not item['State']['Running']
# Remove only this exact-owned completed version probe, never a serving container.
subprocess.run(['docker','rm',item['Id']],check=True,capture_output=True)
bench.require_headroom()
vmstat=subprocess.check_output(['vmstat','-w','1','2'],text=True,timeout=10)
# Raw counters preserve baseline CPU/idle/load/available-memory context; quotas
# and resource monitoring, not an invented dedicated-core claim, govern scoring.
after=s.profile();assert bench.runtime_issue(before,after) is None
value={'scope':'Actual pre-load runner image/version and available-memory/physical CPU reserve; no k6 script/workload run','runner_version':'1.3.0','runner_probe':selected,'serving':after,'host':b.host_sample(),'vmstat_two_samples':vmstat,'physical_cpu_count':os.cpu_count(),'required_cpu_allocation':{'serving':1,'runner':2,'reserve':1},'required_available_memory_beyond_running_serving':{'runner_bytes':8589934592,'reserve_bytes':1073741824},'shared_host_not_dedicated':True,'known_clean_shutdown':{'result':'FAILED','backend_exit':139,'capacity_owner_exception':True}}
with (out/'native-runner-reserve-preflight.json').open('x') as output:json.dump(value,output,indent=2);output.write('\n')
print('ACTUAL_K6_1_3_0_NATIVE_PIN_AND2CPU8G_ZERO_SWAP_LIMITS_RUNNER_PLUS_RESERVE_HEADROOM_VERIFIED_NO_WORKLOAD_YET',flush=True)
