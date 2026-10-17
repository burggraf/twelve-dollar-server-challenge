"""Live observer contract with fake IO; no Docker deployment/SQL workload."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
if importlib.util.find_spec('convex_retest_observer'):
    import convex_retest_observer as observer
else:observer=None
PROJECT='baas-convex4g-retest-v1';SLICE='tdsbaasconvex4gretestv1.slice'


class LiveObserver(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name);self.proc=self.root/'proc';self.groups=self.root/'cgroup';self.out=self.root/'raw-private'
        self.targets={}
        for role,pid,char,memory in [('backend',123,'b',3221225472),('postgres',124,'c',1073741824)]:
            cid=char*64
            self.targets[role]={'Id':cid,'Image':'sha256:'+'d'*64,'RestartCount':0,'Config':{'Labels':{'com.docker.compose.project':PROJECT,'com.docker.compose.service':role},'Env':['JWT_SECRET=private-value-never-export']},'State':{'Pid':pid,'Running':True,'OOMKilled':False,'Paused':False,'Restarting':False,'StartedAt':'retained-start','Health':{'Status':'healthy'}}}
            process=self.proc/str(pid);process.mkdir(parents=True)
            (process/'cgroup').write_text('0::/'+SLICE+'/docker-'+cid+'.scope\n')
            (process/'status').write_text('VmRSS:\t12 kB\nRssAnon:\t8 kB\nRssFile:\t4 kB\nRssShmem:\t0 kB\nVmSwap:\t0 kB\nThreads:\t7\n')
            self.group(self.groups/SLICE/('docker-'+cid+'.scope'),memory)
        self.group(self.groups/SLICE,4294967296)
        self.current=copy.deepcopy(list(self.targets.values()));self.commands=[]
        self.pg={'settings':{'max_connections':'100','reserved_connections':'0','superuser_reserved_connections':'3','fsync':'on','synchronous_commit':'on','full_page_writes':'on','work_mem':'4MB'},'connections':{'total':8,'client_backends':3,'active':1,'idle':2,'idle_in_transaction':0,'waiting':0}}
        self.metrics='\n'.join('convex_local_backend_'+name+' '+str(value) for name,value in {'cache_size_bytes':0,'isolate_pool_max_info':300,'isolate_total_used_heap_size_bytes':4096,'postgres_get_connection_seconds_count':5}.items())+'\n'

    def group(self,path,memory):
        path.mkdir(parents=True,exist_ok=True)
        fields={'cpu.max':'100000 100000','memory.max':str(memory),'memory.swap.max':'0','memory.current':'65536','memory.peak':'131072','memory.events':'low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n','memory.stat':'anon 32768\nfile 32768\n','cpu.stat':'usage_usec 7\nnr_throttled 0\nthrottled_usec 0\n','cpu.pressure':'some avg10=0.00 avg60=0.00 avg300=0.00 total=0\n','memory.pressure':'some avg10=0.00 avg60=0.00 avg300=0.00 total=0\n','io.stat':'','io.pressure':'some avg10=0.00 avg60=0.00 avg300=0.00 total=0\n'}
        for name,value in fields.items():(path/name).write_text(value)

    def create(self):
        factory=getattr(observer,'Observer',None)
        self.assertTrue(callable(factory),'Missing live owned native observation behavior')
        def capture(argv,**kwargs):
            self.commands.append((argv,kwargs))
            if argv[:2]==['docker','inspect']:return json.dumps(self.current)
            if argv[:2]==['docker','exec']:return json.dumps(self.pg)
            raise AssertionError('Unexpected/mutating observer command')
        return factory(self.out,{'project':PROJECT,'slice':SLICE,'targets':self.targets},capture=capture,fetch=lambda:self.metrics.encode(),proc=self.proc,cgroups=self.groups)

    def test_complete_sample_preserves_raw_private_inputs_and_exposes_only_numeric_views(self):
        value=self.create().sample()
        self.assertEqual(value['processes']['backend']['rss_bytes'],12288)
        self.assertEqual(value['postgres']['connections']['client_backends'],3)
        self.assertEqual(value['metrics']['convex_local_backend_isolate_total_used_heap_size_bytes'],[4096.])
        self.assertNotIn('private-value-never-export',json.dumps(value))
        self.assertTrue(self.out.is_dir());self.assertTrue(list(self.out.iterdir()))
        self.assertTrue(value['raw_sha256'])

    def test_all_parent_and_child_limits_are_checked_on_every_sample(self):
        instance=self.create();(self.groups/SLICE/'memory.max').write_text('8589934592')
        with self.assertRaises(RuntimeError):instance.sample()

    def test_child_cgroup_membership_cannot_change_or_escape_owned_parent(self):
        instance=self.create();(self.proc/'123/cgroup').write_text('0::/unrelated.slice/docker-other.scope\n')
        with self.assertRaises(RuntimeError):instance.sample()

    def test_either_required_runtime_exit_oom_restart_or_unhealthy_state_stops_observation(self):
        instance=self.create()
        for key,bad in [('Running',False),('OOMKilled',True),('Paused',True),('Restarting',True),('Pid',999)]:
            self.current=copy.deepcopy(list(self.targets.values()));self.current[0]['State'][key]=bad
            with self.subTest(key=key),self.assertRaises(RuntimeError):instance.sample()

    def test_replaced_container_or_image_is_not_adopted(self):
        instance=self.create();self.current[0]['Id']='e'*64
        with self.assertRaises(RuntimeError):instance.sample()

    def test_parent_oom_is_a_stop_even_if_the_backend_pid_is_still_running(self):
        instance=self.create();(self.groups/SLICE/'memory.events').write_text('oom 1\noom_kill 0\noom_group_kill 0\n')
        with self.assertRaises(RuntimeError):instance.sample()

    def test_query_result_cache_must_remain_zero_during_observation(self):
        instance=self.create();self.metrics=self.metrics.replace('cache_size_bytes 0','cache_size_bytes 64')
        with self.assertRaises(RuntimeError):instance.sample()

    def test_unavailable_or_nonfinite_metric_is_not_silently_filled_with_zero(self):
        instance=self.create();self.metrics=''
        with self.assertRaises(RuntimeError):instance.sample()

    def test_missing_pg_counts_or_weakened_durability_cannot_support_headroom_claim(self):
        instance=self.create();self.pg['settings']['fsync']='off'
        with self.assertRaises(RuntimeError):instance.sample()
        self.pg['settings']['fsync']='on';del self.pg['connections']['active']
        with self.assertRaises(RuntimeError):instance.sample()

    def test_metadata_sql_and_exec_arguments_never_include_serving_queries_or_secret_values(self):
        self.create().sample()
        argv,kwargs=next(pair for pair in self.commands if pair[0][:2]==['docker','exec'])
        encoded=json.dumps(argv)
        self.assertNotIn('private-value-never-export',encoded)
        sql=kwargs.get('input','')
        self.assertIn('pg_stat_activity',sql);self.assertIn('current_setting',sql)
        self.assertNotIn('FROM posts',sql);self.assertNotIn('FROM likes',sql)

    def test_raw_sample_outputs_are_exclusive_and_repeated_observations_are_separate(self):
        instance=self.create();one=instance.sample();two=instance.sample()
        self.assertNotEqual(one['sample_index'],two['sample_index'])
        self.assertEqual(one['raw_sha256']['metrics'],two['raw_sha256']['metrics'])
        self.assertGreaterEqual(len(list(self.out.iterdir())),6)

    def test_required_proc_or_kernel_evidence_missing_is_a_failed_monitor_not_a_zero(self):
        instance=self.create();(self.proc/'123/status').unlink()
        with self.assertRaises(RuntimeError):instance.sample()


if __name__=='__main__':unittest.main(verbosity=2)
