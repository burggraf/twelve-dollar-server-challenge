"""Numeric native diagnostics: no labels, bodies, credentials or fake memory sums."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
if importlib.util.find_spec('convex_retest_metrics'):
    import convex_retest_metrics as metrics
else:metrics=None
PREFIX='convex_local_backend_'


def sample():
    return '\n'.join(PREFIX+name+' '+str(value) for name,value in {
        'cache_size_bytes':0,'isolate_pool_max_info':300,
        'isolate_total_used_heap_size_bytes':4096,
        'postgres_get_connection_seconds_count':5,
    }.items())+'\n'


class NativeDiagnostics(unittest.TestCase):
    def function(self,name):
        function=getattr(metrics,name,None)
        self.assertTrue(callable(function),'Missing numeric native diagnostic behavior: '+name)
        return function

    def test_only_exact_pinned_metric_namespace_and_allowlisted_families_are_kept(self):
        parse=self.function('parse_metrics')
        value=parse(sample()+'another_backend_isolate_pool_max_info 999\n'+PREFIX+'unrelated_secret_metric 123\n')
        self.assertEqual(set(value),{PREFIX+name for name in ['cache_size_bytes','isolate_pool_max_info','isolate_total_used_heap_size_bytes','postgres_get_connection_seconds_count']})
        self.assertEqual(value[PREFIX+'isolate_pool_max_info'],[300.0])

    def test_multiple_series_are_not_falsely_treated_as_one_worker_pool(self):
        parse=self.function('parse_metrics')
        value=parse(sample()+PREFIX+'isolate_pool_max_info{pool_name="second"} 64\n')
        self.assertEqual(value[PREFIX+'isolate_pool_max_info'],[300.0,64.0])

    def test_all_labels_are_stripped_including_client_identifiers_and_escapes(self):
        parse=self.function('parse_metrics')
        value=parse(sample()+PREFIX+'isolate_pool_running_count_info{client_id="private-label-data",pool_name="funrun"} 3\n')
        encoded=json.dumps(value)
        self.assertNotIn('private-label-data',encoded)
        self.assertNotIn('funrun',encoded)
        self.assertEqual(value[PREFIX+'isolate_pool_running_count_info'],[3.0])

    def test_missing_required_family_is_not_silent_zero(self):
        parse=self.function('parse_metrics')
        for name in ['cache_size_bytes','isolate_pool_max_info','isolate_total_used_heap_size_bytes','postgres_get_connection_seconds_count']:
            text='\n'.join(line for line in sample().splitlines() if not line.startswith(PREFIX+name+' '))
            with self.subTest(name=name),self.assertRaises(RuntimeError):parse(text)

    def test_malformed_or_nonfinite_selected_samples_fail_without_echoing_raw_content(self):
        parse=self.function('parse_metrics')
        for bad in ['NaN','+Inf','-1','not-a-number']:
            with self.subTest(bad=bad),self.assertRaises(RuntimeError) as caught:
                parse(sample()+PREFIX+'udf_queue_seconds_sum '+bad+'\n')
            self.assertNotIn('not-a-number',str(caught.exception))

    def test_histogram_sum_and_count_remain_separate_from_instantaneous_memory_gauges(self):
        parse=self.function('parse_metrics')
        value=parse(sample()+PREFIX+'isolate_used_heap_size_bytes_sum 1048576\n'+PREFIX+'isolate_used_heap_size_bytes_count 12\n')
        self.assertEqual(value[PREFIX+'isolate_used_heap_size_bytes_sum'],[1048576.0])
        self.assertEqual(value[PREFIX+'isolate_used_heap_size_bytes_count'],[12.0])
        self.assertEqual(value[PREFIX+'isolate_total_used_heap_size_bytes'],[4096.0])

    def test_pg_connection_trial_accounts_for_all_pools_other_clients_and_maintenance(self):
        check=self.function('connection_headroom')
        settings={'max_connections':'100','reserved_connections':'0','superuser_reserved_connections':'3','fsync':'on','synchronous_commit':'on','full_page_writes':'on'}
        value=check(settings,pool_count=2,pool_limit=32,other_clients=4,maintenance_reserve=8)
        self.assertEqual(value['ordinary_usable_connections'],97)
        self.assertEqual(value['proposed_pool_connection_ceiling'],64)
        self.assertEqual(value['spare_after_pools_other_clients_and_maintenance'],21)
        with self.assertRaises(RuntimeError):check(settings,pool_count=3,pool_limit=32,other_clients=4,maintenance_reserve=8)

    def test_unknown_counts_and_weakened_pg_durability_do_not_authorize_pool_trial(self):
        check=self.function('connection_headroom')
        settings={'max_connections':'100','reserved_connections':'0','superuser_reserved_connections':'3','fsync':'on','synchronous_commit':'on','full_page_writes':'on'}
        for field,bad in [('pool_count',None),('pool_count',True),('pool_count',0),('other_clients',-1)]:
            kwargs={'pool_count':1,'pool_limit':32,'other_clients':0,'maintenance_reserve':8};kwargs[field]=bad
            with self.subTest(field=field,bad=bad),self.assertRaises((ValueError,RuntimeError)):check(settings,**kwargs)
        for name in ['fsync','synchronous_commit','full_page_writes']:
            with self.subTest(setting=name),self.assertRaises(RuntimeError):check(settings|{name:'off'},pool_count=1,pool_limit=32,other_clients=0,maintenance_reserve=8)

    def startup(self,texts,*,limit=120,late=False,broken=False):
        function=self.function('startup_metrics')
        elapsed=[0.0];raw=[];calls=[];waiting=[]
        def verify():
            calls.append('verify')
            if broken:raise RuntimeError('Runtime changed')
        def fetch():
            calls.append('fetch')
            if late:elapsed[0]=121
            return texts.pop(0) if len(texts)>1 else texts[0]
        def wait(seconds):waiting.append(seconds);elapsed[0]+=seconds
        value=function(fetch,verify,raw.append,clock=lambda:elapsed[0],wait=wait,limit=limit)
        return value,raw,calls,waiting

    def cold(self):
        return '\n'.join(line for line in sample().splitlines() if 'isolate_total_used_heap_size_bytes' not in line).encode()

    def test_startup_observes_actual_delayed_aggregate_heap_gauge_without_zero_filling(self):
        value,raw,calls,waiting=self.startup([self.cold(),sample().encode()])
        self.assertEqual(value[PREFIX+'isolate_total_used_heap_size_bytes'],[4096.0]);self.assertEqual(len(raw),2)
        self.assertEqual(calls,['verify','fetch','verify','fetch']);self.assertEqual(waiting,[3])

    def test_startup_ready_metrics_need_no_wait_or_repeated_requests(self):
        _,raw,calls,waiting=self.startup([sample().encode()]);self.assertEqual(len(raw),1);self.assertFalse(waiting)

    def test_startup_missing_gauge_never_becomes_synthetic_zero_after_deadline(self):
        with self.assertRaises(RuntimeError):self.startup([self.cold()])

    def test_startup_does_not_wait_for_other_missing_monitoring_families(self):
        text=self.cold().replace((PREFIX+'cache_size_bytes 0').encode(),b'')
        with self.assertRaises(RuntimeError):self.startup([text,sample().encode()])

    def test_startup_never_retries_malformed_nonfinite_or_negative_metrics(self):
        for bad in (b'NaN',b'-1',b'not-a-number'):
            with self.subTest(bad=bad),self.assertRaises(RuntimeError):self.startup([self.cold()+b'\n'+(PREFIX+'udf_queue_seconds_sum ').encode()+bad,sample().encode()])

    def test_startup_runtime_change_is_not_a_readiness_retry(self):
        with self.assertRaisesRegex(RuntimeError,'Runtime changed'):self.startup([self.cold(),sample().encode()],broken=True)

    def test_startup_cannot_accept_valid_metrics_returned_after_deadline(self):
        with self.assertRaises(RuntimeError):self.startup([sample().encode()],late=True)

    def test_startup_observation_ceiling_is_bounded_to_120_seconds(self):
        with self.assertRaises((ValueError,RuntimeError)):self.startup([sample().encode()],limit=121)

    def test_proc_memory_summary_never_reads_or_emits_arguments_environment_or_mapped_paths(self):
        read=self.function('process_memory')
        with tempfile.TemporaryDirectory() as directory:
            proc=Path(directory);(proc/'123').mkdir()
            (proc/'123/status').write_text('Name:\tbackend\nVmRSS:\t12 kB\nRssAnon:\t8 kB\nRssFile:\t4 kB\nRssShmem:\t0 kB\nVmSwap:\t0 kB\nThreads:\t7\n')
            (proc/'123/cmdline').write_text('private-argv-never-read')
            (proc/'123/environ').write_text('private-env-never-read')
            value=read(123,proc=proc)
            self.assertEqual(value,{'pid':123,'rss_bytes':12288,'rss_anon_bytes':8192,'rss_file_bytes':4096,'rss_shmem_bytes':0,'swap_bytes':0,'threads':7})
            self.assertNotIn('private-',json.dumps(value))

    def test_missing_or_malformed_proc_memory_is_an_invalid_observation(self):
        read=self.function('process_memory')
        with tempfile.TemporaryDirectory() as directory:
            proc=Path(directory);(proc/'123').mkdir();(proc/'123/status').write_text('VmRSS: missing\n')
            with self.assertRaises(RuntimeError):read(123,proc=proc)
            with self.assertRaises(RuntimeError):read(999,proc=proc)


if __name__=='__main__':unittest.main(verbosity=2)
