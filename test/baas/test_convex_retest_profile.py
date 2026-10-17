"""Explicit new ownership/configuration profile without relaxing legacy budgets."""
import copy
import inspect
import os
from pathlib import Path
import runpy
import json
import subprocess
from types import SimpleNamespace
import tempfile
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import benchmark as common
import convex_profile as profile
import test_convex_budget as legacy_budget

NEW_PROJECT='baas-convex4g-retest-v1'
NEW_SLICE='tdsbaasconvex4gretestv1.slice'


class FreshProfile(unittest.TestCase):
    def fixture(self):
        original=legacy_budget.ConvexPostgresBudget('test_both_native_processes_share_exact_aggregate_budget')
        original.setUp();value=copy.deepcopy(original.value)
        for target in value['targets'].values():
            target['compose_project']=NEW_PROJECT;target['cgroup_parent']=NEW_SLICE
            target['process_cgroup']='0::/'+NEW_SLICE+'/docker-'+target['Id']+'.scope\n'
        return value

    def selected(self,name):
        with patch.dict(os.environ,{'CONVEX_DEPLOYMENT_PROFILE':name}):
            return runpy.run_path(str(ROOT/'scripts/convex_profile.py'))

    def test_only_exact_approved_new_project_gets_a_separate_native_track(self):
        value=None
        try:value=common.deployment_settings('Linux','x86_64',{'BENCHMARK_PROJECT':NEW_PROJECT})
        except ValueError:pass
        self.assertEqual(value,{'project':NEW_PROJECT,'platform':'linux/amd64','track':'vps16-linux-amd64-convex4g-retest-v1'})
        for project in ['baas-convex4g-retest-v2','baas-convex4g-production','baas-convex-random']:
            with self.subTest(project=project),self.assertRaises(ValueError):
                common.deployment_settings('Linux','x86_64',{'BENCHMARK_PROJECT':project})

    def test_new_project_cannot_run_on_mac_or_emulated_arm(self):
        for system,machine in [('Darwin','arm64'),('Darwin','x86_64'),('Linux','aarch64')]:
            error=None
            try:common.deployment_settings(system,machine,{'BENCHMARK_PROJECT':NEW_PROJECT})
            except ValueError as caught:error=caught
            self.assertIsNotNone(error)

    def test_legacy_namespace_and_limits_remain_default(self):
        with patch.dict(os.environ,{},clear=True):value=runpy.run_path(str(ROOT/'scripts/convex_profile.py'))
        self.assertEqual(value['PROJECT'],'baas-convexpg-vps16')
        self.assertEqual(value['SLICE'],'tdsbaasconvexpgvps16.slice')
        self.assertEqual(value['MEMORY'],{'backend':3221225472,'postgres':1073741824})

    def test_explicit_new_selection_changes_both_namespace_and_ports(self):
        value=self.selected('retest-v1')
        self.assertEqual(value['PROJECT'],NEW_PROJECT)
        self.assertEqual(value['SLICE'],NEW_SLICE)
        self.assertEqual(value.get('SITE_PORT'),14100)
        self.assertEqual(value.get('CONTROL_PORT'),13211)
        self.assertEqual(value['MEMORY'],{'backend':3221225472,'postgres':1073741824})

    def test_unknown_profile_does_not_silently_fall_back_to_historical(self):
        error=None
        try:self.selected('unknown-retry')
        except ValueError as caught:error=caught
        self.assertIsNotNone(error)

    def require_new_validator(self):
        self.assertIn('deployment',inspect.signature(profile.validate_stack).parameters,'Experimental validation must be explicitly selected')

    def test_named_profile_accepts_only_its_actual_new_project_and_parent(self):
        self.require_new_validator()
        self.assertTrue(profile.validate_stack(self.fixture(),deployment='retest-v1'))
        old=legacy_budget.ConvexPostgresBudget('test_both_native_processes_share_exact_aggregate_budget');old.setUp()
        with self.assertRaises(RuntimeError):profile.validate_stack(old.value,deployment='retest-v1')
        with self.assertRaises(RuntimeError):profile.validate_stack(self.fixture())

    def test_new_profile_does_not_relax_actual_enforcement_or_accounting(self):
        self.require_new_validator()
        for section,key,bad in [('parent','memory.max','8589934592'),('parent','cpu.max','200000 100000'),('parent','memory.swap.max','1'),('parent','children',[])]:
            value=self.fixture();value[section][key]=bad
            with self.subTest(key=key),self.assertRaises(RuntimeError):profile.validate_stack(value,deployment='retest-v1')
        for role in ['backend','postgres']:
            for key,bad in [('platform','linux/arm64'),('image_manifest_digest','sha256:wrong'),('process_cgroup','0::/system.slice/unrelated.scope')]:
                value=self.fixture();value['targets'][role][key]=bad
                with self.subTest(role=role,key=key),self.assertRaises(RuntimeError):profile.validate_stack(value,deployment='retest-v1')

    def validator(self):
        function=getattr(profile,'validate_backend_environment',None)
        self.assertTrue(callable(function),'Effective allowlisted sizing settings need a fail-closed validator')
        return function

    def test_each_stage_requires_exact_allowlisted_effective_sizing_settings(self):
        validate=self.validator();base={'UDF_CACHE_MAX_SIZE':'0','RUNTIME_WORKER_THREADS':'1'}
        official={name:'16' for name in ['APPLICATION_MAX_CONCURRENT_QUERIES','APPLICATION_MAX_CONCURRENT_MUTATIONS','APPLICATION_MAX_CONCURRENT_V8_ACTIONS','APPLICATION_MAX_CONCURRENT_NODE_ACTIONS']}
        stages={'baseline':{},'official':official,'pg32':dict(official,POSTGRES_MAX_CONNECTIONS='32'),'workers64':dict(official,POSTGRES_MAX_CONNECTIONS='32',MAX_ISOLATE_WORKERS='64'),'http8':dict(official,POSTGRES_MAX_CONNECTIONS='32',MAX_ISOLATE_WORKERS='64',APPLICATION_MAX_CONCURRENT_V8_ACTIONS='8')}
        for stage,expected in stages.items():
            with self.subTest(stage=stage):
                self.assertTrue(validate(base|expected,deployment='retest-v1',stage=stage))
                for key in ['MAX_ISOLATE_WORKERS','POSTGRES_MAX_CONNECTIONS','APPLICATION_MAX_CONCURRENT_V8_ACTIONS']:
                    with self.assertRaises(RuntimeError):validate(base|expected|{key:'999'},deployment='retest-v1',stage=stage)

    def test_cache_native_function_limits_and_unknown_stages_fail_closed(self):
        validate=self.validator();base={'UDF_CACHE_MAX_SIZE':'0','RUNTIME_WORKER_THREADS':'1'}
        for key,bad in [('UDF_CACHE_MAX_SIZE','1'),('RUNTIME_WORKER_THREADS','2'),('TRANSACTION_MAX_READ_SIZE_ROWS','999999'),('DATABASE_UDF_USER_TIMEOUT_SECONDS','99')]:
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(base|{key:bad},deployment='retest-v1',stage='baseline')
        with self.assertRaises(ValueError):validate(base,deployment='retest-v1',stage='unknown')
        with self.assertRaises(ValueError):validate(base,deployment='unknown',stage='baseline')

    def test_real_compose_and_adapter_use_only_new_namespace_ports_and_exact_budgets(self):
        selected=self.selected('retest-v1')
        with patch.dict(sys.modules,{'convex_profile':SimpleNamespace(**selected)}):
            adapter=runpy.run_path(str(ROOT/'scripts/convex_benchmark.py'))
        command=adapter['compose']()
        self.assertIn(str(ROOT/'services/convex/compose.retest-v1.yaml'),command)
        self.assertEqual(command[command.index('-p')+1],NEW_PROJECT)
        value=json.loads(subprocess.check_output(command+['--profile','*','config','--no-env-resolution','--format','json'],text=True))
        self.assertEqual(value['name'],NEW_PROJECT)
        self.assertEqual(set(value['services']),{'backend','postgres','tools','k6'})
        for role,memory in [('backend',3221225472),('postgres',1073741824)]:
            item=value['services'][role]
            self.assertEqual(item['cgroup_parent'],NEW_SLICE)
            self.assertEqual(int(item['mem_limit']),memory)
            self.assertEqual(item['memswap_limit'],item['mem_limit'])
            self.assertEqual(float(item['cpus']),1)
        self.assertEqual({(p['host_ip'],str(p['published']),p['target']) for p in value['services']['backend']['ports']},{('127.0.0.1','14100',3211),('127.0.0.1','13211',3210)})
        self.assertEqual({v['name'] for v in value['volumes'].values()},{NEW_PROJECT+'_data',NEW_PROJECT+'_pgdata'})
        runner=value['services']['k6']
        self.assertEqual(int(runner['mem_limit']),8589934592)
        self.assertEqual(float(runner['cpus']),2)
        self.assertNotIn('cgroup_parent',runner)
        self.assertEqual(set(v['target'] for v in runner['volumes']),{'/tokens.json','/runs','/work/bench'})

    def test_new_profile_cannot_enter_the_historical_unbudgeted_cli(self):
        selected=self.selected('retest-v1')
        with patch.dict(sys.modules,{'convex_profile':SimpleNamespace(**selected)}):
            adapter=runpy.run_path(str(ROOT/'scripts/convex_benchmark.py'))
        calls=[];error=None
        def unbudgeted(*args,**kwargs):calls.append(args);return 'pass','retained/unbudgeted'
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(adapter['main'].__globals__,{'STATE':Path(directory),'attempt':unbudgeted}),patch.object(sys,'argv',['convex_benchmark.py','--vus','3000']):
                try:adapter['main']()
                except BaseException as caught:error=caught
        self.assertIsInstance(error,RuntimeError)
        self.assertEqual(calls,[])

    def test_retest_direct_adapter_rejects_out_of_scope_traffic_before_native_probes(self):
        selected=self.selected('retest-v1')
        with patch.dict(sys.modules,{'convex_profile':SimpleNamespace(**selected)}):
            adapter=runpy.run_path(str(ROOT/'scripts/convex_benchmark.py'))
        calls=[]
        def unexpected_probe():calls.append('headroom');raise AssertionError('Native probes must not precede scope validation')
        with patch.dict(adapter['attempt'].__globals__,{'require_headroom':unexpected_probe}):
            for args in [(2001,'standard',False),(1000,'standard',True),(25,'large',False)]:
                error=None
                try:adapter['attempt'](*args)
                except BaseException as caught:error=caught
                self.assertIsInstance(error,ValueError)
        self.assertEqual(calls,[])

    def test_valid_retest_traffic_cannot_borrow_historical_lifecycle_attestation(self):
        selected=self.selected('retest-v1')
        with patch.dict(sys.modules,{'convex_profile':SimpleNamespace(**selected)}):
            adapter=runpy.run_path(str(ROOT/'scripts/convex_benchmark.py'))
        calls=[];error=None
        def unexpected_probe():calls.append('headroom');raise AssertionError('Historical adapter must not start fresh serving work')
        with patch.dict(adapter['attempt'].__globals__,{'require_headroom':unexpected_probe}):
            try:adapter['attempt'](25,'standard',False)
            except BaseException as caught:error=caught
        self.assertIsInstance(error,RuntimeError)
        self.assertEqual(calls,[])

    def test_legacy_effective_settings_cannot_borrow_new_tuning_authority(self):
        validate=self.validator();base={'UDF_CACHE_MAX_SIZE':'0','RUNTIME_WORKER_THREADS':'1'}
        self.assertTrue(validate(base))
        with self.assertRaises(RuntimeError):validate(base|{'MAX_ISOLATE_WORKERS':'64'})
        with self.assertRaises(ValueError):validate(base,stage='workers64')


if __name__=='__main__':unittest.main(verbosity=2)
