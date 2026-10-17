"""The owner waived only known requested shutdown139, never serving crashes/OOM."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
if importlib.util.find_spec('convex_retest_safety'):
    import convex_retest_safety as safety
else:safety=None


class ServingPathSafety(unittest.TestCase):
    def function(self,name):
        function=getattr(safety,name,None)
        self.assertTrue(callable(function),'Missing versioned retest safety behavior: '+name)
        return function

    def fixture(self):
        intent={'project':'baas-convex4g-retest-v1','ordinal':1,'container_id':'a'*64,'image_id':'sha256:'+'b'*64,
                'signal':'SIGINT','predeclared':True,'was_running':True,'known_shutdown_exception_approved':True}
        observed={'project':intent['project'],'container_id':intent['container_id'],'image_id':intent['image_id'],
                  'stop_request_issued':True,'running':False,'oom_killed':False,'exit_code':139,
                  'known_teardown_evidence_matches':True,'unexpected_serving_failure':False,
                  'parent_oom_before':{'oom':0,'oom_kill':0,'oom_group_kill':0},
                  'parent_oom_after':{'oom':0,'oom_kill':0,'oom_group_kill':0}}
        return intent,observed

    def test_known_requested_sigint139_is_failed_non_gating_not_clean(self):
        intent,observed=self.fixture();value=self.function('planned_shutdown')(intent,observed)
        self.assertEqual(value['clean_shutdown'],'FAILED')
        self.assertEqual(value['scope'],'serving-path-only')
        self.assertTrue(value['planned_start_permitted'])
        self.assertTrue(value['acknowledged_data_reverification_required'])

    def test_a_clean_exit_remains_separate_from_the_historical_failure(self):
        intent,observed=self.fixture();observed.update(exit_code=0,known_teardown_evidence_matches=False)
        value=self.function('planned_shutdown')(intent,observed)
        self.assertEqual(value['clean_shutdown'],'PASS')
        self.assertTrue(value['acknowledged_data_reverification_required'])

    def test_only_the_new_namespace_and_exact_owned_image_container_are_permitted(self):
        check=self.function('planned_shutdown');intent,observed=self.fixture()
        for key,bad in [('project','baas-convexpg-vps16'),('container_id','c'*64),('image_id','sha256:'+'d'*64)]:
            bad_observed=observed|{key:bad}
            with self.subTest(field=key),self.assertRaises(RuntimeError):check(intent,bad_observed)
        with self.assertRaises(RuntimeError):check(intent|{'project':'baas-convexpg-vps16'},observed|{'project':'baas-convexpg-vps16'})

    def test_eight_transition_ceiling_is_not_a_crash_retry_loop(self):
        check=self.function('planned_shutdown');intent,observed=self.fixture()
        self.assertTrue(check(intent|{'ordinal':8},observed)['planned_start_permitted'])
        for ordinal in [0,9,True,None]:
            with self.subTest(ordinal=ordinal),self.assertRaises(RuntimeError):check(intent|{'ordinal':ordinal},observed)

    def test_no_automatic_revival_without_exact_predeclared_requested_stop(self):
        check=self.function('planned_shutdown');intent,observed=self.fixture()
        for key,bad in [('predeclared',False),('was_running',False),('signal','SIGTERM'),('known_shutdown_exception_approved',False)]:
            with self.subTest(key=key),self.assertRaises(RuntimeError):check(intent|{key:bad},observed)
        with self.assertRaises(RuntimeError):check(intent,observed|{'stop_request_issued':False})

    def test_unexpected_serving_failure_oom_or_unmatched_shutdown_still_stop(self):
        check=self.function('planned_shutdown');intent,observed=self.fixture()
        for key,bad in [('unexpected_serving_failure',True),('oom_killed',True),('running',True),('exit_code',137),('exit_code',1),('known_teardown_evidence_matches',False)]:
            with self.subTest(key=key,bad=bad),self.assertRaises(RuntimeError):check(intent,observed|{key:bad})

    def test_parent_oom_events_cannot_be_hidden_by_a_non_oom_container_exit(self):
        check=self.function('planned_shutdown');intent,observed=self.fixture()
        for key in ['oom','oom_kill','oom_group_kill']:
            value=copy.deepcopy(observed);value['parent_oom_after'][key]=1
            with self.subTest(event=key),self.assertRaises(RuntimeError):check(intent,value)

    def test_missing_or_wrongly_typed_evidence_fails_closed(self):
        check=self.function('planned_shutdown');intent,observed=self.fixture()
        for key in observed:
            value=dict(observed);del value[key]
            with self.subTest(missing=key),self.assertRaises(RuntimeError):check(intent,value)
        for key,bad in [('oom_killed',None),('exit_code',False),('running',0)]:
            with self.subTest(key=key),self.assertRaises(RuntimeError):check(intent,observed|{key:bad})

    def test_only_approved_low_smokes_and_bounded_full_loads_are_allowed(self):
        check=self.function('validate_attempt')
        for vus in [25,100]:self.assertTrue(check(vus,'standard',True))
        for vus in [1,5,10,25,50,100,200,400,800,1600,2000]:self.assertTrue(check(vus,'standard',False))
        for vus,tier,smoke in [(2001,'standard',False),(1000,'standard',True),(1,'standard',True),(25,'large',False),(True,'standard',False)]:
            with self.subTest(vus=vus,tier=tier,smoke=smoke),self.assertRaises(ValueError):check(vus,tier,smoke)

    def recovery(self,before=None,after=None):
        function=self.function('setup_recovery_targets')
        def item(role):
            memory=3221225472 if role=='backend' else 1073741824
            return {'Id':('a' if role=='backend' else 'b')*64,'Image':'sha256:'+'c'*64,'RestartCount':0,'Config':{'Labels':{'com.docker.compose.project':'baas-convex4g-retest-v1','com.docker.compose.service':role},'Env':['PRIVATE_VALUE=retained-private-input']},'HostConfig':{'CgroupParent':'tdsbaasconvex4gretestv1.slice','NanoCpus':1000000000,'Memory':memory,'MemorySwap':memory},'Mounts':[{'Type':'volume','Name':'baas-convex4g-retest-v1_'+('data' if role=='backend' else 'pgdata'),'RW':True}],'State':{'Running':False,'Pid':0,'ExitCode':0,'OOMKilled':False,'Paused':False,'Restarting':False,'Dead':False}}
        original={role:item(role) for role in ('backend','postgres')}
        prior=original if before is None else before
        current=__import__('copy').deepcopy(original)
        if after:after(current)
        return function(prior,current)

    def test_setup_recovery_uses_exact_retained_cleanly_stopped_owned_ids(self):
        self.assertEqual(self.recovery(),{'backend':'a'*64,'postgres':'b'*64})

    def test_setup_recovery_never_adopts_a_replaced_container_or_image(self):
        for field in ('Id','Image'):
            with self.subTest(field=field),self.assertRaises(RuntimeError):self.recovery(after=lambda rows:rows['backend'].update({field:'d'*64}))

    def test_setup_recovery_refuses_running_oom_or_failed_exit_instead_of_reviving(self):
        for field,value in (('Running',True),('OOMKilled',True),('ExitCode',139),('Pid',12),('Paused',True)):
            with self.subTest(field=field),self.assertRaises(RuntimeError):self.recovery(after=lambda rows:rows['backend']['State'].update({field:value}))

    def test_setup_recovery_refuses_secret_or_command_configuration_drift_without_echo(self):
        with self.assertRaises(RuntimeError) as caught:self.recovery(after=lambda rows:rows['backend']['Config'].update(Env=['PRIVATE_VALUE=changed-private-input']))
        self.assertNotIn('changed-private-input',str(caught.exception))

    def test_setup_recovery_refuses_volume_or_resource_or_parent_changes(self):
        for mutate in (lambda rows:rows['backend']['Mounts'][0].update(Name='unrelated'),lambda rows:rows['backend']['HostConfig'].update(Memory=4),lambda rows:rows['backend']['HostConfig'].update(CgroupParent='unrelated.slice')):
            with self.subTest(change=mutate),self.assertRaises(RuntimeError):self.recovery(after=mutate)

    def test_setup_recovery_refuses_restart_count_and_ownership_label_drift(self):
        with self.assertRaises(RuntimeError):self.recovery(after=lambda rows:rows['postgres'].update(RestartCount=1))
        with self.assertRaises(RuntimeError):self.recovery(after=lambda rows:rows['backend']['Config']['Labels'].update({'com.docker.compose.project':'unrelated'}))

    def match(self,message='traps: isolate[202] general protection fault ip:0 error:0',tids=None,log=None):
        function=self.function('known_teardown_matches')
        if log is None:log=b'A Tokio 1.x context was found, but it is being shutdown.'
        return function(log,json.dumps({'MESSAGE':message}).encode(),owned_tids={101,202} if tids is None else tids)

    def test_known_fault_matches_a_preobserved_owned_isolate_tid_not_only_pid1(self):
        self.assertTrue(self.match())

    def test_foreign_isolate_tid_is_not_evidence_for_the_owned_backend(self):
        self.assertFalse(self.match(tids={101}))

    def test_fault_without_the_known_native_teardown_panic_does_not_get_a_waiver(self):
        self.assertFalse(self.match(log=b'other unexpected failure'))

    def test_non_isolate_fault_or_different_fault_kind_is_unmatched(self):
        self.assertFalse(self.match(message='traps: unrelated[202] general protection fault'))
        self.assertFalse(self.match(message='isolate[202]: segfault at0'))

    def test_malformed_kernel_or_unknown_owned_thread_inventory_fails_closed(self):
        check=self.function('known_teardown_matches')
        for tids in [set(),{True},{0},{'202'},None]:
            with self.subTest(tids=tids):self.assertFalse(check(b'A Tokio 1.x context was found, but it is being shutdown.',b'not json',owned_tids=tids))

    def test_kernel_pid_substring_is_not_an_exact_owned_tid_match(self):
        self.assertFalse(self.match(message='traps: isolate[1202] general protection fault',tids={202}))


if __name__=='__main__':unittest.main(verbosity=2)
