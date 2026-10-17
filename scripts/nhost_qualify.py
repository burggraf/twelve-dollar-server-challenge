"""Full unchanged contract/native gate, unavailable storage, actual HTTP acknowledgements across restart and canonical refreeze."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
import nhost as n
import nhost_profile as s
import nhost_benchmark as bench
import import_nhost

def qualify(name):
 if not re.fullmatch('[a-z0-9-]{1,24}',name):raise ValueError('Exclusive qualification name required')
 if (s.STATE/'correctness-manifest.json').exists() or (s.STATE/'correctness.log').exists():raise RuntimeError('Existing full qualification must be retained/classified before another freeze')
 n.claim(name+'-prepare');original=n.evidence()/'full-correctness-original-PRIVATE.log'
 with original.open('xb') as output:
  def tools(script,label):
   path=n.tools(script,label);raw=path.read_bytes();output.write(('\n=== '+label+' ===\n').encode()+raw);output.flush();return raw
  try:
   n.up(('db',));canonical=import_nhost.verify(s.identities()['db']);n.up();before=s.deployment_attestation();frozen=bench.inputs(before)
   raw=tools('node --version; node --test --test-reporter=tap services/nhost/app/native-contract.test.mjs services/nhost/app/http.test.mjs services/supabase/functions/feed/contract.test.mjs; bash test/test.sh "$BASE_URL"; python3 -B test/baas/test_api.py; python3 -B test/baas/nhost_native.py','complete-original-shared-native')
   if b'passed=42 failed=0' not in raw or b'# tests 19' not in raw:raise RuntimeError('Unchanged original42-check or19-node-test completion marker missing')
   tools(f'export RESTART_PROOF=/state/{name}-restart.json; python3 -B test/baas/nhost_lifecycle.py prepare','acknowledged-http-prepare')
   restart_before=s.targets()
   stopped=n.stop_owned(s.identities(),n.evidence()/'dependency-database-stop',roles=('db',))
   if stopped['failures']:raise RuntimeError('Storage-dependency stop failed')
   tools(f'export RESTART_PROOF=/state/{name}-restart.json; python3 -B test/baas/nhost_lifecycle.py unavailable','storage-unavailable-contract')
  finally:n.down()
  n.claim(name+'-restart')
  try:
   n.up();restart_after=s.targets()
   if any(restart_before[role]['Id']!=restart_after[role]['Id'] or restart_before[role]['State']['StartedAt']==restart_after[role]['State']['StartedAt'] for role in s.SERVICES):raise RuntimeError('Actual same-owned-component process restart not proved')
   tools(f'export RESTART_PROOF=/state/{name}-restart.json; python3 -B test/baas/nhost_lifecycle.py verify','acknowledged-http-restart-verify')
   dataset=n.evidence()/'canonical-after-full-gate.json';n.reset(dataset)
   current=bench.inputs();bench.validate_correctness({'inputs':frozen,'log_sha256':'original'},current,'original')
   final=s.profile();output.write(b'\nNHOST_FULL_CANONICAL_ORIGINAL42_NODE19_SHARED6_NATIVE7_DEPENDENCY_HTTP_ACK_RESTART_RESET_FREEZE_PASS\n');output.flush()
  finally:closure=n.down()
 if not closure['all_stopped'] or closure['failures']:raise RuntimeError('Full qualification terminal checks failed')
 digest=hashlib.sha256(original.read_bytes()).hexdigest();proof={'inputs':frozen,'log_sha256':digest,'original_contract_checks':42,'node_tests':19,'shared_contract_methods':6,'native_methods':7,'acknowledged_http_write_restart':True,'storage_failure_contract':True,'canonical_data':canonical,'final_profile':final,'restart_before':restart_before,'restart_after':restart_after,'full_stack_clean_stop':closure['full_stack_clean_stop'],'qualification_name':name,'power_loss_certification':False}
 shutil.copyfile(original,s.STATE/'correctness.log')
 with (s.STATE/'correctness-manifest.json').open('x') as stream:stream.write(json.dumps(proof,indent=2)+'\n')
 print('NHOST_FULL_QUALIFICATION_AND_CURRENT_SOURCE_FREEZE_PASS',json.dumps({'original':42,'node':19,'shared':6,'native':7,'http_acknowledged_restart':True,'canonical_data':canonical,'correctness_log_sha256':digest,'full_stack_clean_stop':closure['full_stack_clean_stop']}),flush=True)
 return proof

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--name',default='qualification-v1');args=parser.parse_args();qualify(args.name)
if __name__=='__main__':main()
