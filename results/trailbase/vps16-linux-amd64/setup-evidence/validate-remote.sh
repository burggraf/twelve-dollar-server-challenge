#!/usr/bin/env bash
set -euo pipefail
base=/opt/twelve-dollar-baas-benchmark-16g
test -f "$base/.benchmark-owned"
export DOCKER_CONFIG="$base/.docker"
export BENCHMARK_PROJECT=baas-trailbase-vps16
export BENCHMARK_RUNNER_PROFILE=k6-2cpu-8g-v3
export TIER=standard TRAILBASE_PORT=14000
test -z "$(ss -H -lnt 'sport = :14000')"
test -z "$(docker ps -aq --filter name=baas-trailbase-vps16)$(docker image ls -q 'baas-trailbase-vps*')"
test -z "$(ls -A "$base/src")"
cd "$base/assets"
sha256sum -c source-vps16.sha256
sha256sum -c native-images-vps16.sha256
tar -xzf source-vps16.tar.gz -C "$base/src"
docker load -i native-images-vps16.tar > "$base/setup-evidence/image-load.log"
docker tag baas-trailbase-vps-feed:0.1.0 baas-trailbase-vps16-feed:0.1.0
docker tag baas-trailbase-vps-tools:0.1.0 baas-trailbase-vps16-tools:0.1.0
cd "$base/src"
python3 - <<'PY'
from pathlib import Path
import json,subprocess,sys
sys.path.insert(0,'scripts')
import benchmark
base=Path('/opt/twelve-dollar-baas-benchmark-16g')
expected=json.loads((base/'assets/source-inputs.json').read_text())
assert expected['app_source_sha256']==benchmark.app_source_hash()
assert expected['verification_source_sha256']==benchmark.verification_source_hash()
assert expected['git_base']==subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
label=subprocess.check_output(['docker','image','inspect','baas-trailbase-vps16-feed:0.1.0','--format','{{index .Config.Labels "benchmark.source_sha256"}}'],text=True).strip()
assert label==expected['app_source_sha256']
assert benchmark.TRACK=='vps16-linux-amd64' and benchmark.RUNNER_PROFILE=='k6-2cpu-8g-v3'
assert benchmark.RUNNER_LIMITS['Memory']==8*1024**3
assert benchmark.TIERS['standard']==(1,4*1024**3)
benchmark.require_vm_headroom('standard',int(benchmark.capture(['docker','info','--format','{{.MemTotal}}'])),int(benchmark.capture(['docker','info','--format','{{.NCPU}}'])))
available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
assert available>=13*1024**3, 'Insufficient available memory; leave existing services alone and ask owner'
print('VPS16_SOURCE_IMAGES_PROFILE_HEADROOM_VERIFIED')
PY
bash services/trailbase/run.sh test
echo VPS16_FULL_CORRECTNESS_PASSED
python3 -u scripts/benchmark.py --smoke --vus 10000
python3 "$base/service-snapshot.py" "$base/setup-evidence/preexisting-after-calibration.json"
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/opt/twelve-dollar-baas-benchmark-16g/setup-evidence')
before=json.loads((root/'preexisting-before-setup.json').read_text())
after=json.loads((root/'preexisting-after-calibration.json').read_text())
changed=[name for name,identity in before['services'].items() if after['services'].get(name)!=identity]
listener_same=all(before[key]==after[key] for key in ['port4000_listener','port4000_processes'])
report={'existing_service_count':len(before['services']),'changed_existing_service_count':len(changed),
        'original_port4000_listener_unchanged':listener_same}
(root/'continuity-calibration-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print('Service continuity summary:',json.dumps(report))
assert not changed and listener_same, 'Existing service state changed; investigate before capacity'
PY
echo VPS16_CORRECTNESS_CALIBRATION_AND_CONTINUITY_PASSED
