import subprocess,sys
from pathlib import Path
C=Path(__file__).parent;O=C.parent
for p in [O/'test_supplemental_policy.py',O/'test_supplemental_rebracket_policy.py',C/'test_supplemental_repeatability_policy.py']:
 subprocess.run([sys.executable,str(p)],check=True)
