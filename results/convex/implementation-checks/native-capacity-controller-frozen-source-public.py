#!/usr/bin/env python3
"""Durable bounded campaign: original common search, no runtime revival or quiet resume."""
import contextlib,fcntl,hashlib,json,os,re,sys
from pathlib import Path
from types import SimpleNamespace
root=Path('/opt/twelve-dollar-baas-convexpg-16g/src');state=root/'.state/convex';out=root.parent/'setup-evidence';sys.path.insert(0,str(root/'scripts'))
import benchmark as common
import convex_profile as profile
import convex_benchmark as bench
profile.require_native();bench.require_headroom()
lock=(state/'campaign.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
run=sys.argv[1];assert re.fullmatch(r'[0-9]{8}T[0-9]{12}Z-standard-[0-9]+vu-k6-2cpu-8g-v3-smoke',run)
calibration=bench.RESULTS/run
summary=json.loads((calibration/'summary.json').read_text());manifest=json.loads((calibration/'manifest.json').read_text())
assert summary['outcome']=='pass' and summary['mode']=='smoke' and manifest['mode']=='smoke'
review=json.loads((out/'native-smoke100-raw-review.json').read_text())
assert review['run']==run and review['outcome']=='pass' and review['mode']=='smoke' and review['runtime_issue'] is None and review['measurement_replay'][0]=='pass' and review['all_original_checksums_verified'] and review['raw_counts_and_quantiles_reproduced']
att=json.loads((state/'correctness-manifest.json').read_text());bench.validate_correctness(att,bench.inputs(),hashlib.sha256((state/'correctness.log').read_bytes()).hexdigest())
assert manifest['inputs']==att['inputs']
assert not (state/'campaign.json').exists(), 'Campaign exists; no automatic resume/overwrite'
initial=profile.profile();assert bench.target_issue(att['serving_targets'],initial['targets']) is None
assert bench.runtime_issue(json.loads((state/'runtime-freeze.json').read_text())['serving_profile'],initial) is None
assert not common.capture(['docker','ps','-aq','--filter','name=^'+common.LOAD+'$']).strip()
# Retain this exact external driver before the first scored interval.
with (out/'native-capacity-controller-frozen-source.py').open('xb') as output:output.write(Path(__file__).read_bytes())
def attempt(vus,tier):
 before=profile.profile();assert bench.runtime_issue(initial,before) is None
 result,path=bench.attempt(vus,tier)
 after=profile.profile();issue=bench.runtime_issue(before,after)
 if issue:raise RuntimeError('New serving runtime failure preserved; campaign stopped without revival')
 # Only fixed progress marker reaches managed stdout; original complete result
 # JSON/logs stay private pending actual-secret/JWT/query screening.
 with terminal_stdout():print('CONVEX_STANDARD_ATTEMPT_FINISHED',flush=True)
 return result,path
original_stdout=sys.stdout
@contextlib.contextmanager
def terminal_stdout():
 with contextlib.redirect_stdout(original_stdout):yield
with (out/'native-capacity-controller-original.log').open('x') as log:
 with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
  common.campaign(SimpleNamespace(max_vus=20000,max_attempts=12),'standard',attempt_runner=attempt,results=bench.RESULTS,campaign_file=state/'campaign.json')
print('CONVEX_BOUNDED_STANDARD_CAMPAIGN_FINISHED_PENDING_RAW_RESOURCE_SOURCE_PRIVACY_REVIEW',flush=True)
