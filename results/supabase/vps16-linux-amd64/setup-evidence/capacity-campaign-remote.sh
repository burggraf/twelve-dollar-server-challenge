#!/usr/bin/env bash
set -euo pipefail
base=/opt/twelve-dollar-baas-supabase-16g
cd "$base/src"
export DOCKER_CONFIG=/opt/twelve-dollar-baas-benchmark-16g/.docker PYTHONDONTWRITEBYTECODE=1
python3 "$base/service-snapshot.py" "$base/setup-evidence/before-capacity.json"
cleanup() {
  status=$?
  python3 "$base/service-snapshot.py" "$base/setup-evidence/after-capacity.json"
  python3 - "$status" <<'PY'
from pathlib import Path
import json,sys
base=Path('/opt/twelve-dollar-baas-supabase-16g/setup-evidence')
a=json.loads((base/'preexisting-before-setup.json').read_text());z=json.loads((base/'after-capacity.json').read_text())
services={k:v for k,v in a['services'].items() if k!='user@0.service'}
result={'campaign_exit':int(sys.argv[1]),'persistent_services_compared':len(services),'changed_persistent_services':[k for k,v in services.items() if z['services'].get(k)!=v],'original_port4000_listener_and_start_identities_unchanged':a['port4000_listener']==z['port4000_listener'] and a['port4000_processes']==z['port4000_processes'],'root_login_manager_changed':a['services'].get('user@0.service')!=z['services'].get('user@0.service'),'root_login_manager_scope':'Normal root SSH-session manager only'}
(base/'capacity-continuity.json').write_text(json.dumps(result,indent=2)+'\n')
print('SUPABASE_CAPACITY_CONTINUITY',json.dumps(result),flush=True)
PY
  exit "$status"
}
trap cleanup EXIT
cp .state/supabase/correctness-manifest.json "$base/setup-evidence/capacity-frozen-correctness-manifest.json"
echo SUPABASE_CAPACITY_CAMPAIGN_BEGIN_NATIVE_STANDARD_V3
bash services/supabase/run.sh search --max-vus 20000 --max-attempts 12
