#!/usr/bin/env bash
set -euo pipefail
stage=.state/vps16/retained-confirmations
mkdir -p "$stage"
base=root@azabab.com:/opt/twelve-dollar-baas-benchmark-16g
opts=(-o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes)
scp -q "${opts[@]}" "$base/src/.state/trailbase/confirmation15000-state.json" "$base/confirm-15000-job.log" "$base/container-lifecycle-confirm15000.log" "$stage/"
python3 - <<'PY' > "$stage/run-ids.txt"
from pathlib import Path
import json,re
v=json.loads(Path('.state/vps16/retained-confirmations/confirmation15000-state.json').read_text())
assert v['status']=='confirmed_lower_bound_pending_human_review'
assert len(v['attempts'])==3 and all(a['outcome']=='pass' and a['vus']==15000 for a in v['attempts'])
assert v['continuity']=={'changed_persistent_services':0,'original_port4000_listener_unchanged':True}
for a in v['attempts']:
 assert re.fullmatch(r'\d{8}T\d{12}Z-standard-15000vu-k6-2cpu-8g-v3',a['run_id'])
 print(a['run_id'])
PY
while IFS= read -r run; do
 scp -q -r "${opts[@]}" "$base/src/results/trailbase/vps16-linux-amd64/$run" "$stage/"
done < "$stage/run-ids.txt"
python3 .state/vps16/verify-confirmations.py
