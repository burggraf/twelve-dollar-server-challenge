from pathlib import Path
import subprocess
R=Path('/opt/twelve-dollar-baas-pocketbase-16g/src/results/pocketbase/vps16-linux-amd64')
paths=sorted(R.glob('*vu-k6-2cpu-8g-v3'));assert len(paths)==18
for p in paths:
 print('VERIFY_ORIGINAL_BUNDLE',p.name,flush=True)
 subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=p,check=True)
print('ALL18ORIGINAL_CHECKSUM_SETS_PASSED_NO_REWRITE',flush=True)
